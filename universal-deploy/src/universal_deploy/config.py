"""
universal_deploy.config
=======================
Loads and resolves project configuration.

Resolution order (highest priority wins):
    CLI flags  →  Environment variables  →  deploy.json  →  Defaults
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# The config filename we search for
CONFIG_FILENAME = "deploy.json"

# Env-var prefix — all env overrides use DEPLOY_ prefix
ENV_PREFIX = "DEPLOY_"

# ──────────────────────────────────────────────
#  Default config values
# ──────────────────────────────────────────────
DEFAULTS: dict[str, Any] = {
    "project_root": ".",
    "downloads_path": "~/Downloads",
    "bundle_prefix": "update_",
    "manifest_file": "update_manifest.json",
    "deploy_log": "config/deploy_log.json",

    # GitHub
    "github_token": "",
    "github_repo": "",

    # Push ignore rules
    "push_ignore_dirs": [
        "venv", "__pycache__", ".git", "node_modules", ".venv",
    ],
    "push_ignore_files": [".env"],
    "push_ignore_extensions": [".pyc", ".pyo", ".log"],

    # Optional features
    "auto_update_readme": False,
    "readme_path": "README.md",
    "commit_prefix": "[Deploy]",
    "deployignore_file": ".deployignore",
}


# ──────────────────────────────────────────────
#  Resolved config dataclass
# ──────────────────────────────────────────────
@dataclass
class DeployConfig:
    """Fully resolved configuration for a deploy run."""

    project_root: Path
    downloads_path: Path
    bundle_prefix: str
    manifest_file: str
    deploy_log: Path

    # GitHub
    github_token: str
    github_repo: str

    # Push ignore
    push_ignore_dirs: set[str]
    push_ignore_files: set[str]
    push_ignore_extensions: set[str]

    # Features
    auto_update_readme: bool
    readme_path: Path
    commit_prefix: str
    deployignore_file: str

    # Runtime (not persisted)
    voice_mode: bool = False
    config_path: Path | None = None

    def deploy_log_abs(self) -> Path:
        """Absolute path to the deploy log."""
        if self.deploy_log.is_absolute():
            return self.deploy_log
        return self.project_root / self.deploy_log

    def readme_abs(self) -> Path:
        """Absolute path to the README."""
        if self.readme_path.is_absolute():
            return self.readme_path
        return self.project_root / self.readme_path


# ──────────────────────────────────────────────
#  Config file discovery
# ──────────────────────────────────────────────

def find_config(start: Path | None = None) -> Path | None:
    """
    Walk up from *start* (default: cwd) looking for deploy.json.
    Returns the path to the file, or None.
    """
    current = (start or Path.cwd()).resolve()
    for _ in range(50):  # safety cap
        candidate = current / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


# ──────────────────────────────────────────────
#  .deployignore loader
# ──────────────────────────────────────────────

def load_deployignore(project_root: Path, filename: str) -> tuple[set[str], set[str], set[str]]:
    """
    Parse a .deployignore file and return (dirs, files, extensions) to add
    to the ignore sets.  Format:

        # comment
        dirname/          → ignore directory
        *.ext             → ignore extension
        filename.txt      → ignore specific file
    """
    ignore_path = project_root / filename
    dirs: set[str] = set()
    files: set[str] = set()
    exts: set[str] = set()

    if not ignore_path.is_file():
        return dirs, files, exts

    with open(ignore_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.endswith("/"):
                dirs.add(line.rstrip("/"))
            elif line.startswith("*."):
                exts.add(line[1:])  # keep the dot
            else:
                files.add(line)

    return dirs, files, exts


# ──────────────────────────────────────────────
#  Loader
# ──────────────────────────────────────────────

def _env(key: str) -> str | None:
    """Fetch DEPLOY_<KEY> from the environment."""
    return os.environ.get(f"{ENV_PREFIX}{key.upper()}") or None


def load_config(
    cli_overrides: dict[str, Any] | None = None,
    config_path: Path | None = None,
) -> DeployConfig:
    """
    Build a fully resolved DeployConfig.

    Priority: cli_overrides > env vars > deploy.json > DEFAULTS
    """
    # 1. Start with defaults
    merged: dict[str, Any] = {**DEFAULTS}

    # 2. Layer in deploy.json
    found = config_path or find_config()
    if found and found.is_file():
        with open(found, "r", encoding="utf-8") as f:
            file_cfg = json.load(f)
        for k, v in file_cfg.items():
            if v is not None:
                merged[k] = v

    # 3. Layer in environment variables (scalars only)
    scalar_keys = [
        "project_root", "downloads_path", "bundle_prefix",
        "manifest_file", "deploy_log", "github_token", "github_repo",
        "commit_prefix", "readme_path", "deployignore_file",
    ]
    for key in scalar_keys:
        env_val = _env(key)
        if env_val is not None:
            merged[key] = env_val

    # auto_update_readme from env
    env_readme = _env("auto_update_readme")
    if env_readme is not None:
        merged["auto_update_readme"] = env_readme.lower() in ("1", "true", "yes")

    # 4. Layer in CLI overrides
    if cli_overrides:
        for k, v in cli_overrides.items():
            if v is not None:
                merged[k] = v

    # 5. Resolve paths
    project_root = Path(os.path.expanduser(merged["project_root"])).resolve()

    # 6. Load .deployignore and merge
    extra_dirs, extra_files, extra_exts = load_deployignore(
        project_root, merged["deployignore_file"]
    )

    cfg = DeployConfig(
        project_root=project_root,
        downloads_path=Path(os.path.expanduser(merged["downloads_path"])).resolve(),
        bundle_prefix=merged["bundle_prefix"],
        manifest_file=merged["manifest_file"],
        deploy_log=Path(merged["deploy_log"]),
        github_token=merged["github_token"],
        github_repo=merged["github_repo"],
        push_ignore_dirs=set(merged["push_ignore_dirs"]) | extra_dirs,
        push_ignore_files=set(merged["push_ignore_files"]) | extra_files,
        push_ignore_extensions=set(merged["push_ignore_extensions"]) | extra_exts,
        auto_update_readme=merged["auto_update_readme"],
        readme_path=Path(merged.get("readme_path", "README.md")),
        commit_prefix=merged["commit_prefix"],
        deployignore_file=merged["deployignore_file"],
        config_path=found,
    )

    return cfg


# ──────────────────────────────────────────────
#  Config generator (for `deploy init`)
# ──────────────────────────────────────────────

def generate_default_config() -> dict[str, Any]:
    """Return a clean deploy.json dict with sensible defaults."""
    return {
        "project_root": ".",
        "downloads_path": "~/Downloads",
        "bundle_prefix": "update_",
        "manifest_file": "update_manifest.json",
        "deploy_log": "config/deploy_log.json",
        "github_token": "",
        "github_repo": "",
        "push_ignore_dirs": DEFAULTS["push_ignore_dirs"],
        "push_ignore_files": DEFAULTS["push_ignore_files"],
        "push_ignore_extensions": DEFAULTS["push_ignore_extensions"],
        "auto_update_readme": False,
        "commit_prefix": "[Deploy]",
    }
