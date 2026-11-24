---
name: forever-brain
description: Use Forever Brain MCP for local-first, AES-256-GCM encrypted, source-attributed, bi-temporal agent memory. Teaches agents when to load startup context, what durable facts to remember, how to correct outdated memories without stale ghosts, and what noisy/ephemeral clutter to keep out of the vault.
---

# Forever Brain Memory Discipline

You have access to the **Forever Brain MCP** server (`forever-brain-mcp`), a local-first, encrypted, bi-temporal memory vault. Use it to maintain sharp, high-signal continuity across sessions without polluting memory with junk.

## Configure a stdio MCP client

After version 0.1.1 is available on PyPI, configure the client to launch `uvx` with the argument `forever-brain-mcp==0.1.1`. Clients that use the `mcpServers` JSON format can use this example.

```json
{
  "mcpServers": {
    "forever-brain": {
      "command": "uvx",
      "args": ["forever-brain-mcp==0.1.1"],
      "env": {
        "FOREVER_BRAIN_DIR": "~/.forever-brain/vault"
      }
    }
  }
}
```

- **Keyfile mode (default):** Auto-creates `0700` directory, `0600` `vault.key`, and encrypted `vault.enc.json`.
- **Passphrase mode (optional):** Set `FOREVER_BRAIN_PASSPHRASE` to derive the AES-256-GCM key via PBKDF2-HMAC-SHA256 (`vault.salt`).
- **Backups:** Stop the server before copying. Keyfile mode requires `vault.enc.json` + `vault.key`; passphrase mode requires `vault.enc.json` + `vault.salt` + your passphrase.

---

## Core Operating Loop

### 1. Start Every Session with Bounded Context
Call `brain_startup(limit=12)` at the beginning of a session before asking the user to repeat standing preferences, architecture decisions, or active priorities.

### 2. Recall Active Truth Before Guessing
When a question touches prior decisions, project setup, or user preferences, call `brain_recall(query=...)`:
- Default recall returns **only active, non-superseded truth** (no stale ghosts).
- Use `as_of="YYYY-MM-DDTHH:MM:SSZ"` to recall what had been recorded by that time.
- Use `brain_recall(query=..., include_history=True)` or `brain_trace(record_id)` only when you explicitly need the revision chain.

### 3. Correct — Never Duplicate — Changed Facts
When a decision, deadline, preference, or architecture changes:
- **DO** call `brain_correct(old_record_id=..., new_record_id=..., text=..., source=...)`.
- **DO NOT** call `brain_remember` with a second conflicting record. Supersession keeps `brain_recall` clean while preserving audit provenance in `brain_trace`.

### 4. Keep Memory High-Signal (Anti-Junk Rules)
A junky memory is as harmful as no memory. Follow these strict boundaries:

**DO store (`brain_remember`):**
- Durable user preferences, working style, and explicit constraints (`trust="user"`).
- Accepted architecture/product decisions and their rationale (`topic="decision.<area>"`).
- Verified environment facts, deployment targets, and recurring project boundaries.
- Explicit corrections to earlier assumptions (`brain_correct`).

**DO NOT store:**
- Raw command logs, stack traces, or temporary debug output.
- One-off ephemeral scratch notes that lose value once the current task ends.
- API keys, passwords, bearer tokens, private keys, or sensitive credentials.
- Unverified speculation or guesses presented as confirmed facts.

### 5. End-of-Session Hygiene
Before wrapping up a multi-step session, review what actually changed:
1. Save or `brain_correct` any newly confirmed decisions or preferences with clear `source` attribution and `event_at` timestamp.
2. Call `brain_health()` periodically to check record counts, encryption status, and vault capacity pressure.
