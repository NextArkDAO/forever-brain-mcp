# Forever Brain MCP

**Local-first, encrypted, source-attributed, bi-temporal memory for AI agents.**

Built with FastMCP for POSIX hosts. Verified host: Hermes Agent 0.23.3 on macOS. Other stdio clients below are example configurations.

---

## Why Forever Brain (Instead of Markdown Files or Vector RAG)?

| Capability | Plain Markdown | Typical Vector RAG | Forever Brain MCP |
|---|---|---|---|
| **Encrypted at rest locally** | No | Cloud-hosted / plaintext | **AES-256-GCM (`0600` local vault)** |
| **Corrections without stale ghosts** | Manual edits | Returns old & new together | **Non-destructive `brain_correct` supersession** |
| **Bi-temporal truth** (*when true* vs. *when learned*) | No | Rarely | Stores both timestamps. `as_of` filters by recording time. |
| **Source attribution & trust tiers** | Informal | Usually lost | **Required `source` + `trust` (`user`/`agent`/`external`)** |
| **Full revision lineage** | Git only | No | **`brain_trace(record_id)` chain** |
| **Bounded startup budget** | Manual | Top-K noise | **`brain_startup(limit)` priority-ranked** |

---

## 60-Second Quickstart

### 1. Install
```bash
pip install -e .
```

### 2. Wire into Hermes Agent (`~/.hermes/config.yaml`)
```yaml
mcp_servers:
  forever-brain:
    command: forever-brain-mcp
    env:
      FOREVER_BRAIN_DIR: ~/.forever-brain/vault
```
Restart Hermes, and your agent immediately gets `brain_startup`, `brain_remember`, `brain_correct`, `brain_recall`, `brain_trace`, and `brain_health`.

### 3. Or Install into Claude Code / Claude Desktop / Cursor
```bash
fastmcp install claude-code src/forever_brain_mcp/server.py:mcp
fastmcp install claude-desktop src/forever_brain_mcp/server.py:mcp
fastmcp install cursor src/forever_brain_mcp/server.py:mcp -e .
```

### 4. Local Validation (Hermes FastMCP Quality Bar)
```bash
fastmcp inspect src/forever_brain_mcp/server.py:mcp
fastmcp list src/forever_brain_mcp/server.py --json
fastmcp call src/forever_brain_mcp/server.py brain_health --json
```

---

## Tools, Resources & Prompts

| Surface | Name | Purpose |
|---|---|---|
| Tool | `brain_startup(limit=12)` | Bounded session-start context (identity, principles, decisions, preferences, focus). |
| Tool | `brain_remember(...)` | Save an encrypted, source-attributed, bi-temporal record (idempotent on `record_id`). |
| Tool | `brain_correct(...)` | Non-destructively supersede an outdated record while preserving full history. |
| Tool | `brain_recall(...)` | Search active truth by default; optional `include_history=True` or point-in-time `as_of`. |
| Tool | `brain_trace(record_id)` | Trace full revision chain from original record to current truth. |
| Tool | `brain_health()` | Verify encryption, capacity pressure, record counts, and vault SHA-256. |
| Resource | `brain://status` | Read-only vault health summary. |
| Resource | `brain://recent` | 10 most recent active records. |
| Prompt | `session_handoff` | Reusable end-of-session memory hygiene template. |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `FOREVER_BRAIN_DIR` | `~/.forever-brain/vault` | Private (`0700`) directory holding `vault.enc.json` and lockfile. |
| `FOREVER_BRAIN_KEY_FILE` | `<FOREVER_BRAIN_DIR>/vault.key` | Base64 encoding of 32 random bytes in an owner-private file. The default key is generated for a new vault. Provision any external key in advance. |
| `FOREVER_BRAIN_PASSPHRASE` | *(unset)* | Optional passphrase (PBKDF2-HMAC-SHA256, 200k iterations) instead of a keyfile. |

## Recovery and local access

For keyfile mode, back up the ciphertext and its original key. Anyone holding both can decrypt the vault. For passphrase mode, retain the ciphertext, original vault.salt and the passphrase. Restore into a dedicated directory owned by the current user (0700), with owner-private files (0600). Back up a consistent snapshot while the server is stopped.

The supported transport is stdio for a trusted local client on POSIX. Every connected client can read and change the entire selected vault. Use a separate vault per trust boundary. Source and trust labels are supplied by the client. Corrections inherit the old trust label unless explicitly set. Keep untrusted inputs attributed as such. A third-party HTTP wrapper is outside the supported configuration.

A correction records its effective date in event_at. The as_of query shows the history the vault knew by the specified recorded time. A future effective date does not defer a saved correction. Set explicit event_at when effective time matters.
