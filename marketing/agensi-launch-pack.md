# Forever Brain — encrypted local memory for AI agents

Listing draft for use after the versioned PyPI install passes verification.

Forever Brain gives a stdio MCP client a local, encrypted memory vault. An agent can start a session with bounded context, recall a decision by topic and trace its corrections back to the original record. Each record carries a source and a trust label. Historical recall uses the time a record was saved, and a separate event timestamp captures when the fact took effect.

The companion skill explains which decisions and preferences to retain, when to supersede a record and how to keep credentials and transient logs out of memory.

## Setup

Configure a stdio MCP client to run `uvx forever-brain-mcp==0.1.1` on macOS or Linux. The server encrypts the local vault with AES-256-GCM. Back up the encrypted vault with its key file, or retain its salt and passphrase when using passphrase mode.

[Companion skill](../skills/forever-brain/SKILL.md) · [Project and recovery instructions](https://github.com/NextArkDAO/forever-brain-mcp)
