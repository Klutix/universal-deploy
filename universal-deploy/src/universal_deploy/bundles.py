"""
universal_deploy.bundles
========================
Bundle discovery, extraction, manifest loading, and file application.

Bundle naming convention:
    {bundle_prefix}{timestamp}
    e.g.  update_2026_03_20_143000

Accepted timestamp formats (postfix after the prefix):
    YYYY_MM_DD_HHMMSS   →  2026_03_20_143000
    YYYY_MM_DD          →  2026_03_20
    YYYYMMDD_HHMMSS     →  20260320_143000
    YYYYMMDD            →  20260320
"""

from __future__ import annotations

import json
import re
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import DeployConfig

from . import log as deploy_log


# ──────────────────────────────────────────────
#  Timestamp parsing
# ──────────────────────────────────────────────

# Patterns we accept, most specific first
_TS_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^(\d{4})_(\d{2})_(\d{2})_(\d{6})$"), "%Y_%m_%d_%H%M%S"),
    (re.compile(r"^(\d{4})_(\d{2})_(\d{2})$"),          "%Y_%m_%d"),
    (re.compile(r"^(\d{8})_(\d{6})$"),                   "%Y%m%d_%H%M%S"),
    (re.compile(r"^(\d{8})$"),                           "%Y%m%d"),
]


def parse_timestamp(raw: str) -> datetime | None:
    """
    Parse a bundle timestamp postfix into a datetime.
    Returns None if the string doesn't match any known format.
    """
    for pattern, fmt in _TS_PATTERNS:
        if pattern.match(raw):
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
    return None


def extract_timestamp(bundle_name: str, prefix: str) -> datetime | None:
    """
    Given a full bundle name (e.g. "update_2026_03_20_143000") and the
    configured prefix (e.g. "update_"), extract and parse the timestamp.
    """
    if not bundle_name.startswith(prefix):
        return None
    postfix = bundle_name[len(prefix):]
    return parse_timestamp(postfix)


# ──────────────────────────────────────────────
#  Bundle discovery
# ──────────────────────────────────────────────

def unzip_bundles(cfg: DeployConfig):
    """Auto-extract any .zip bundles in the downloads path."""
    downloads = cfg.downloads_path
    prefix = cfg.bundle_prefix

    zips = sorted([
        f for f in downloads.iterdir()
        if f.is_file()
        and f.suffix == ".zip"
        and f.stem.startswith(prefix)
    ])

    for zip_path in zips:
        target_dir = downloads / zip_path.stem
        if target_dir.exists():
            continue

        if not cfg.voice_mode:
            print(f"📂  Unzipping {zip_path.name}...")

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(downloads)

        if not cfg.voice_mode:
            print(f"    → {target_dir.name}/")


def find_bundles(cfg: DeployConfig) -> list[Path]:
    """
    Return bundle directories sorted by their parsed timestamp.
    Bundles whose postfix isn't a valid timestamp are warned and skipped.
    """
    candidates = [
        d for d in cfg.downloads_path.iterdir()
        if d.is_dir() and d.name.startswith(cfg.bundle_prefix)
    ]

    valid: list[tuple[datetime, Path]] = []
    for d in candidates:
        ts = extract_timestamp(d.name, cfg.bundle_prefix)
        if ts is None:
            print(f"  ⚠️  Skipping '{d.name}' — postfix is not a valid timestamp")
            continue
        valid.append((ts, d))

    # Sort by parsed timestamp (chronological order)
    valid.sort(key=lambda pair: pair[0])
    return [path for _, path in valid]


def filter_bundles(
    bundles: list[Path],
    prefix: str,
    from_timestamp: str | None,
) -> list[Path]:
    """
    Filter bundles to those at or after *from_timestamp*.
    If from_timestamp is None, return only the latest bundle.

    from_timestamp can be any of the accepted formats:
        2026_03_20_143000
        2026_03_20
        20260320
    """
    if not from_timestamp:
        return bundles[-1:] if bundles else []

    cutoff = parse_timestamp(from_timestamp)
    if cutoff is None:
        print(f"  ⚠️  '{from_timestamp}' is not a valid timestamp format.")
        print(f"      Accepted: YYYY_MM_DD_HHMMSS, YYYY_MM_DD, YYYYMMDD_HHMMSS, YYYYMMDD")
        return []

    result: list[Path] = []
    for b in bundles:
        bundle_ts = extract_timestamp(b.name, prefix)
        if bundle_ts is not None and bundle_ts >= cutoff:
            result.append(b)

    return result


# ──────────────────────────────────────────────
#  Manifest + apply
# ──────────────────────────────────────────────

def load_manifest(bundle: Path, manifest_file: str) -> dict | None:
    """Load and return the manifest JSON from a bundle directory."""
    manifest_path = bundle / manifest_file
    if not manifest_path.exists():
        print(f"  ⚠️  No {manifest_file} found in {bundle.name} — skipping")
        return None
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def apply_bundle(cfg: DeployConfig, bundle: Path) -> tuple[int, int]:
    """
    Apply a single bundle to the project.
    Returns (applied_count, skipped_count).
    """
    manifest = load_manifest(bundle, cfg.manifest_file)
    if manifest is None:
        return 0, 0

    description = manifest.get("description", "no description")
    files = manifest.get("files", [])

    if not cfg.voice_mode:
        ts = extract_timestamp(bundle.name, cfg.bundle_prefix)
        ts_display = ts.strftime("%Y-%m-%d %H:%M:%S") if ts else "unknown"
        print(f"\n📦  Bundle : {bundle.name}")
        print(f"    Time   : {ts_display}")
        print(f"    Desc   : {description}")
        print(f"    Files  : {len(files)}")

    applied = 0
    skipped = 0
    applied_files: list[str] = []

    for entry in files:
        src_name = entry.get("file")
        dest_rel = entry.get("destination")

        if not src_name or not dest_rel:
            print(f"  ⚠️  Malformed entry: {entry} — skipping")
            skipped += 1
            continue

        src = bundle / src_name
        dest = cfg.project_root / dest_rel

        if not src.exists():
            print(f"  ⚠️  Source not found: {src_name} — skipping")
            skipped += 1
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        applied += 1
        applied_files.append(dest_rel)

        if not cfg.voice_mode:
            print(f"  ✅  {src_name}  →  {dest_rel}")

    deploy_log.append_entry(
        cfg,
        bundle_name=bundle.name,
        description=description,
        files_applied=applied_files,
        files_skipped=skipped,
    )

    return applied, skipped


# ──────────────────────────────────────────────
#  List
# ──────────────────────────────────────────────

def list_bundles(cfg: DeployConfig):
    """Print all available bundles to stdout."""
    unzip_bundles(cfg)
    bundles = find_bundles(cfg)
    if not bundles:
        print("No update bundles found.")
        return

    print(f"\nFound {len(bundles)} bundle(s) in {cfg.downloads_path}:\n")
    for b in bundles:
        ts = extract_timestamp(b.name, cfg.bundle_prefix)
        ts_display = ts.strftime("%Y-%m-%d %H:%M:%S") if ts else "?"
        manifest = load_manifest(b, cfg.manifest_file)
        if manifest:
            desc = manifest.get("description", "—")
            count = len(manifest.get("files", []))
            print(f"  {b.name}  |  {ts_display}  |  {count} file(s)  |  {desc}")
        else:
            print(f"  {b.name}  |  {ts_display}  |  no manifest")
