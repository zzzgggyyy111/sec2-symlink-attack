"""Public contract tests for linkguard."""

import os
import subprocess
from pathlib import Path

from linkguard.api import inside, link_batch, safe_write

SAFE_POLICY = {
    "allow_overwrite": False,
    "check_links": True,
    "restrict_root": True,
}


def _make_dir_link(link: Path, target: Path) -> None:
    try:
        os.symlink(target, link, target_is_directory=True)
        return
    except (OSError, NotImplementedError):
        if os.name != "nt":
            raise
    proc = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stdout or "") + (proc.stderr or ""))


def _make_file_link(link: Path, target: Path) -> None:
    try:
        os.symlink(target, link)
        return
    except (OSError, NotImplementedError):
        if os.name != "nt":
            raise
    os.link(target, link)


def test_normal_path_write(tmp_path):
    root = tmp_path / "CaseRoot"
    (root / "docs").mkdir(parents=True)
    target = root / "docs" / "Report.TXT"

    result = safe_write(str(root), "docs/Report.TXT", b"hello", SAFE_POLICY)

    assert result["ok"] is True
    assert result["path"] == str(target)
    assert target.read_bytes() == b"hello"


def test_final_link_rejected(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"secret")
    _make_file_link(root / "payload.txt", outside)

    result = safe_write(str(root), "payload.txt", b"owned", SAFE_POLICY)

    assert result["ok"] is False
    assert outside.read_bytes() == b"secret"


def test_intermediate_dir_link_rejected(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    _make_dir_link(root / "pivot", outside)

    result = safe_write(str(root), "pivot/pwned.txt", b"owned", SAFE_POLICY)

    assert result["ok"] is False
    assert not (outside / "pwned.txt").exists()


def test_inside_rejects_sibling_prefix(tmp_path):
    root = tmp_path / "safe"
    root.mkdir()
    sibling = tmp_path / "safe-escape"
    sibling.mkdir()

    assert inside(str(root), str(sibling / "payload.txt")) is False


def test_batch_tasks_independent(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    tasks = [
        {"root": str(root), "path": "first.txt", "data": b"first"},
        {"root": str(root), "path": "second.txt", "data": b"second"},
    ]

    result = link_batch(tasks, SAFE_POLICY)

    assert result["ok"] is True
    assert (root / "first.txt").read_bytes() == b"first"
    assert (root / "second.txt").read_bytes() == b"second"