import os

def fix_server():
    with open('server.py', 'r', encoding='utf-8-sig') as f:
        content = f.read()

    lines = content.split('\n')
    start_idx = 0
    for i, line in enumerate(lines):
        if "# server.py  -  AI 3D Studio  -  VERSION 7.0" in line:
            start_idx = i
            break

    print(f"Found version 7 header at line {start_idx}")
    
    clean_lines = lines[start_idx:]
    
    # We will inject the missing methods right after "import datetime"
    inject_idx = 0
    for i, line in enumerate(clean_lines):
        if line.startswith("import datetime"):
            inject_idx = i + 1
            break

    missing_code = """
import json, threading

COLOR_MAP = {"red":(1.0,0.0,0.0),"green":(0.0,0.8,0.0),"blue":(0.0,0.3,1.0),
             "yellow":(1.0,0.9,0.0),"orange":(1.0,0.5,0.0),"purple":(0.5,0.0,0.8),
             "pink":(1.0,0.4,0.7),"cyan":(0.0,0.9,1.0),"white":(1.0,1.0,1.0),
             "black":(0.05,0.05,0.05),"gray":(0.5,0.5,0.5),"grey":(0.5,0.5,0.5),
             "brown":(0.4,0.2,0.1),"gold":(1.0,0.8,0.0),"silver":(0.75,0.75,0.75)}
_hist_lock = threading.Lock()

def load_history():
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, list) else []
    except Exception: pass
    return []

def save_history(hist):
    try:
        with _hist_lock:
            hist = sorted(hist, key=lambda x: x.get("id", 0), reverse=True)
            if len(hist) > MAX_HISTORY: hist = hist[:MAX_HISTORY]
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(hist, f, indent=2)
    except Exception: pass

def add_history_entry(entry):
    try:
        h = load_history()
        h.insert(0, entry)
        save_history(h)
    except Exception: pass

def load_folders():
    try:
        if os.path.exists(FOLDERS_FILE):
            with open(FOLDERS_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, list) else list(DEFAULT_FOLDERS)
    except Exception: pass
    return list(DEFAULT_FOLDERS)

def save_folders(folders):
    try:
        with open(FOLDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(folders, f, indent=2)
    except Exception: pass

def load_index():
    try:
        if os.path.exists(INDEX_FILE):
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, list) else []
    except Exception: pass
    return []

def save_index(idx):
    try:
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(idx[:MAX_HISTORY], f, indent=2)
    except Exception: pass

def call_llm(system_msg, user_msg, max_tokens=4000, temperature=0.2):
    import requests, urllib3, time
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    _base = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key="
    
    for _i in range(max(len(GEMINI_KEYS), 1)):
        _k = get_gemini_key()
        if not _k: return None
            
        payload = {
            "system_instruction": {"parts": [{"text": system_msg}]},
            "contents": [{"parts": [{"text": user_msg}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "candidateCount": 1
            }
        }
        try:
            r = requests.post(_base + _k, headers={"Content-Type": "application/json"}, json=payload, timeout=90, verify=False)
            if r.status_code == 200:
                c = r.json().get("candidates", [])
                if c:
                    p = c[0].get("content", {}).get("parts", [])
                    if p:
                        mark_key_success(_k)
                        return p[0].get("text", "")
            elif r.status_code == 429:
                log_srv(f"[GEMINI] 429 Too Many Requests. Sleeping 5s before retrying...")
                time.sleep(5)
                continue
            elif r.status_code in (401, 403):
                mark_key_dead(_k)
            else:
                log_srv(f"[GEMINI] status {r.status_code}: {r.text}")
                rotate_gemini_key()
        except Exception as e:
            log_srv(f"[GEMINI] exception: {str(e)}")
            rotate_gemini_key()
    return None

def run_blender_script(script_text, output_path):
    import tempfile, subprocess as _sp, os
    if not os.path.isfile(BLENDER_EXE): 
        log_error(f"[BLENDER] Blender executable not found at {BLENDER_EXE}")
        return False
    try:
        full = "import bpy,math,os\\nOUTPUT_PATH=r'" + output_path.replace("\\\\", "/") + "'\\n" + script_text
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tf:
            tf.write(full)
            tmp = tf.name
        cf = 0x08000000 if os.name == "nt" else 0
        r = _sp.run([BLENDER_EXE, "--background", "--python", tmp], capture_output=True, text=True, timeout=120, creationflags=cf)
        try: os.unlink(tmp)
        except: pass
        if r.returncode == 0 and os.path.exists(output_path):
            ok, msg = validate_glb(output_path)
            if not ok: log_error(f"[BLENDER] Validated GLB failed: {msg}")
            return ok
        else:
            log_error(f"[BLENDER] exited with {r.returncode}, stderr: {r.stderr[-500:] if r.stderr else ''}")
        return False
    except Exception as e:
        log_error(f"[BLENDER] Error running script: {e}")
        return False
"""

    clean_lines.insert(inject_idx, missing_code)
    
    with open('server.py', 'w', encoding='utf-8') as f:
        f.write('\\n'.join(clean_lines))

    print("server.py cleaned and patched successfully.")

if __name__ == "__main__":
    fix_server()
