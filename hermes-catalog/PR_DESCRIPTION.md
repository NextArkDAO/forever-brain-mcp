# Upstream PR Draft: Add `forever-brain` to Hermes MCP Catalog

- **Target repository:** `NousResearch/hermes-agent`
- **Target file:** `optional-mcps/forever-brain/manifest.yaml`
- **Post-PyPI Gate (required before opening PR):** After `forever-brain-mcp==0.1.1` is published to PyPI, verify `uvx forever-brain-mcp==0.1.1` starts cleanly over stdio against PyPI.

## Summary
Adds **Forever Brain** (`forever-brain-mcp`) to `optional-mcps/`: a local-first, AES-256-GCM encrypted, source-attributed, bi-temporal memory MCP server built with FastMCP for trusted local stdio clients on POSIX.

### Why it's useful for Hermes users
- **Non-destructive corrections (`brain_correct`):** Supersedes outdated facts while keeping full audit history and preventing stale ghosts in recall/startup.
- **Bi-temporal truth:** Stores `event_at` (effective time) and `recorded_at` (recording time), with full revision lineage (`brain_trace`).
- **Local privacy & zero cloud lock-in:** Auto-initializes a `0700`/`0600` AES-256-GCM local vault (keyfile or PBKDF2 passphrase mode); no external API keys required.
- **6 focused tools over stdio:** `brain_startup`, `brain_remember`, `brain_correct`, `brain_recall`, `brain_trace`, `brain_health`.

### Verification (Shipped Stdio Entry Point)
- `pytest -v`: 13/13 tests passed (core encryption, POSIX permissions, bi-temporal supersession/trace, concurrency, restore/missing-material checks, and stdio-only CLI enforcement).
- `twine check --strict dist/*`: passed on both wheel and sdist for `0.1.1`.
- Isolated stdio smoke test of the installed `forever-brain-mcp` `0.1.1` wheel: verified all 6 tools over stdio.
- Candidate `manifest.yaml` validated directly against Hermes `0.23.3`'s `hermes_cli.mcp_catalog` parser.
