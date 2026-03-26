# universal-deploy

A configurable, project-agnostic update deployer with GitHub push, audit logging, and bundle management. Drop it into any project — no code changes needed, just a `deploy.json`.

## Install

```bash
# From the repo
pip install .

# Or in editable mode for development
pip install -e .
```

After install, the `deploy` command is available globally.

## Quick Start

```bash
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
```

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

```json
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
```

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
| `push_ignore_extensions` | array | see above | Extensions to exclude from push |
| `auto_update_readme` | bool | `false` | Auto-update README changelog on push |
| `commit_prefix` | string | `"[Deploy]"` | Prefix for GitHub commit messages |

### Environment Variables

Every config field can be overridden with a `DEPLOY_` prefixed env var:

```bash
export DEPLOY_GITHUB_TOKEN="ghp_xxxxxxxxxxxx"
export DEPLOY_GITHUB_REPO="myuser/myproject"
export DEPLOY_DOWNLOADS_PATH="/custom/path"
export DEPLOY_BUNDLE_PREFIX="myapp_update_"
export DEPLOY_COMMIT_PREFIX="[MyApp]"
export DEPLOY_AUTO_UPDATE_README="true"
```

### Resolution Order

Settings are resolved with this priority (highest wins):

1. **CLI flags** (`--project-root`, `--downloads-path`, `--config`)
2. **Environment variables** (`DEPLOY_*`)
3. **`deploy.json`** (found by walking up from cwd)
4. **Built-in defaults**

### `.deployignore`

Optional file in your project root. Adds to the ignore rules from `deploy.json`.

```
# Directories (trailing slash)
logs/
dist/

# Specific files
credentials.json
secrets.json

# Extensions (leading asterisk)
*.wav
*.mp3
*.onnx
```

## Bundle Format

A bundle is a directory (or `.zip` that extracts to one) containing:

```
update_2026_03_20_120000/
├── update_manifest.json
├── file1.py
├── file2.html
└── ...
```

### `update_manifest.json`

```json
{
  "description": "Add user authentication module",
  "files": [
    { "file": "file1.py", "destination": "src/auth/login.py" },
    { "file": "file2.html", "destination": "templates/login.html" }
  ]
}
```

## Migrating from the Original `deploy.py`

If you're coming from the Jarvis-specific `deploy.py`:

1. **Install the package**: `pip install .` (or `pip install universal-deploy`)
2. **Run `deploy init`** in your project root
3. **Edit `deploy.json`**:
   - Set `bundle_prefix` to `"jarvis_update_"` (to match your existing bundles)
   - Set `downloads_path` to your Windows Downloads path
   - Set `project_root` to your project path
   - Move your custom ignore entries (`piper/`, `gmail_credentials.json`, etc.) into the ignore arrays or a `.deployignore` file
   - Set `commit_prefix` to `"[Jarvis Deploy]"` if you want to keep the same commit style
   - Set `auto_update_readme` to `true` if you used the changelog feature
4. **Set env vars**: `DEPLOY_GITHUB_TOKEN` replaces `GITHUB_TOKEN`
5. **Legacy CLI still works**: `deploy --list`, `deploy --push --full`, etc. are translated automatically

## Project Structure

```
universal-deploy/
├── pyproject.toml                  # Package metadata + CLI entry point
├── deploy.json.example             # Example config
├── .deployignore.example           # Example ignore file
├── README.md
├── LICENSE
└── src/
    └── universal_deploy/
        ├── __init__.py             # Version
        ├── cli.py                  # CLI entry point + argument parsing
        ├── config.py               # Config loading, resolution, defaults
        ├── bundles.py              # Bundle discovery, extraction, application
        ├── github.py               # GitHub Contents API push
        ├── log.py                  # Deploy audit log
        └── doctor.py               # Diagnostic checks
```

## License

MIT
