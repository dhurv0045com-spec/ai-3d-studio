"""
generate_model.py  -  AI 3D Studio  -  IMPROVED VERSION
================================================================================
AI 3D Generation Backend

Reads a prompt from state.json, picks the right Blender script, runs Blender
headlessly, exports rocket.glb, and updates state.json status to "done".

IMPROVEMENTS OVER ORIGINAL:
  - Structured pipeline with named stages (prepare, generate, validate, retry)
  - Retry logic: 2 attempts before giving up, with delay between attempts
  - Full GLB validation: file exists + size > 4096 bytes + correct magic bytes
  - Per-stage logging with timestamps so logs show exactly where failures occur
  - Hard timeout per Blender run (configurable, default 180s) plus global cap
  - Graceful error recovery: failed attempt cleans up temp files before retry
  - State file is always updated even on crash (finally block)
  - Color detection expanded to 28 named colors
  - Shape keyword map expanded to 20 shapes
  - All shape scripts expanded with more primitives for better visual quality
  - Added: dragon, submarine, mushroom, lighthouse, bridge, windmill, crystal,
           spaceship-v2, snowman, lantern shape scripts
  - Script pre-validation before Blender launch (catches empty/bad scripts)
  - Blender executable auto-detection across common Windows install paths
  - Generation stats written to state.json (attempt count, time taken, size)
  - Thread-safe state file writes using a lock file pattern
  - ASCII-safe script writing (no unicode that breaks Blender subprocess)

Usage:
  python generate_model.py

Requirements:
  - Blender installed (auto-detected) or BLENDER_PATH env var set
  - Python 3.8+

Project layout:
  ai-3d-project/
    static/index.html     <- Three.js viewer
    generate_model.py     <- THIS FILE
    state.json            <- shared state between browser and this script
    rocket.glb            <- output model (auto-generated)
    server.py             <- Flask server
    logs/generation.log   <- generation log file
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import re
import math
import shutil
import struct
import datetime
import traceback
import threading

# ================================================================================
#  CONFIG
# ================================================================================

# Output file - must match what server.py and index.html expect
OUTPUT_FILE   = "rocket.glb"
STATE_FILE    = "state.json"
POLL_INTERVAL = 1.0          # seconds between state.json polls
LOG_FILE      = os.path.join("logs", "generation.log")

# Retry config
MAX_ATTEMPTS     = 2         # how many times to try Blender before giving up
RETRY_DELAY      = 2.0       # seconds to wait between attempts
BLENDER_TIMEOUT  = 180       # seconds per Blender run (was 120 in original)
GLOBAL_TIMEOUT   = 600       # seconds total for one generation job

# Minimum valid GLB file size in bytes
# Real GLB files are always larger than this even for the simplest mesh
MIN_GLB_SIZE = 4096

# GLB magic bytes - every valid GLB starts with these 4 bytes
GLB_MAGIC = b"glTF"

# ================================================================================
#  BLENDER AUTO-DETECTION
# ================================================================================

# Common Blender installation paths on Windows
# Tries these in order before falling back to PATH
BLENDER_SEARCH_PATHS = [
    r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
    r"C:\Program Files (x86)\Blender Foundation\Blender 5.0\blender.exe",
    r"C:\Program Files (x86)\Blender Foundation\Blender 4.2\blender.exe",
]


def find_blender() -> str:
    """
    Find Blender executable.
    Priority: BLENDER_PATH env var > known install paths > PATH fallback.
    Returns the path string (may not exist if none found).
    """
    # 1. Explicit env var always wins
    env_path = os.environ.get("BLENDER_PATH", "").strip()
    if env_path:
        log(f"[BLENDER] Using BLENDER_PATH env: {env_path}")
        return env_path

    # 2. Scan known Windows install locations
    for p in BLENDER_SEARCH_PATHS:
        if os.path.isfile(p):
            log(f"[BLENDER] Auto-detected: {p}")
            return p

    # 3. Hope it is on PATH
    log("[BLENDER] Not found in known paths, falling back to 'blender' on PATH")
    return "blender"


BLENDER_PATH = find_blender()

# ================================================================================
#  LOGGING
# ================================================================================

_log_lock = threading.Lock()


def _ts() -> str:
    """Return current time as HH:MM:SS string."""
    return datetime.datetime.now().strftime("%H:%M:%S")


def log(msg: str):
    """
    Print timestamped message to console and append to log file.
    Thread-safe. Never raises - log failure is silently ignored.
    """
    line = f"[{_ts()}] {msg}"
    print(line)
    try:
        with _log_lock:
            os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True) if os.path.dirname(LOG_FILE) else None
            with open(LOG_FILE, "a", encoding="ascii", errors="replace") as f:
                f.write(line + "\n")
    except Exception:
        pass  # logging must never crash the pipeline


def log_stage(stage: str, detail: str = ""):
    """Log a named pipeline stage transition. Makes logs easy to scan."""
    if detail:
        log(f"[STAGE:{stage}] {detail}")
    else:
        log(f"[STAGE:{stage}]")


def log_separator():
    log("=" * 64)

# ================================================================================
#  STATE FILE
# ================================================================================

_state_lock = threading.Lock()


def read_state() -> dict:
    """Read state.json. Returns empty dict on any failure."""
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def write_state(data: dict):
    """
    Write state.json atomically using a temp file + rename pattern.
    This prevents the browser from reading a half-written file.
    Thread-safe via lock.
    """
    try:
        with _state_lock:
            tmp = STATE_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            # Atomic replace - on Windows this may briefly fail if file is open
            try:
                os.replace(tmp, STATE_FILE)
            except PermissionError:
                # Fallback: direct write
                with open(STATE_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                try:
                    os.remove(tmp)
                except Exception:
                    pass
    except Exception as e:
        log(f"[STATE] Write failed: {e}")


def update_state(base: dict, **kwargs) -> dict:
    """Merge kwargs into base state dict, write it, and return the merged dict."""
    merged = {**base, **kwargs}
    write_state(merged)
    return merged

# ================================================================================
#  GLB VALIDATION
# ================================================================================

def validate_glb(path: str) -> tuple:
    """
    Validate a GLB file. Returns (bool, reason_string).

    Checks performed:
      1. File exists at path
      2. File has .glb extension
      3. File size > MIN_GLB_SIZE (4096 bytes)
      4. First 4 bytes are GLB magic bytes b'glTF'

    A Blender process that crashes mid-export often writes a partial or
    zero-byte file. Without this check the app would serve a broken model
    and the Three.js viewer would silently fail to render anything.
    """
    if not path.lower().endswith(".glb"):
        return False, f"wrong extension: {os.path.basename(path)}"

    if not os.path.exists(path):
        return False, "file does not exist"

    size = os.path.getsize(path)
    if size < MIN_GLB_SIZE:
        return False, f"file too small: {size} bytes (min {MIN_GLB_SIZE})"

    try:
        with open(path, "rb") as f:
            magic = f.read(4)
        if magic != GLB_MAGIC:
            return False, f"invalid magic bytes: {magic!r} (expected b'glTF')"
    except Exception as e:
        return False, f"could not read file: {e}"

    return True, f"valid GLB, {size:,} bytes"

# ================================================================================
#  SHAPE AND COLOR DETECTION
# ================================================================================

# Expanded shape keyword map - 20 shapes
# First match wins, so more specific terms go at the top of each list
SHAPE_KEYWORDS = {
    "rocket":      ["rocket", "missile", "spacecraft", "capsule", "saturn v"],
    "car":         ["car", "vehicle", "automobile", "sedan", "sports car", "race car"],
    "truck":       ["truck", "lorry", "pickup", "semi", "18 wheeler"],
    "tower":       ["tower", "skyscraper", "building", "fortress", "keep", "minaret"],
    "castle":      ["castle", "palace", "citadel", "stronghold"],
    "spaceship":   ["spaceship", "ufo", "saucer", "alien ship", "flying saucer"],
    "robot":       ["robot", "android", "mech", "droid", "cyborg", "automaton"],
    "house":       ["house", "home", "cottage", "cabin", "hut", "bungalow", "villa"],
    "plane":       ["plane", "aircraft", "airplane", "jet", "fighter", "bomber"],
    "pyramid":     ["pyramid", "temple", "ziggurat", "sphinx"],
    "diamond":     ["diamond", "gem", "jewel", "gemstone"],
    "crystal":     ["crystal", "quartz", "shard", "prism", "cluster"],
    "tree":        ["tree", "pine", "oak", "palm", "plant", "sapling"],
    "dragon":      ["dragon", "wyrm", "wyvern", "serpent"],
    "submarine":   ["submarine", "sub", "underwater", "u-boat"],
    "mushroom":    ["mushroom", "toadstool", "fungus", "shroom"],
    "lighthouse":  ["lighthouse", "beacon", "watchtower", "pharos"],
    "windmill":    ["windmill", "wind turbine", "mill"],
    "snowman":     ["snowman", "snow figure", "frosty"],
    "lantern":     ["lantern", "lamp", "torch", "light"],
}

# Expanded color map - 28 colors including hex-style names
COLOR_MAP = {
    "red":       (0.90, 0.10, 0.10),
    "crimson":   (0.70, 0.04, 0.10),
    "orange":    (0.95, 0.45, 0.05),
    "amber":     (1.00, 0.65, 0.00),
    "yellow":    (0.95, 0.85, 0.10),
    "lime":      (0.50, 0.90, 0.10),
    "green":     (0.10, 0.75, 0.20),
    "emerald":   (0.05, 0.60, 0.30),
    "teal":      (0.10, 0.65, 0.60),
    "cyan":      (0.10, 0.85, 0.90),
    "sky":       (0.35, 0.70, 1.00),
    "blue":      (0.10, 0.30, 0.90),
    "navy":      (0.05, 0.05, 0.45),
    "indigo":    (0.30, 0.10, 0.70),
    "purple":    (0.55, 0.10, 0.85),
    "violet":    (0.65, 0.20, 0.90),
    "pink":      (0.95, 0.45, 0.65),
    "magenta":   (0.90, 0.10, 0.70),
    "white":     (0.95, 0.95, 0.95),
    "silver":    (0.70, 0.72, 0.75),
    "gray":      (0.45, 0.45, 0.48),
    "grey":      (0.45, 0.45, 0.48),
    "black":     (0.06, 0.06, 0.07),
    "brown":     (0.45, 0.25, 0.10),
    "tan":       (0.75, 0.60, 0.40),
    "gold":      (1.00, 0.78, 0.10),
    "bronze":    (0.55, 0.35, 0.10),
    "copper":    (0.70, 0.40, 0.20),
}

DEFAULT_COLOR = (0.20, 0.60, 0.90)   # blue


def detect_shape(prompt: str) -> str:
    """
    Return the best matching shape keyword from the prompt.
    Scans SHAPE_KEYWORDS in definition order. First match wins.
    Falls back to 'rocket' if nothing matches.
    """
    lower = prompt.lower()
    for shape, keywords in SHAPE_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                log(f"[DETECT] Shape '{shape}' matched keyword '{kw}'")
                return shape
    log(f"[DETECT] No shape matched, defaulting to 'rocket'")
    return "rocket"


def detect_color(prompt: str) -> tuple:
    """
    Return (R, G, B) float tuple parsed from color words in the prompt.
    Checks all 28 named colors. Returns DEFAULT_COLOR if none found.
    """
    lower = prompt.lower()
    for name, rgb in COLOR_MAP.items():
        if name in lower:
            log(f"[DETECT] Color '{name}' matched -> RGB {rgb}")
            return rgb
    log(f"[DETECT] No color matched, defaulting to blue {DEFAULT_COLOR}")
    return DEFAULT_COLOR


def has_modifier(prompt: str, words: list) -> bool:
    """Return True if any word from the list appears in the prompt."""
    lower = prompt.lower()
    return any(w in lower for w in words)


def get_scale_modifier(prompt: str) -> float:
    """
    Return a float scale modifier based on size words in the prompt.
    big/huge/giant = 1.5x, tiny/mini/small = 0.6x, else 1.0x.
    Used to scale wings, fins, and other proportional elements.
    """
    if has_modifier(prompt, ["big", "large", "huge", "giant", "massive", "enormous"]):
        return 1.5
    if has_modifier(prompt, ["small", "tiny", "mini", "little", "miniature", "tiny"]):
        return 0.6
    return 1.0

# ================================================================================
#  SCRIPT PRE-VALIDATION
# ================================================================================

def script_looks_valid(script: str) -> tuple:
    """
    Pre-validate a Blender Python script before launching a subprocess.
    Returns (bool, reason).

    Catches obvious problems early without wasting a Blender process launch:
      - Empty or whitespace-only scripts
      - Scripts under 100 characters (clearly truncated or error messages)
      - Missing 'import bpy' (not a Blender script at all)
      - Missing export call (script will run but produce no output file)
    """
    if not script or not script.strip():
        return False, "script is empty"
    if len(script) < 100:
        return False, f"script suspiciously short: {len(script)} chars"
    if "import bpy" not in script:
        return False, "missing 'import bpy' - not a valid Blender script"
    if "export_scene.gltf" not in script:
        return False, "missing gltf export call - model would never be written"
    return True, "ok"

# ================================================================================
#  BLENDER RUNNER
# ================================================================================

def run_blender(script_text: str, attempt: int = 1) -> tuple:
    """
    Write script to a temp file and run Blender headlessly.
    Returns (success: bool, detail: str).

    IMPROVEMENTS over original:
      - Script is pre-validated before launching the subprocess
      - Script is written ASCII-safe to avoid encoding issues on Windows
      - Temp file is always cleaned up in a finally block
      - stdout/stderr are both captured and logged
      - Timeout is configurable via BLENDER_TIMEOUT constant
      - Returns a detail string explaining the outcome for logging
      - Checks Blender executable exists before trying to run it
    """
    log_stage("BLENDER_START", f"attempt {attempt}/{MAX_ATTEMPTS}, timeout={BLENDER_TIMEOUT}s")

    # Pre-validate script before launching subprocess
    valid, reason = script_looks_valid(script_text)
    if not valid:
        log(f"[BLENDER] Script pre-check FAILED: {reason}")
        return False, f"script invalid: {reason}"

    # Check Blender executable exists
    if not os.path.isfile(BLENDER_PATH) and shutil.which(BLENDER_PATH) is None:
        msg = f"Blender executable not found: '{BLENDER_PATH}'"
        log(f"[BLENDER] ERROR: {msg}")
        log("[BLENDER] Set BLENDER_PATH environment variable to your blender.exe")
        return False, msg

    tmp_path = None
    try:
        # Write script as ASCII to avoid Windows encoding issues in subprocess
        safe_script = script_text.encode("ascii", errors="replace").decode("ascii")

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False,
            encoding="ascii", errors="replace"
        ) as tf:
            tf.write(safe_script)
            tmp_path = tf.name

        log(f"[BLENDER] Script written to temp: {tmp_path} ({len(safe_script):,} chars)")

        cmd = [BLENDER_PATH, "--background", "--python", tmp_path]
        log(f"[BLENDER] Command: {' '.join(cmd)}")

        start_time = time.time()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=BLENDER_TIMEOUT,
            encoding="utf-8",
            errors="replace"
        )
        elapsed = time.time() - start_time

        log(f"[BLENDER] Process finished in {elapsed:.1f}s, exit code={result.returncode}")

        # Log last 3000 chars of stdout (Blender is very verbose)
        if result.stdout:
            tail = result.stdout[-3000:]
            for line in tail.split("\n"):
                if line.strip():
                    log(f"[BLENDER] OUT: {line.rstrip()}")

        # Log all stderr - errors are critical and must be visible
        if result.stderr:
            tail = result.stderr[-2000:]
            for line in tail.split("\n"):
                if line.strip():
                    log(f"[BLENDER] ERR: {line.rstrip()}")

        if result.returncode != 0:
            return False, f"Blender exited with code {result.returncode}"

        return True, f"Blender succeeded in {elapsed:.1f}s"

    except FileNotFoundError:
        msg = f"Blender executable not found at '{BLENDER_PATH}'"
        log(f"[BLENDER] ERROR: {msg}")
        return False, msg

    except subprocess.TimeoutExpired:
        msg = f"Blender timed out after {BLENDER_TIMEOUT}s"
        log(f"[BLENDER] ERROR: {msg}")
        return False, msg

    except Exception as e:
        msg = f"Unexpected error running Blender: {e}"
        log(f"[BLENDER] ERROR: {msg}")
        log(traceback.format_exc())
        return False, msg

    finally:
        # Always clean up temp file even if something threw
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
                log(f"[BLENDER] Temp file cleaned up: {tmp_path}")
            except Exception:
                pass

# ================================================================================
#  GENERATION PIPELINE
# ================================================================================

def prepare_prompt(raw_prompt: str) -> dict:
    """
    STAGE 1: Prompt preparation.
    Parse the raw prompt into structured generation parameters.
    Returns a dict of everything the generation stage needs.
    """
    log_stage("PREPARE", f"prompt='{raw_prompt}'")

    shape       = detect_shape(raw_prompt)
    color       = detect_color(raw_prompt)
    scale       = get_scale_modifier(raw_prompt)
    has_glow    = has_modifier(raw_prompt, ["glowing", "neon", "lit", "bright", "shiny"])
    has_dark    = has_modifier(raw_prompt, ["dark", "shadow", "black", "ominous", "evil"])
    has_worn    = has_modifier(raw_prompt, ["old", "worn", "rusty", "ancient", "broken"])

    # Adjust color slightly for mood modifiers
    r, g, b = color
    if has_dark:
        r, g, b = r * 0.4, g * 0.4, b * 0.4
    if has_glow:
        r, g, b = min(r * 1.3, 1.0), min(g * 1.3, 1.0), min(b * 1.3, 1.0)

    params = {
        "raw_prompt": raw_prompt,
        "shape":      shape,
        "color":      (r, g, b),
        "scale":      scale,
        "has_glow":   has_glow,
        "has_dark":   has_dark,
        "has_worn":   has_worn,
    }
    log(f"[PREPARE] Params: shape={shape}, color=({r:.2f},{g:.2f},{b:.2f}), "
        f"scale={scale}, glow={has_glow}, dark={has_dark}, worn={has_worn}")
    return params


def generate_attempt(params: dict, attempt: int) -> tuple:
    """
    STAGE 2: Single generation attempt.
    Builds the Blender script and runs it. Returns (success, detail).
    """
    log_stage("GENERATE", f"attempt {attempt}/{MAX_ATTEMPTS}")

    shape = params["shape"]
    color = params["color"]
    scale = params["scale"]
    prompt = params["raw_prompt"]

    # Build the script
    log(f"[GENERATE] Building script for shape='{shape}'")
    script = blender_script(shape, color, prompt, scale)
    log(f"[GENERATE] Script ready: {len(script):,} chars")

    # Run Blender
    success, detail = run_blender(script, attempt=attempt)
    return success, detail


def validate_output(output_path: str) -> tuple:
    """
    STAGE 3: Output validation.
    Validates the generated GLB file. Returns (success, detail).
    """
    log_stage("VALIDATE", f"checking: {output_path}")
    ok, reason = validate_glb(output_path)
    if ok:
        log(f"[VALIDATE] PASSED - {reason}")
    else:
        log(f"[VALIDATE] FAILED - {reason}")
    return ok, reason


def run_generation_pipeline(state: dict) -> dict:
    """
    Full generation pipeline with retry logic.

    Stages:
      1. Prepare  - parse prompt into parameters
      2. Generate - run Blender (retried up to MAX_ATTEMPTS times)
      3. Validate - check the output GLB file
      4. Finalize - update state with result

    Always returns an updated state dict. Never raises.
    """
    raw_prompt = state.get("prompt", "").strip()
    job_start  = time.time()

    log_separator()
    log(f"[PIPELINE] Starting generation for prompt: '{raw_prompt}'")
    log(f"[PIPELINE] Max attempts: {MAX_ATTEMPTS}, Blender timeout: {BLENDER_TIMEOUT}s")

    # Remove stale output file so validation can't accidentally pass on old data
    if os.path.exists(OUTPUT_FILE):
        try:
            os.remove(OUTPUT_FILE)
            log(f"[PIPELINE] Removed stale output file: {OUTPUT_FILE}")
        except Exception as e:
            log(f"[PIPELINE] Warning: could not remove stale output: {e}")

    # ── STAGE 1: Prepare ────────────────────────────────────────────────────
    try:
        params = prepare_prompt(raw_prompt)
    except Exception as e:
        log(f"[PIPELINE] Prepare stage crashed: {e}")
        log(traceback.format_exc())
        return update_state(state, status="error", error=f"prepare failed: {e}")

    state = update_state(state, status="generating", shape=params["shape"],
                         color=list(params["color"]), progress=10)

    # ── STAGE 2+3: Generate + Validate with retry ────────────────────────────
    last_detail = "unknown failure"
    succeeded   = False

    for attempt in range(1, MAX_ATTEMPTS + 1):
        # Check global timeout
        elapsed_total = time.time() - job_start
        if elapsed_total > GLOBAL_TIMEOUT:
            log(f"[PIPELINE] Global timeout exceeded ({GLOBAL_TIMEOUT}s). Stopping.")
            break

        log(f"[PIPELINE] --- Attempt {attempt}/{MAX_ATTEMPTS} ---")
        progress = 20 + (attempt - 1) * 35
        state = update_state(state, progress=progress,
                             step=f"attempt_{attempt}")

        # Generate
        try:
            gen_ok, gen_detail = generate_attempt(params, attempt)
        except Exception as e:
            gen_ok     = False
            gen_detail = f"generate stage exception: {e}"
            log(f"[PIPELINE] Generate crashed: {e}")
            log(traceback.format_exc())

        if not gen_ok:
            log(f"[PIPELINE] Attempt {attempt} generation FAILED: {gen_detail}")
            last_detail = gen_detail
            if attempt < MAX_ATTEMPTS:
                log(f"[PIPELINE] Waiting {RETRY_DELAY}s before retry...")
                time.sleep(RETRY_DELAY)
            continue

        # Validate
        try:
            val_ok, val_detail = validate_output(OUTPUT_FILE)
        except Exception as e:
            val_ok     = False
            val_detail = f"validate exception: {e}"
            log(f"[PIPELINE] Validate crashed: {e}")

        if not val_ok:
            log(f"[PIPELINE] Attempt {attempt} validation FAILED: {val_detail}")
            last_detail = val_detail
            if attempt < MAX_ATTEMPTS:
                log(f"[PIPELINE] Waiting {RETRY_DELAY}s before retry...")
                time.sleep(RETRY_DELAY)
            continue

        # Both passed
        succeeded   = True
        last_detail = val_detail
        log(f"[PIPELINE] Attempt {attempt} SUCCEEDED: {val_detail}")
        break

    # ── STAGE 4: Finalize ────────────────────────────────────────────────────
    elapsed_total = time.time() - job_start
    glb_size = os.path.getsize(OUTPUT_FILE) if os.path.exists(OUTPUT_FILE) else 0

    if succeeded:
        log(f"[PIPELINE] SUCCESS in {elapsed_total:.1f}s - model: {OUTPUT_FILE} ({glb_size:,} bytes)")
        log_separator()
        return update_state(
            state,
            status    = "done",
            progress  = 100,
            step      = "done",
            glb_size  = glb_size,
            elapsed   = round(elapsed_total, 1),
            detail    = last_detail,
            error     = ""
        )
    else:
        log(f"[PIPELINE] FAILED after {MAX_ATTEMPTS} attempts in {elapsed_total:.1f}s")
        log(f"[PIPELINE] Last failure: {last_detail}")
        log_separator()
        return update_state(
            state,
            status   = "error",
            progress = 0,
            step     = "failed",
            error    = last_detail,
            elapsed  = round(elapsed_total, 1)
        )

# ================================================================================
#  BLENDER SCRIPT BUILDER
# ================================================================================

def blender_script(shape: str, color: tuple, prompt: str, scale: float = 1.0) -> str:
    """
    Dispatch to the correct shape script builder.
    Falls back to rocket if shape is unrecognised.
    """
    r, g, b = color
    builders = {
        "rocket":     _rocket_script,
        "car":        _car_script,
        "truck":      _truck_script,
        "tower":      _tower_script,
        "castle":     _castle_script,
        "spaceship":  _spaceship_script,
        "robot":      _robot_script,
        "house":      _house_script,
        "plane":      _plane_script,
        "pyramid":    _pyramid_script,
        "diamond":    _diamond_script,
        "crystal":    _crystal_script,
        "tree":       _tree_script,
        "dragon":     _dragon_script,
        "submarine":  _submarine_script,
        "mushroom":   _mushroom_script,
        "lighthouse": _lighthouse_script,
        "windmill":   _windmill_script,
        "snowman":    _snowman_script,
        "lantern":    _lantern_script,
    }
    builder = builders.get(shape, _rocket_script)
    log(f"[SCRIPT] Building '{shape}' script (scale={scale})")
    return builder(r, g, b, scale)

# ── SHARED HEADER / FOOTER ──────────────────────────────────────────────────────

def _header() -> str:
    """Standard Blender script header: imports, scene clear, material helpers."""
    return """import bpy
