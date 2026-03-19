FILE = "server.py"
with open(FILE, "r", encoding="utf-8") as f:
    code = f.read()

orig = code
changes = []

# FIX 1 - interpret_prompt: call_llm -> call_llm_unified
old1 = '    raw = call_llm(INTERPRETER_SYSTEM, prompt_text, max_tokens=500, temperature=0.1)\n    if raw:'
new1 = '    _r1 = call_llm_unified(INTERPRETER_SYSTEM, prompt_text, max_tokens=500, temperature=0.1)\n    raw = _r1[0] if isinstance(_r1, tuple) else _r1\n    if raw:'
if old1 in code:
    code = code.replace(old1, new1, 1)
    changes.append("FIX 1: interpret_prompt uses call_llm_unified")

# FIX 2 - stage_b first call
old2 = '    script_raw = call_llm(BLENDER_SYSTEM, user_msg, max_tokens=4000, temperature=0.2)\n    if not script_raw:\n        log_gen("[MODEL_B] Gemini returned no script")\n        return False'
new2 = '    _r2 = call_llm_unified(BLENDER_SYSTEM, user_msg, max_tokens=4000, temperature=0.2)\n    script_raw = _r2[0] if isinstance(_r2, tuple) else _r2\n    _provider = _r2[1] if isinstance(_r2, tuple) else "Gemini"\n    log_gen("[MODEL_B] Provider: " + str(_provider))\n    if not script_raw:\n        log_gen("[MODEL_B] All providers returned no script")\n        return False'
if old2 in code:
    code = code.replace(old2, new2, 1)
    changes.append("FIX 2: stage_b first call uses call_llm_unified")

# FIX 3 - stage_b retry call
old3 = '    script_raw_simp = call_llm(BLENDER_SYSTEM, user_msg_simp, max_tokens=2500, temperature=0.1)'
new3 = '    _r3 = call_llm_unified(BLENDER_SYSTEM, user_msg_simp, max_tokens=2500, temperature=0.1)\n    script_raw_simp = _r3[0] if isinstance(_r3, tuple) else _r3'
if old3 in code:
    code = code.replace(old3, new3, 1)
    changes.append("FIX 3: stage_b retry call uses call_llm_unified")

# FIX 4 - run_blender_with_retry internal fix call
old4 = '            fixed = call_llm(BLENDER_SYSTEM, fix_msg, max_tokens=3000, temperature=0.05)'
new4 = '            _r4 = call_llm_unified(BLENDER_SYSTEM, fix_msg, max_tokens=3000, temperature=0.05)\n            fixed = _r4[0] if isinstance(_r4, tuple) else _r4'
if old4 in code:
    code = code.replace(old4, new4, 1)
    changes.append("FIX 4: blender retry fix call uses call_llm_unified")

if code != orig:
    with open(FILE, "w", encoding="utf-8") as f:
        f.write(code)
    print("DONE! " + str(len(changes)) + " fixes applied:")
    for c in changes: print("  + " + c)
else:
    print("ERROR: No patterns matched - check manually")
