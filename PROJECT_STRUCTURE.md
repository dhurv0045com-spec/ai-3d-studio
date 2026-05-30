# Project Structure

> Complete file manifest, runtime behavior, and repository hygiene policy for Aurex AI 3D Studio V8.0.

---

## Source Files (Committed)

These are the core files that make up the application. All are tracked in Git.

### Backend

| File | Lines | Description |
|---|---|---|
| [`server.py`](server.py) | ~7,500 | **The entire Flask backend.** Routes, LLM cascade (OpenRouter → Gemini → Groq), Blender subprocess orchestration, Cloudinary uploads, Supabase REST API, Google OAuth, key rotation, caching, rate limiting, GLB validation, quality scoring, pipeline stage logging, preset scripts, and the generation pipeline. |
| [`generate_model.py`](generate_model.py) | ~1,389 | **Pure-Python GLB fallback builder.** Zero external dependencies — uses only `struct`, `math`, `os`, `json`. Contains the `GLBBuilder` class with geometry primitives (box, sphere, cylinder, cone, torus) and 55 hand-crafted shape builders (rocket, dragon, car, robot, castle, spaceship, etc.). This is the last safety net — it **never raises** and **always produces a valid file**. |
| [`wsgi.py`](wsgi.py) | 27 | **Gunicorn WSGI entry point.** Runs `setup_dirs()`, `startup_health_check()`, and `start_key_resurrection()` on import. Creates a placeholder `rocket.glb` if none exists. |

### Frontend

| File | Size | Description |
|---|---|---|
| [`static/index.html`](static/index.html) | ~282 KB | **Single-page application.** Contains the Three.js 3D viewer, prompt input UI, pipeline visualizer, variant selector, history panel, folder manager, community gallery, hand control panel, and all embedded CSS/JS. |
| [`static/login.html`](static/login.html) | ~45 KB | **Animated login/landing page.** Google OAuth sign-in button, guest access option, and animated 3D background effects. |
| [`static/gesture-engine.js`](static/gesture-engine.js) | ~1,417 lines | **MediaPipe hand gesture controller (v2).** One Euro filter for smooth landmark tracking, gesture classification (open palm, fist, pinch, pointing, peace sign), orbit/pan/zoom application, momentum/inertia system, part-level focus, two-hand zoom, camera preview with skeleton overlay, and the full settings/HUD UI. |
| [`static/logo.png`](static/logo.png) | ~41 KB | App logo used in login page and PWA manifest. |

### Configuration & Deployment

| File | Description |
|---|---|
| [`Dockerfile`](Dockerfile) | Docker build: `python:3.11-slim` → installs X11/GL libs → downloads Blender 4.2 Linux x64 → installs pip deps → exposes port 8080 → runs gunicorn. |
| [`Procfile`](Procfile) | Heroku-style process declaration: `web: gunicorn wsgi:app`. |
| [`requirements.txt`](requirements.txt) | Python dependencies: `flask`, `flask-cors`, `requests`, `urllib3`, `Pillow`, `numpy`, `pyyaml`, `authlib`, `gunicorn`. Optional: `torch` (Shap-E). |
| [`railway.json`](railway.json) | Railway platform build settings. |
| [`nixpacks.toml`](nixpacks.toml) | Nixpacks build hints for Railway auto-detection. |
| [`settings.example.json`](settings.example.json) | Local config template with sections: `ai` (provider, model, keys), `generation` (defaults, timeouts), `quality` (min thresholds), `blender` (path, version), `paths` (directory overrides). |

### Documentation

| File | Description |
|---|---|
| [`README.md`](README.md) | Project overview, architecture, quick start, API reference, deployment guide. |
| [`USAGE.md`](USAGE.md) | End-user guide: prompting, viewer controls, gestures, variants, history, export. |
| [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md) | This file. |
| [`DEPLOY_GUIDE.txt`](DEPLOY_GUIDE.txt) | Step-by-step Railway deployment walkthrough for beginners (Git install → GitHub setup → Railway deploy → troubleshooting). |

---

## Runtime Files (Git-Ignored)

These files are created automatically by the application at startup or during operation. They are listed in `.gitignore` and **must not be committed**.

### Application State

| File / Directory | Purpose |
|---|---|
| `settings.json` | Local development settings (copy of `settings.example.json` with real API keys). |
| `state.json` | Current generation state — serialized on every status change. |
| `history.json` | Legacy shared history file (superseded by per-user files). |
| `history_*.json` | Per-user local history files (e.g., `history_user@example.com.json`). |
| `folders.json` | Local folder list fallback when Supabase is unavailable. |

### Generated Content

