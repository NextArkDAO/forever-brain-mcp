import base64
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import shutil
import sys

import pytest

from forever_brain_mcp import server
from forever_brain_mcp import vault as module
from forever_brain_mcp.vault import ForeverBrainVault


def write(vault, record="sample.one"):
    return vault.remember(record_id=record, topic="sample.topic", text="sample", source="fixture")


def worker(args):
    directory, record, key = args
    return write(ForeverBrainVault(directory, key_file=key), record)["saved"]


def test_wire_size_boundary(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "utc_now", lambda: "2026-11-22T00:00:00Z")
    first = ForeverBrainVault(tmp_path / "first")
    write(first)
    size = first.vault_path.stat().st_size
    vault = ForeverBrainVault(tmp_path / "second")
    monkeypatch.setattr(module, "MAX_VAULT_BYTES", size)
    write(vault)
    assert vault.health()["vault_bytes"] == size
    before = vault.vault_path.read_bytes()
    with pytest.raises(ValueError, match="capacity"):
        write(vault, "sample.two")
    assert vault.vault_path.read_bytes() == before
    assert ForeverBrainVault(vault.vault_dir).recall(query="sample")["count"] == 1
    monkeypatch.setattr(module, "MAX_VAULT_BYTES", size - 1)
    with pytest.raises(ValueError, match="capacity"):
        write(ForeverBrainVault(tmp_path / "third"))


@pytest.mark.parametrize("passphrase,material", [(None, "vault.key"), ("test passphrase", "vault.salt")])
def test_restore_and_missing_material(tmp_path, passphrase, material):
    vault = ForeverBrainVault(tmp_path / "original", passphrase=passphrase)
    write(vault)
    restored = ForeverBrainVault(tmp_path / "restored", passphrase=passphrase)
    restored.vault_dir.mkdir(mode=0o700)
    shutil.copy2(vault.vault_path, restored.vault_path)
    before = restored.vault_path.read_bytes()
    for action in (restored.health, restored.startup, lambda: write(restored)):
        with pytest.raises(ValueError, match="Restore"):
            action()
        assert not (restored.vault_dir / material).exists()
    assert restored.vault_path.read_bytes() == before
    shutil.copy2(vault.vault_dir / material, restored.vault_dir / material)
    assert restored.recall(query="sample")["count"] == 1


def test_concurrent_clients(tmp_path):
    key_dir = tmp_path / "keys"
    key_dir.mkdir()
    mode = key_dir.stat().st_mode
    key = key_dir / "shared"
    jobs = [(tmp_path / f"vault{i}", "sample.one", key) for i in range(2)]
    with ProcessPoolExecutor(2) as pool:
        missing = [pool.submit(worker, job) for job in jobs]
        for future in missing:
            with pytest.raises(ValueError, match="Pre-provision"):
                future.result()
        assert not key.exists()
        key.write_bytes(base64.urlsafe_b64encode(bytes(range(32))))
        key.chmod(0o644)
        with pytest.raises(ValueError, match="private"):
            worker(jobs[0])
        key.chmod(0o400)
        assert all(pool.map(worker, jobs))
        shared = tmp_path / "same"
        assert all(pool.map(worker, [(shared, f"record.{i}", key) for i in range(8)]))
    assert ForeverBrainVault(shared, key_file=key).health()["total_records"] == 8
    assert key_dir.stat().st_mode == mode


def test_cli_rejects_http(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["forever-brain-mcp", "--transport", "http"])
    with pytest.raises(SystemExit) as error:
        server.main()
    assert error.value.code == 2


def test_retry_after_later_correction_and_recorded_cutoff(tmp_path, monkeypatch):
    vault = ForeverBrainVault(tmp_path / "vault")
    monkeypatch.setattr(module, "utc_now", lambda: "2026-11-01T00:00:00Z")
    write(vault)
    monkeypatch.setattr(module, "utc_now", lambda: "2026-11-03T00:00:00Z")
    change = dict(old_record_id="sample.one", new_record_id="sample.two", text="sample two",
                  source="fixture", event_at="2027-01-01T00:00:00Z")
    original = vault.correct(**change)["record"]
    assert vault.recall(query="sample", as_of="2026-11-02T00:00:00Z")["records"][0]["id"] == "sample.one"
    assert vault.recall(query="sample", as_of="2026-11-04T00:00:00Z")["records"][0]["id"] == "sample.two"
    vault.correct(old_record_id="sample.two", new_record_id="sample.three", text="sample three", source="fixture")
    before = vault.vault_path.read_bytes()
    assert vault.correct(**change)["record"] == original
    with pytest.raises(ValueError, match="different content"):
        vault.correct(**{**change, "source": "different"})
    assert vault.vault_path.read_bytes() == before
    assert vault.trace("sample.one")["current_truth_id"] == "sample.three"