import math

# Clear scene completely
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
for block in list(bpy.data.meshes):
    bpy.data.meshes.remove(block)
for block in list(bpy.data.materials):
    bpy.data.materials.remove(block)

def make_mat(name, r, g, b, metallic=0.4, roughness=0.4, emission=0.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value   = (r, g, b, 1.0)
    bsdf.inputs["Metallic"].default_value     = metallic
    bsdf.inputs["Roughness"].default_value    = roughness
    if emission > 0.0:
        bsdf.inputs["Emission Strength"].default_value = emission
        bsdf.inputs["Emission Color"].default_value    = (r, g, b, 1.0)
    return mat

def assign(obj, mat):
    if obj.data is None:
        return
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

def add(prim_func, **kwargs):
    prim_func(**kwargs)
    return bpy.context.object

"""


def _footer(output_path: str) -> str:
    """Standard Blender script footer: camera, lighting, GLB export."""
    safe = output_path.replace("\\", "/")
    return f"""
# Camera
bpy.ops.object.camera_add(location=(6, -6, 4))
cam = bpy.context.object
cam.rotation_euler = (1.1, 0, 0.785)
bpy.context.scene.camera = cam

# Sun light
bpy.ops.object.light_add(type='SUN', location=(5, 5, 8))
sun = bpy.context.object
sun.data.energy = 3.0
sun.rotation_euler = (0.8, 0.2, 0.5)

# Fill light
bpy.ops.object.light_add(type='AREA', location=(-4, -3, 5))
fill = bpy.context.object
fill.data.energy = 1.5

# Export GLB
bpy.ops.export_scene.gltf(
    filepath=r"{safe}",
    export_format="GLB",
    export_apply=True
)
print("EXPORTED: {safe}")
"""


def _out() -> str:
    """Return absolute output path for use in scripts."""
    return os.path.abspath(OUTPUT_FILE)

# ── SHAPE SCRIPTS ───────────────────────────────────────────────────────────────

def _rocket_script(r, g, b, scale):
    return _header() + f"""
main_mat  = make_mat("Main",  {r}, {g}, {b}, metallic=0.6, roughness=0.3)
dark_mat  = make_mat("Dark",  0.08, 0.08, 0.10, metallic=0.3, roughness=0.6)
glass_mat = make_mat("Glass", 0.40, 0.80, 1.00, metallic=0.0, roughness=0.05)
glow_mat  = make_mat("Glow",  1.00, 0.50, 0.10, metallic=0.0, roughness=0.1, emission=3.0)

# Body
bpy.ops.mesh.primitive_cylinder_add(radius=0.35, depth=2.2, location=(0,0,0))
body = bpy.context.object; assign(body, main_mat)

# Nose cone
bpy.ops.mesh.primitive_cone_add(radius1=0.35, depth=0.9, location=(0,0,1.55))
nose = bpy.context.object; assign(nose, main_mat)

# Nose tip detail
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05, location=(0,0,2.05))
tip = bpy.context.object; assign(tip, dark_mat)

