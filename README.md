# universal-deploy

A configurable, project-agnostic update deployer with GitHub push, audit logging, and bundle management. Drop it into any project — no code changes needed, just a `deploy.json`.

---

## Install

```bash
# From the repo
pip install .

# Or in editable mode (auto-picks up changes on git pull — no reinstall)
pip install -e .
```

After install, the `deploy` command is available globally. Verify with:

```bash
deploy --version
```

> **Tip:** Install globally (outside any virtual environment). `deploy` is a system tool that operates *on* projects — like `git` — not a dependency *of* them.

---

## Quick Start

```bash
# 1. Navigate to your project
cd ~/my-project

# 2. Generate a config file
deploy init

# 3. Edit deploy.json to set your paths (see Configuration below)

# 4. Verify everything is set up
deploy doctor

# 5. Apply the latest update bundle
deploy
```

---

## Commands

| Command | Description |
|---|---|
| `deploy` | Apply the latest bundle (alias for `deploy apply`) |
| `deploy apply` | Apply the latest bundle |
| `deploy apply 2026_03_20` | Apply all bundles from this date forward |
| `deploy apply 2026_03_20_143000` | Apply from an exact timestamp forward |
| `deploy list` | Show all available bundles with timestamps and descriptions |
| `deploy log` | Show full deployment history |
| `deploy log 5` | Show last 5 deployments |
| `deploy push` | Push only unpushed changes to GitHub (incremental) |
| `deploy push --full` | Push the entire project to GitHub (first-time sync or reset) |
| `deploy init` | Generate a `deploy.json` in the current directory |
| `deploy doctor` | Validate config, paths, GitHub token, and repo connectivity |

### Understanding `deploy` vs `push`

These are two separate stages:

- **`deploy`** copies files from a bundle into your local project. Nothing touches GitHub. You can run it multiple times.
- **`deploy push`** sends all locally deployed (but not yet pushed) files to GitHub in one batch.
- **`deploy push --full`** ignores the log and pushes every file in the project. Use this for first-time repo setup or to get back in sync.

Typical workflow:

```bash
deploy                  # apply bundle A (3 files changed)
deploy                  # apply bundle B (5 files changed)
deploy                  # apply bundle C (2 files changed)
deploy push             # pushes all 10 changed files to GitHub at once
```

If the same file was changed by multiple bundles, it's only pushed once (latest version).

### Global Flags

These work with any command:

| Flag | Description |
|---|---|
| `--voice` | Terse output optimized for voice assistants |
| `--config PATH` | Use a specific `deploy.json` instead of auto-discovery |
| `--project-root PATH` | Override the project root directory |
| `--downloads-path PATH` | Override the downloads/bundle source path |
| `--version` | Show version number |

---

## Configuration

### `deploy.json`

Created by `deploy init`. Lives in your project root. Every field has a sensible default — you only need to change what's different for your project.

```json
{
  "project_root": ".",
  "downloads_path": "~/Downloads",
  "bundle_prefix": "update_",
  "manifest_file": "update_manifest.json",
  "deploy_log": "config/deploy_log.json",

  "github_token": "",
  "github_repo": "",

  "push_ignore_dirs": ["venv", "__pycache__", ".git", "node_modules", ".venv"],
  "push_ignore_files": [".env"],
  "push_ignore_extensions": [".pyc", ".pyo", ".log"],

  "auto_update_readme": false,
  "commit_prefix": "[Deploy]"
}
```

### Field Reference

