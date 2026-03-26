# BUNDLE_SPEC.md — How to Create Update Bundles for This Project

> **Audience:** This document is written for AI assistants (Claude, ChatGPT, Copilot, etc.)
> and human developers who need to produce update bundles that the `universal-deploy`
> tool can consume. If you are an AI assistant, follow these rules exactly.

---

## What Is a Bundle?

A **bundle** is a timestamped directory (or `.zip` file) containing:

1. The actual source files to deploy.
2. A **manifest** (`update_manifest.json`) that maps each source file to its
   destination path inside the project.

The deploy tool scans a configurable downloads directory, finds bundles by their
naming prefix, and copies the files into the project according to the manifest.

---

## Naming Convention

```
{prefix}{timestamp}
```

| Component | Description | Example |
|-----------|-------------|---------|
| `prefix` | The project's configured `bundle_prefix` from `deploy.json`. Ask the user what theirs is, or default to `update_`. | `update_` |
| `timestamp` | A sortable timestamp in one of the accepted formats (see below). **Always use UTC or local time consistently.** | `2026_03_25_143000` |

### Accepted Timestamp Formats

| Format | Example | Notes |
|--------|---------|-------|
| `YYYY_MM_DD_HHMMSS` | `2026_03_25_143000` | **Preferred.** Most precise. |
| `YYYY_MM_DD` | `2026_03_25` | Date only — use when only one bundle per day. |
| `YYYYMMDD_HHMMSS` | `20260325_143000` | Compact with time. |
| `YYYYMMDD` | `20260325` | Compact date only. |

**Rules:**
- The timestamp MUST be the **entire postfix** after the prefix — no extra suffixes, labels, or version numbers.
- Bundles are sorted chronologically by their parsed timestamp. Lexicographic tricks won't work if the format is wrong.

✅ `update_2026_03_25_143000`
✅ `myapp_update_2026_03_25`
❌ `update_2026_03_25_v2` — extra suffix
❌ `update_march_25` — not a parseable timestamp
❌ `update_25_03_2026` — wrong field order (must be YYYY first)

---

## Directory Structure

```
update_2026_03_25_143000/
├── update_manifest.json        ← REQUIRED
├── auth_handler.py             ← source files (flat or nested)
├── login.html
├── styles/
│   └── auth.css
└── README_patch.md
```

- All source files referenced in the manifest **must** exist at the paths specified in the `"file"` field.
- Files can be flat (all in the root) or in subdirectories — just make sure `"file"` matches.

---

## Manifest Format (`update_manifest.json`)

```json
{
  "description": "A short human-readable summary of what this update does",
  "files": [
    {
      "file": "auth_handler.py",
      "destination": "src/auth/auth_handler.py"
    },
    {
      "file": "login.html",
      "destination": "templates/login.html"
    },
    {
      "file": "styles/auth.css",
      "destination": "static/css/auth.css"
    }
  ]
}
```

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `description` | string | **Yes** | What this bundle does. Logged in the audit trail. Be specific: "Add OAuth2 login flow" not "update". |
| `files` | array | **Yes** | List of file mappings. |
| `files[].file` | string | **Yes** | Path to the source file **relative to the bundle root**. |
| `files[].destination` | string | **Yes** | Path where the file should be placed **relative to the project root**. Use forward slashes (`/`) even on Windows. |

### Rules for the Manifest

1. **Every file in the bundle that should be deployed MUST be listed.** Unlisted files are ignored.
2. **`destination` paths are relative to the project root**, not absolute. The deploy tool resolves them.
3. **Parent directories are auto-created.** If `destination` is `src/new_module/handler.py` and `src/new_module/` doesn't exist yet, it will be created.
4. **Existing files are overwritten** without prompting. The deploy log records what was replaced.
5. **Do NOT include the manifest itself** (`update_manifest.json`) in the `files` array.
6. **Use forward slashes** in all paths, even on Windows.

---

## Zipping a Bundle

