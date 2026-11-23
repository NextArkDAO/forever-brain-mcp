"""Unit, security, and FastMCP client tests for forever-brain-mcp."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import stat

import pytest
from fastmcp import Client

from forever_brain_mcp.vault import ForeverBrainVault
import forever_brain_mcp.server as server_mod


def test_encrypted_at_rest_and_posix_permissions(tmp_path: Path) -> None:
    vault_dir = tmp_path / "vault"
    vault = ForeverBrainVault(vault_dir=vault_dir)

    secret_phrase = "Launch date moved to December 15 for Project Phoenix"
    res = vault.remember(
        record_id="phoenix.launch.v1",
        topic="project.phoenix",
        text=secret_phrase,
        source="founder call 2026-11-20",
        kind="decision",
        trust="user",
        event_at="2026-11-20T14:00:00-05:00",
    )
    assert res["saved"] is True
    assert res["idempotent_replay"] is False
    assert res["record"]["event_at"] == "2026-11-20T19:00:00Z"

    # Ciphertext must not contain plaintext
    raw_disk = (vault_dir / "vault.enc.json").read_text(encoding="utf-8")
    assert secret_phrase not in raw_disk
    assert "AES-256-GCM" in raw_disk

    # Strict POSIX permissions
    assert stat.S_IMODE(vault_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE((vault_dir / "vault.enc.json").stat().st_mode) == 0o600
    assert stat.S_IMODE((vault_dir / "vault.key").stat().st_mode) == 0o600


def test_passphrase_mode_and_wrong_passphrase_rejected(tmp_path: Path) -> None:
    vault_dir = tmp_path / "pass_vault"
    v_ok = ForeverBrainVault(vault_dir=vault_dir, passphrase="correct-horse-battery-staple")
    v_ok.remember(
        record_id="auth.test.v1",
        topic="security.test",
        text="Encrypted with user passphrase",
        source="unit test",
        kind="fact",
    )
    assert v_ok.health()["key_mode"] == "passphrase"

    v_bad = ForeverBrainVault(vault_dir=vault_dir, passphrase="wrong-passphrase")
    with pytest.raises(Exception):
        v_bad.recall(query="passphrase")


def test_bitemporal_correction_supersession_and_trace(tmp_path: Path) -> None:
    vault = ForeverBrainVault(vault_dir=tmp_path / "vault")

    vault.remember(
        record_id="pricing.tier.v1",
        topic="product.pricing",
        text="Pro tier costs $19/month.",
        source="initial draft 2026-11-01",
        kind="decision",
        trust="user",
        event_at="2026-11-01T12:00:00Z",
    )

    corr = vault.correct(
        old_record_id="pricing.tier.v1",
        new_record_id="pricing.tier.v2",
        text="Pro tier costs $29/month and includes team sync.",
        source="founder decision 2026-11-22",
        event_at="2026-11-22T18:00:00Z",
    )
    assert corr["corrected"] is True
    assert corr["superseded_id"] == "pricing.tier.v1"

    # Default recall returns ONLY the corrected truth (no stale ghost)
    active = vault.recall(query="Pro tier costs")
    assert active["count"] == 1
    assert active["records"][0]["id"] == "pricing.tier.v2"
    assert "$29/month" in active["records"][0]["text"]
    assert active["records"][0]["is_superseded"] is False

    # History recall returns both revisions
    hist = vault.recall(query="Pro tier costs", include_history=True)
    assert hist["count"] == 2
    ids = {r["id"] for r in hist["records"]}
    assert ids == {"pricing.tier.v1", "pricing.tier.v2"}

    # Trace returns full ordered lineage from either ID
    tr = vault.trace("pricing.tier.v1")
    assert tr["root_id"] == "pricing.tier.v1"
    assert tr["current_truth_id"] == "pricing.tier.v2"
    assert tr["revisions"] == 2
    assert tr["chain"][0]["is_current_truth"] is False
    assert tr["chain"][1]["is_current_truth"] is True

    # Double-superseding an old record is blocked
    with pytest.raises(ValueError, match="already superseded"):
        vault.correct(
            old_record_id="pricing.tier.v1",
            new_record_id="pricing.tier.v3",
            text="Another edit",
            source="test",
        )


def test_idempotent_retry_and_conflict_detection(tmp_path: Path) -> None:
    vault = ForeverBrainVault(vault_dir=tmp_path / "vault")
    kwargs = dict(
        record_id="ops.rule.v1",
        topic="ops.rules",
        text="Always log maintenance changes.",
        source="founder direction 2026-11-22",
        kind="principle",
        trust="user",
    )
    first = vault.remember(**kwargs)
    replay = vault.remember(**kwargs)
    assert first["idempotent_replay"] is False
    assert replay["idempotent_replay"] is True

    with pytest.raises(ValueError, match="already exists with different content"):
        vault.remember(**{**kwargs, "text": "Mutated text without brain_correct"})


def test_startup_priority_and_bounds(tmp_path: Path) -> None:
    vault = ForeverBrainVault(vault_dir=tmp_path / "vault")
    vault.remember(record_id="work.1", topic="eng.misc", text="Misc log 1", source="s", kind="work")
    vault.remember(record_id="id.1", topic="agent.id", text="Core identity", source="s", kind="identity")
    vault.remember(record_id="dec.1", topic="product.bet", text="Forever Brain flagship", source="s", kind="decision")

    res = vault.startup(limit=2)
    assert res["total_active"] == 3
    assert res["omitted"] == 1
    assert [r["id"] for r in res["records"]] == ["id.1", "dec.1"]


def test_symlink_vault_dir_refused(tmp_path: Path) -> None:
    real_dir = tmp_path / "real"
    real_dir.mkdir(mode=0o700)
    link_dir = tmp_path / "symlink_vault"
    os.symlink(real_dir, link_dir)

    vault = ForeverBrainVault(vault_dir=link_dir)
    with pytest.raises(ValueError, match="symlink"):
        vault.health()


def test_fastmcp_server_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FOREVER_BRAIN_DIR", str(tmp_path / "mcp_vault"))
    server_mod._vault_instance = None

    async def _run() -> None:
        async with Client(server_mod.mcp) as client:
            tools = await client.list_tools()
            tool_names = {t.name for t in tools}
            assert tool_names == {
                "brain_startup",
                "brain_remember",
                "brain_correct",
                "brain_recall",
                "brain_trace",
                "brain_health",
            }

            r1 = await client.call_tool(
                "brain_remember",
                {
                    "record_id": "flagship.v1",
                    "topic": "company.strategy",
                    "text": "Flagship is x402 storefront.",
                    "source": "old plan",
                    "kind": "decision",
                    "trust": "user",
                    "event_at": "2026-11-06T12:00:00Z",
                },
            )
            assert json.loads(r1.content[0].text)["saved"] is True

            r2 = await client.call_tool(
                "brain_correct",
                {
                    "old_record_id": "flagship.v1",
                    "new_record_id": "flagship.v2",
                    "text": "Flagship is Forever Brain MCP + Hermes.",
                    "source": "founder decision 2026-11-22",
                    "event_at": "2026-11-22T21:21:00-05:00",
                },
            )
            assert json.loads(r2.content[0].text)["corrected"] is True

            r3 = await client.call_tool("brain_recall", {"query": "Flagship"})
            recalled = json.loads(r3.content[0].text)
            assert recalled["count"] == 1
            assert recalled["records"][0]["id"] == "flagship.v2"

            r4 = await client.call_tool("brain_trace", {"record_id": "flagship.v1"})
            traced = json.loads(r4.content[0].text)
            assert traced["current_truth_id"] == "flagship.v2"

            status_res = await client.read_resource("brain://status")
            status_json = json.loads(status_res[0].text)
            assert status_json["status"] == "ok"
            assert status_json["active_records"] == 1
            assert status_json["superseded_records"] == 1

            prompt_res = await client.get_prompt("session_handoff", {"project": "forever-brain"})
            assert "brain_correct" in prompt_res.messages[0].content.text

    asyncio.run(_run())