| Field | Type | Default | Description |
|---|---|---|---|
| `project_root` | string | `"."` | Path to the project. Usually `"."` if you run deploy from the project dir. Can be absolute. |
| `downloads_path` | string | `"~/Downloads"` | Where to scan for update bundles and zips. |
| `bundle_prefix` | string | `"update_"` | Filename prefix that identifies bundles. Only dirs/zips starting with this are picked up. |
| `manifest_file` | string | `"update_manifest.json"` | Name of the manifest file inside each bundle. |
| `deploy_log` | string | `"config/deploy_log.json"` | Audit log path, relative to project root. Tracks every deployment and push status. |
| `github_token` | string | `""` | GitHub personal access token. **Prefer the env var** `DEPLOY_GITHUB_TOKEN` over putting this in the file. |
| `github_repo` | string | `""` | GitHub repo in `"user/repo"` format. Auto-detected from token + project dir name if empty. |
| `push_ignore_dirs` | array | `["venv", "__pycache__", ".git", "node_modules", ".venv"]` | Directories to never push to GitHub. |
| `push_ignore_files` | array | `[".env"]` | Specific filenames to never push. |
| `push_ignore_extensions` | array | `[".pyc", ".pyo", ".log"]` | File extensions to never push. |
| `auto_update_readme` | bool | `false` | If true, auto-appends a changelog section to README.md before each push. |
| `commit_prefix` | string | `"[Deploy]"` | Prefix for all GitHub commit messages. |

### Configuration Examples

**Python web app (Flask/Django):**

```json
{
  "project_root": ".",
  "downloads_path": "~/Downloads",
  "bundle_prefix": "webapp_update_",
  "deploy_log": "config/deploy_log.json",
  "github_repo": "myuser/my-webapp",
  "push_ignore_dirs": ["venv", "__pycache__", ".git", "node_modules", "migrations", "media"],
  "push_ignore_files": [".env", "db.sqlite3", "local_settings.py"],
  "push_ignore_extensions": [".pyc", ".log", ".sqlite3"],
  "commit_prefix": "[WebApp Deploy]"
}
```

**Node.js project:**

```json
{
  "project_root": ".",
  "downloads_path": "~/Downloads",
  "bundle_prefix": "frontend_patch_",
  "deploy_log": ".deploy/log.json",
  "github_repo": "myuser/my-frontend",
  "push_ignore_dirs": ["node_modules", ".git", "dist", "coverage", ".next"],
  "push_ignore_files": [".env", ".env.local"],
  "push_ignore_extensions": [".log", ".map"],
  "commit_prefix": "[Frontend]"
}
```

**Voice assistant / IoT project (like Jarvis):**

```json
{
  "project_root": ".",
  "downloads_path": "C:\\Users\\gabri\\Downloads",
  "bundle_prefix": "jarvis_update_",
  "deploy_log": "config/deploy_log.json",
  "github_repo": "Klutix/voice-assistant",
  "push_ignore_dirs": ["venv", "__pycache__", ".git", "node_modules", "logs", "piper"],
  "push_ignore_files": [
    "gmail_credentials.json", "gmail_token.json",
    "app_registry_cache.json", "deploy_log.json", ".env"
  ],
  "push_ignore_extensions": [".pyc", ".pyo", ".log", ".wav", ".mp3", ".onnx", ".onnx.json"],
  "auto_update_readme": true,
  "commit_prefix": "[Jarvis Deploy]"
}
```

**Monorepo (run from a subdirectory):**

```json
{
  "project_root": "C:\\Projects\\monorepo\\packages\\api",
  "downloads_path": "~/Downloads",
  "bundle_prefix": "api_update_",
  "github_repo": "myorg/monorepo",
  "commit_prefix": "[API]"
}
```

### Environment Variables

Every scalar config field can be overridden with a `DEPLOY_` prefixed environment variable. These take priority over `deploy.json` values.

| Variable | Overrides | Example |
|---|---|---|
| `DEPLOY_GITHUB_TOKEN` | `github_token` | `ghp_xxxxxxxxxxxx` |
| `DEPLOY_GITHUB_REPO` | `github_repo` | `myuser/myproject` |
| `DEPLOY_DOWNLOADS_PATH` | `downloads_path` | `/custom/bundles/` |
| `DEPLOY_BUNDLE_PREFIX` | `bundle_prefix` | `myapp_update_` |
| `DEPLOY_PROJECT_ROOT` | `project_root` | `/opt/myproject` |
| `DEPLOY_COMMIT_PREFIX` | `commit_prefix` | `[CI Deploy]` |
| `DEPLOY_AUTO_UPDATE_README` | `auto_update_readme` | `true` |

