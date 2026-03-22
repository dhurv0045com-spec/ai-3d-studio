"""
Reads the server.py SOURCE from stdin (or a provided path),
applies all 4 fixes, writes to OUTPUT path.
Usage: python3 apply_fixes.py input.py output.py
"""
import re, sys

if len(sys.argv) < 3:
    print("Usage: apply_fixes.py input.py output.py")
    sys.exit(1)

with open(sys.argv[1], "r", encoding="utf-8") as f:
    code = f.read()

original = code
changes = []

# ── FIX 1: Remove hardcoded Supabase block ──────────────────
# Match the literal-key block that appears right after the first
# `from supabase import create_client` line.
code, n = re.subn(
    r'from supabase import create_client\s*\n'
    r'SUPABASE_URL\s*=\s*"https://kinqcwteqgwvinfhqxgw[^"]*"\s*\n'
    r'SUPABASE_KEY\s*=\s*"eyJ[^"]*"\s*\n\n?'
    r'supabase\s*=\s*create_client\(SUPABASE_URL,\s*SUPABASE_KEY\)\s*\n',
    '# (hardcoded Supabase block removed - see env-var init below)\n',
    code, count=1)
if n:
    changes.append("FIX 1: Removed hardcoded Supabase credentials")

# ── FIX 2: Add `import flask` module-level import ───────────
flask_import_line = 'from flask import Flask, request, jsonify, send_file, abort, send_from_directory, session, redirect'
if 'import flask\n' not in code and flask_import_line in code:
    code = code.replace(flask_import_line,
                        'import flask\n' + flask_import_line, 1)
    changes.append("FIX 2: Added 'import flask' module import")

# ── FIX 3: Add call_llm_unified() ───────────────────────────
if 'def call_llm_unified(' not in code:
    unified_fn = '''

# ---------------------------------------------------------------------------
#  UNIFIED LLM CALL - returns (text, provider_name) or (None, None)
#  Priority: OpenRouter -> Gemini -> Groq
# ---------------------------------------------------------------------------
def call_llm_unified(system_msg, user_msg, max_tokens=4000, temperature=0.2):
    """Try all AI providers in order. Returns (text, provider_name) or (None, None)."""

    # Priority 1: OpenRouter
    if OPENROUTER_KEYS:
        result = call_openrouter(system_msg, user_msg, max_tokens, temperature)
        if result:
            return result, "OpenRouter"

    # Priority 2: Gemini with full key rotation
    _base = (
        "https://generativelanguage.googleapis.com"
        "/v1beta/models/gemini-2.0-flash:generateContent"
    )
    for _attempt in range(len(GEMINI_KEYS) + 2):
        key_str = get_gemini_key()
        if not key_str:
            break
        url = _base + "?key=" + key_str
        payload = {
            "system_instruction": {"parts": [{"text": system_msg}]},
            "contents": [{"parts": [{"text": user_msg}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature
            }
        }
        try:
            r = requests.post(url, json=payload, timeout=90, verify=False)
            if r.status_code == 200:
                parts = (r.json().get("candidates", [{}])[0]
                         .get("content", {}).get("parts", []))
                text = "".join(p.get("text", "") for p in parts).strip()
                if text:
                    mark_key_success(key_str)
                    log_srv("[LLM_UNIFIED] Gemini success attempt=" + str(_attempt + 1))
                    return text, "Gemini"
                rotate_gemini_key()
            elif r.status_code in (401, 403):
                mark_key_dead(key_str)
            elif r.status_code == 429:
                rotate_gemini_key()
                time.sleep(2)
            else:
                rotate_gemini_key()
        except requests.exceptions.Timeout:
            rotate_gemini_key()
        except Exception as _e:
            log_srv("[LLM_UNIFIED] Gemini exception: " + str(_e))
            rotate_gemini_key()

    # Priority 3: Groq
    if GROQ_KEYS:
        result = call_groq(system_msg, user_msg, max_tokens, temperature)
        if result:
            log_srv("[LLM_UNIFIED] Groq success")
            return result, "Groq"

    log_srv("[LLM_UNIFIED] All providers failed")
    return None, None

'''
    # Insert before run_generation
    if '\ndef run_generation(' in code:
        code = code.replace('\ndef run_generation(', unified_fn + '\ndef run_generation(', 1)
        changes.append("FIX 3: call_llm_unified() added before run_generation")
    elif '\n@app.route("/")\n' in code:
        code = code.replace('\n@app.route("/")\n', unified_fn + '\n@app.route("/")\n', 1)
        changes.append("FIX 3: call_llm_unified() added before Flask routes")

