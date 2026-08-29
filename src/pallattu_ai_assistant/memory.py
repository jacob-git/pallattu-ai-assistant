from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from pallattu_ai_assistant.ports import MemoryPort, ToolPort

_TOKEN_PATTERN = re.compile(r"[a-z0-9']+")
_SENSITIVE_MARKERS = (
    "api key",
    "password",
    "passcode",
    "secret",
    "access token",
    "refresh token",
    "private key",
)


class SQLiteMemoryAdapter:
    """Local persistent conversation history and explicit long-term memories."""

    def __init__(self, path: Path, max_conversation_messages: int = 500) -> None:
        self.path = path.expanduser()
        self.max_conversation_messages = max(20, max_conversation_messages)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS long_term_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    normalized TEXT NOT NULL UNIQUE,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def recent_messages(self, limit: int = 8) -> list[dict[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT role, content
                FROM conversation_messages
                ORDER BY id DESC
                LIMIT ?
                """,
                (max(0, limit),),
            ).fetchall()
        return [
            {"role": str(row["role"]), "content": str(row["content"])}
            for row in reversed(rows)
        ]

    def append_message(self, role: str, content: str) -> None:
        if role not in {"user", "assistant"} or not content.strip():
            return
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO conversation_messages(role, content) VALUES (?, ?)",
                (role, content.strip()),
            )
        self.prune_conversations()

    def prune_conversations(self, max_messages: int | None = None) -> int:
        keep = max(20, max_messages or self.max_conversation_messages)
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM conversation_messages
                WHERE id NOT IN (
                    SELECT id FROM conversation_messages ORDER BY id DESC LIMIT ?
                )
                """,
                (keep,),
            )
        return int(cursor.rowcount)

    def clear_conversations(self) -> int:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM conversation_messages")
        return int(cursor.rowcount)

    def clear_memories(self) -> int:
        with self._connect() as connection:
            cursor = connection.execute("DELETE FROM long_term_memories")
        return int(cursor.rowcount)

    def stats(self) -> dict[str, Any]:
        with self._connect() as connection:
            conversation_count = int(
                connection.execute("SELECT COUNT(*) FROM conversation_messages").fetchone()[0]
            )
            memory_count = int(
                connection.execute("SELECT COUNT(*) FROM long_term_memories").fetchone()[0]
            )
        return {
            "conversation_messages": conversation_count,
            "long_term_memories": memory_count,
            "max_conversation_messages": self.max_conversation_messages,
            "database": str(self.path),
        }

    def search(self, query: str, limit: int = 5) -> list[str]:
        query_tokens = _tokens(query)
        if not query_tokens:
            return []

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT content
                FROM long_term_memories
                ORDER BY updated_at DESC, id DESC
                LIMIT 250
                """
            ).fetchall()

        scored: list[tuple[int, str]] = []
        lowered_query = query.lower()
        for row in rows:
            content = str(row["content"])
            content_tokens = _tokens(content)
            overlap = len(query_tokens & content_tokens)
            phrase_bonus = 3 if lowered_query in content.lower() or content.lower() in lowered_query else 0
            score = overlap + phrase_bonus
            if score > 0:
                scored.append((score, content))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [content for _, content in scored[: max(0, limit)]]

    def remember(self, fact: str) -> dict[str, Any]:
        cleaned = " ".join(fact.split()).strip()
        if not cleaned:
            return {"ok": False, "error": "Memory cannot be empty."}
        if _looks_sensitive(cleaned):
            return {
                "ok": False,
                "error": "Sensitive credentials and secrets are not stored in long-term memory.",
            }

        normalized = cleaned.casefold()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO long_term_memories(normalized, content)
                VALUES (?, ?)
                ON CONFLICT(normalized) DO UPDATE SET
                    content = excluded.content,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (normalized, cleaned),
            )
        return {"ok": True, "memory": cleaned}

    def forget(self, query: str) -> dict[str, Any]:
        cleaned = query.strip()
        if not cleaned:
            return {"ok": False, "error": "A memory description is required."}

        pattern = f"%{cleaned.casefold()}%"
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM long_term_memories WHERE lower(content) LIKE ?",
                (pattern,),
            )
        return {"ok": True, "deleted": int(cursor.rowcount)}

    def list_memories(self, limit: int = 20) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT content
                FROM long_term_memories
                ORDER BY updated_at DESC, id DESC
                LIMIT ?
                """,
                (max(0, limit),),
            ).fetchall()
        return [str(row["content"]) for row in rows]


class MemoryToolAdapter:
    """Typed tool surface for explicit long-term memory operations."""

    def __init__(self, memory: MemoryPort) -> None:
        self.memory = memory

    def definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "name": "remember_fact",
                "description": (
                    "Save a stable fact or preference for future conversations. Use when the user "
                    "explicitly asks you to remember something or clearly asks to save a preference."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "fact": {"type": "string", "description": "The fact or preference to remember."}
                    },
                    "required": ["fact"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
            {
                "type": "function",
                "name": "forget_memory",
                "description": "Delete long-term memories matching the user's description.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Memory text or topic to forget."}
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
            {
                "type": "function",
                "name": "list_memories",
                "description": "List the facts and preferences stored in long-term memory.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False,
                },
                "strict": True,
            },
        ]

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "remember_fact":
            return self.memory.remember(str(arguments.get("fact", "")))
        if name == "forget_memory":
            return self.memory.forget(str(arguments.get("query", "")))
        if name == "list_memories":
            return {"ok": True, "memories": self.memory.list_memories()}
        return {"ok": False, "error": f"Unknown memory tool: {name}"}


class CompositeToolRegistry:
    """Combine typed tool adapters without coupling the model to implementations."""

    def __init__(self, *registries: ToolPort) -> None:
        self.registries = registries

    def definitions(self) -> list[dict[str, Any]]:
        definitions: list[dict[str, Any]] = []
        for registry in self.registries:
            definitions.extend(registry.definitions())
        return definitions

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        for registry in self.registries:
            names = {definition["name"] for definition in registry.definitions()}
            if name in names:
                return registry.execute(name, arguments)
        return {"ok": False, "error": f"Unknown tool: {name}"}


def _tokens(value: str) -> set[str]:
    return {token for token in _TOKEN_PATTERN.findall(value.casefold()) if len(token) > 2}


def _looks_sensitive(value: str) -> bool:
    lowered = value.casefold()
    return any(marker in lowered for marker in _SENSITIVE_MARKERS)