Set them in your shell profile or CI environment:

```bash
# Linux/macOS — add to ~/.bashrc or ~/.zshrc
export DEPLOY_GITHUB_TOKEN="ghp_xxxxxxxxxxxx"

# Windows — Command Prompt
setx DEPLOY_GITHUB_TOKEN "ghp_xxxxxxxxxxxx"

# Windows — PowerShell
[System.Environment]::SetEnvironmentVariable("DEPLOY_GITHUB_TOKEN", "ghp_xxxxxxxxxxxx", "User")
```

### Resolution Order

When the same setting is defined in multiple places, the highest priority wins:

1. **CLI flags** (`--project-root`, `--downloads-path`, `--config`)
2. **Environment variables** (`DEPLOY_*`)
3. **`deploy.json`** (auto-discovered by walking up from cwd)
4. **Built-in defaults**

### `.deployignore`

Optional file in your project root. Adds to the ignore rules from `deploy.json` — both apply.

```
# Directories (trailing slash)
logs/
dist/
data/
models/

# Specific files
credentials.json
secrets.json
local_config.py

# Extensions (leading asterisk)
*.wav
*.mp3
*.onnx
*.sqlite3
```

Use `.deployignore` when your ignore list is long or when you want to manage ignore rules separately from the config file.

---

## Bundle Format

A bundle is a timestamped directory (or `.zip`) containing source files and a manifest.

### Naming

```
{bundle_prefix}{timestamp}
```

Accepted timestamp formats:

| Format | Example |
|---|---|
| `YYYY_MM_DD_HHMMSS` | `update_2026_03_25_143000` |
| `YYYY_MM_DD` | `update_2026_03_25` |
| `YYYYMMDD_HHMMSS` | `update_20260325_143000` |
| `YYYYMMDD` | `update_20260325` |

Bundles are sorted chronologically by their parsed timestamp. Invalid postfixes are warned and skipped.

### Structure

```
update_2026_03_25_143000/
├── update_manifest.json        ← required
├── new_feature.py
├── updated_template.html
└── styles/
    └── theme.css
```

### Manifest (`update_manifest.json`)

```json
{
  "description": "Add user authentication module",
  "files": [
    { "file": "new_feature.py", "destination": "src/auth/feature.py" },
    { "file": "updated_template.html", "destination": "templates/login.html" },
    { "file": "styles/theme.css", "destination": "static/css/theme.css" }
  ]
}
```

- `file` — path relative to the bundle root
- `destination` — path relative to the project root (use forward slashes, parent dirs auto-created)

### Zipping Bundles

The zip must contain a single root folder matching the zip filename:

```
update_2026_03_25_143000.zip
└── update_2026_03_25_143000/
    ├── update_manifest.json
    └── ...
```

Zips are auto-extracted before scanning.

---

## Running Examples

### First-time setup for a new project

```bash
cd ~/my-new-project
deploy init                    # creates deploy.json
# edit deploy.json...
deploy doctor                  # verify everything

# Output:
# 🩺  Deploy Doctor
#   ✅  Config loaded from: ~/my-new-project/deploy.json
#   ✅  Project root exists: ~/my-new-project
#   ✅  Downloads path exists: ~/Downloads
#   ⚠️  No bundles found with prefix 'update_'
#   ⚠️  Deploy log not found (will be created on first deploy)
#   ✅  GitHub token is set
#   ✅  GitHub auth valid — logged in as: myuser
#   ✅  GitHub repo accessible: myuser/my-new-project
```

### Applying a bundle

```bash
deploy

# Output:
# 📦  Bundle : jarvis_update_2026_03_23_120000
#     Time   : 2026-03-23 12:00:00
#     Desc   : Add health check endpoint
#     Files  : 2
#   ✅  health.py  →  src/routes/health.py
#   ✅  test_health.py  →  tests/test_health.py
# ──────────────────────────────────────────────────
# Done. 1 bundle(s) applied.
#       2 file(s) copied,  0 skipped.
#       Logged to config/deploy_log.json
# ──────────────────────────────────────────────────
```

