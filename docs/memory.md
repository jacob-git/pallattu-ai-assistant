# Persistent local memory

Pallattu AI Assistant `0.6.0` adds a local-first memory boundary that works the same way on macOS and Raspberry Pi.

## What persists

Two kinds of memory are stored in SQLite:

1. **Recent conversation history** — user and assistant turns are written automatically so context can survive an app restart. Only the most recent turns are sent back to the model for normal conversation context.
2. **Long-term facts and preferences** — stored explicitly through typed memory tools and retrieved only when relevant to the current request.

The default database is:

```text
~/.pallattu-ai-assistant/memory.sqlite3
```

Override it with:

```text
PALLATTU_MEMORY_PATH=/your/local/path/memory.sqlite3
```

No cloud database or separate memory API is required.

## Voice examples

```text
Hey Jarvis
Remember that I prefer concise answers.
```

Later, even after restarting the app:

```text
Hey Jarvis
How do I prefer you to answer me?
```

You can inspect stored long-term memories:

```text
Hey Jarvis
What do you remember about me?
```

And remove one:

```text
Hey Jarvis
Forget that I prefer concise answers.
```

## Privacy and safety

- Memory stays in the local SQLite file unless a relevant memory is included as context in an OpenAI request needed to answer the current question.
- Long-term memory is not an arbitrary database interface. The model can only use typed operations: `remember_fact`, `forget_memory`, and `list_memories`.
- Credentials and obvious secrets such as passwords, API keys, access tokens, and private keys are rejected from long-term memory.
- Conversation history and long-term memories are separate tables.
- The database file should remain private and should never be committed to Git.

## Architecture

```text
Voice request
    |
    v
OpenAI voice adapter
    |
    +--> MemoryPort.recent_messages()
    |
    +--> MemoryPort.search(current request)
    |
    v
LLM + typed tools
    |
    +--> remember_fact / forget_memory / list_memories
    |
    v
SQLiteMemoryAdapter
    |
    v
~/.pallattu-ai-assistant/memory.sqlite3
```

The application and model depend on the `MemoryPort` contract rather than SQLite itself, so another storage implementation can be introduced later without changing the assistant core.
