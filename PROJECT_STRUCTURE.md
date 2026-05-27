# Project Structure

Keep the repository root limited to deployable source and configuration:

- `server.py` - Flask backend and generation pipeline.
- `wsgi.py` - Gunicorn entry point.
- `static/index.html` - production single-page UI.
- `static/login.html`, `static/logo.png` - static assets used by routes.
- `generate_model.py` - local shaped fallback generator.
- `Dockerfile`, `Procfile`, `requirements.txt` - deployment/runtime files.
- `README.md`, `DEPLOY_GUIDE.txt`, `PROJECT_STRUCTURE.md` - documentation.
- `settings.example.json` - non-secret local configuration template.

Runtime files are intentionally ignored and should not be committed:

- `settings.json`
- `folders.json`
- `history*.json`
- `state.json`
- `rocket.glb`
- `logs/`
- `storage/`
- generated `models/**/*.glb`
- `__pycache__/` and `*.pyc`

The application creates missing runtime files and directories on startup. Keep API
keys in environment variables in production, or in a local untracked
`settings.json` during development.
