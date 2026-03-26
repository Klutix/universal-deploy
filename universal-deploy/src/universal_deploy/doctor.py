"""
universal_deploy.doctor
=======================
Diagnostic checks to verify the deploy environment is healthy.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import DeployConfig

from .github import _request, detect_repo


def run_doctor(cfg: DeployConfig) -> bool:
    """
    Run all diagnostic checks. Returns True if everything passes.
    """
    passed = 0
    failed = 0
    warned = 0

    def ok(msg: str):
        nonlocal passed
        passed += 1
        print(f"  ✅  {msg}")

    def fail(msg: str):
        nonlocal failed
        failed += 1
        print(f"  ❌  {msg}")

    def warn(msg: str):
        nonlocal warned
        warned += 1
        print(f"  ⚠️  {msg}")

    print("\n🩺  Deploy Doctor\n")

    # ── Config file ──
    if cfg.config_path:
        ok(f"Config loaded from: {cfg.config_path}")
    else:
        warn("No deploy.json found — using defaults. Run 'deploy init' to create one.")

    # ── Project root ──
    if cfg.project_root.is_dir():
        ok(f"Project root exists: {cfg.project_root}")
    else:
        fail(f"Project root not found: {cfg.project_root}")

    # ── Downloads path ──
    if cfg.downloads_path.is_dir():
        ok(f"Downloads path exists: {cfg.downloads_path}")
        # Check for bundles
        bundles = [
            d for d in cfg.downloads_path.iterdir()
            if d.is_dir() and d.name.startswith(cfg.bundle_prefix)
        ]
        zips = [
            f for f in cfg.downloads_path.iterdir()
            if f.is_file() and f.suffix == ".zip" and f.stem.startswith(cfg.bundle_prefix)
        ]
        total = len(bundles) + len(zips)
        if total > 0:
            ok(f"Found {total} bundle(s) ({len(bundles)} dirs, {len(zips)} zips)")
        else:
            warn(f"No bundles found with prefix '{cfg.bundle_prefix}'")
    else:
        fail(f"Downloads path not found: {cfg.downloads_path}")

    # ── Deploy log ──
    log_path = cfg.deploy_log_abs()
    if log_path.exists():
        ok(f"Deploy log exists: {log_path}")
    else:
        warn(f"Deploy log not found (will be created on first deploy): {log_path}")

    # ── .deployignore ──
    ignore_path = cfg.project_root / cfg.deployignore_file
    if ignore_path.is_file():
        ok(f".deployignore found: {ignore_path}")
    else:
        warn(f"No {cfg.deployignore_file} found (optional)")

    # ── GitHub token ──
    if cfg.github_token:
        ok("GitHub token is set")

        # Test authentication
        data, status = _request(cfg.github_token, "GET", "/user")
        if status == 200:
            username = data.get("login", "unknown")
            ok(f"GitHub auth valid — logged in as: {username}")

            # Test repo access
            repo = detect_repo(cfg)
            if repo:
                ok(f"GitHub repo accessible: {repo}")
            else:
                warn("Could not detect/access GitHub repo. Set 'github_repo' in config.")
        else:
            fail(f"GitHub auth failed (HTTP {status})")
    else:
        warn("GitHub token not set — push features disabled")

    # ── Ignore rules summary ──
    print(f"\n  📋  Ignore rules:")
    print(f"      Dirs:       {sorted(cfg.push_ignore_dirs)}")
    print(f"      Files:      {sorted(cfg.push_ignore_files)}")
    print(f"      Extensions: {sorted(cfg.push_ignore_extensions)}")

    # ── Summary ──
    print(f"\n{'─' * 50}")
    print(f"  Results: {passed} passed, {failed} failed, {warned} warnings")
    print(f"{'─' * 50}\n")

    return failed == 0
