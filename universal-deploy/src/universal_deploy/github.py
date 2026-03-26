"""
universal_deploy.github
=======================
GitHub Contents API integration — push files to a repo.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .config import DeployConfig

from . import log as deploy_log


# ──────────────────────────────────────────────
#  Low-level HTTP helpers
# ──────────────────────────────────────────────

def _headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "Universal-Deploy/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _request(
    token: str,
    method: str,
    url: str,
    body: dict | None = None,
) -> tuple[dict | list | str, int]:
    """Make a GitHub API request. Returns (parsed_body, status_code)."""
    if not url.startswith("http"):
        url = f"https://api.github.com{url}"

    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=_headers(token), method=method)
    if body:
        req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
            try:
                return json.loads(raw), resp.status
            except json.JSONDecodeError:
                return raw, resp.status
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        try:
            msg = json.loads(error_body).get("message", error_body[:200])
        except Exception:
            msg = error_body[:200]
        return {"error": msg}, e.code
    except Exception as e:
        return {"error": str(e)}, 0


# ──────────────────────────────────────────────
#  Repo detection
# ──────────────────────────────────────────────

def detect_repo(cfg: DeployConfig) -> str:
    """Auto-detect the GitHub repo from token, or use configured value."""
    if cfg.github_repo:
        return cfg.github_repo

    data, status = _request(cfg.github_token, "GET", "/user")
    if status != 200:
        return ""
    username = data.get("login", "")
    if not username:
        return ""

    project_name = cfg.project_root.name
    repo = f"{username}/{project_name}"

    check, status = _request(cfg.github_token, "GET", f"/repos/{repo}")
    if status == 200:
        return repo
    return ""


# ──────────────────────────────────────────────
#  File filtering
# ──────────────────────────────────────────────

def should_push_file(cfg: DeployConfig, rel_path: str) -> bool:
    """Check if a file should be included in the repo push."""
    parts = Path(rel_path).parts

    for part in parts:
        if part in cfg.push_ignore_dirs:
            return False

    filename = os.path.basename(rel_path)
    if filename in cfg.push_ignore_files:
        return False
    if filename.startswith("."):
        return False

    _, ext = os.path.splitext(filename)
    if ext in cfg.push_ignore_extensions:
        return False

    return True


# ──────────────────────────────────────────────
#  Single-file push
# ──────────────────────────────────────────────

def _get_existing_sha(token: str, repo: str, path: str) -> str | None:
    encoded = urllib.parse.quote(path, safe="/")
    data, status = _request(token, "GET", f"/repos/{repo}/contents/{encoded}")
    if status == 200 and isinstance(data, dict):
        return data.get("sha")
    return None


def _push_file(cfg: DeployConfig, repo: str, rel_path: str, commit_msg: str) -> bool:
    """Push a single file to the GitHub repo. Returns True on success."""
    full_path = cfg.project_root / rel_path
    if not full_path.exists():
        print(f"  ⚠️  File not found locally: {rel_path}")
        return False

    try:
        with open(full_path, "rb") as f:
            content = f.read()
        content_b64 = base64.b64encode(content).decode("ascii")
    except Exception as e:
        print(f"  ⚠️  Could not read {rel_path}: {e}")
        return False

    github_path = rel_path.replace("\\", "/")
    existing_sha = _get_existing_sha(cfg.github_token, repo, github_path)

    body: dict = {
        "message": commit_msg,
        "content": content_b64,
    }
    if existing_sha:
        body["sha"] = existing_sha

    encoded_path = urllib.parse.quote(github_path, safe="/")
    data, status = _request(
        cfg.github_token, "PUT",
        f"/repos/{repo}/contents/{encoded_path}", body,
    )

    if status in (200, 201):
        action = "Updated" if existing_sha else "Created"
        commit_sha = data.get("commit", {}).get("sha", "")[:7] if isinstance(data, dict) else ""
        print(f"  ✅  {action}: {github_path} ({commit_sha})")
        return True
    else:
        error = data.get("error", "unknown error") if isinstance(data, dict) else str(data)
        print(f"  ❌  Failed: {github_path} — {error}")
        return False


# ──────────────────────────────────────────────
#  Collect project files (full push)
# ──────────────────────────────────────────────

def collect_project_files(cfg: DeployConfig) -> list[str]:
    """Walk the project and collect all files that should be pushed."""
    files: list[str] = []
    for path in cfg.project_root.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(cfg.project_root))
        if should_push_file(cfg, rel):
            files.append(rel)
    return sorted(files)


# ──────────────────────────────────────────────
#  README changelog (opt-in)
# ──────────────────────────────────────────────

def _build_changelog_section(cfg: DeployConfig) -> str:
    log = deploy_log.load_log(cfg)
    if not log:
        return "*No deployments logged yet.*"

    lines: list[str] = []
    current_date = None
    for entry in reversed(log):
        ts   = entry.get("timestamp", "")[:10]
        desc = entry.get("description", "no description")
        bundle = entry.get("bundle", "")
        count = entry.get("files_count", 0)

        if ts != current_date:
            current_date = ts
            lines.append(f"\n### {ts}\n")
        lines.append(f"- **{bundle}** — {desc} ({count} files)")

    return "\n".join(lines)


def _update_readme_changelog(cfg: DeployConfig):
    readme = cfg.readme_abs()
    if not readme.exists():
        print("  ⚠️  README.md not found, skipping changelog update")
        return

    content = readme.read_text(encoding="utf-8")
    changelog = _build_changelog_section(cfg)
    marker = "## Changelog"

    if marker in content:
        before = content[:content.index(marker)]
        new_content = f"{before}{marker}\n\n{changelog}\n"
    else:
        new_content = f"{content.rstrip()}\n\n{marker}\n\n{changelog}\n"

    readme.write_text(new_content, encoding="utf-8")
    print("  📝  Updated README.md changelog")


# ──────────────────────────────────────────────
#  Main push orchestrator
# ──────────────────────────────────────────────

def push_to_github(cfg: DeployConfig, full: bool = False):
    """Push changes to GitHub repo (incremental or full)."""
    if not cfg.github_token:
        print("❌  GitHub token not set.")
        print("    Set DEPLOY_GITHUB_TOKEN env var or 'github_token' in deploy.json.")
        return False

    repo = detect_repo(cfg)
    if not repo:
        print("❌  Could not detect GitHub repo.")
        print("    Set DEPLOY_GITHUB_REPO env var or 'github_repo' in deploy.json.")
        return False

    print(f"\n🔄  Pushing to GitHub: {repo}")

    if full:
        files = collect_project_files(cfg)
        print(f"    Mode: FULL — {len(files)} file(s) to push")
    else:
        files = deploy_log.get_changed_files_since_push(cfg)
        if not files:
            print("    No unpushed changes found. Use --push --full for a complete sync.")
            return True
        files = [f for f in files if should_push_file(cfg, f)]
        print(f"    Mode: INCREMENTAL — {len(files)} changed file(s) to push")

    if not files:
        print("    Nothing to push.")
        return True

    # Optionally update README changelog
    if cfg.auto_update_readme:
        _update_readme_changelog(cfg)
        readme_rel = str(cfg.readme_path)
        if readme_rel not in files:
            files.append(readme_rel)

    success = 0
    failed = 0
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    for rel_path in files:
        commit_msg = f"{cfg.commit_prefix} Update {rel_path} — {timestamp}"
        if _push_file(cfg, repo, rel_path, commit_msg):
            success += 1
        else:
            failed += 1

    if success > 0:
        deploy_log.mark_as_pushed(cfg)

    print(f"\n{'─' * 50}")
    print(f"Push complete: {success} succeeded, {failed} failed")
    print(f"{'─' * 50}\n")
    return failed == 0
