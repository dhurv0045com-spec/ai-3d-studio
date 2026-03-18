import re

FILE = "server.py"
print("Reading " + FILE + "...")
with open(FILE, "r", encoding="utf-8") as f:
    code = f.read()

original = code
changes = []

# ============================================================
# FIX 1 - folders_delete saves h instead of h_new (BUG!)
# ============================================================
old1 = "    save_history(h)\n\n    # Remove from index\n    idx = load_index()\n    idx = [e for e in idx if e.get(\"folder\") != name]\n    save_index(idx)\n\n    return jsonify({\"success\": True, \"folders\": load_folders(user_id)})"
new1 = "    save_history(h_new)\n\n    # Remove from index\n    idx = load_index()\n    idx = [e for e in idx if e.get(\"folder\") != name]\n    save_index(idx)\n\n    return jsonify({\"success\": True, \"folders\": load_folders(user_id)})"
if old1 in code:
    code = code.replace(old1, new1, 1)
    changes.append("FIX 1: folders_delete now saves h_new not h (critical bug fix)")
else:
    print("  WARN FIX1: folders_delete pattern not found")

# ============================================================
# FIX 2 - Track deleted model IDs in a file so sync skips them
# Add DELETED_IDS_FILE constant after HISTORY_FILE line
# ============================================================
old2 = 'HISTORY_FILE    = os.path.join(BASE_DIR, "history.json")'
new2 = ('HISTORY_FILE    = os.path.join(BASE_DIR, "history.json")\n'
        'DELETED_IDS_FILE = os.path.join(BASE_DIR, "deleted_ids.json")')
if old2 in code and "DELETED_IDS_FILE" not in code:
    code = code.replace(old2, new2, 1)
    changes.append("FIX 2a: DELETED_IDS_FILE constant added")

# ============================================================
# FIX 3 - Add load/save deleted_ids helpers after save_history
# ============================================================
old3 = "def add_history_entry(entry):"
new3 = (
    "def load_deleted_ids():\n"
    "    try:\n"
    "        if os.path.exists(DELETED_IDS_FILE):\n"
    "            with open(DELETED_IDS_FILE, 'r', encoding='utf-8') as f:\n"
    "                return set(json.load(f))\n"
    "    except Exception:\n"
    "        pass\n"
    "    return set()\n"
    "\n"
    "def save_deleted_id(model_id):\n"
    "    try:\n"
    "        ids = load_deleted_ids()\n"
    "        ids.add(str(model_id))\n"
    "        with open(DELETED_IDS_FILE, 'w', encoding='utf-8') as f:\n"
    "            json.dump(list(ids), f)\n"
    "    except Exception as e:\n"
    "        log_srv('[DELETED_IDS] save failed: ' + str(e))\n"
    "\n"
    "def add_history_entry(entry):"
)
if old3 in code and "load_deleted_ids" not in code:
    code = code.replace(old3, new3, 1)
    changes.append("FIX 3: load_deleted_ids / save_deleted_id helpers added")

# ============================================================
# FIX 4 - delete_model: also call save_deleted_id
# ============================================================
old4 = "        # Remove from history\n        h = [e for e in h if str(e.get(\"id\")) != str(target_entry.get(\"id\"))]\n        save_history(h)"
new4 = ("        # Track deleted ID so sync never brings it back\n"
        "        save_deleted_id(str(target_entry.get('id', '')))\n"
        "        # Remove from history\n"
        "        h = [e for e in h if str(e.get(\"id\")) != str(target_entry.get(\"id\"))]\n"
        "        save_history(h)")
if old4 in code:
    code = code.replace(old4, new4, 1)
    changes.append("FIX 4: delete_model now persists deleted ID to file")
else:
    print("  WARN FIX4: delete_model remove-from-history pattern not found")