# ── FIX 4: Fix delete_model logic bug ───────────────────────
# The broken version has the actual delete logic unreachably nested
# inside the "no target found + path given" early-return branch.
# Replace the entire function with a corrected version.

broken_marker = '        return jsonify({"success": True})\n\n        if target_entry:\n'
if broken_marker in code:
    # Find the full function and replace it
    old_fn_re = re.compile(
        r'@app\.route\("/delete_model",\s*methods=\["POST"\]\)\s*\n'
        r'def delete_model\(\):.*?'
        r'return jsonify\(\{"success": False, "error": "not found"\}\),\s*404',
        re.DOTALL)
    new_fn = '''@app.route("/delete_model", methods=["POST"])
def delete_model():
    """Delete a saved model from disk and history."""
    data = request.get_json(force=True, silent=True) or {}
    model_id   = data.get("id", None)
    model_path = data.get("path", None)

    h = load_history()
    target_entry = None

    if model_id is not None:
        for e in h:
            if str(e.get("id")) == str(model_id):
                target_entry = e
                break
    elif model_path:
        for e in h:
            if e.get("file") == model_path:
                target_entry = e
                break

    # No history entry found but a path was given - try direct file deletion
    if not target_entry and model_path:
        full = os.path.join(BASE_DIR, model_path)
        resolved = os.path.realpath(full)
        base_real = os.path.realpath(BASE_DIR)
        if not resolved.startswith(base_real):
            return jsonify({"success": False, "error": "path traversal"}), 403
        try:
            if os.path.exists(resolved):
                os.remove(resolved)
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
        return jsonify({"success": True})

    if target_entry:
        # Delete the physical file from disk
        file_path = target_entry.get("file", "")
        if file_path:
            full = os.path.join(BASE_DIR, file_path)
            resolved = os.path.realpath(full)
            base_real = os.path.realpath(BASE_DIR)
            if resolved.startswith(base_real) and os.path.exists(resolved):
                try:
                    os.remove(resolved)
                    log_srv("[delete_model] removed: " + resolved)
                except Exception as e:
                    log_error("[delete_model] remove failed: " + str(e))

        # Remove from Supabase if enabled
        if SUPABASE_ENABLED:
            try:
                res = supabase_request("DELETE", "models?id=eq." + str(target_entry.get("id", "")))
                if res is not None:
                    log_srv("[SUPABASE] Deleted model " + str(target_entry.get("id")))
                else:
                    log_error("[SUPABASE] Failed to delete model from Supabase")
            except Exception as e:
                log_error("[delete_model] Supabase err: " + str(e))

        # Remove from local history file
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                local_h = json.load(f)
            local_h = [e for e in local_h
                       if str(e.get("id")) != str(target_entry.get("id"))]
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(local_h, f, indent=2)
        except Exception:
            pass

        # Remove from index
        idx = load_index()
        idx = [e for e in idx
               if str(e.get("id")) != str(target_entry.get("id"))]
        save_index(idx)
        return jsonify({"success": True})

    return jsonify({"success": False, "error": "not found"}), 404'''

    code2, n = old_fn_re.subn(new_fn, code, count=1)
    if n:
        code = code2
        changes.append("FIX 4: delete_model logic bug fixed (unreachable code corrected)")
    else:
        changes.append("FIX 4: delete_model - broken marker found but regex replacement failed")
else:
    changes.append("FIX 4 SKIPPED: broken_marker not found (may already be fixed)")

# ── WRITE OUTPUT ─────────────────────────────────────────────
with open(sys.argv[2], "w", encoding="utf-8") as f:
    f.write(code)

print("=" * 60)
print(f"Applied {len(changes)} change(s):")
for c in changes:
    print("  + " + c)
print(f"Output written to: {sys.argv[2]}")
print("=" * 60)
