# universal-deploy

A configurable, project-agnostic update deployer with GitHub push, audit logging, and bundle management. Drop it into any project — no code changes needed, just a `deploy.json`.

## Install

bash
# From the repo
pip install .

# Or in editable mode for development
pip install -e .


After install, the `deploy` command is available globally.

## Quick Start

bash
# 1. Navigate to your project
cd ~/my-project

# 2. Generate a config file
deploy init

# 3. Edit deploy.json to set your paths
#    (see Configuration below)

# 4. Verify everything is set up
deploy doctor

# 5. Apply the latest update bundle
deploy


## Commands

| Command | Description |
|---|---|
| `deploy` | Apply the latest bundle (alias for `deploy apply`) |
| `deploy apply` | Apply the latest bundle |
| `deploy apply 2026_03_20` | Apply all bundles from this date forward |
| `deploy list` | Show all available bundles |
| `deploy log` | Show full deployment history |
| `deploy log 10` | Show last 10 deployments |
| `deploy push` | Push unpushed changes to GitHub |
| `deploy push --full` | Push entire project to GitHub |
| `deploy init` | Generate `deploy.json` in the current directory |
| `deploy doctor` | Validate config, paths, and GitHub connectivity |

### Global Flags

These work with any command:

| Flag | Description |
|---|---|
| `--voice` | Terse output for voice assistants |
| `--config PATH` | Use a specific `deploy.json` |
| `--project-root PATH` | Override the project root |
| `--downloads-path PATH` | Override the downloads path |
| `--version` | Show version |

## Configuration

### `deploy.json`

Created by `deploy init`. Place it in your project root.


{
  "project_root": ".",
  "downloads_path": "~/Downloads",
  "bundle_prefix": "update_",
  "manifest_file": "update_manifest.json",
  "deploy_log": "config/deploy_log.json",

  "github_token": "",
  "github_repo": "",

  "push_ignore_dirs": ["venv", "__pycache__", ".git", "node_modules"],
  "push_ignore_files": [".env"],
  "push_ignore_extensions": [".pyc", ".pyo", ".log"],

  "auto_update_readme": false,
  "commit_prefix": "[Deploy]"
}


### Field Reference

| Field | Type | Default | Description |
|---|---|---|---|
| `project_root` | string | `"."` | Path to the project directory |
| `downloads_path` | string | `"~/Downloads"` | Where to look for update bundles |
| `bundle_prefix` | string | `"update_"` | Filename prefix for bundles |
| `manifest_file` | string | `"update_manifest.json"` | Manifest filename inside each bundle |
| `deploy_log` | string | `"config/deploy_log.json"` | Path to audit log (relative to project root) |
| `github_token` | string | `""` | GitHub personal access token |
| `github_repo` | string | `""` | GitHub repo (`user/repo`). Auto-detected if empty. |
| `push_ignore_dirs` | array | see above | Directories to exclude from push |
| `push_ignore_files` | array | `[".env"]` | Files to exclude from push |
| `push_ignore_extensions` | array | see above |