| File / Directory | Purpose |
|---|---|
| `rocket.glb` | Current model placeholder — always exists (created on startup if missing). |
| `models/` | Parent directory for all model files. |
| `models/generated/` | Per-request generated GLBs (UUIDs, auto-cleaned after 24h). |
| `models/cache/` | Prompt+color hash-keyed GLB cache. |
| `models/presets/` | Preset model storage. |
| `models/scripts/` | Saved Blender scripts. |
| `models/variant_*.glb` | Temporary variant generation outputs. |
| `storage/` | Per-user file storage tree (`storage/users/<sub_id>/<folder>/`). |

### Logs

| File | Purpose |
|---|---|
| `logs/server.log` | HTTP request logging, key rotation events, startup diagnostics. |
| `logs/generation.log` | Per-generation pipeline log (stages, timing, LLM responses). |
| `logs/error.log` | Errors and exceptions. |

### Temporary / Transient

| File | Purpose |
|---|---|
| `_last_gemini_script.py` | Most recent LLM-generated Blender script (for live preview). |
| `_temp_export_script.py` | Temporary Blender conversion script (OBJ/FBX export). |
| `_temp_output.glb` | Temporary generation output. |
| `_temp_preset_script.py` | Temporary preset Blender script. |
| `shapee_installed.flag` | Sentinel file indicating Shap-E is available. |
| `__pycache__/`, `*.pyc` | Python bytecode cache. |

---

## Directory Tree (Runtime)

After the application starts and a few models have been generated, the directory looks like this:

```
ai-3d-studio/
├── server.py
├── generate_model.py
├── wsgi.py
├── static/
│   ├── index.html
│   ├── login.html
│   ├── gesture-engine.js
│   └── logo.png
├── models/                        ← git-ignored
│   ├── generated/
│   │   ├── a1b2c3d4...f.glb
│   │   └── e5f6g7h8...i.glb
│   ├── cache/
│   │   ├── 9f86d081884c...a3.glb
│   │   └── d4735e3a265e...b4.glb
│   ├── presets/
│   └── scripts/
├── storage/                       ← git-ignored
│   └── users/
│       ├── user@example.com/
│       │   ├── default/
│       │   ├── vehicles/
│       │   ├── creatures/
│       │   └── buildings/
│       └── guest/
│           └── default/
├── logs/                          ← git-ignored
│   ├── server.log
│   ├── generation.log
│   └── error.log
├── Dockerfile
├── Procfile
├── requirements.txt
├── railway.json
├── nixpacks.toml
├── settings.example.json
├── DEPLOY_GUIDE.txt
├── PROJECT_STRUCTURE.md
├── USAGE.md
├── README.md
└── .gitignore
```

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **Single `server.py` file** | Simplifies deployment and debugging. All 7,500 lines are in one place — no module fragmentation for a production Flask app that runs as one process. |
| **No Supabase Python client** | The official Python client was reading `SUPABASE_KEY` instead of `SUPABASE_ANON_KEY`, causing silent `None` in production. All Supabase calls use `requests` via `supabase_request()`. |
| **Pure-Python GLB builder** | The fallback generator (`generate_model.py`) has zero external deps — it can produce a valid model even if PyTorch, Blender, and all APIs are down. |
| **Per-user history files** | Prevents cross-user data mixing when Supabase is temporarily unavailable. Each user gets `history_<email>.json`. |
| **Environment variable case-insensitivity** | All key-loading code lowercases env var names before matching, so `GEMINI_KEY_1` and `gemini_key_1` both work. |
| **Gesture engine as separate `.js`** | Keeps the 1,400-line MediaPipe integration modular and independently testable outside `index.html`. |

---

## Startup Sequence

When the application starts (via `python server.py` or `gunicorn wsgi:app`):

1. **`setup_dirs()`** — Creates all required directories (`models/`, `logs/`, `storage/`, etc.).
2. **Log files** — Touches `server.log`, `generation.log`, `error.log`.
3. **`reset_state()`** — Resets generation state to idle.
4. **`startup_health_check()`** — Checks Python version, Blender installation, Gemini key health, Cloudinary status, disk space, Shap-E availability.
5. **`start_key_resurrection()`** — Starts a background thread that periodically revives transiently-failed API keys (default: every 900 seconds).
6. **Fallback GLB** — Creates `rocket.glb` if it doesn't exist.
7. **Flask app** — Binds to `0.0.0.0:$PORT` (default 5000 locally, 8080 in Docker).

---

<div align="center">
  <sub><em>Aurex AI 3D Studio V8.0 — Project Structure Reference</em></sub>
</div>
