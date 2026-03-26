"""
universal_deploy.cli
====================
Command-line interface — the `deploy` entry point.

Usage:
    deploy                              # apply latest bundle
    deploy 2026_03_20                   # apply bundles from this date forward
    deploy --list                       # show available bundles
    deploy --log [N]                    # show deployment history
    deploy --push                       # push unpushed changes to GitHub
    deploy --push --full                # push entire project (first time / full sync)
    deploy --voice                      # voice-friendly terse output
    deploy init                         # generate deploy.json in current directory
    deploy doctor                       # validate configuration and connectivity
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import (
    CONFIG_FILENAME,
    DeployConfig,
    generate_default_config,
    load_config,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deploy",
        description="Universal Deploy — configurable update deployer with GitHub push.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}",
    )

    sub = parser.add_subparsers(dest="command")

    # ── init ──
    init_p = sub.add_parser("init", help="Generate a deploy.json config in the current directory")

    # ── doctor ──
    doc_p = sub.add_parser("doctor", help="Validate configuration and environment")

    # ── apply (default) ──
    apply_p = sub.add_parser("apply", help="Apply update bundles (default command)")
    apply_p.add_argument("from_timestamp", nargs="?", default=None,
                         help="Apply bundles from this timestamp forward (e.g. 2026_03_20)")

    # ── list ──
    list_p = sub.add_parser("list", help="Show all available bundles")

    # ── log ──
    log_p = sub.add_parser("log", help="Show deployment history")
    log_p.add_argument("count", nargs="?", type=int, default=None,
                       help="Number of recent entries to show")

    # ── push ──
    push_p = sub.add_parser("push", help="Push changes to GitHub")
    push_p.add_argument("--full", action="store_true",
                        help="Push entire project instead of just changed files")

    # ── Global flags (apply to all subcommands) ──
    for p in [parser, apply_p, list_p, log_p, push_p]:
        p.add_argument("--voice", action="store_true",
                       help="Voice-friendly terse output")
        p.add_argument("--config", type=str, default=None,
                       help="Explicit path to deploy.json")
        p.add_argument("--project-root", type=str, default=None,
                       help="Override project root directory")
        p.add_argument("--downloads-path", type=str, default=None,
                       help="Override downloads path")

    return parser


def _handle_legacy_args(argv: list[str]) -> list[str]:
    """
    Support the legacy CLI style from the original deploy.py:
        deploy --list
        deploy --log 10
        deploy --push --full
        deploy 2026_03_20

    Translates these into the subcommand style.
    """
    if not argv:
        return ["apply"]

    # If the first arg is already a subcommand, pass through
    subcommands = {"init", "doctor", "apply", "list", "log", "push"}
    if argv[0] in subcommands:
        return argv

    # Pass through top-level argparse flags
    if argv[0] in ("--version", "--help", "-h"):
        return argv

    # Legacy flag translations
    if argv[0] == "--list":
        return ["list"] + argv[1:]

    if argv[0] == "--log":
        return ["log"] + argv[1:]

    if argv[0] == "--push":
        return ["push"] + argv[1:]

    # Bare timestamp → apply
    if argv[0] and not argv[0].startswith("-"):
        return ["apply"] + argv

    return ["apply"] + argv


def cmd_init(args: argparse.Namespace):
    """Generate a deploy.json in the current directory."""
    target = Path.cwd() / CONFIG_FILENAME
    if target.exists():
        print(f"⚠️  {CONFIG_FILENAME} already exists in {Path.cwd()}")
        response = input("Overwrite? [y/N] ").strip().lower()
        if response != "y":
            print("Aborted.")
            return

    config = generate_default_config()
    with open(target, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"✅  Created {target}")
    print()
    print("Next steps:")
    print(f"  1. Edit {CONFIG_FILENAME} to set your paths and preferences")
    print("  2. (Optional) Create a .deployignore file for push ignore rules")
    print("  3. Set DEPLOY_GITHUB_TOKEN env var for GitHub push")
    print("  4. Run 'deploy doctor' to verify everything is set up")


def cmd_doctor(args: argparse.Namespace):
    """Run diagnostic checks."""
    from .doctor import run_doctor

    cli_overrides = _cli_overrides(args)
    config_path = Path(args.config) if getattr(args, "config", None) else None
    cfg = load_config(cli_overrides=cli_overrides, config_path=config_path)
    cfg.voice_mode = getattr(args, "voice", False)

    healthy = run_doctor(cfg)
    sys.exit(0 if healthy else 1)


def cmd_apply(args: argparse.Namespace):
    """Apply update bundles."""
    from .bundles import apply_bundle, filter_bundles, find_bundles, unzip_bundles

    cfg = _resolve_config(args)

    if not cfg.downloads_path.exists():
        print(f"❌  Downloads path not found: {cfg.downloads_path}")
        sys.exit(1)
    if not cfg.project_root.exists():
        print(f"❌  Project root not found: {cfg.project_root}")
        sys.exit(1)

    unzip_bundles(cfg)
    bundles = find_bundles(cfg)

    if not bundles:
        print("No update bundles found.")
        return

    from_ts = args.from_timestamp
    selected = filter_bundles(bundles, cfg.bundle_prefix, from_ts)

    if not selected:
        print(f"No bundles found at or after: {from_ts}")
        return

    total_applied = 0
    total_skipped = 0

    for bundle in selected:
        a, s = apply_bundle(cfg, bundle)
        total_applied += a
        total_skipped += s

    if cfg.voice_mode:
        parts = [f"Applied {len(selected)} update bundle{'s' if len(selected) != 1 else ''}."]
        parts.append(f"{total_applied} file{'s' if total_applied != 1 else ''} updated.")
        if total_skipped:
            parts.append(f"{total_skipped} skipped.")
        print(" ".join(parts))
    else:
        log_path = cfg.deploy_log_abs()
        print(f"\n{'─' * 50}")
        print(f"Done. {len(selected)} bundle(s) applied.")
        print(f"      {total_applied} file(s) copied,  {total_skipped} skipped.")
        print(f"      Logged to {log_path}")
        print(f"{'─' * 50}\n")


def cmd_list(args: argparse.Namespace):
    """List available bundles."""
    from .bundles import list_bundles

    cfg = _resolve_config(args)
    list_bundles(cfg)


def cmd_log(args: argparse.Namespace):
    """Show deployment history."""
    from .log import show_log

    cfg = _resolve_config(args)
    show_log(cfg, args.count)


def cmd_push(args: argparse.Namespace):
    """Push changes to GitHub."""
    from .github import push_to_github

    cfg = _resolve_config(args)
    success = push_to_github(cfg, full=args.full)
    sys.exit(0 if success else 1)


def _cli_overrides(args: argparse.Namespace) -> dict:
    """Extract CLI flag overrides into a dict."""
    overrides = {}
    if getattr(args, "project_root", None):
        overrides["project_root"] = args.project_root
    if getattr(args, "downloads_path", None):
        overrides["downloads_path"] = args.downloads_path
    return overrides


def _resolve_config(args: argparse.Namespace) -> DeployConfig:
    """Build a DeployConfig from parsed args."""
    cli_overrides = _cli_overrides(args)
    config_path = Path(args.config) if getattr(args, "config", None) else None
    cfg = load_config(cli_overrides=cli_overrides, config_path=config_path)
    cfg.voice_mode = getattr(args, "voice", False)
    return cfg


def main(argv: list[str] | None = None):
    """Main entry point for the `deploy` CLI."""
    raw_args = argv if argv is not None else sys.argv[1:]
    translated = _handle_legacy_args(raw_args)

    parser = _build_parser()
    args = parser.parse_args(translated)

    commands = {
        "init":   cmd_init,
        "doctor": cmd_doctor,
        "apply":  cmd_apply,
        "list":   cmd_list,
        "log":    cmd_log,
        "push":   cmd_push,
    }

    handler = commands.get(args.command, cmd_apply)
    handler(args)


if __name__ == "__main__":
    main()