### Applying bundles from a specific date

```bash
deploy apply 2026_03_20

# Applies ALL bundles with timestamps at or after March 20, 2026.
# Useful after being away and having multiple bundles queued up.
```

### Checking what's available

```bash
deploy list

# Output:
# Found 3 bundle(s) in ~/Downloads:
#   update_2026_03_20_090000  |  2026-03-20 09:00:00  |  4 file(s)  |  Refactor config module
#   update_2026_03_22_140000  |  2026-03-22 14:00:00  |  2 file(s)  |  Fix auth bug
#   update_2026_03_23_120000  |  2026-03-23 12:00:00  |  3 file(s)  |  Add test runner assertions
```

### Checking deployment history

```bash
deploy log 3

# Output:
# Deployment History (3 of 8 entries):
# ──────────────────────────────────────────────────────────────────────
#   2026-03-23T12:15:04  |  update_2026_03_23_120000
#     Add test runner assertions
#     Files: 3 applied, 0 skipped  |  Pushed: ✗
#       → core/test_runner.py
#       → featuretesting/tests/test_excel.md
#       → featuretesting/tests/test_filesystem.md
# ──────────────────────────────────────────────────────────────────────
```

### Pushing to GitHub

```bash
# Incremental — only files changed since last push
deploy push

# Output:
# 🔄  Pushing to GitHub: myuser/my-project
#     Mode: INCREMENTAL — 3 changed file(s) to push
#   ✅  Created: src/routes/health.py (a3b2c1d)
#   ✅  Updated: src/auth/handler.py (e4f5a6b)
#   ✅  Created: tests/test_health.py (c7d8e9f)
# ──────────────────────────────────────────────────
# Push complete: 3 succeeded, 0 failed
# ──────────────────────────────────────────────────

# Full project push — use for first time or to resync
deploy push --full

# Output:
# 🔄  Pushing to GitHub: myuser/my-project
#     Mode: FULL — 47 file(s) to push
#   ✅  Updated: README.md (1a2b3c4)
#   ✅  Updated: src/main.py (5d6e7f8)
#   ...
```

### Using CLI overrides

```bash
# Apply bundles from a different downloads folder
deploy --downloads-path /tmp/staging

# Use a specific config file
deploy --config ~/configs/deploy-production.json

# Combine overrides
deploy push --project-root /opt/production --config /etc/deploy/prod.json
```

### Voice mode (for voice assistants)

```bash
deploy --voice

# Output (terse, no emojis):
# Applied 1 update bundle. 3 files updated.
```

---

## AI Assistant Integration

If you use Claude, ChatGPT, or another AI to generate code updates, share the `BUNDLE_SPEC.md` file with the AI at the start of your conversation. It contains the complete specification for how to name bundles, structure the zip, and write the manifest.

The workflow:

1. Paste `BUNDLE_SPEC.md` into the conversation (or reference it in your system prompt)
2. Ask the AI to make changes to your project
3. The AI produces a correctly structured bundle
4. Download it to your Downloads folder
5. Run `deploy`

---

## Project Structure

```
universal-deploy/
├── pyproject.toml              # Package metadata + `deploy` CLI entry point
├── README.md                   # This file
├── SETUP_GUIDE.md              # Step-by-step guide for adding to a new project
├── BUNDLE_SPEC.md              # AI-facing spec for producing bundles
├── LICENSE
├── deploy.json.example         # Example config
├── .deployignore.example       # Example ignore file
└── src/
    └── universal_deploy/
        ├── __init__.py         # Version
        ├── cli.py              # CLI entry point + arg parsing + legacy translation
        ├── config.py           # Config loading, resolution, defaults, .deployignore
        ├── bundles.py          # Discovery, timestamp parsing, extraction, application
        ├── github.py           # GitHub Contents API push
        ├── log.py              # Deploy audit log
        └── doctor.py           # Diagnostic checks
```

## License

MIT