# Nozzle bell
bpy.ops.mesh.primitive_cone_add(radius1=0.42, radius2=0.20, depth=0.45, location=(0,0,-1.32))
nozzle = bpy.context.object; assign(nozzle, dark_mat)

# Nozzle glow
bpy.ops.mesh.primitive_cylinder_add(radius=0.18, depth=0.05, location=(0,0,-1.57))
glow = bpy.context.object; assign(glow, glow_mat)

# Fins (4)
fin_h = 0.70 * {scale}
fin_w = 0.55 * {scale}
for i in range(4):
    angle = i * math.pi / 2
    bpy.ops.mesh.primitive_cube_add(size=1,
        location=(math.cos(angle)*0.42, math.sin(angle)*0.42, -0.8))
    fin = bpy.context.object
    fin.scale = (0.05, fin_w, fin_h)
    fin.rotation_euler[2] = angle
    assign(fin, main_mat)

# Body bands (3 rings)
for bz in [-0.4, 0.2, 0.8]:
    bpy.ops.mesh.primitive_torus_add(major_radius=0.36, minor_radius=0.025, location=(0,0,bz))
    ring = bpy.context.object; assign(ring, dark_mat)

# Porthole window
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(0.36, 0, 0.35))
win = bpy.context.object; win.scale[2] = 0.5; assign(win, glass_mat)

# Porthole frame
bpy.ops.mesh.primitive_torus_add(major_radius=0.14, minor_radius=0.02,
    location=(0.36, 0, 0.35), rotation=(0, math.pi/2, 0))
frame = bpy.context.object; assign(frame, dark_mat)

# Legs (3 landing legs)
for i in range(3):
    a = i * math.pi * 2 / 3
    bpy.ops.mesh.primitive_cylinder_add(radius=0.03, depth=0.6,
        location=(math.cos(a)*0.5, math.sin(a)*0.5, -1.3),
        rotation=(0, math.radians(20), a))
    leg = bpy.context.object; assign(leg, dark_mat)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.08, depth=0.04,
        location=(math.cos(a)*0.55, math.sin(a)*0.55, -1.62))
    pad = bpy.context.object; assign(pad, dark_mat)
""" + _footer(_out())


def _car_script(r, g, b, scale):
    return _header() + f"""
body_mat  = make_mat("Body",   {r}, {g}, {b},  metallic=0.5, roughness=0.3)
dark_mat  = make_mat("Dark",   0.05, 0.05, 0.05, metallic=0.3, roughness=0.8)
glass_mat = make_mat("Glass",  0.50, 0.75, 1.00, metallic=0.0, roughness=0.05)
chrome_mat= make_mat("Chrome", 0.80, 0.80, 0.85, metallic=1.0, roughness=0.1)

# Main body
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.28))
body = bpy.context.object; body.scale=(1.1*{scale}, 0.55, 0.28); assign(body, body_mat)

# Cabin
bpy.ops.mesh.primitive_cube_add(size=1, location=(-0.08, 0, 0.68))
cabin = bpy.context.object; cabin.scale=(0.65, 0.48, 0.22); assign(cabin, body_mat)

# Hood slope front
bpy.ops.mesh.primitive_cube_add(size=1, location=(0.8, 0, 0.48))
hood = bpy.context.object; hood.scale=(0.25, 0.52, 0.06)
hood.rotation_euler[1] = math.radians(-20); assign(hood, body_mat)

# Boot slope rear
bpy.ops.mesh.primitive_cube_add(size=1, location=(-0.85, 0, 0.48))
boot = bpy.context.object; boot.scale=(0.2, 0.52, 0.06)
boot.rotation_euler[1] = math.radians(20); assign(boot, body_mat)

# Wheels (4)
for px in [-0.65, 0.65]:
    for py in [-0.58, 0.58]:
        bpy.ops.mesh.primitive_cylinder_add(radius=0.19, depth=0.14,
            location=(px*{scale}, py, 0.18), rotation=(math.pi/2, 0, 0))
        w = bpy.context.object; assign(w, dark_mat)
        # Hub cap
        bpy.ops.mesh.primitive_cylinder_add(radius=0.10, depth=0.02,
            location=(px*{scale}, py + (0.08 if py > 0 else -0.08), 0.18),
            rotation=(math.pi/2, 0, 0))
        hub = bpy.context.object; assign(hub, chrome_mat)

# Windows
bpy.ops.mesh.primitive_cube_add(size=1, location=(-0.08, 0, 0.72))
glass = bpy.context.object; glass.scale=(0.58, 0.44, 0.18); assign(glass, glass_mat)

# Headlights
for hy in [-0.38, 0.38]:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.08, location=(1.1*{scale}, hy, 0.3))
    hl = bpy.context.object; hl.scale[2] = 0.5
    hl_mat = make_mat("Headlight", 1.0, 1.0, 0.9, emission=2.0)
    assign(hl, hl_mat)

# Taillights
for ty in [-0.38, 0.38]:
    bpy.ops.mesh.primitive_cube_add(size=1, location=(-1.1*{scale}, ty, 0.32))
    tl = bpy.context.object; tl.scale=(0.04, 0.1, 0.06)
    tl_mat = make_mat("Taillight", 1.0, 0.05, 0.05, emission=1.5)
    assign(tl, tl_mat)

# Bumpers
bpy.ops.mesh.primitive_cube_add(size=1, location=(1.15*{scale}, 0, 0.22))
fb = bpy.context.object; fb.scale=(0.05, 0.52, 0.10); assign(fb, chrome_mat)
bpy.ops.mesh.primitive_cube_add(size=1, location=(-1.15*{scale}, 0, 0.22))
rb = bpy.context.object; rb.scale=(0.05, 0.52, 0.10); assign(rb, chrome_mat)

# Windshield
bpy.ops.mesh.primitive_cube_add(size=1, location=(0.35, 0, 0.82))
ws = bpy.context.object; ws.scale=(0.08, 0.44, 0.18)
ws.rotation_euler[1] = math.radians(-55); assign(ws, glass_mat)

# Roof rack detail
bpy.ops.mesh.primitive_cube_add(size=1, location=(-0.08, 0, 0.91))
rack = bpy.context.object; rack.scale=(0.55, 0.44, 0.02); assign(rack, chrome_mat)
""" + _footer(_out())


def _truck_script(r, g, b, scale):
    return _header() + f"""
body_mat  = make_mat("Body",  {r}, {g}, {b}, metallic=0.4, roughness=0.4)
dark_mat  = make_mat("Dark",  0.05, 0.05, 0.05, metallic=0.3, roughness=0.8)
chrome_mat= make_mat("Chrome",0.80, 0.80, 0.85, metallic=1.0, roughness=0.1)
glass_mat = make_mat("Glass", 0.50, 0.75, 1.00, metallic=0.0, roughness=0.05)
cargo_mat = make_mat("Cargo", {r*0.7}, {g*0.7}, {b*0.7}, metallic=0.1, roughness=0.7)

# Cab
bpy.ops.mesh.primitive_cube_add(size=1, location=(0.85, 0, 0.65))
cab = bpy.context.object; cab.scale=(0.65, 0.7, 0.55); assign(cab, body_mat)

# Cab roof
bpy.ops.mesh.primitive_cube_add(size=1, location=(0.85, 0, 1.28))
roof = bpy.context.object; roof.scale=(0.58, 0.65, 0.12); assign(roof, body_mat)

# Cargo container
bpy.ops.mesh.primitive_cube_add(size=1, location=(-0.65, 0, 0.65))
cargo = bpy.context.object; cargo.scale=(1.2, 0.68, 0.65); assign(cargo, cargo_mat)

# Wheels (6 - two rear axles)
for px, py in [(0.7,-0.72),(0.7,0.72),(-0.3,-0.72),(-0.3,0.72),(-1.1,-0.72),(-1.1,0.72)]:
    bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=0.16,
        location=(px, py, 0.22), rotation=(math.pi/2, 0, 0))
    w = bpy.context.object; assign(w, dark_mat)

# Exhaust stacks
for ey in [-0.2, 0.2]:
    bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=0.9,
        location=(0.35, ey, 1.3))
    ex = bpy.context.object; assign(ex, chrome_mat)

# Front grille
bpy.ops.mesh.primitive_cube_add(size=1, location=(1.52, 0, 0.52))
grille = bpy.context.object; grille.scale=(0.04, 0.6, 0.35); assign(grille, chrome_mat)

# Headlights
for hy in [-0.4, 0.4]:
    bpy.ops.mesh.primitive_cylinder_add(radius=0.09, depth=0.05,
        location=(1.53, hy, 0.72), rotation=(0, math.pi/2, 0))
    hl = bpy.context.object
    assign(hl, make_mat("HL", 1.0, 1.0, 0.85, emission=2.0))

# Windshield
bpy.ops.mesh.primitive_cube_add(size=1, location=(1.0, 0, 1.1))
ws = bpy.context.object; ws.scale=(0.06, 0.6, 0.28)
ws.rotation_euler[1] = math.radians(-75); assign(ws, glass_mat)
""" + _footer(_out())


def _tower_script(r, g, b, scale):
    return _header() + f"""