# ============================================================
# FIX 5 - sync_cloudinary_history: skip deleted IDs + store user_id
# Replace the entry building loop
# ============================================================
old5 = (
    '                entry = {\n'
    '                    "id": ts_int,\n'
    '                    "prompt": ctx.get("prompt", "imported from cloud"),\n'
    '                    "color": ctx.get("color", "#aaaaaa"),\n'
    '                    "folder": ctx.get("folder", "default"),\n'
    '                    "service": "Cloudinary Sync",\n'
    '                    "file": "", # Since it\'s from cloud, local file might not exist\n'
    '                    "cloud_url": r.get("secure_url", ""),\n'
    '                    "created": r.get("created_at", str(ts_int)),\n'
    '                    "size": r.get("bytes", 0),\n'
    '                    "quality_score": 0\n'
    '                }\n'
    '                new_history.append(entry)'
)
new5 = (
    '                # Skip permanently deleted models\n'
    '                deleted_ids = load_deleted_ids()\n'
    '                if str(ts_int) in deleted_ids:\n'
    '                    continue\n'
    '                entry = {\n'
    '                    "id": ts_int,\n'
    '                    "prompt": ctx.get("prompt", "imported from cloud"),\n'
    '                    "color": ctx.get("color", "#aaaaaa"),\n'
    '                    "folder": ctx.get("folder", "default"),\n'
    '                    "service": "Cloudinary Sync",\n'
    '                    "file": "",\n'
    '                    "cloud_url": r.get("secure_url", ""),\n'
    '                    "created": r.get("created_at", str(ts_int)),\n'
    '                    "size": r.get("bytes", 0),\n'
    '                    "quality_score": 0,\n'
    '                    "user_id": ctx.get("user_id", "anonymous")\n'
    '                }\n'
    '                new_history.append(entry)'
)
if old5 in code:
    code = code.replace(old5, new5, 1)
    changes.append("FIX 5: sync_cloudinary_history skips deleted IDs + stores user_id")
else:
    print("  WARN FIX5: sync entry pattern not found")

# ============================================================
# FIX 6 - Call startup_health_check and sync on boot
# Find the startup call at bottom of file
# ============================================================
old6 = "validate_env()\nfrom collections import defaultdict as _defaultdict"
new6 = "validate_env()\nfrom collections import defaultdict as _defaultdict"

# Look for where startup is called
startup_call = "startup_health_check()"
sync_call = "sync_cloudinary_history()"
startup_thread = "start_key_resurrection()"

# Find if startup is already called
if startup_call in code:
    # check if sync is called near startup
    idx = code.find(startup_call)
    nearby = code[idx:idx+200]
    if sync_call not in nearby:
        # Add sync call right after startup_health_check()
        code = code.replace(
            startup_call + "\n",
            startup_call + "\n"
            "try:\n"
            "    threading.Thread(target=sync_cloudinary_history, daemon=True).start()\n"
            "    log_srv('[STARTUP] Cloudinary sync thread started')\n"
            "except Exception as _se:\n"
            "    log_srv('[STARTUP] sync start failed: ' + str(_se))\n",
            1
        )
        changes.append("FIX 6: Cloudinary sync called on startup in background thread")
    else:
        print("  INFO FIX6: sync already called near startup")
else:
    print("  WARN FIX6: startup_health_check() call not found")

# ============================================================
# FIX 7 - Redirect / to /login if not logged in
# Add login check to root route
# ============================================================
old7 = "@app.route(\"/\")\ndef index():"
new7 = ("@app.route(\"/\")\n"
        "def index():\n"
        "    user = session.get('user')\n"
        "    if not user:\n"
        "        return redirect('/login')\n")
# Only do this if index() currently just serves the file without login check
if old7 in code:
    # Check what's right after def index():
    idx = code.find(old7)
    snippet = code[idx:idx+200]
    if "redirect('/login')" not in snippet:
        code = code.replace(old7, new7, 1)
        changes.append("FIX 7: Root / redirects to /login if not logged in")
    else:
        print("  INFO FIX7: login redirect already in place")
else:
    print("  WARN FIX7: root route not found")

# ============================================================
# FIX 8 - Guest mode: clicking guest sets anonymous session
# Add /guest route
# ============================================================
guest_route = (
    "\n@app.route('/guest')\n"
    "def guest_login():\n"
    "    session['user'] = {'sub': 'anonymous', 'name': 'Guest', 'email': '', 'picture': ''}\n"
    "    return redirect('/')\n"
)
if "/guest" not in code:
    # Add after auth_me route
    code = code.replace(
        "@app.route('/auth/me')\ndef auth_me():",
        "@app.route('/auth/me')\ndef auth_me():",
        1
    )
    # Find auth_logout and add after it
    idx = code.find("def auth_logout():")
    if idx != -1:
        # find end of auth_logout function
        end_idx = code.find("\n\n@app", idx)
        if end_idx != -1:
            code = code[:end_idx] + guest_route + code[end_idx:]
            changes.append("FIX 8: /guest route added for guest login")
    else:
        print("  WARN FIX8: auth_logout not found")

# ============================================================
# WRITE OUTPUT
# ============================================================
if code != original:
    with open(FILE, "w", encoding="utf-8") as f:
        f.write(code)
    print("\nDone! " + str(len(changes)) + " fixes applied:")
    for c in changes:
        print("  + " + c)
    print("\nFile saved: " + FILE)
else:
    print("\nNo changes made - check warnings above")
