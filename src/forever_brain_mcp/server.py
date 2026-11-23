"""Forever Brain FastMCP server.

Single trusted local client over stdio.
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Literal

from fastmcp import FastMCP

from forever_brain_mcp.vault import ForeverBrainVault

os.umask(0o077)

mcp = FastMCP(
    name="Forever Brain",
    instructions=(
        "Local-first, encrypted, source-attributed, bi-temporal memory for AI agents. "
        "Call brain_startup at session start, brain_recall before assuming prior facts, "
        "brain_remember for new durable facts/decisions, and brain_correct whenever a prior "
        "fact changes so history is preserved without stale ghosts."
    ),
)

_vault_instance: ForeverBrainVault | None = None


def _get_vault() -> ForeverBrainVault:
    global _vault_instance
    if _vault_instance is None:
        _vault_instance = ForeverBrainVault()
    return _vault_instance


@mcp.tool
def brain_startup(limit: int = 12) -> dict:
    """Recall bounded startup context (identity, principles, active decisions, focus) for a new session."""
    return _get_vault().startup(limit=limit)


@mcp.tool
def brain_remember(
    record_id: str,
    topic: str,
    text: str,
    source: str,
    kind: Literal[
        "identity",
        "decision",
        "principle",
        "preference",
        "work",
        "lesson",
        "focus",
        "fact",
        "history",
    ] = "work",
    status: Literal["current", "completed", "unknown"] = "current",
    trust: Literal["user", "agent", "external"] = "agent",
    event_at: str | None = None,
) -> dict:
    """Save an encrypted, source-attributed, bi-temporal memory record.

    Args:
        record_id: Stable lowercase slug (e.g. 'project.pricing.v1'). Reusing the exact
            same ID and payload is an idempotent no-op.
        topic: Dot-separated category (e.g. 'project.pricing', 'user.preferences').
        text: The durable fact, decision, or lesson to remember (1-12000 chars).
        source: Where this fact came from (file path, URL, conversation date, or user quote).
        kind: Record type (identity, decision, principle, preference, work, lesson, focus, fact, history).
        status: Lifecycle status (current, completed, unknown).
        trust: Trust boundary (user, agent, external). External data is never automatic authority.
        event_at: Optional ISO-8601 timestamp with timezone of WHEN this fact became true
            (distinct from recorded_at, when the agent learned it).
    """
    return _get_vault().remember(
        record_id=record_id,
        topic=topic,
        text=text,
        source=source,
        kind=kind,
        status=status,
        trust=trust,
        event_at=event_at,
    )


@mcp.tool
def brain_correct(
    old_record_id: str,
    new_record_id: str,
    text: str,
    source: str,
    event_at: str | None = None,
    status: Literal["current", "completed", "unknown"] | None = None,
    trust: Literal["user", "agent", "external"] | None = None,
) -> dict:
    """Non-destructively supersede an outdated memory with a corrected fact.

    Preserves the full audit trail while ensuring future brain_recall and brain_startup
    calls return only the corrected truth.

    Args:
        old_record_id: The existing active record_id being replaced.
        new_record_id: A new unique lowercase slug (e.g. 'project.pricing.v2').
        text: The updated truth.
        source: Evidence or attribution for why this changed.
        event_at: Optional ISO-8601 timestamp with timezone of when the new truth took effect.
        status: Optional updated status (defaults to the superseded record's status).
        trust: Optional updated trust tier (defaults to the superseded record's trust tier).
    """
    return _get_vault().correct(
        old_record_id=old_record_id,
        new_record_id=new_record_id,
        text=text,
        source=source,
        event_at=event_at,
        status=status,
        trust=trust,
    )


@mcp.tool
def brain_recall(
    query: str,
    topic: str | None = None,
    include_history: bool = False,
    as_of: str | None = None,
    limit: int = 10,
) -> dict:
    """Search memory records by keywords or topic.

    Returns active (non-superseded) truth by default. Set include_history=True to inspect
    superseded records, or pass as_of (ISO-8601 with timezone) to return what was recorded by that time. event_at is descriptive, not a query cutoff.
    """
    return _get_vault().recall(
        query=query,
        topic=topic,
        include_history=include_history,
        as_of=as_of,
        limit=limit,
    )


@mcp.tool
def brain_trace(record_id: str) -> dict:
    """Trace the complete revision lineage (original -> corrections -> current truth) for a record_id."""
    return _get_vault().trace(record_id=record_id)


@mcp.tool
def brain_health() -> dict:
    """Check vault encryption, capacity pressure, record counts, and integrity hash without exposing secrets."""
    return _get_vault().health()


@mcp.resource("brain://status")
def resource_status() -> str:
    """Read-only JSON summary of Forever Brain vault health and capacity."""
    return json.dumps(_get_vault().health(), indent=2)


@mcp.resource("brain://recent")
def resource_recent() -> str:
    """Read-only JSON list of the 10 most recent active memory records."""
    return json.dumps(_get_vault().recent(limit=10), indent=2)


@mcp.prompt
def session_handoff(project: str = "general") -> str:
    """Reusable end-of-session prompt to save verified decisions and corrections to Forever Brain."""
    return (
        f"Before ending this '{project}' session, review what changed:\n"
        "1. Call brain_recall to check if any existing record is now outdated.\n"
        "2. For any changed fact or decision, call brain_correct with the old_record_id, a new_record_id, "
        "exact source attribution, and event_at (when it became true).\n"
        "3. For genuinely new durable decisions or lessons, call brain_remember with an explicit source and trust tier.\n"
        "4. Never store secrets, API keys, or unverified guesses."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Forever Brain FastMCP server.")
    parser.add_argument("--transport", choices=("stdio",), default="stdio")
    parser.parse_args()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
