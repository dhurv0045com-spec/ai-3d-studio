import re

FILE = "server.py"
print("Reading " + FILE + "...")
with open(FILE, "r", encoding="utf-8") as f:
    code = f.read()

original = code
changes = []

# ============================================================
# FIX 1 - Add OpenAI + OpenRouter key builders after GEMINI_KEYS
# ============================================================
inject_after = "_GEMINI_DAILY_LIMIT = int((os.environ.get(\"GEMINI_DAILY_LIMIT\") or \"200\").strip() or \"200\")"

openai_openrouter_code = """

# ---------------------------------------------------------------------------
#  OPENAI KEY SYSTEM
# ---------------------------------------------------------------------------
def _build_openai_keys():
    keys = []
    for i in range(1, 11):
        val = (os.environ.get(f"OPENAI_KEY_{i}") or "").strip()
        if val and val.startswith("sk-"):
            keys.append({"name": f"openai{i}", "key": val,
                        "fails": 0, "dead": False, "last_used": 0.0,
                        "rate_limited_until": 0.0, "death_reason": ""})
    single = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if single and single.startswith("sk-") and not any(k["key"]==single for k in keys):
        keys.append({"name": "openai_env", "key": single,
                    "fails": 0, "dead": False, "last_used": 0.0,
                    "rate_limited_until": 0.0, "death_reason": ""})
    return keys

OPENAI_KEYS = _build_openai_keys()
_openai_lock = threading.Lock()
_openai_index = 0

def get_openai_key():
    with _openai_lock:
        alive = [k for k in OPENAI_KEYS if not k["dead"]]
        if not alive:
            return None
        alive.sort(key=lambda k: k["last_used"])
        k = alive[0]
        k["last_used"] = time.time()
        return k["key"]

def mark_openai_dead(key_val, reason="auth"):
    with _openai_lock:
        for k in OPENAI_KEYS:
            if k["key"] == key_val:
                if reason == "429":
                    k["rate_limited_until"] = time.time() + 60
                k["dead"] = True
                k["death_reason"] = reason

# ---------------------------------------------------------------------------
#  OPENROUTER KEY SYSTEM
# ---------------------------------------------------------------------------
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free").strip()

def _build_openrouter_keys():
    keys = []
    for i in range(1, 11):
        val = (os.environ.get(f"OPENROUTER_KEY_{i}") or "").strip()
        if val and val.startswith("sk-or"):
            keys.append({"name": f"openrouter{i}", "key": val,
                        "fails": 0, "dead": False, "last_used": 0.0,
                        "rate_limited_until": 0.0, "death_reason": ""})
    return keys

OPENROUTER_KEYS = _build_openrouter_keys()
_openrouter_lock = threading.Lock()

def get_openrouter_key():
    with _openrouter_lock:
        alive = [k for k in OPENROUTER_KEYS if not k["dead"]]
        if not alive:
            return None
        alive.sort(key=lambda k: k["last_used"])
        k = alive[0]
        k["last_used"] = time.time()
        return k["key"]

def mark_openrouter_dead(key_val, reason="auth"):
    with _openrouter_lock:
        for k in OPENROUTER_KEYS:
            if k["key"] == key_val:
                if reason == "429":
                    k["rate_limited_until"] = time.time() + 60
                k["dead"] = True
                k["death_reason"] = reason
"""

if "OPENAI_KEYS" not in code:
    if inject_after in code:
        code = code.replace(inject_after, inject_after + openai_openrouter_code, 1)
        changes.append("FIX 1: OpenAI + OpenRouter key systems added")
    else:
        print("  WARN FIX1: injection point not found")