mat1 = make_mat("Stone", {r}, {g}, {b}, metallic=0.05, roughness=0.85)
mat2 = make_mat("Dark",  {r*0.5}, {g*0.5}, {b*0.5}, metallic=0.05, roughness=0.9)
win_mat = make_mat("Window", 0.5, 0.75, 1.0, metallic=0.0, roughness=0.05, emission=1.0)
flag_mat = make_mat("Flag", 0.9, 0.1, 0.1, metallic=0.0, roughness=0.8)

# Stacked floors (8 floors)
for i in range(8):
    s = 0.9 - i * 0.055
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, i*0.65 + 0.32))
    fl = bpy.context.object; fl.scale=(s*{scale}, s*{scale}, 0.32)
    assign(fl, mat1 if i % 2 == 0 else mat2)

    # Floor ledge
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, i*0.65 + 0.65))
    ledge = bpy.context.object; ledge.scale=(s*{scale}+0.06, s*{scale}+0.06, 0.04)
    assign(ledge, mat2)

# Windows on each floor
for i in range(1, 8):
    for side in [0, 1, 2, 3]:
        a = side * math.pi / 2
        s = 0.9 - i * 0.055
        wx = math.cos(a) * s * {scale}
        wy = math.sin(a) * s * {scale}
        bpy.ops.mesh.primitive_cube_add(size=1, location=(wx, wy, i*0.65 + 0.3))
        win = bpy.context.object; win.scale=(0.08, 0.08, 0.14)
        win.rotation_euler[2] = a; assign(win, win_mat)

# Spire
bpy.ops.mesh.primitive_cone_add(radius1=0.35*{scale}, depth=1.4,
    location=(0, 0, 8*0.65 + 0.7))
spire = bpy.context.object; assign(spire, mat2)

# Battlements (8)
for i in range(8):
    a = i * math.pi / 4
    r2 = 0.38 * {scale}
    bpy.ops.mesh.primitive_cube_add(size=1,
        location=(math.cos(a)*r2, math.sin(a)*r2, 8*0.65 + 0.42))
    bt = bpy.context.object; bt.scale=(0.1, 0.1, 0.18); assign(bt, mat1)

# Flag
bpy.ops.mesh.primitive_cylinder_add(radius=0.02, depth=0.5,
    location=(0, 0, 8*0.65 + 1.55))
pole = bpy.context.object; assign(pole, mat2)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0.28, 0, 8*0.65 + 1.6))
flag = bpy.context.object; flag.scale=(0.28, 0.18, 1.0); assign(flag, flag_mat)

# Base foundation
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, -0.08))
base = bpy.context.object; base.scale=(1.2*{scale}, 1.2*{scale}, 0.1); assign(base, mat2)
""" + _footer(_out())


def _castle_script(r, g, b, scale):
    return _header() + f"""
stone_mat = make_mat("Stone", {r}, {g}, {b}, metallic=0.0, roughness=0.9)
dark_mat  = make_mat("Dark",  {r*0.55}, {g*0.55}, {b*0.55}, metallic=0.0, roughness=0.95)
gate_mat  = make_mat("Gate",  0.3, 0.2, 0.1, metallic=0.2, roughness=0.8)

s = {scale}

# Outer walls (4 sides)
for pos, rot, scl in [
    ((0,  1.8*s, 0.7), 0, (1.8*s, 0.18, 0.7)),
    ((0, -1.8*s, 0.7), 0, (1.8*s, 0.18, 0.7)),
    (( 1.8*s, 0, 0.7), math.pi/2, (1.8*s, 0.18, 0.7)),
    ((-1.8*s, 0, 0.7), math.pi/2, (1.8*s, 0.18, 0.7)),
]:
    bpy.ops.mesh.primitive_cube_add(size=1, location=pos)
    w = bpy.context.object; w.scale=scl; w.rotation_euler[2]=rot; assign(w, stone_mat)

# Corner towers (4)
for tx, ty in [(1.8*s,1.8*s),(1.8*s,-1.8*s),(-1.8*s,1.8*s),(-1.8*s,-1.8*s)]:
    bpy.ops.mesh.primitive_cylinder_add(radius=0.42*s, depth=2.2, location=(tx, ty, 1.1))
    t = bpy.context.object; assign(t, stone_mat)
    bpy.ops.mesh.primitive_cone_add(radius1=0.46*s, depth=0.7, location=(tx, ty, 2.35))
    tc = bpy.context.object; assign(tc, dark_mat)

# Keep (central tower)
bpy.ops.mesh.primitive_cylinder_add(radius=0.7*s, depth=3.0, location=(0, 0, 1.5))
keep = bpy.context.object; assign(keep, stone_mat)
bpy.ops.mesh.primitive_cone_add(radius1=0.75*s, depth=0.9, location=(0, 0, 3.15))
keeproof = bpy.context.object; assign(keeproof, dark_mat)

# Gate
bpy.ops.mesh.primitive_cube_add(size=1, location=(1.82*s, 0, 0.55))
gate = bpy.context.object; gate.scale=(0.15, 0.38, 0.55); assign(gate, gate_mat)

# Drawbridge
bpy.ops.mesh.primitive_cube_add(size=1, location=(2.05*s, 0, 0.08))
db = bpy.context.object; db.scale=(0.28, 0.35, 0.05); assign(db, gate_mat)

# Battlements on walls
for i in range(6):
    for side in [1.85*s, -1.85*s]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=((-1.2+i*0.5)*s, side, 1.58))
        m = bpy.context.object; m.scale=(0.15, 0.15, 0.22); assign(m, stone_mat)

# Ground
bpy.ops.mesh.primitive_plane_add(size=5.5*s, location=(0, 0, -0.05))
ground = bpy.context.object; assign(ground, dark_mat)
""" + _footer(_out())


def _spaceship_script(r, g, b, scale):
    return _header() + f"""
hull_mat = make_mat("Hull",  {r}, {g}, {b},  metallic=0.7, roughness=0.2)
dark_mat = make_mat("Dark",  0.05, 0.06, 0.08, metallic=0.5, roughness=0.5)
glow_mat = make_mat("Glow",  1.00, 0.90, 0.10, metallic=0.0, roughness=0.1, emission=4.0)
glass_mat= make_mat("Dome",  0.40, 0.80, 1.00, metallic=0.0, roughness=0.05)
engine_mat=make_mat("Engine",0.80, 0.40, 0.10, metallic=0.0, roughness=0.1, emission=3.0)

# Main saucer body
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.4*{scale}, location=(0,0,0))
saucer = bpy.context.object; saucer.scale[2] = 0.25; assign(saucer, hull_mat)

# Underside dish
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.35*{scale}, location=(0,0,-0.04))
under = bpy.context.object; under.scale[2] = 0.18; assign(under, dark_mat)

# Dome (command module)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.55*{scale}, location=(0,0,0.22))
dome = bpy.context.object; dome.scale[2] = 0.7; assign(dome, glass_mat)

# Dome rim
bpy.ops.mesh.primitive_torus_add(major_radius=0.56*{scale}, minor_radius=0.04,
    location=(0,0,0.2))
rim = bpy.context.object; assign(rim, hull_mat)

# Light pods (8 around rim)
for i in range(8):
    a = i * math.pi / 4
    r2 = 1.2 * {scale}
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.09, location=(math.cos(a)*r2, math.sin(a)*r2, 0.0))
    pod = bpy.context.object; assign(pod, glow_mat)

# Engine vents (3 on underside)
for i in range(3):
    a = i * math.pi * 2 / 3
    bpy.ops.mesh.primitive_cylinder_add(radius=0.18, depth=0.12,
        location=(math.cos(a)*0.7*{scale}, math.sin(a)*0.7*{scale}, -0.18))
    eng = bpy.context.object; assign(eng, engine_mat)

# Antenna array
bpy.ops.mesh.primitive_cylinder_add(radius=0.025, depth=0.7, location=(0,0,0.75))
ant = bpy.context.object; assign(ant, dark_mat)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.07, location=(0,0,1.12))
antball = bpy.context.object; assign(antball, glow_mat)

# Landing struts (3)
for i in range(3):
    a = i * math.pi * 2 / 3
    bpy.ops.mesh.primitive_cylinder_add(radius=0.03, depth=0.45,
        location=(math.cos(a)*0.9*{scale}, math.sin(a)*0.9*{scale}, -0.35),
        rotation=(0, math.radians(25), a))
    strut = bpy.context.object; assign(strut, dark_mat)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.09, depth=0.04,
        location=(math.cos(a)*1.05*{scale}, math.sin(a)*1.05*{scale}, -0.55))
    pad = bpy.context.object; assign(pad, dark_mat)
""" + _footer(_out())


def _robot_script(r, g, b, scale):
    return _header() + f"""
body_mat = make_mat("Body",  {r}, {g}, {b},  metallic=0.6, roughness=0.3)
dark_mat = make_mat("Dark",  0.08, 0.08, 0.12, metallic=0.4, roughness=0.5)
eye_mat  = make_mat("Eyes",  1.0, 0.1, 0.1,  metallic=0.0, roughness=0.1, emission=4.0)
glow_mat = make_mat("Glow",  0.1, 1.0, 0.9,  metallic=0.0, roughness=0.1, emission=3.0)
joint_mat= make_mat("Joint", 0.7, 0.7, 0.7,  metallic=0.8, roughness=0.2)

s = {scale}

# Torso
bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,0.6))
torso = bpy.context.object; torso.scale=(0.42*s, 0.28*s, 0.5); assign(torso, body_mat)

# Chest panel detail
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0.29*s, 0.65))
panel = bpy.context.object; panel.scale=(0.28*s, 0.01, 0.25); assign(panel, dark_mat)

# Chest glow strip
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0.3*s, 0.62))
strip = bpy.context.object; strip.scale=(0.22*s, 0.008, 0.04); assign(strip, glow_mat)

# Head
bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,1.42))
head = bpy.context.object; head.scale=(0.36*s, 0.26*s, 0.3); assign(head, body_mat)

# Eyes (2)
for ex in [-0.12*s, 0.12*s]:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.07, location=(ex, 0.27*s, 1.48))
    eye = bpy.context.object; assign(eye, eye_mat)

# Ear panels
for ex in [-0.37*s, 0.37*s]:
    bpy.ops.mesh.primitive_cube_add(size=1, location=(ex, 0, 1.42))
    ear = bpy.context.object; ear.scale=(0.04, 0.06*s, 0.15); assign(ear, dark_mat)

# Neck
bpy.ops.mesh.primitive_cylinder_add(radius=0.1*s, depth=0.2, location=(0,0,1.14))
neck = bpy.context.object; assign(neck, joint_mat)

# Shoulders
for sx in [-0.6*s, 0.6*s]:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.16, location=(sx, 0, 1.0))
    sh = bpy.context.object; sh.scale=(1, 0.7, 0.7); assign(sh, joint_mat)

# Upper arms
for sx in [-0.72*s, 0.72*s]:
    bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=0.45, location=(sx, 0, 0.72))
    ua = bpy.context.object; assign(ua, body_mat)

# Elbow joints
for sx in [-0.72*s, 0.72*s]:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, location=(sx, 0, 0.48))
    ej = bpy.context.object; assign(ej, joint_mat)

# Lower arms
for sx in [-0.72*s, 0.72*s]:
    bpy.ops.mesh.primitive_cylinder_add(radius=0.09, depth=0.4, location=(sx, 0, 0.22))
    la = bpy.context.object; assign(la, dark_mat)

# Hands
for sx in [-0.72*s, 0.72*s]:
    bpy.ops.mesh.primitive_cube_add(size=1, location=(sx, 0, -0.02))
    hand = bpy.context.object; hand.scale=(0.13, 0.1, 0.18); assign(hand, body_mat)

# Hip block
bpy.ops.mesh.primitive_cube_add(size=1, location=(0,0,0.18))
hip = bpy.context.object; hip.scale=(0.38*s, 0.25*s, 0.16); assign(hip, dark_mat)

# Thighs
for lx in [-0.2*s, 0.2*s]:
    bpy.ops.mesh.primitive_cylinder_add(radius=0.13, depth=0.45, location=(lx, 0, -0.16))
    th = bpy.context.object; assign(th, body_mat)

# Knee joints
for lx in [-0.2*s, 0.2*s]:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(lx, 0, -0.42))
    kj = bpy.context.object; assign(kj, joint_mat)

