"""
universal_deploy.log
====================
Deploy audit log — read, write, and query deployment history.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import DeployConfig


def load_log(cfg: DeployConfig) -> list[dict]:
    """Load the deploy log from disk."""
    log_path = cfg.deploy_log_abs()
    if not log_path.exists():
        return []
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_log(cfg: DeployConfig, log: list[dict]):
    """Write the deploy log to disk."""
    log_path = cfg.deploy_log_abs()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def append_entry(
    cfg: DeployConfig,
    bundle_name: str,
    description: str,
    files_applied: list[str],
    files_skipped: int,
):
    """Append a deployment entry to the log."""
    log = load_log(cfg)
    log.append({
        "timestamp":      datetime.now().isoformat(),
        "bundle":         bundle_name,
        "description":    description,
        "files_applied":  files_applied,
        "files_count":    len(files_applied),
        "files_skipped":  files_skipped,
        "pushed_to_repo": False,
    })
    save_log(cfg, log)


def get_unpushed(cfg: DeployConfig) -> list[dict]:
    """Return log entries that haven't been pushed to repo yet."""
    return [e for e in load_log(cfg) if not e.get("pushed_to_repo", False)]


def get_changed_files_since_push(cfg: DeployConfig) -> list[str]:
    """Deduplicated list of all files changed since the last repo push."""
    seen: dict[str, str] = {}
    for entry in get_unpushed(cfg):
        for filepath in entry.get("files_applied", []):
            seen[filepath] = entry.get("bundle", "unknown")
    return list(seen.keys())


def mark_as_pushed(cfg: DeployConfig, up_to_timestamp: str | None = None):
    """Mark deploy log entries as pushed to repo."""
    log = load_log(cfg)
    for entry in log:
        if not entry.get("pushed_to_repo"):
            if up_to_timestamp is None or entry.get("timestamp", "") <= up_to_timestamp:
                entry["pushed_to_repo"] = True
    save_log(cfg, log)


def show_log(cfg: DeployConfig, count: int | None = None):
    """Print deployment history to stdout."""
    log = load_log(cfg)
    if not log:
        print("No deployments logged yet.")
        return

    entries = log[-count:] if count else log
    print(f"\nDeployment History ({len(entries)} of {len(log)} entries):\n")
    print(f"{'─' * 70}")

    for entry in entries:
        ts      = entry.get("timestamp", "?")[:19]
        bundle  = entry.get("bundle", "?")
        desc    = entry.get("description", "")
        count_f = entry.get("files_count", 0)
        skipped = entry.get("files_skipped", 0)
        pushed  = "✓" if entry.get("pushed_to_repo") else "✗"

        print(f"  {ts}  |  {bundle}")
        print(f"    {desc}")
        print(f"    Files: {count_f} applied, {skipped} skipped  |  Pushed: {pushed}")

        files = entry.get("files_applied", [])
        if files:
            for f in files[:10]:
                print(f"      → {f}")
            if len(files) > 10:
                print(f"      ...and {len(files) - 10} more")
        print(f"{'─' * 70}")