# ============================================================
# FIX 2 - Add call_openai and call_openrouter functions
# ============================================================
openai_fn = """

# ---------------------------------------------------------------------------
#  OPENAI LLM CALL
# ---------------------------------------------------------------------------
def call_openai(system_msg, user_msg, max_tokens=4000, temperature=0.2):
    \"\"\"Call OpenAI API. Returns text or None.\"\"\"
    _base = "https://api.openai.com/v1/chat/completions"
    for _i in range(max(len(OPENAI_KEYS), 1) + 2):
        _k = get_openai_key()
        if not _k:
            return None
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        try:
            r = requests.post(
                _base,
                headers={"Content-Type": "application/json",
                         "Authorization": "Bearer " + _k},
                json=payload,
                timeout=90,
                verify=False,
            )
            if r.status_code == 200:
                data = r.json()
                choices = data.get("choices", [])
                if choices:
                    text = choices[0].get("message", {}).get("content", "")
                    if text:
                        log_srv("[OPENAI] Success")
                        return text
            elif r.status_code == 429:
                log_srv("[OPENAI] 429 rate limit - sleeping 5s")
                time.sleep(5)
                continue
            elif r.status_code in (401, 403):
                log_srv("[OPENAI] Auth error - marking key dead")
                mark_openai_dead(_k, reason="auth")
            else:
                log_srv("[OPENAI] status " + str(r.status_code) + ": " + r.text[:200])
        except Exception as e:
            log_srv("[OPENAI] exception: " + str(e))
    return None


# ---------------------------------------------------------------------------
#  OPENROUTER LLM CALL
# ---------------------------------------------------------------------------
def call_openrouter(system_msg, user_msg, max_tokens=4000, temperature=0.2):
    \"\"\"Call OpenRouter API. Returns text or None.\"\"\"
    _base = "https://openrouter.ai/api/v1/chat/completions"
    for _i in range(max(len(OPENROUTER_KEYS), 1) + 2):
        _k = get_openrouter_key()
        if not _k:
            return None
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        try:
            r = requests.post(
                _base,
                headers={"Content-Type": "application/json",
                         "Authorization": "Bearer " + _k,
                         "HTTP-Referer": "https://aurex-3d.up.railway.app",
                         "X-Title": "Aurex 3D"},
                json=payload,
                timeout=90,
                verify=False,
            )
            if r.status_code == 200:
                data = r.json()
                choices = data.get("choices", [])
                if choices:
                    text = choices[0].get("message", {}).get("content", "")
                    if text:
                        log_srv("[OPENROUTER] Success with model: " + OPENROUTER_MODEL)
                        return text
            elif r.status_code == 429:
                log_srv("[OPENROUTER] 429 rate limit - sleeping 5s")
                time.sleep(5)
                continue
            elif r.status_code in (401, 403):
                log_srv("[OPENROUTER] Auth error - marking key dead")
                mark_openrouter_dead(_k, reason="auth")
            else:
                log_srv("[OPENROUTER] status " + str(r.status_code) + ": " + r.text[:200])
        except Exception as e:
            log_srv("[OPENROUTER] exception: " + str(e))
    return None


# ---------------------------------------------------------------------------
#  UNIFIED LLM CALL - Tries Gemini -> OpenRouter -> OpenAI
# ---------------------------------------------------------------------------
def call_llm_unified(system_msg, user_msg, max_tokens=4000, temperature=0.2):
    \"\"\"Try all available AI providers in order. Returns (text, provider_name) or (None, None).\"\"\"
    # Try Gemini first (cheapest, 7 keys)
    alive_gemini = [k for k in GEMINI_KEYS if not k["dead"]]
    if alive_gemini:
        result = call_llm(system_msg, user_msg, max_tokens, temperature)
        if result:
            return result, "Gemini"

    # Try OpenRouter second (free models available)
    alive_or = [k for k in OPENROUTER_KEYS if not k["dead"]]
    if alive_or:
        log_srv("[LLM] Gemini failed/unavailable - trying OpenRouter")
        result = call_openrouter(system_msg, user_msg, max_tokens, temperature)
        if result:
            return result, "OpenRouter"

    # Try OpenAI last (paid)
    alive_oai = [k for k in OPENAI_KEYS if not k["dead"]]
    if alive_oai:
        log_srv("[LLM] OpenRouter failed/unavailable - trying OpenAI")
        result = call_openai(system_msg, user_msg, max_tokens, temperature)
        if result:
            return result, "OpenAI"

    log_srv("[LLM] All providers failed")
    return None, None
"""

if "call_openai" not in code:
    # Insert after call_llm function
    insert_point = "\ndef _gemini_inc_daily_used_by_key"
    if insert_point in code:
        code = code.replace(insert_point, openai_fn + "\ndef _gemini_inc_daily_used_by_key", 1)
        changes.append("FIX 2: call_openai + call_openrouter + call_llm_unified added")
    else:
        print("  WARN FIX2: insertion point not found")