# Shins
for lx in [-0.2*s, 0.2*s]:
    bpy.ops.mesh.primitive_cylinder_add(radius=0.11, depth=0.42, location=(lx, 0, -0.68))
    sh = bpy.context.object; assign(sh, dark_mat)

# Feet
for lx in [-0.2*s, 0.2*s]:
    bpy.ops.mesh.primitive_cube_add(size=1, location=(lx, 0.06*s, -0.95))
    foot = bpy.context.object; foot.scale=(0.16, 0.24*s, 0.09); assign(foot, body_mat)

# Antenna
bpy.ops.mesh.primitive_cylinder_add(radius=0.022, depth=0.4, location=(0, 0, 1.88))
ant = bpy.context.object; assign(ant, dark_mat)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.07, location=(0, 0, 2.1))
antball = bpy.context.object; assign(antball, glow_mat)
""" + _footer(_out())


def _house_script(r, g, b, scale):
    return _header() + f"""
wall_mat = make_mat("Walls",  {r}, {g}, {b},  metallic=0.0, roughness=0.9)
roof_mat = make_mat("Roof",   {r*0.45}, {g*0.45}, {b*0.45}, metallic=0.0, roughness=0.85)
door_mat = make_mat("Door",   0.35, 0.20, 0.05, metallic=0.1, roughness=0.9)
win_mat  = make_mat("Win",    0.50, 0.75, 1.00, metallic=0.0, roughness=0.05)
trim_mat = make_mat("Trim",   0.90, 0.88, 0.82, metallic=0.0, roughness=0.8)

s = {scale}

# Foundation
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, -0.08))
fnd = bpy.context.object; fnd.scale=(1.25*s, 1.0*s, 0.1); assign(fnd, trim_mat)

# Main walls
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.6))
walls = bpy.context.object; walls.scale=(1.15*s, 0.9*s, 0.62); assign(walls, wall_mat)

# Roof (4-sided pyramid)
bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=1.45*s, depth=0.95,
    location=(0, 0, 1.55))
roof = bpy.context.object; roof.rotation_euler[2] = math.pi/4; assign(roof, roof_mat)

# Roof overhang trim
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 1.12))
overhang = bpy.context.object; overhang.scale=(1.22*s, 0.97*s, 0.04); assign(overhang, trim_mat)

# Chimney
bpy.ops.mesh.primitive_cube_add(size=1, location=(0.55*s, 0.2*s, 1.68))
ch = bpy.context.object; ch.scale=(0.14, 0.12, 0.4); assign(ch, roof_mat)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0.55*s, 0.2*s, 1.9))
chcap = bpy.context.object; chcap.scale=(0.18, 0.16, 0.04); assign(chcap, trim_mat)

# Front door
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0.92*s, 0.38))
door = bpy.context.object; door.scale=(0.2, 0.04, 0.36); assign(door, door_mat)

# Door knob
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.03, location=(0.14, 0.96*s, 0.36))
knob = bpy.context.object; assign(knob, trim_mat)

# Door frame
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0.92*s, 0.42))
df = bpy.context.object; df.scale=(0.25, 0.035, 0.42); assign(df, trim_mat)

# Porch overhang
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 1.15*s, 0.85))
porch = bpy.context.object; porch.scale=(0.5, 0.3, 0.04); assign(porch, roof_mat)

# Porch posts
for px in [-0.32*s, 0.32*s]:
    bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=0.7, location=(px, 1.18*s, 0.52))
    post = bpy.context.object; assign(post, trim_mat)

# Front windows (2)
for wx in [-0.55*s, 0.55*s]:
    bpy.ops.mesh.primitive_cube_add(size=1, location=(wx, 0.92*s, 0.65))
    win = bpy.context.object; win.scale=(0.22, 0.03, 0.22); assign(win, win_mat)
    # Window cross
    bpy.ops.mesh.primitive_cube_add(size=1, location=(wx, 0.93*s, 0.65))
    cross = bpy.context.object; cross.scale=(0.22, 0.015, 0.015); assign(cross, trim_mat)

# Side windows
for wy, wz in [(0.3*s, 0.65), (-0.3*s, 0.65)]:
    bpy.ops.mesh.primitive_cube_add(size=1, location=(1.16*s, wy, wz))
    sw = bpy.context.object; sw.scale=(0.03, 0.2, 0.2); assign(sw, win_mat)

# Porch steps
for i in range(3):
    bpy.ops.mesh.primitive_cube_add(size=1,
        location=(0, 1.12*s + i*0.18, 0.28 - i*0.07))
    step = bpy.context.object; step.scale=(0.4, 0.1, 0.07); assign(step, trim_mat)

# Mailbox
bpy.ops.mesh.primitive_cylinder_add(radius=0.025, depth=0.65,
    location=(-1.4*s, -1.2*s, 0.3))
mpost = bpy.context.object; assign(mpost, trim_mat)
bpy.ops.mesh.primitive_cube_add(size=1, location=(-1.4*s, -1.2*s, 0.68))
mbox = bpy.context.object; mbox.scale=(0.12, 0.18, 0.1); assign(mbox, wall_mat)

# Garden path
bpy.ops.mesh.primitive_cylinder_add(radius=0.18, depth=0.02, location=(0, 1.6*s, -0.04))
path = bpy.context.object; path.scale=(0.5, 1.0, 1.0); assign(path, trim_mat)

# Fence posts (5)
for i in range(5):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.025, depth=0.45,
        location=(-1.1*s + i*0.55*s, -1.4*s, 0.2))
    fp = bpy.context.object; assign(fp, trim_mat)
""" + _footer(_out())


def _plane_script(r, g, b, scale):
    return _header() + f"""
body_mat  = make_mat("Body",    {r}, {g}, {b},  metallic=0.5, roughness=0.3)
dark_mat  = make_mat("Dark",    0.10, 0.10, 0.12, metallic=0.4, roughness=0.5)
glass_mat = make_mat("Cockpit", 0.40, 0.80, 1.00, metallic=0.0, roughness=0.05)
engine_mat= make_mat("Engine",  0.20, 0.20, 0.22, metallic=0.6, roughness=0.4)
stripe_mat= make_mat("Stripe",  {min(r+0.3,1)}, {min(g+0.3,1)}, {min(b+0.3,1)}, metallic=0.3, roughness=0.4)

s = {scale}

# Fuselage
bpy.ops.mesh.primitive_cylinder_add(radius=0.24, depth=3.6,
    location=(0,0,0), rotation=(0, math.pi/2, 0))
fuse = bpy.context.object; assign(fuse, body_mat)

# Nose
bpy.ops.mesh.primitive_cone_add(radius1=0.24, depth=0.65,
    location=(2.13,0,0), rotation=(0, math.pi/2, 0))
nose = bpy.context.object; assign(nose, body_mat)

# Tail cone
bpy.ops.mesh.primitive_cone_add(radius1=0.22, radius2=0.06, depth=0.55,
    location=(-2.08,0,0), rotation=(0, -math.pi/2, 0))
tail = bpy.context.object; assign(tail, body_mat)

# Main wings
bpy.ops.mesh.primitive_cube_add(size=1, location=(0.2,0,0))
mw = bpy.context.object; mw.scale=(0.06, 1.8*s, 0.38); assign(mw, body_mat)

# Winglets
for wy in [-1.85*s, 1.85*s]:
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.2, wy, 0.22))
    wl = bpy.context.object; wl.scale=(0.04, 0.06, 0.22)
    wl.rotation_euler[0] = math.radians(10 if wy > 0 else -10); assign(wl, body_mat)

# Wing stripe
bpy.ops.mesh.primitive_cube_add(size=1, location=(0.2, 0, 0.06))
wstripe = bpy.context.object; wstripe.scale=(0.04, 1.75*s, 0.05); assign(wstripe, stripe_mat)

# Vertical stabilizer
bpy.ops.mesh.primitive_cube_add(size=1, location=(-1.45, 0, 0.4))
vs = bpy.context.object; vs.scale=(0.28, 0.05, 0.38); assign(vs, body_mat)

# Horizontal stabilizers
bpy.ops.mesh.primitive_cube_add(size=1, location=(-1.45, 0, 0.05))
hs = bpy.context.object; hs.scale=(0.06, 0.65*s, 0.2); assign(hs, body_mat)

# Cockpit dome
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.28, location=(1.3, 0, 0.14))
cock = bpy.context.object; cock.scale[2] = 0.65; assign(cock, glass_mat)

# Cockpit frame
bpy.ops.mesh.primitive_torus_add(major_radius=0.29, minor_radius=0.02,
    location=(1.3, 0, 0.14), rotation=(0, math.pi/2, 0))
cf = bpy.context.object; assign(cf, body_mat)

# Engines (2 under wings)
for ey in [-0.75*s, 0.75*s]:
    bpy.ops.mesh.primitive_cylinder_add(radius=0.14, depth=0.62,
        location=(0.05, ey, -0.32), rotation=(0, math.pi/2, 0))
    eng = bpy.context.object; assign(eng, engine_mat)
    # Engine intake ring
    bpy.ops.mesh.primitive_torus_add(major_radius=0.14, minor_radius=0.025,
        location=(0.37, ey, -0.32), rotation=(0, math.pi/2, 0))
    ring = bpy.context.object; assign(ring, dark_mat)
    # Engine exhaust glow
    bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=0.04,
        location=(-0.27, ey, -0.32), rotation=(0, math.pi/2, 0))
    exh = bpy.context.object
    assign(exh, make_mat("Exhaust", 1.0, 0.5, 0.1, emission=2.0))

# Landing gear (front)
bpy.ops.mesh.primitive_cylinder_add(radius=0.035, depth=0.45,
    location=(0.9, 0, -0.45))
lgf = bpy.context.object; assign(lgf, dark_mat)
bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=0.12,
    location=(0.9, 0, -0.7), rotation=(math.pi/2, 0, 0))
wf = bpy.context.object; assign(wf, dark_mat)

# Landing gear (rear, 2)
for gy in [-0.38*s, 0.38*s]:
    bpy.ops.mesh.primitive_cylinder_add(radius=0.035, depth=0.38,
        location=(-0.4, gy, -0.42))
    lgr = bpy.context.object; assign(lgr, dark_mat)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=0.12,
        location=(-0.4, gy, -0.64), rotation=(math.pi/2, 0, 0))
    wr = bpy.context.object; assign(wr, dark_mat)
""" + _footer(_out())


def _pyramid_script(r, g, b, scale):
    return _header() + f"""
stone_mat = make_mat("Stone",  {r}, {g}, {b},  metallic=0.05, roughness=0.88)
dark_mat  = make_mat("Dark",   {r*0.55}, {g*0.55}, {b*0.55}, metallic=0.05, roughness=0.92)
gold_mat  = make_mat("Gold",   1.00, 0.78, 0.10, metallic=1.0, roughness=0.1)
sand_mat  = make_mat("Sand",   0.85, 0.75, 0.50, metallic=0.0, roughness=0.95)

s = {scale}

# Ground
bpy.ops.mesh.primitive_plane_add(size=5.5*s, location=(0, 0, -0.05))
ground = bpy.context.object; assign(ground, sand_mat)

# Base platform
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.0))
base = bpy.context.object; base.scale=(2.1*s, 2.1*s, 0.08); assign(base, dark_mat)

# Step tiers (4)
for i, (r2, h) in enumerate([(1.85, 0.25),(1.45, 0.5),(1.05, 0.75),(0.65, 1.0)]):
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=r2*s, depth=0.28,
        location=(0, 0, h))
    tier = bpy.context.object; tier.rotation_euler[2] = math.pi/4
    assign(tier, stone_mat if i % 2 == 0 else dark_mat)

# Main pyramid body
bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=1.85*s, depth=2.1,
    location=(0, 0, 1.05))
pyr = bpy.context.object; pyr.rotation_euler[2] = math.pi/4; assign(pyr, stone_mat)

# Capstone
bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=0.18*s, depth=0.32,
    location=(0, 0, 2.2))
cap = bpy.context.object; cap.rotation_euler[2] = math.pi/4; assign(cap, gold_mat)

# Entrance
bpy.ops.mesh.primitive_cube_add(size=1, location=(1.88*s, 0, 0.25))
entrance = bpy.context.object; entrance.scale=(0.08, 0.3, 0.3); assign(entrance, dark_mat)

