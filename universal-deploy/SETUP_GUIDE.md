# SETUP_GUIDE.md — Adding universal-deploy to Your Project

This guide walks you through adding `universal-deploy` to any existing project,
from zero to working deploys in about 5 minutes.

---

## Prerequisites

- **Python 3.10+** installed
- Your project already exists in a local directory
- (Optional) A GitHub personal access token if you want the push feature

---

## Step 1 — Install the Tool

**Option A: Install from the repo (recommended)**

```bash
# Clone or download the universal-deploy repo
git clone https://github.com/yourusername/universal-deploy.git

# Install globally
cd universal-deploy
pip install .
```

After this, the `deploy` command is available anywhere on your system.

**Option B: Install in a virtual environment**

```bash
cd universal-deploy
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install .
```

**Verify installation:**

```bash
deploy --version
# → deploy 1.0.0
```

---

## Step 2 — Initialize Your Project

Navigate to your project root and run:

```bash
cd ~/my-project
deploy init
```

This creates a `deploy.json` file in your project directory with sensible defaults.

---

## Step 3 — Configure `deploy.json`

Open `deploy.json` and adjust the settings for your project:

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

### What to Change

| Field | What to Set |
|-------|-------------|
| `project_root` | Usually `"."` (current dir). Set an absolute path if you run `deploy` from elsewhere. |
| `downloads_path` | Where your bundles land. Typically `"~/Downloads"` or a custom staging folder. |
| `bundle_prefix` | A prefix unique to your project. Examples: `"myapp_update_"`, `"api_patch_"`, `"update_"`. |
| `commit_prefix` | Shows in GitHub commits. Examples: `"[MyApp]"`, `"[API Deploy]"`. |
| `github_repo` | Your repo in `"username/reponame"` format. Leave empty for auto-detection. |

### What to Leave Alone (Usually)

- `manifest_file` — only change if you have a naming conflict
- `deploy_log` — the default `config/deploy_log.json` works for most projects

---

## Step 4 — Set Up Ignore Rules

You have two options for controlling what gets pushed to GitHub (use one or both):

**Option A: In `deploy.json`** (already done above)

Add project-specific entries to the arrays:

```json
{
  "push_ignore_dirs": ["venv", "__pycache__", ".git", "node_modules", "data", "models"],
  "push_ignore_files": [".env", "credentials.json", "local_settings.py"],
  "push_ignore_extensions": [".pyc", ".log", ".sqlite3", ".wav"]
}
```

**Option B: Create a `.deployignore` file** (cleaner for large lists)

Create a file called `.deployignore` in your project root:

```
# Directories (trailing slash)
data/
models/
logs/
dist/

# Specific files
credentials.json
local_settings.py

# Extensions
*.sqlite3
*.wav
*.onnx
```

The `.deployignore` rules are **merged** with the `deploy.json` rules. Both apply.

---

## Step 5 — Set Up GitHub Push (Optional)

If you want `deploy push` to work:

**1. Create a GitHub personal access token:**

- Go to https://github.com/settings/tokens
- Generate a new token (classic) with `repo` scope
- Copy the token

**2. Set it as an environment variable:**

```bash
# Linux/macOS — add to ~/.bashrc or ~/.zshrc
export DEPLOY_GITHUB_TOKEN="ghp_your_token_here"

# Windows — Command Prompt
setx DEPLOY_GITHUB_TOKEN "ghp_your_token_here"

# Windows — PowerShell
[System.Environment]::SetEnvironmentVariable("DEPLOY_GITHUB_TOKEN", "ghp_your_token_here", "User")
```

**3. Set your repo** (or let it auto-detect):

```bash
export DEPLOY_GITHUB_REPO="yourusername/your-project"
```

> **Security note:** Never put your token directly in `deploy.json`. Use the
> environment variable. The `deploy.json` `github_token` field exists for
> CI/CD environments where env injection is preferred through other means.

---

## Step 6 — Verify Everything

Run the doctor to make sure it's all working:

```bash
deploy doctor
```

You should see something like:

```
🩺  Deploy Doctor

  ✅  Config loaded from: /home/you/my-project/deploy.json
  ✅  Project root exists: /home/you/my-project
  ✅  Downloads path exists: /home/you/Downloads
  ⚠️  No bundles found with prefix 'update_'
  ⚠️  Deploy log not found (will be created on first deploy)
  ✅  .deployignore found: /home/you/my-project/.deployignore
  ✅  GitHub token is set
  ✅  GitHub auth valid — logged in as: yourusername
  ✅  GitHub repo accessible: yourusername/my-project
```

Warnings are fine at this stage — there are no bundles yet and the log hasn't been created.

---

## Step 7 — Add to `.gitignore`

If your project uses git, add the deploy log to `.gitignore` (it's local state):

```
# universal-deploy
config/deploy_log.json
```

You may also want to commit your `deploy.json` and `.deployignore` so teammates
share the same config.

---

## Step 8 — Create Your First Bundle

See `BUNDLE_SPEC.md` for the full specification. Here's the quick version:

```
my_downloads_folder/
└── update_2026_03_25_143000/
    ├── update_manifest.json
    └── new_feature.py
```

Where `update_manifest.json` contains:

```json
{
  "description": "Add new feature module",
  "files": [
    {
      "file": "new_feature.py",
      "destination": "src/features/new_feature.py"
    }
  ]
}
```

Then run:

```bash
deploy
```

---

## Day-to-Day Usage

```bash
# Apply the latest bundle
deploy

# Apply all bundles from a specific date
deploy apply 2026_03_25

# See what bundles are available
deploy list

# Check deployment history
deploy log
deploy log 5          # last 5

# Push deployed changes to GitHub
deploy push           # incremental (only new changes)
deploy push --full    # entire project (first time setup)
```

---

## Using with AI Assistants

If you use Claude, ChatGPT, or another AI to generate code updates:

1. **Share `BUNDLE_SPEC.md`** with the AI at the start of the conversation
   (paste it in, or reference it in your system prompt).
2. The AI will know exactly how to structure the bundle, name it, and write the manifest.
3. Download the bundle, drop it in your downloads folder, and run `deploy`.

This is the intended workflow — the AI produces correctly structured bundles,
and the deploy tool handles the rest.

---

## Folder Structure After Setup

```
my-project/
├── deploy.json              ← created by 'deploy init'
├── .deployignore             ← your ignore rules (optional)
├── config/
│   └── deploy_log.json       ← auto-created on first deploy
├── src/
│   └── ...                   ← your project code
└── ...
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `deploy: command not found` | Make sure `pip install .` completed. Check `pip show universal-deploy`. |
| `No deploy.json found` | Run `deploy init` in your project root, or use `--config path/to/deploy.json`. |
| `Downloads path not found` | Update `downloads_path` in `deploy.json` to match your OS. |
| `No bundles found` | Check that your bundle uses the correct `bundle_prefix` and a valid timestamp format. |
| `GitHub auth failed` | Regenerate your token at github.com/settings/tokens and re-export it. |
| `Could not detect GitHub repo` | Set `github_repo` explicitly in `deploy.json` or `DEPLOY_GITHUB_REPO` env var. |

---

## Uninstalling

```bash
pip uninstall universal-deploy
```

The `deploy.json`, `.deployignore`, and `config/deploy_log.json` in your project
are just files — delete them if you no longer need them.