The tool auto-extracts `.zip` files before scanning for directories. When creating a zip:

```
update_2026_03_25_143000.zip
└── update_2026_03_25_143000/       ← the zip MUST contain a single root folder
    ├── update_manifest.json            matching the zip's stem name
    ├── file1.py
    └── file2.html
```

**Critical:** The zip must extract to a directory whose name matches the zip filename (minus `.zip`). This means the zip contains **one root folder**, not loose files.

✅ Correct — zip contains: `update_2026_03_25_143000/update_manifest.json`
❌ Wrong — zip contains: `update_manifest.json` (loose at root)

### How to Create the Zip

**From a terminal (any OS):**
```bash
cd ~/Downloads
zip -r update_2026_03_25_143000.zip update_2026_03_25_143000/
```

**From Python:**
```python
import zipfile
from pathlib import Path
from datetime import datetime

def create_bundle_zip(bundle_dir: Path, output_dir: Path = None):
    """Zip a bundle directory for deployment."""
    output_dir = output_dir or bundle_dir.parent
    zip_path = output_dir / f"{bundle_dir.name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in bundle_dir.rglob("*"):
            if file.is_file():
                arcname = f"{bundle_dir.name}/{file.relative_to(bundle_dir)}"
                zf.write(file, arcname)
    return zip_path
```

---

## AI Assistant Instructions

When a user asks you to prepare an update for a project that uses `universal-deploy`:

### Step 1 — Determine the Bundle Prefix

Ask the user or check their `deploy.json` for the `bundle_prefix` value. Default: `update_`.

### Step 2 — Generate the Timestamp

Use the current date/time in `YYYY_MM_DD_HHMMSS` format:

```python
from datetime import datetime
ts = datetime.now().strftime("%Y_%m_%d_%H%M%S")
bundle_name = f"{prefix}{ts}"  # e.g. "update_2026_03_25_143000"
```

### Step 3 — Understand the Project Structure

Before writing the manifest, you MUST understand where files live in the project. Ask the user for their project structure, or review it if provided. The `destination` paths must match real locations in the project tree.

### Step 4 — Create the Files

Write each source file with the changes needed.

### Step 5 — Write the Manifest

Create `update_manifest.json` with:
- A clear `description` of the change
- A `files` entry for every file, mapping `"file"` (name in the bundle) to `"destination"` (path in the project)

### Step 6 — Package It

Either:
- Give the user a directory they can place in their downloads folder, OR
- Give them a `.zip` file structured correctly (single root folder matching the name)

### Step 7 — Tell the User How to Apply

```
Place the bundle (or zip) in your downloads folder, then run:
    deploy
Or to apply from a specific date forward:
    deploy apply 2026_03_25
```

---

## Example: Complete Bundle

User request: *"Add a health check endpoint to my Flask API."*

**Bundle name:** `update_2026_03_25_143000`

**Bundle contents:**

`update_manifest.json`:
```json
{
  "description": "Add /health endpoint for uptime monitoring",
  "files": [
    {
      "file": "health.py",
      "destination": "src/routes/health.py"
    },
    {
      "file": "test_health.py",
      "destination": "tests/test_health.py"
    }
  ]
}
```

`health.py`:
```python
from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)

@health_bp.route("/health")
def health_check():
    return jsonify({"status": "ok"}), 200
```

`test_health.py`:
```python
def test_health_endpoint(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json["status"] == "ok"
```

---

## Common Mistakes to Avoid

| Mistake | Why It Breaks |
|---------|---------------|
| Extra text after timestamp (`update_2026_03_25_v2`) | Timestamp parser rejects it |
| Loose files in zip (no root folder) | Extracts into downloads root, not found as a bundle directory |
| Missing manifest | Bundle is skipped entirely |
| `destination` as absolute path (`C:\Users\...`) | Copies to wrong location; not portable |
| Forgetting to list a file in the manifest | File sits in bundle but never gets deployed |
| Using backslashes in paths | Works on Windows only; use `/` always |