# Corner obelisks (4)
for ox, oy in [(2.2*s,2.2*s),(2.2*s,-2.2*s),(-2.2*s,2.2*s),(-2.2*s,-2.2*s)]:
    bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=0.9, location=(ox, oy, 0.45))
    ob = bpy.context.object; assign(ob, dark_mat)
    bpy.ops.mesh.primitive_cone_add(radius1=0.12, depth=0.2, location=(ox, oy, 0.95))
    obc = bpy.context.object; assign(obc, gold_mat)
""" + _footer(_out())


def _diamond_script(r, g, b, scale):
    return _header() + f"""
gem_mat  = make_mat("Gem",   {r}, {g}, {b}, metallic=0.0, roughness=0.02)
glow_mat = make_mat("Glow",  {r}, {g}, {b}, metallic=0.0, roughness=0.0, emission=2.0)
base_mat = make_mat("Base",  0.15, 0.15, 0.18, metallic=0.8, roughness=0.2)

s = {scale}

# Upper crown (8-sided)
bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=0.78*s, depth=1.1,
    location=(0, 0, 0.55))
crown = bpy.context.object; assign(crown, gem_mat)

# Lower pavilion (8-sided, inverted)
bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=0.78*s, depth=0.75,
    location=(0, 0, -0.38))
pav = bpy.context.object; pav.rotation_euler[0] = math.pi; assign(pav, gem_mat)

# Girdle (thin ring at widest point)
bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.8*s, depth=0.04,
    location=(0, 0, 0.0))
girdle = bpy.context.object; assign(girdle, glow_mat)

# Crown facet rings (3)
for z, rad in [(0.25, 0.72*s), (0.52, 0.55*s), (0.78, 0.32*s)]:
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=rad, depth=0.025,
        location=(0, 0, z))
    ring = bpy.context.object; assign(ring, gem_mat)

# Pavilion facet rings (2)
for z, rad in [(-0.22, 0.6*s), (-0.5, 0.35*s)]:
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=rad, depth=0.025,
        location=(0, 0, z))
    ring = bpy.context.object; assign(ring, gem_mat)

# Table (flat top facet)
bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.28*s, depth=0.03,
    location=(0, 0, 1.08))
table = bpy.context.object; assign(table, glow_mat)

# Culet (bottom point cap)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.04, location=(0, 0, -0.76))
culet = bpy.context.object; assign(culet, glow_mat)

# Display base
bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.45*s, depth=0.12,
    location=(0, 0, -1.0))
base = bpy.context.object; assign(base, base_mat)
bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=0.45*s, radius2=0.32*s, depth=0.2,
    location=(0, 0, -0.82))
basecone = bpy.context.object; assign(basecone, base_mat)
""" + _footer(_out())


def _crystal_script(r, g, b, scale):
    return _header() + f"""
gem_mat  = make_mat("Crystal", {r}, {g}, {b}, metallic=0.0, roughness=0.02)
glow_mat = make_mat("Glow",    {r}, {g}, {b}, metallic=0.0, roughness=0.0, emission=3.0)
rock_mat = make_mat("Rock",    0.25, 0.22, 0.20, metallic=0.0, roughness=0.95)

s = {scale}

# Central large crystal
bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=0.32*s, depth=1.8,
    location=(0, 0, 0.9))
main = bpy.context.object; main.rotation_euler[0] = math.radians(5); assign(main, gem_mat)
bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=0.28*s, depth=0.3,
    location=(0, 0, -0.15))
mainbase = bpy.context.object; mainbase.rotation_euler[0] = math.pi; assign(mainbase, gem_mat)

# Cluster crystals (6 around base)
heights = [1.2, 0.9, 1.4, 0.85, 1.1, 1.3]
tilts   = [8, 15, -10, 20, -15, 12]
for i in range(6):
    a = i * math.pi / 3
    dist = 0.55 * s
    bpy.ops.mesh.primitive_cone_add(vertices=6,
        radius1=0.18*s, depth=heights[i],
        location=(math.cos(a)*dist, math.sin(a)*dist, heights[i]/2))
    c = bpy.context.object
    c.rotation_euler = (math.radians(tilts[i]), 0, a)
    assign(c, gem_mat)

# Small accent crystals
for i in range(4):
    a = i * math.pi / 2 + math.pi/4
    dist = 0.85 * s
    bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=0.09*s, depth=0.6,
        location=(math.cos(a)*dist, math.sin(a)*dist, 0.3))
    sc = bpy.context.object; sc.rotation_euler[0] = math.radians(25); assign(sc, gem_mat)

# Glow at tips
for z in [1.85, 1.25, 1.45]:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05, location=(0, 0, z))
    g = bpy.context.object; assign(g, glow_mat)

# Rock base
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.7*s, location=(0, 0, -0.35))
rock = bpy.context.object; rock.scale[2] = 0.38; assign(rock, rock_mat)
""" + _footer(_out())


def _tree_script(r, g, b, scale):
    return _header() + f"""
trunk_mat  = make_mat("Trunk",  0.35, 0.20, 0.06, metallic=0.0, roughness=0.95)
leaves_mat = make_mat("Leaves", {r}, {g}, {b},  metallic=0.0, roughness=0.75)
dark_leaf  = make_mat("DarkLeaf", {r*0.65}, {g*0.65}, {b*0.65}, metallic=0.0, roughness=0.8)
ground_mat = make_mat("Ground", 0.22, 0.42, 0.12, metallic=0.0, roughness=0.95)

s = {scale}

# Ground disc
bpy.ops.mesh.primitive_cylinder_add(radius=1.4*s, depth=0.06, location=(0,0,-0.03))
gd = bpy.context.object; assign(gd, ground_mat)

# Roots (4 buttress roots)
for i in range(4):
    a = i * math.pi / 2
    bpy.ops.mesh.primitive_cone_add(radius1=0.22, radius2=0.06, depth=0.5,
        location=(math.cos(a)*0.22*s, math.sin(a)*0.22*s, 0.1),
        rotation=(0, math.radians(40), a))
    root = bpy.context.object; assign(root, trunk_mat)

# Trunk base
bpy.ops.mesh.primitive_cylinder_add(radius=0.2*s, depth=1.2, location=(0,0,0.6))
trunk = bpy.context.object; assign(trunk, trunk_mat)

# Trunk taper
bpy.ops.mesh.primitive_cone_add(radius1=0.18*s, radius2=0.1*s, depth=0.8,
    location=(0,0,1.4))
trunkm = bpy.context.object; assign(trunkm, trunk_mat)

# Branches (4 main branches)
for i in range(4):
    a = i * math.pi / 2
    bpy.ops.mesh.primitive_cylinder_add(radius=0.05, depth=0.9,
        location=(math.cos(a)*0.5*s, math.sin(a)*0.5*s, 1.85),
        rotation=(0, math.radians(45), a))
    branch = bpy.context.object; assign(branch, trunk_mat)

# Foliage layers (cone stack)
for z, rad, dark in [(2.0,0.95,False),(2.55,0.82,True),(3.05,0.65,False),(3.48,0.48,True),(3.82,0.3,False)]:
    bpy.ops.mesh.primitive_cone_add(vertices=12, radius1=rad*s, depth=0.7,
        location=(0, 0, z))
    layer = bpy.context.object
    assign(layer, dark_leaf if dark else leaves_mat)

# Top tuft
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.28*s, location=(0, 0, 4.1))
top = bpy.context.object; assign(top, leaves_mat)

# Branch foliage clusters
for i in range(4):
    a = i * math.pi / 2
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.35*s,
        location=(math.cos(a)*0.75*s, math.sin(a)*0.75*s, 2.4))
    cluster = bpy.context.object; cluster.scale[2] = 0.75; assign(cluster, leaves_mat)
""" + _footer(_out())


def _dragon_script(r, g, b, scale):
    return _header() + f"""
body_mat  = make_mat("Body",  {r}, {g}, {b},  metallic=0.1, roughness=0.5)
dark_mat  = make_mat("Dark",  {r*0.5}, {g*0.5}, {b*0.5}, metallic=0.1, roughness=0.6)
eye_mat   = make_mat("Eyes",  1.0, 0.8, 0.0,  metallic=0.0, roughness=0.1, emission=3.0)
wing_mat  = make_mat("Wings", {r*0.7}, {g*0.7}, {b*0.7}, metallic=0.0, roughness=0.7)
fire_mat  = make_mat("Fire",  1.0, 0.4, 0.0,  metallic=0.0, roughness=0.1, emission=5.0)

s = {scale}

# Body
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.8*s, location=(0,0,0))
body = bpy.context.object; body.scale=(1.2,0.75,0.7); assign(body, body_mat)

# Chest
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.65*s, location=(0.65*s,0,0.05))
chest = bpy.context.object; chest.scale=(0.85,0.65,0.65); assign(chest, body_mat)

# Neck (3 segments)
for i, (nx,nz,nr) in enumerate([(1.15*s,0.38,0.28),(1.48*s,0.72,0.24),(1.72*s,1.05,0.20)]):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=nr*s, location=(nx,0,nz))
    neck = bpy.context.object; assign(neck, body_mat)

# Head
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.4*s, location=(1.85*s,0,1.3))
head = bpy.context.object; head.scale=(1.4,0.88,0.88); assign(head, body_mat)

# Snout
bpy.ops.mesh.primitive_cone_add(radius1=0.24*s, radius2=0.14*s, depth=0.65,
    location=(2.35*s,0,1.25), rotation=(0,math.pi/2,0))
snout = bpy.context.object; assign(snout, body_mat)

# Nostrils
for ny in [-0.08*s, 0.08*s]:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.045, location=(2.62*s, ny, 1.25))
    nostril = bpy.context.object; assign(nostril, dark_mat)

# Fire breath
bpy.ops.mesh.primitive_cone_add(radius1=0.18*s, radius2=0.0, depth=0.85,
    location=(3.05*s,0,1.22), rotation=(0,math.pi/2,0))
fire = bpy.context.object; assign(fire, fire_mat)

# Eyes
for ey in [-0.28*s, 0.28*s]:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, location=(1.92*s, ey, 1.42))
    eye = bpy.context.object; assign(eye, eye_mat)

# Horns
for hy in [-0.22*s, 0.22*s]:
    bpy.ops.mesh.primitive_cone_add(radius1=0.07, radius2=0.0, depth=0.6,
        location=(1.72*s, hy, 1.72))
    horn = bpy.context.object
    horn.rotation_euler=(0,math.radians(-25),math.radians(15 if hy>0 else -15))
    assign(horn, dark_mat)

# Spine ridge
for sx in [0.3, -0.1, -0.5, -0.8]:
    bpy.ops.mesh.primitive_cone_add(radius1=0.07, radius2=0.0, depth=0.42,
        location=(sx*s, 0, 0.88))
    spine = bpy.context.object; spine.rotation_euler[1]=math.radians(10); assign(spine, dark_mat)

# Wings (left)
bpy.ops.mesh.primitive_cone_add(radius1=0.06, radius2=0.0, depth=2.4,
    location=(-0.2*s,-1.9*s,1.2), rotation=(math.radians(-75),0,math.radians(20)))
wl = bpy.context.object; assign(wl, wing_mat)

# Wings (right)
bpy.ops.mesh.primitive_cone_add(radius1=0.06, radius2=0.0, depth=2.4,
    location=(-0.2*s,1.9*s,1.2), rotation=(math.radians(75),0,math.radians(-20)))
wr = bpy.context.object; assign(wr, wing_mat)

# Legs (4)
for lx,ly,lz in [(0.5*s,-0.65*s,-0.55),(0.5*s,0.65*s,-0.55),(-0.6*s,-0.65*s,-0.55),(-0.6*s,0.65*s,-0.55)]:
    bpy.ops.mesh.primitive_cylinder_add(radius=0.16, depth=0.85, location=(lx,ly,lz))
    leg = bpy.context.object; assign(leg, body_mat)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.15, location=(lx,ly,lz-0.5))
    claw = bpy.context.object; claw.scale=(1,1,0.5); assign(claw, dark_mat)

# Tail
for tx,tz,tr in [(-0.85*s,0,-0.1,),(-1.35*s,0,-0.28),(-1.8*s,0,-0.45),(-2.2*s,0,-0.6)]:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=max(0.28-abs(tx)*0.05,0.1)*s,
        location=(tx,0,tz))
    tseg = bpy.context.object; assign(tseg, body_mat)
