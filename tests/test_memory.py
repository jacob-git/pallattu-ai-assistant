from pallattu_ai_assistant.memory import (
    CompositeToolRegistry,
    MemoryToolAdapter,
    SQLiteMemoryAdapter,
)


class FakeTools:
    def definitions(self):
        return [
            {
                "type": "function",
                "name": "ping",
                "parameters": {"type": "object", "properties": {}, "required": []},
            }
        ]

    def execute(self, name, arguments):
        if name == "ping":
            return {"ok": True, "pong": True}
        return {"ok": False}


def test_conversation_history_survives_new_adapter_instance(tmp_path):
    path = tmp_path / "memory.sqlite3"
    memory = SQLiteMemoryAdapter(path)
    memory.append_message("user", "My name is Jacob")
    memory.append_message("assistant", "Nice to meet you")

    reopened = SQLiteMemoryAdapter(path)

    assert reopened.recent_messages() == [
        {"role": "user", "content": "My name is Jacob"},
        {"role": "assistant", "content": "Nice to meet you"},
    ]


def test_long_term_memory_can_be_saved_and_retrieved(tmp_path):
    memory = SQLiteMemoryAdapter(tmp_path / "memory.sqlite3")

    result = memory.remember("My preferred assistant volume is high")

    assert result["ok"] is True
    assert memory.search("assistant volume") == ["My preferred assistant volume is high"]


def test_memory_rejects_credentials(tmp_path):
    memory = SQLiteMemoryAdapter(tmp_path / "memory.sqlite3")

    result = memory.remember("My API key is abc123")

    assert result["ok"] is False
    assert memory.list_memories() == []


def test_memory_can_be_forgotten(tmp_path):
    memory = SQLiteMemoryAdapter(tmp_path / "memory.sqlite3")
    memory.remember("My preferred wake phrase is Hey Pallattu")

    result = memory.forget("wake phrase")

    assert result == {"ok": True, "deleted": 1}
    assert memory.list_memories() == []


def test_memory_tools_are_typed_and_composable(tmp_path):
    memory = SQLiteMemoryAdapter(tmp_path / "memory.sqlite3")
    tools = CompositeToolRegistry(FakeTools(), MemoryToolAdapter(memory))

    names = {definition["name"] for definition in tools.definitions()}
    remember_result = tools.execute("remember_fact", {"fact": "I prefer concise answers"})

    assert names == {"ping", "remember_fact", "forget_memory", "list_memories"}
    assert remember_result["ok"] is True
    assert tools.execute("ping", {}) == {"ok": True, "pong": True}
    assert tools.execute("list_memories", {}) == {
        "ok": True,
        "memories": ["I prefer concise answers"],
    }
