"""Create a portable Investment OS backup archive.

The archive supplements Git history by including selected runtime data that is
intentionally ignored by Git. Secrets and local environments are excluded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "backup_output"

# Runtime content needed for disaster recovery. Missing paths are allowed.
RUNTIME_PATHS = [
    "history",
    "reports",
    "data/AI_portfolio.xlsx",
]

EXCLUDE_PARTS = {
    ".git", ".venv", "venv", "__pycache__", ".cache", ".idea", ".vscode",
    ".streamlit", "backup_output",
}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}
EXCLUDE_NAMES = {".env", "secrets.toml"}


def git_value(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def should_exclude(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if any(part in EXCLUDE_PARTS for part in rel.parts):
        return True
    if path.name in EXCLUDE_NAMES or path.suffix.lower() in EXCLUDE_SUFFIXES:
        return True
    return False


def iter_runtime_files():
    for relative in RUNTIME_PATHS:
        path = ROOT / relative
        if path.is_file() and not should_exclude(path):
            yield path
        elif path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file() and not should_exclude(child):
                    yield child


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def create_backup(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    archive = output_dir / f"investment-os-backup-{stamp}.zip"

    runtime_files = list(dict.fromkeys(iter_runtime_files()))
    manifest = {
        "schema_version": 1,
        "created_at_utc": now.isoformat(),
        "repository": "tonnirasmussen70/Investment-OS",
        "git_commit": git_value("rev-parse", "HEAD"),
        "git_branch": git_value("rev-parse", "--abbrev-ref", "HEAD"),
        "runtime_paths": RUNTIME_PATHS,
        "files": [
            {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "size": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in runtime_files
        ],
    }

    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("backup_manifest.json", json.dumps(manifest, indent=2))
        for path in runtime_files:
            zf.write(path, arcname=str(path.relative_to(ROOT)))

    checksum = sha256(archive)
    archive.with_suffix(archive.suffix + ".sha256").write_text(
        f"{checksum}  {archive.name}\n", encoding="utf-8"
    )
    return archive


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    archive = create_backup(args.output)
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