bpy.ops.mesh.primitive_cone_add(radius1=0.12*s, radius2=0.0, depth=0.5,
    location=(-2.5*s,0,-0.7), rotation=(0,math.radians(-40),0))
tailtip = bpy.context.object; assign(tailtip, dark_mat)
""" + _footer(_out())


def _submarine_script(r, g, b, scale):
    return _header() + f"""
hull_mat  = make_mat("Hull",    {r}, {g}, {b},  metallic=0.5, roughness=0.4)
dark_mat  = make_mat("Dark",    {r*0.5}, {g*0.5}, {b*0.5}, metallic=0.4, roughness=0.5)
glass_mat = make_mat("Port",    0.40, 0.80, 1.00, metallic=0.0, roughness=0.05)
prop_mat  = make_mat("Prop",    0.70, 0.65, 0.30, metallic=0.8, roughness=0.2)

s = {scale}

# Main pressure hull
bpy.ops.mesh.primitive_cylinder_add(radius=0.55*s, depth=3.8, location=(0,0,0),
    rotation=(0,math.pi/2,0))
hull = bpy.context.object; assign(hull, hull_mat)

# Bow (rounded front)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.55*s, location=(1.9,0,0))
bow = bpy.context.object; bow.scale=(0.8,1,1); assign(bow, hull_mat)

# Stern (tapered rear)
bpy.ops.mesh.primitive_cone_add(radius1=0.55*s, radius2=0.18*s, depth=0.8,
    location=(-2.25,0,0), rotation=(0,-math.pi/2,0))
stern = bpy.context.object; assign(stern, hull_mat)

# Conning tower (sail)
bpy.ops.mesh.primitive_cylinder_add(radius=0.2*s, depth=0.9, location=(0.3,0,0.68))
sail = bpy.context.object; assign(sail, hull_mat)
bpy.ops.mesh.primitive_cylinder_add(radius=0.22*s, depth=0.1, location=(0.3,0,1.15))
sailcap = bpy.context.object; assign(sailcap, dark_mat)

# Periscope
bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=0.7, location=(0.4,0,1.6))
peri = bpy.context.object; assign(peri, dark_mat)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0.4,0,1.98))
perih = bpy.context.object; perih.scale=(0.06,0.12,0.06); assign(perih, dark_mat)

# Portholes
for px in [0.8, 0.2, -0.4, -1.0]:
    for py in [-0.56*s, 0.56*s]:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.07, location=(px, py, 0.12))
        port = bpy.context.object; port.scale[2] = 0.4; assign(port, glass_mat)

# Diving planes (2 pairs)
for px in [1.2, -1.5]:
    bpy.ops.mesh.primitive_cube_add(size=1, location=(px, 0, 0))
    dp = bpy.context.object; dp.scale=(0.25, 0.85*s, 0.07); assign(dp, dark_mat)

# Propeller
bpy.ops.mesh.primitive_cylinder_add(radius=0.08, depth=0.15, location=(-2.48,0,0),
    rotation=(0,math.pi/2,0))
phub = bpy.context.object; assign(phub, prop_mat)
for i in range(4):
    a = i * math.pi / 2
    bpy.ops.mesh.primitive_cube_add(size=1,
        location=(-2.52, math.cos(a)*0.38*s, math.sin(a)*0.38*s))
    blade = bpy.context.object; blade.scale=(0.06, 0.28, 0.06)
    blade.rotation_euler=(a, 0, math.radians(20)); assign(blade, prop_mat)

# Hull bands (3 reinforcing rings)
for bx in [-0.8, 0.2, 1.2]:
    bpy.ops.mesh.primitive_torus_add(major_radius=0.56*s, minor_radius=0.03,
        location=(bx,0,0), rotation=(0,math.pi/2,0))
    band = bpy.context.object; assign(band, dark_mat)

# Torpedo tubes (2)
for ty in [-0.25*s, 0.25*s]:
    bpy.ops.mesh.primitive_cylinder_add(radius=0.08, depth=0.4,
        location=(2.1, ty, 0), rotation=(0,math.pi/2,0))
    tube = bpy.context.object; assign(tube, dark_mat)
""" + _footer(_out())


def _mushroom_script(r, g, b, scale):
    return _header() + f"""
cap_mat   = make_mat("Cap",   {r}, {g}, {b},  metallic=0.0, roughness=0.7)
spot_mat  = make_mat("Spots", 0.95, 0.95, 0.92, metallic=0.0, roughness=0.8)
stem_mat  = make_mat("Stem",  0.90, 0.85, 0.75, metallic=0.0, roughness=0.85)
gill_mat  = make_mat("Gills", 0.80, 0.72, 0.62, metallic=0.0, roughness=0.9)
grass_mat = make_mat("Grass", 0.22, 0.55, 0.15, metallic=0.0, roughness=0.9)

s = {scale}

# Grass base
bpy.ops.mesh.primitive_cylinder_add(radius=1.2*s, depth=0.06, location=(0,0,-0.03))
grass = bpy.context.object; assign(grass, grass_mat)

# Stem
bpy.ops.mesh.primitive_cylinder_add(radius=0.28*s, depth=1.1, location=(0,0,0.55))
stem = bpy.context.object; assign(stem, stem_mat)

# Stem base flare
bpy.ops.mesh.primitive_cone_add(radius1=0.42*s, radius2=0.28*s, depth=0.22,
    location=(0,0,0.08))
base = bpy.context.object; base.rotation_euler[0]=math.pi; assign(base, stem_mat)

# Cap
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.95*s, location=(0,0,1.55))
cap = bpy.context.object; cap.scale=(1,1,0.72); assign(cap, cap_mat)

# Cap rim
bpy.ops.mesh.primitive_torus_add(major_radius=0.96*s, minor_radius=0.08,
    location=(0,0,1.18))
rim = bpy.context.object; assign(rim, cap_mat)

# Gills under cap
for i in range(12):
    a = i * math.pi / 6
    bpy.ops.mesh.primitive_cube_add(size=1,
        location=(math.cos(a)*0.6*s, math.sin(a)*0.6*s, 1.2))
    gill = bpy.context.object; gill.scale=(0.04, 0.4*s, 0.12)
    gill.rotation_euler[2] = a; assign(gill, gill_mat)

# White spots on cap (7)
spot_positions = [(0,0.65*s,1.88),(0.55*s,0.28*s,1.82),(-0.55*s,0.28*s,1.82),
                  (0.45*s,-0.42*s,1.78),(-0.45*s,-0.42*s,1.78),(0,0,1.98),(0.28*s,0.55*s,1.95)]
for sx,sy,sz in spot_positions:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, location=(sx,sy,sz))
    spot = bpy.context.object; spot.scale[2]=0.45; assign(spot, spot_mat)

# Small side mushrooms (2)
for ox, oy, osc in [(0.9*s, 0.5*s, 0.55), (-0.8*s, -0.6*s, 0.45)]:
    bpy.ops.mesh.primitive_cylinder_add(radius=0.1*osc, depth=0.45*osc, location=(ox,oy,0.22*osc))
    sm_stem = bpy.context.object; assign(sm_stem, stem_mat)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.32*osc, location=(ox,oy,0.52*osc))
    sm_cap = bpy.context.object; sm_cap.scale[2]=0.72; assign(sm_cap, cap_mat)
""" + _footer(_out())


def _lighthouse_script(r, g, b, scale):
    return _header() + f"""
tower_mat = make_mat("Tower",  {r}, {g}, {b},  metallic=0.05, roughness=0.85)
dark_mat  = make_mat("Dark",   {r*0.55}, {g*0.55}, {b*0.55}, metallic=0.05, roughness=0.9)
glass_mat = make_mat("Glass",  0.80, 0.95, 1.00, metallic=0.0, roughness=0.02)
light_mat = make_mat("Light",  1.00, 0.95, 0.70, metallic=0.0, roughness=0.0, emission=8.0)
stripe_mat= make_mat("Stripe", 0.90, 0.15, 0.15, metallic=0.0, roughness=0.85)
rock_mat  = make_mat("Rock",   0.40, 0.38, 0.35, metallic=0.0, roughness=0.95)

s = {scale}

# Rock base
bpy.ops.mesh.primitive_cylinder_add(radius=1.0*s, depth=0.5, location=(0,0,-0.25))
rock = bpy.context.object; rock.scale[2]=0.5; assign(rock, rock_mat)

# Foundation
bpy.ops.mesh.primitive_cylinder_add(radius=0.75*s, depth=0.4, location=(0,0,0.2))
fnd = bpy.context.object; assign(fnd, dark_mat)

# Tower body (tapered cylinder, 6 stripes)
stripe_height = 0.4
for i in range(6):
    rad = (0.6 - i * 0.04) * s
    bpy.ops.mesh.primitive_cylinder_add(radius=rad, depth=stripe_height,
        location=(0, 0, 0.6 + i * stripe_height))
    seg = bpy.context.object
    assign(seg, stripe_mat if i % 2 == 0 else tower_mat)

# Balcony
bpy.ops.mesh.primitive_torus_add(major_radius=0.62*s, minor_radius=0.06,
    location=(0, 0, 3.08))
balcony = bpy.context.object; assign(balcony, dark_mat)
bpy.ops.mesh.primitive_cylinder_add(radius=0.64*s, depth=0.08, location=(0,0,2.95))
floor = bpy.context.object; assign(floor, dark_mat)

# Balcony railing posts (8)
for i in range(8):
    a = i * math.pi / 4
    bpy.ops.mesh.primitive_cylinder_add(radius=0.02, depth=0.28,
        location=(math.cos(a)*0.62*s, math.sin(a)*0.62*s, 3.15))
    post = bpy.context.object; assign(post, dark_mat)

# Lantern room glass
bpy.ops.mesh.primitive_cylinder_add(radius=0.48*s, depth=0.7, location=(0,0,3.55))
lantern = bpy.context.object; assign(lantern, glass_mat)

# Light source (the actual beam)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.22, location=(0,0,3.55))
lightsrc = bpy.context.object; assign(lightsrc, light_mat)

# Lamp room roof (cone)
bpy.ops.mesh.primitive_cone_add(radius1=0.52*s, depth=0.55, location=(0,0,4.0))
roof = bpy.context.object; assign(roof, dark_mat)

# Lightning rod
bpy.ops.mesh.primitive_cylinder_add(radius=0.02, depth=0.4, location=(0,0,4.38))
rod = bpy.context.object; assign(rod, dark_mat)

# Door
bpy.ops.mesh.primitive_cube_add(size=1, location=(0.62*s, 0, 0.55))
door = bpy.context.object; door.scale=(0.06, 0.22, 0.35); assign(door, dark_mat)

# Windows (3 on tower)
for wz in [1.1, 1.9, 2.7]:
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.57*s, 0, wz))
    win = bpy.context.object; win.scale=(0.04, 0.12, 0.18); assign(win, glass_mat)
""" + _footer(_out())


def _windmill_script(r, g, b, scale):
    return _header() + f"""
tower_mat = make_mat("Tower", {r}, {g}, {b},  metallic=0.05, roughness=0.85)
dark_mat  = make_mat("Dark",  {r*0.55}, {g*0.55}, {b*0.55}, metallic=0.1, roughness=0.8)
blade_mat = make_mat("Blade", 0.88, 0.82, 0.70, metallic=0.0, roughness=0.7)
roof_mat  = make_mat("Roof",  0.35, 0.22, 0.10, metallic=0.1, roughness=0.75)
stone_mat = make_mat("Stone", 0.62, 0.58, 0.50, metallic=0.0, roughness=0.9)

s = {scale}

# Stone base
bpy.ops.mesh.primitive_cylinder_add(radius=0.85*s, depth=0.5, location=(0,0,0.25))
base = bpy.context.object; assign(base, stone_mat)

# Tower body (tapered)
bpy.ops.mesh.primitive_cylinder_add(radius=0.7*s, depth=3.0, location=(0,0,1.85))
tower = bpy.context.object; tower.scale=(1,1,1); assign(tower, tower_mat)

# Tower top narrowing
bpy.ops.mesh.primitive_cone_add(radius1=0.72*s, radius2=0.52*s, depth=0.6, location=(0,0,3.45))
taper = bpy.context.object; assign(taper, tower_mat)

# Conical roof
bpy.ops.mesh.primitive_cone_add(radius1=0.56*s, depth=1.2, location=(0,0,4.35))
roof = bpy.context.object; assign(roof, roof_mat)