# ============================================================
# FIX 3 - Replace call_llm() calls in generation pipeline
#         with call_llm_unified()
# ============================================================
# Find where call_llm is used in stage_b and replace
if "call_llm_unified" in code:
    # Replace call_llm( in stage_b_gemini_blender with call_llm_unified
    old_call = "result = call_llm("
    new_call = "result_tuple = call_llm_unified("
    # Only replace the main generation calls, not the function def itself
    count_replaced = 0
    lines = code.split("\n")
    new_lines = []
    for line in lines:
        if "result = call_llm(" in line and "def call_llm" not in line:
            # Replace and unpack tuple
            indent = len(line) - len(line.lstrip())
            sp = " " * indent
            new_lines.append(line.replace("result = call_llm(", "result_tuple = call_llm_unified("))
            new_lines.append(sp + "result = result_tuple[0] if result_tuple else None")
            new_lines.append(sp + "_provider_used = result_tuple[1] if result_tuple else 'Unknown'")
            count_replaced += 1
        else:
            new_lines.append(line)
    if count_replaced > 0:
        code = "\n".join(new_lines)
        changes.append(f"FIX 3: {count_replaced} call_llm() replaced with call_llm_unified()")

# ============================================================
# FIX 4 - Add /api/keys/status endpoint
# ============================================================
keys_status_route = """
@app.route("/api/keys/status", methods=["GET"])
def api_keys_status():
    \"\"\"Return health of all AI provider keys.\"\"\"
    def key_summary(keys, provider):
        alive = [k for k in keys if not k["dead"]]
        dead  = [k for k in keys if k["dead"]]
        return {
            "provider": provider,
            "total": len(keys),
            "alive": len(alive),
            "dead": len(dead),
            "keys": [{"name": k["name"], "dead": k["dead"],
                     "reason": k.get("death_reason","")} for k in keys]
        }
    return jsonify({
        "gemini":      key_summary(GEMINI_KEYS, "Gemini"),
        "openai":      key_summary(OPENAI_KEYS, "OpenAI"),
        "openrouter":  key_summary(OPENROUTER_KEYS, "OpenRouter"),
        "openrouter_model": OPENROUTER_MODEL,
    })
"""

if "/api/keys/status" not in code:
    # Insert before the health route
    if "@app.route(\"/health\"" in code:
        code = code.replace("@app.route(\"/health\"", keys_status_route + "\n@app.route(\"/health\"", 1)
        changes.append("FIX 4: /api/keys/status endpoint added")

# ============================================================
# FIX 5 - Update validate_env to check for at least one provider
# ============================================================
old_validate = """    if missing:
        print(f"CRITICAL: Missing environment variables: {', '.join(missing)}")
        if os.environ.get("RAILWAY_ENVIRONMENT"):
            # Exit in production if secrets are missing
            sys.exit(1)"""

new_validate = """    # At least one AI provider must be available
    has_gemini = any(os.environ.get(f"GEMINI_KEY_{i}") for i in range(1,8))
    has_openai = any(os.environ.get(f"OPENAI_KEY_{i}") for i in range(1,4)) or os.environ.get("OPENAI_API_KEY")
    has_openrouter = any(os.environ.get(f"OPENROUTER_KEY_{i}") for i in range(1,4))
    if not has_gemini and not has_openai and not has_openrouter:
        missing.append("No AI provider keys found (need GEMINI_KEY_x or OPENAI_KEY_x or OPENROUTER_KEY_x)")
    if missing:
        print(f"CRITICAL: Missing environment variables: {', '.join(missing)}")
        if os.environ.get("RAILWAY_ENVIRONMENT") and len(missing) > 1:
            # Only exit if multiple critical vars missing
            sys.exit(1)"""

if old_validate in code:
    code = code.replace(old_validate, new_validate, 1)
    changes.append("FIX 5: validate_env updated - accepts any provider")
else:
    print("  WARN FIX5: validate_env pattern not found")

# ============================================================
# WRITE
# ============================================================
if code != original:
    with open(FILE, "w", encoding="utf-8") as f:
        f.write(code)
    print("\nDone! " + str(len(changes)) + " fixes applied:")
    for c in changes:
        print("  + " + c)
    print("\nNow add to Railway Variables:")
    print("  OPENAI_KEY_1 = sk-...")
    print("  OPENROUTER_KEY_1 = sk-or-...")
    print("  OPENROUTER_KEY_2 = sk-or-...")
    print("  OPENROUTER_KEY_3 = sk-or-...")
    print("  OPENROUTER_MODEL = meta-llama/llama-3.1-8b-instruct:free")
    print("\nThen run:")
    print("  git add .")
    print('  git commit -m "Add OpenAI + OpenRouter multi-provider support"')
    print("  git push origin main")
else:
    print("\nNo changes - check warnings above")