# Axle hub
bpy.ops.mesh.primitive_cylinder_add(radius=0.14, depth=0.35,
    location=(0.72*s,0,3.35), rotation=(0,math.pi/2,0))
hub = bpy.context.object; assign(hub, dark_mat)

# Blades (4 sails)
for i in range(4):
    a = i * math.pi / 2
    # Blade arm
    bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=1.4,
        location=(0.72*s + 0.0, math.cos(a)*0.7*s, math.sin(a)*0.7*s),
        rotation=(a, math.pi/2, 0))
    arm = bpy.context.object; assign(arm, dark_mat)
    # Blade sail
    bpy.ops.mesh.primitive_cube_add(size=1,
        location=(0.72*s, math.cos(a)*0.7*s, math.sin(a)*0.7*s))
    sail = bpy.context.object
    sail.scale = (0.04, 0.35, 0.6)
    sail.rotation_euler = (a, 0, 0)
    assign(sail, blade_mat)

# Windows (4 on tower)
for wz in [0.85, 1.55, 2.25, 2.95]:
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.72*s, 0, wz))
    win = bpy.context.object; win.scale=(0.04, 0.14, 0.18); assign(win, dark_mat)

# Door
bpy.ops.mesh.primitive_cube_add(size=1, location=(0.72*s, 0, 0.38))
door = bpy.context.object; door.scale=(0.06, 0.2, 0.32); assign(door, dark_mat)

# Steps
for i in range(3):
    bpy.ops.mesh.primitive_cube_add(size=1,
        location=(0.9*s + i*0.12, 0, 0.1 - i*0.05))
    step = bpy.context.object; step.scale=(0.12, 0.28, 0.07); assign(step, stone_mat)
""" + _footer(_out())


def _snowman_script(r, g, b, scale):
    return _header() + f"""
snow_mat  = make_mat("Snow",   0.95, 0.96, 0.98, metallic=0.0, roughness=0.6)
carrot_mat= make_mat("Carrot", 0.95, 0.45, 0.05, metallic=0.0, roughness=0.7)
coal_mat  = make_mat("Coal",   0.04, 0.04, 0.05, metallic=0.1, roughness=0.8)
hat_mat   = make_mat("Hat",    0.06, 0.06, 0.08, metallic=0.1, roughness=0.7)
scarf_mat = make_mat("Scarf",  {r}, {g}, {b},  metallic=0.0, roughness=0.8)
button_mat= make_mat("Button", 0.04, 0.04, 0.06, metallic=0.2, roughness=0.6)
ground_mat= make_mat("Snow2",  0.88, 0.90, 0.94, metallic=0.0, roughness=0.7)

s = {scale}

# Ground snow
bpy.ops.mesh.primitive_cylinder_add(radius=1.6*s, depth=0.12, location=(0,0,-0.06))
ground = bpy.context.object; assign(ground, ground_mat)

# Bottom ball
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.75*s, location=(0,0,0.75))
bottom = bpy.context.object; assign(bottom, snow_mat)

# Middle ball
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.55*s, location=(0,0,1.85))
middle = bpy.context.object; assign(middle, snow_mat)

# Head ball
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.4*s, location=(0,0,2.72))
head = bpy.context.object; assign(head, snow_mat)

# Carrot nose
bpy.ops.mesh.primitive_cone_add(radius1=0.06, radius2=0.0, depth=0.42,
    location=(0.41*s, 0, 2.75), rotation=(0, math.pi/2, 0))
nose = bpy.context.object; assign(nose, carrot_mat)

# Coal eyes
for ey in [-0.18*s, 0.18*s]:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.06, location=(0.36*s, ey, 2.88))
    eye = bpy.context.object; assign(eye, coal_mat)

# Coal smile (7 pieces)
for i in range(7):
    a = math.radians(-50 + i * 16)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.05,
        location=(0.39*s, math.cos(a)*0.22*s, 2.62 + math.sin(a)*0.12*s))
    sm = bpy.context.object; assign(sm, coal_mat)

# Buttons (3 on middle)
for bz in [1.72, 1.87, 2.02]:
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.06, location=(0.55*s, 0, bz))
    btn = bpy.context.object; assign(btn, button_mat)

# Scarf
bpy.ops.mesh.primitive_torus_add(major_radius=0.57*s, minor_radius=0.08,
    location=(0,0,2.28))
scarf = bpy.context.object; assign(scarf, scarf_mat)
# Scarf tail
bpy.ops.mesh.primitive_cube_add(size=1, location=(0.45*s, 0.35*s, 2.08))
scarftail = bpy.context.object; scarftail.scale=(0.08, 0.06, 0.28); assign(scarftail, scarf_mat)

# Top hat brim
bpy.ops.mesh.primitive_cylinder_add(radius=0.52*s, depth=0.06, location=(0,0,3.15))
brim = bpy.context.object; assign(brim, hat_mat)
# Top hat body
bpy.ops.mesh.primitive_cylinder_add(radius=0.32*s, depth=0.55, location=(0,0,3.48))
hatbody = bpy.context.object; assign(hatbody, hat_mat)
# Hat band
bpy.ops.mesh.primitive_torus_add(major_radius=0.33*s, minor_radius=0.04,
    location=(0,0,3.23))
hatband = bpy.context.object; assign(hatband, scarf_mat)

# Stick arms (2)
for sx, sa in [(-0.55*s, -0.4), (0.55*s, 0.4)]:
    bpy.ops.mesh.primitive_cylinder_add(radius=0.03, depth=0.85,
        location=(sx, 0, 1.85),
        rotation=(0, sa, 0))
    arm = bpy.context.object; assign(arm, coal_mat)
""" + _footer(_out())


def _lantern_script(r, g, b, scale):
    return _header() + f"""
frame_mat = make_mat("Frame",  {r*0.5}, {g*0.5}, {b*0.5}, metallic=0.8, roughness=0.3)
glass_mat = make_mat("Glass",  0.90, 0.85, 0.60, metallic=0.0, roughness=0.02)
light_mat = make_mat("Light",  1.00, 0.90, 0.50, metallic=0.0, roughness=0.0, emission=6.0)
glow_mat  = make_mat("Glow",   {r}, {g}, {b},  metallic=0.0, roughness=0.0, emission=4.0)
chain_mat = make_mat("Chain",  0.60, 0.58, 0.55, metallic=0.7, roughness=0.4)

s = {scale}

# Base plate
bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.48*s, depth=0.08,
    location=(0,0,-0.04))
baseplate = bpy.context.object; assign(baseplate, frame_mat)

# Base feet (3)
for i in range(3):
    a = i * math.pi * 2 / 3
    bpy.ops.mesh.primitive_cylinder_add(radius=0.06, depth=0.12,
        location=(math.cos(a)*0.38*s, math.sin(a)*0.38*s, -0.1))
    foot = bpy.context.object; assign(foot, frame_mat)

# Frame body (6-sided)
bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.4*s, depth=1.2,
    location=(0,0,0.64))
body = bpy.context.object; assign(body, glass_mat)

# Glass panels highlight (thin slightly bigger cylinder)
bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.42*s, depth=1.18,
    location=(0,0,0.64))
glassout = bpy.context.object; assign(glassout, glass_mat)

# Corner frame bars (6 vertical)
for i in range(6):
    a = i * math.pi / 3
    bpy.ops.mesh.primitive_cylinder_add(radius=0.035, depth=1.28,
        location=(math.cos(a)*0.41*s, math.sin(a)*0.41*s, 0.64))
    bar = bpy.context.object; assign(bar, frame_mat)

# Top frame ring
bpy.ops.mesh.primitive_torus_add(major_radius=0.41*s, minor_radius=0.03,
    location=(0,0,1.28))
topring = bpy.context.object; assign(topring, frame_mat)

# Bottom frame ring
bpy.ops.mesh.primitive_torus_add(major_radius=0.41*s, minor_radius=0.03,
    location=(0,0,0.06))
botring = bpy.context.object; assign(botring, frame_mat)

# Mid frame ring
bpy.ops.mesh.primitive_torus_add(major_radius=0.41*s, minor_radius=0.025,
    location=(0,0,0.64))
midring = bpy.context.object; assign(midring, frame_mat)

# Roof pyramid
bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=0.44*s, depth=0.55,
    location=(0,0,1.56))
roof = bpy.context.object; assign(roof, frame_mat)

# Finial (decorative top spike)
bpy.ops.mesh.primitive_cylinder_add(radius=0.04, depth=0.3, location=(0,0,1.98))
finial = bpy.context.object; assign(finial, frame_mat)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.07, location=(0,0,2.15))
finball = bpy.context.object; assign(finball, glow_mat)

# Inner candle flame (light source)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.18, location=(0,0,0.65))
flame = bpy.context.object; flame.scale[2] = 1.5; assign(flame, light_mat)

# Candle
bpy.ops.mesh.primitive_cylinder_add(radius=0.08, depth=0.3, location=(0,0,0.35))
candle = bpy.context.object
assign(candle, make_mat("Candle", 0.95, 0.92, 0.82, roughness=0.9))

# Hanging chain (top)
bpy.ops.mesh.primitive_cylinder_add(radius=0.025, depth=0.5, location=(0,0,2.48))
chain = bpy.context.object; assign(chain, chain_mat)
bpy.ops.mesh.primitive_torus_add(major_radius=0.08, minor_radius=0.02,
    location=(0,0,2.75))
hook = bpy.context.object; hook.rotation_euler[0]=math.pi/2; assign(hook, chain_mat)

# Ambient glow sphere
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.55*s, location=(0,0,0.65))
amglow = bpy.context.object; assign(amglow, glow_mat)
""" + _footer(_out())


# ================================================================================
#  MAIN POLL LOOP
# ================================================================================

def main():
    log_separator()
    log("  AI 3D Studio - Generation Backend - IMPROVED VERSION")
    log_separator()
    log(f"  State file  : {os.path.abspath(STATE_FILE)}")
    log(f"  Output file : {os.path.abspath(OUTPUT_FILE)}")
    log(f"  Blender     : {BLENDER_PATH}")
    log(f"  Log file    : {os.path.abspath(LOG_FILE)}")
    log(f"  Poll every  : {POLL_INTERVAL}s")
    log(f"  Max attempts: {MAX_ATTEMPTS}")
    log(f"  Timeout     : {BLENDER_TIMEOUT}s per attempt")
    log(f"  Shapes      : {len(SHAPE_KEYWORDS)} shapes available")
    log(f"  Colors      : {len(COLOR_MAP)} named colors")
    log("  Press Ctrl+C to stop")
    log_separator()

    # Verify Blender exists before entering loop
    if not os.path.isfile(BLENDER_PATH) and shutil.which(BLENDER_PATH) is None:
        log(f"WARNING: Blender not found at '{BLENDER_PATH}'")
        log("WARNING: Set BLENDER_PATH environment variable to your blender.exe")
        log("WARNING: Continuing anyway - will fail on first generation attempt")

    last_prompt    = None
    last_timestamp = None
    total_jobs     = 0
    success_jobs   = 0

    while True:
        try:
            state     = read_state()
            prompt    = state.get("prompt", "").strip()
            status    = state.get("status", "")
            timestamp = state.get("timestamp", "")

            # Only process if this is a NEW pending job
            is_new      = prompt != last_prompt or timestamp != last_timestamp
            is_pending  = status == "pending"

            if prompt and is_pending and is_new:
                last_prompt    = prompt
                last_timestamp = timestamp
                total_jobs    += 1

                log(f"[MAIN] Job #{total_jobs} received: '{prompt}'")

                # Run full pipeline
                final_state = run_generation_pipeline(state)

                if final_state.get("status") == "done":
                    success_jobs += 1
                    log(f"[MAIN] Job #{total_jobs} complete. "
                        f"Success rate: {success_jobs}/{total_jobs}")
                else:
                    log(f"[MAIN] Job #{total_jobs} failed. "
                        f"Success rate: {success_jobs}/{total_jobs}")

        except KeyboardInterrupt:
            raise  # re-raise to exit cleanly
        except Exception as e:
            # Never let the poll loop crash
            log(f"[MAIN] Poll loop exception: {e}")
            log(traceback.format_exc())
            try:
                # Try to reset state so the user knows something went wrong
                state = read_state()
                write_state({**state, "status": "error", "error": str(e)})
            except Exception:
                pass

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    # Ensure logs directory exists
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    except Exception:
        pass

    try:
        main()
    except KeyboardInterrupt:
        log("\n[MAIN] Stopped by user.")
        sys.exit(0)
