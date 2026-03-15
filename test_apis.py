# test_apis.py  -  AI 3D Studio  -  System Diagnostics v5.0
#
# Usage:
#   python test_apis.py
#   python test_apis.py --quiet      (summary only)
#   python test_apis.py --no-server  (skip server start test)
#
# Exit codes:
#   0 = all tests pass
#   1 = one or more failures

import os
import sys
import json
import time
import socket
import platform
import subprocess
import datetime
import traceback
import argparse
import threading

# ---------------------------------------------------------------------------
#  PATHS
# ---------------------------------------------------------------------------
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
SETTINGS     = os.path.join(BASE_DIR, "settings.json")
LOG_DIR      = os.path.join(BASE_DIR, "logs")
LOG_FILE     = os.path.join(LOG_DIR, "test_apis.log")
SERVER_PY    = os.path.join(BASE_DIR, "server.py")
INDEX_HTML   = os.path.join(BASE_DIR, "static", "index.html")
TRAY_PY      = os.path.join(BASE_DIR, "tray_launcher.pyw")
HISTORY_JSON = os.path.join(BASE_DIR, "history.json")
FOLDERS_JSON = os.path.join(BASE_DIR, "folders.json")
SHAPEE_FLAG  = os.path.join(BASE_DIR, "shapee_installed.flag")
BLENDER_EXE  = r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"

REQUIRED_DIRS = [
    "models",
    "models/cache",
    "models/presets",
    "models/scripts",
    "logs",
    "static",
    "storage",
    "storage/users",
    "storage/users/user",
    "storage/users/user/default",
    "storage/users/user/vehicles",
    "storage/users/user/creatures",
    "storage/users/user/buildings",
]

GEMINI_KEYS = [
    ("default",   "AIzaSyAtIvYM0-R1tqA9FayG0xIDeogkRruiIL8"),
    ("django",    "AIzaSyCAb4OBP1YrJtJ-jz7iiUJA9rx95LsUqns"),
    ("waltz",     "AIzaSyCw0ADc4GOpyegypb4Rr9Mc1s061tjNxeo"),
    ("panther",   "AIzaSyBOwoj4wV0tyHaJAWbNlBzNcEXfcnGRhil"),
    ("B2",        "AIzaSyB96tpp2Vmzkwwlt3oVdJtfpZa8uLvqGll"),
    ("blackbird", "AIzaSyDl3j8nne99ClsSQUJ13QMCSgD4G4AVDyY"),
    ("daru",      "AIzaSyC3mUx6kyGdSR-Gb7g7whUtcYnyBQtdGF8"),
    ("vikrant",   "AIzaSyB5dli5AOpsnpMwamY78iAOUPahxdm1pO0"),
    ("kang",      "AIzaSyCAupuJnceO7f5v7BtZ4HWeEyTKp7MWrWA"),
    ("decagon",   "AIzaSyBjCVzVcKWZZLFHGizeSnYSM98fHgLy1ug"),
]

SERVER_PORT = 5000
SERVER_HOST = "127.0.0.1"

# ---------------------------------------------------------------------------
#  ARGUMENT PARSING
# ---------------------------------------------------------------------------
_parser = argparse.ArgumentParser(description="AI 3D Studio Diagnostics v5.0")
_parser.add_argument("--quiet",     action="store_true", help="Show summary only")
_parser.add_argument("--no-server", action="store_true", help="Skip server launch test")
ARGS = _parser.parse_args()

# ---------------------------------------------------------------------------
#  LOGGING
# ---------------------------------------------------------------------------
_log_buf  = []
_quiet    = ARGS.quiet

def _ts():
    return datetime.datetime.now().strftime("%H:%M:%S")

def _log(msg, force=False):
    line = "[%s] %s" % (_ts(), msg)
    _log_buf.append(line)
    if not _quiet or force:
        print(line)

def _log_raw(msg, force=False):
    _log_buf.append(msg)
    if not _quiet or force:
        print(msg)

def _flush_log():
    os.makedirs(LOG_DIR, exist_ok=True)
    try:
        header = "=" * 60 + "\n"
        header += "  AI 3D Studio Diagnostics - %s\n" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header += "=" * 60 + "\n"
        with open(LOG_FILE, "w", encoding="ascii", errors="replace") as f:
            f.write(header)
            for line in _log_buf:
                f.write(line + "\n")
        print("\n  Full report saved to: %s" % LOG_FILE)
    except Exception as e:
        print("  WARNING: Could not save log: %s" % e)

# ---------------------------------------------------------------------------
#  RESULT TRACKING
# ---------------------------------------------------------------------------
_section_results = {}   # section_name -> "PASS" / "WARN" / "FAIL"
_has_critical    = False
_has_warnings    = False

def _record(section, status):
    global _has_critical, _has_warnings
    _section_results[section] = status
    if status == "FAIL":
        _has_critical = True
    elif status == "WARN":
        _has_warnings = True

def _pf(ok, warn=False):
    if ok:
        return "PASS"
    return "WARN" if warn else "FAIL"

# ---------------------------------------------------------------------------
#  SECTION 1 - ENVIRONMENT
# ---------------------------------------------------------------------------
def check_environment():
    _log_raw("")
    _log_raw("=" * 60)
    _log_raw("  SECTION 1 - ENVIRONMENT")
    _log_raw("=" * 60)

    passed = True

    # Python version
    ver = sys.version.split()[0]
    parts = ver.split(".")
    try:
        major, minor = int(parts[0]), int(parts[1])
        ok = (major == 3 and minor >= 10)
    except Exception:
        ok = False
    _log("  Python version     : %s  [%s]" % (ver, _pf(ok, warn=True)))
    if not ok:
        _log("    WARNING: Python 3.10+ recommended")
        passed = False

    # OS
    _log("  OS                 : %s %s  [INFO]" % (platform.system(), platform.release()))
    _log("  Architecture       : %s  [INFO]" % platform.machine())

    # Disk space
    try:
        import shutil as _sh
        total, used, free = _sh.disk_usage(BASE_DIR)
        free_gb = free / (1024 ** 3)
        ok = free_gb >= 1.0
        _log("  Disk free          : %.1f GB  [%s]" % (free_gb, _pf(ok, warn=True)))
        if not ok:
            _log("    WARNING: Less than 1GB free - may cause issues")
    except Exception:
        _log("  Disk free          : unknown  [SKIP]")

    # RAM (psutil optional)
    try:
        import psutil
        ram_gb = psutil.virtual_memory().available / (1024 ** 3)
        ok = ram_gb >= 2.0
        _log("  RAM available      : %.1f GB  [%s]" % (ram_gb, _pf(ok, warn=True)))
    except ImportError:
        _log("  RAM available      : psutil not installed  [SKIP]")

    # Project directory
    ok = os.path.isdir(BASE_DIR)
    _log("  Project dir        : %s  [%s]" % (BASE_DIR, _pf(ok)))
    if not ok:
        passed = False

    # Required directories
    _log("")
    _log("  Required directories:")
    all_dirs_ok = True
    for d in REQUIRED_DIRS:
        full = os.path.join(BASE_DIR, d.replace("/", os.sep))
        ok = os.path.isdir(full)
        _log("    %-38s [%s]" % (d, _pf(ok, warn=True)))
        if not ok:
            all_dirs_ok = False
    if not all_dirs_ok:
        _log("    Run install.bat to create missing directories")

    # Required JSON files
    _log("")
    _log("  Required JSON files:")
    for fname, req in [("history.json", True), ("folders.json", True),
                       ("settings.json", True), ("state.json", False)]:
        fpath = os.path.join(BASE_DIR, fname)
        exists = os.path.exists(fpath)
        valid  = False
        if exists:
            try:
                with open(fpath, "r") as f:
                    json.load(f)
                valid = True
            except Exception:
                pass
        status = "PASS" if (exists and valid) else ("WARN" if not req else "FAIL")
        _log("    %-20s exists=%-5s valid=%-5s  [%s]" % (
            fname, exists, valid, status))

    _record("Environment", "PASS" if passed else "WARN")

# ---------------------------------------------------------------------------
#  SECTION 2 - DEPENDENCIES
# ---------------------------------------------------------------------------
def check_dependencies():
    _log_raw("")
    _log_raw("=" * 60)
    _log_raw("  SECTION 2 - DEPENDENCIES")
    _log_raw("=" * 60)

    deps = [
        ("requests",    "requests",    True,  "pip install requests"),
        ("flask",       "flask",       True,  "pip install flask"),
        ("flask_cors",  "flask_cors",  True,  "pip install flask-cors"),
        ("PIL",         "PIL",         True,  "pip install pillow"),
        ("pystray",     "pystray",     True,  "pip install pystray"),
        ("urllib3",     "urllib3",     True,  "pip install urllib3"),
        ("yaml",        "yaml",        False, "pip install pyyaml"),
        ("ipywidgets",  "ipywidgets",  False, "pip install ipywidgets"),
        ("torch",       "torch",       False, "pip install torch (optional - for Shap-E)"),
        ("shap_e",      "shap_e",      False, "pip install git+https://github.com/openai/shap-e"),
    ]

    all_required_ok = True
    for name, module, required, install_cmd in deps:
        try:
            m = __import__(module)
            ver = getattr(m, "__version__", "installed")
            tag = "REQUIRED" if required else "OPTIONAL"
            _log("  %-12s %-12s  [PASS] %s" % (name, ver[:12], tag))
        except ImportError:
            tag = "REQUIRED" if required else "OPTIONAL"
            status = "FAIL" if required else "SKIP"
            _log("  %-12s %-12s  [%s] %s" % (name, "not found", status, tag))
            if required:
                all_required_ok = False
                _log("    Install with: %s" % install_cmd)

    _record("Dependencies", "PASS" if all_required_ok else "FAIL")

# ---------------------------------------------------------------------------
#  SECTION 3 - BLENDER
# ---------------------------------------------------------------------------
def check_blender():
    _log_raw("")
    _log_raw("=" * 60)
    _log_raw("  SECTION 3 - BLENDER")
    _log_raw("=" * 60)

    # Check configured path
    paths_to_check = [
        BLENDER_EXE,
        r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
    ]

    found_path = None
    for p in paths_to_check:
        if os.path.isfile(p):
            found_path = p
            break

    if not found_path:
        _log("  Blender            : NOT FOUND  [FAIL]")
        _log("  Expected path      : %s" % BLENDER_EXE)
        _log("  Download from      : https://blender.org")
        _log("  NOTE: Generation falls back to preset shapes without Blender")
        _record("Blender", "WARN")
        return

    _log("  Blender path       : %s  [PASS]" % found_path)

    # Get version
    try:
        result = subprocess.run(
            [found_path, "--version"],
            capture_output=True,
            timeout=10
        )
        output = result.stdout.decode("ascii", errors="replace").strip()
        first_line = output.split("\n")[0] if output else "unknown"
        _log("  Blender version    : %s  [INFO]" % first_line.strip())
        _record("Blender", "PASS")
    except subprocess.TimeoutExpired:
        _log("  Blender version    : timeout reading version  [WARN]")
        _record("Blender", "WARN")
    except Exception as e:
        _log("  Blender version    : error: %s  [WARN]" % e)
        _record("Blender", "WARN")

# ---------------------------------------------------------------------------
#  SECTION 4 - GEMINI API KEYS
# ---------------------------------------------------------------------------
def _test_gemini_key(name, key):
    """Test a single Gemini key. Returns (ok, latency_ms, detail)."""
    try:
        import requests
        import urllib3
        urllib3.disable_warnings()
    except ImportError:
        return False, 0, "requests not installed"

    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           "gemini-2.0-flash:generateContent?key=" + key)
    payload = {
        "contents": [{"parts": [{"text": "respond with the single word: OK"}]}],
        "generationConfig": {"maxOutputTokens": 10, "temperature": 0.0}
    }

    t0 = time.perf_counter()
    try:
        resp = requests.post(url, json=payload, timeout=15, verify=False)
        latency_ms = (time.perf_counter() - t0) * 1000

        if resp.status_code == 200:
            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            tag  = "SLOW" if latency_ms > 3000 else "PASS"
            return True, latency_ms, "%s | %dms" % (tag, int(latency_ms))
        elif resp.status_code == 429:
            return False, latency_ms, "QUOTA EXCEEDED (429)"
        elif resp.status_code == 403:
            return False, latency_ms, "FORBIDDEN (403) - key invalid or quota reset"
        else:
            return False, latency_ms, "HTTP %d" % resp.status_code
    except Exception as e:
        latency_ms = (time.perf_counter() - t0) * 1000
        return False, latency_ms, "ERROR: %s" % str(e)[:60]

def check_gemini_keys():
    _log_raw("")
    _log_raw("=" * 60)
    _log_raw("  SECTION 4 - GEMINI API KEYS (all 10)")
    _log_raw("=" * 60)
    _log_raw("")
    _log_raw("  %-10s %-14s %-10s %s" % ("Name", "Key Prefix", "Status", "Detail"))
    _log_raw("  " + "-" * 56)

    working    = 0
    failed     = 0
    latencies  = []
    fastest    = None
    fastest_ms = 999999.0

    for name, key in GEMINI_KEYS:
        prefix = key[:16] + "..."
        ok, ms, detail = _test_gemini_key(name, key)
        if ok:
            working += 1
            latencies.append(ms)
            if ms < fastest_ms:
                fastest_ms = ms
                fastest = name
            status = "PASS"
        else:
            failed += 1
            status = "FAIL"
        _log_raw("  %-10s %-14s %-10s %s" % (name, prefix, status, detail))

    _log_raw("")
    _log_raw("  Total keys    : %d" % len(GEMINI_KEYS))
    _log_raw("  Working keys  : %d" % working)
    _log_raw("  Failed keys   : %d" % failed)
    if latencies:
        avg = sum(latencies) / len(latencies)
        _log_raw("  Avg latency   : %dms" % int(avg))
        if fastest:
            _log_raw("  Fastest key   : %s (%dms)" % (fastest, int(fastest_ms)))
            _log_raw("  Recommended   : %s" % fastest)

    if working == 0:
        _log_raw("")
        _log_raw("  CRITICAL: No Gemini keys are working.")
        _log_raw("  Get free keys at: https://aistudio.google.com/app/apikey")
        _log_raw("  Without working keys all generation falls back to preset shapes.")
        _record("Gemini API", "FAIL")
    elif failed > 0:
        _record("Gemini API", "WARN")
    else:
        _record("Gemini API", "PASS")

    return working

# ---------------------------------------------------------------------------
#  SECTION 5 - SERVER TEST
# ---------------------------------------------------------------------------
def check_server():
    _log_raw("")
    _log_raw("=" * 60)
    _log_raw("  SECTION 5 - SERVER ENDPOINT TEST")
    _log_raw("=" * 60)

    if ARGS.no_server:
        _log("  Skipped (--no-server flag)")
        _record("Server", "SKIP")
        return

    import urllib.request

    # Check if already running
    already_running = False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        r = s.connect_ex((SERVER_HOST, SERVER_PORT))
        s.close()
        already_running = (r == 0)
    except Exception:
        pass

    proc = None
    if not already_running:
        _log("  Starting server for test...")
        try:
            proc = subprocess.Popen(
                [sys.executable, SERVER_PY],
                cwd=BASE_DIR,
                creationflags=0x08000000,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            # Wait up to 10s for it to respond
            started = False
            for _ in range(20):
                time.sleep(0.5)
                try:
                    urllib.request.urlopen("http://%s:%d/ping" % (SERVER_HOST, SERVER_PORT), timeout=1)
                    started = True
                    break
                except Exception:
                    pass
            if not started:
                _log("  Server did not start within 10s  [FAIL]")
                if proc:
                    proc.terminate()
                _record("Server", "FAIL")
                return
        except Exception as e:
            _log("  Could not launch server: %s  [FAIL]" % e)
            _record("Server", "FAIL")
            return

    # Test endpoints
    endpoints = [
        ("/ping",    "Health check"),
        ("/status",  "Generation status"),
        ("/folders", "Folder list"),
        ("/history", "History list"),
    ]

    all_ok = True
    for path, label in endpoints:
        url = "http://%s:%d%s" % (SERVER_HOST, SERVER_PORT, path)
        try:
            t0 = time.perf_counter()
            with urllib.request.urlopen(url, timeout=5) as resp:
                ms = (time.perf_counter() - t0) * 1000
                data = json.loads(resp.read().decode("utf-8"))
                _log("  %-10s %-24s [PASS] %dms" % (path, label, int(ms)))
        except Exception as e:
            _log("  %-10s %-24s [FAIL] %s" % (path, label, str(e)[:50]))
            all_ok = False

    if proc:
        try:
            proc.terminate()
            proc.wait(timeout=3)
            _log("  Test server stopped")
        except Exception:
            pass

    _record("Server", "PASS" if all_ok else "FAIL")

# ---------------------------------------------------------------------------
#  SECTION 6 - GENERATION PIPELINE
# ---------------------------------------------------------------------------
def check_pipeline():
    _log_raw("")
    _log_raw("=" * 60)
    _log_raw("  SECTION 6 - GENERATION PIPELINE")
    _log_raw("=" * 60)

    issues = 0

    # Shap-E flag
    flag_ok = os.path.exists(SHAPEE_FLAG)
    _log("  shapee_installed.flag : %s  [%s]" % (flag_ok, _pf(flag_ok, warn=True)))
    if not flag_ok:
        _log("    Create with: type nul > shapee_installed.flag")
        issues += 1

    # Shap-E packages
    shapee_pkgs = []
    for pkg in ("yaml", "torch", "ipywidgets"):
        try:
            __import__(pkg)
            shapee_pkgs.append(pkg)
        except ImportError:
            pass
    _log("  Shap-E packages       : %s installed  [INFO]" % "/".join(shapee_pkgs) if shapee_pkgs else "  Shap-E packages       : none  [INFO]")

    # Preset directory
    presets_dir = os.path.join(BASE_DIR, "models", "presets")
    if os.path.isdir(presets_dir):
        glb_count = len([f for f in os.listdir(presets_dir) if f.endswith(".glb")])
        _log("  Preset GLBs cached    : %d  [INFO]" % glb_count)
    else:
        _log("  Preset GLBs cached    : directory missing  [WARN]")
        issues += 1

    # Scripts library
    scripts_dir = os.path.join(BASE_DIR, "models", "scripts")
    if os.path.isdir(scripts_dir):
        script_count = len([f for f in os.listdir(scripts_dir) if f.endswith(".py")])
        _log("  Script library        : %d scripts  [INFO]" % script_count)
    else:
        _log("  Script library        : directory missing  [WARN]")

    # Cache size
    cache_dir = os.path.join(BASE_DIR, "models", "cache")
    if os.path.isdir(cache_dir):
        cache_files = [f for f in os.listdir(cache_dir) if f.endswith(".glb")]
        cache_mb = sum(
            os.path.getsize(os.path.join(cache_dir, f))
            for f in cache_files
        ) / (1024 * 1024)
        _log("  Cache                 : %d entries, %.1f MB  [INFO]" % (len(cache_files), cache_mb))
    else:
        _log("  Cache                 : directory missing  [WARN]")

    _record("Pipeline", "PASS" if issues == 0 else "WARN")

# ---------------------------------------------------------------------------
#  SECTION 7 - FILE INTEGRITY
# ---------------------------------------------------------------------------
def check_files():
    _log_raw("")
    _log_raw("=" * 60)
    _log_raw("  SECTION 7 - FILE INTEGRITY")
    _log_raw("=" * 60)

    files = [
        (SERVER_PY,        "server.py",            True,  50 * 1024),
        (INDEX_HTML,       "static/index.html",    True,  50 * 1024),
        (TRAY_PY,          "tray_launcher.pyw",    True,  0),
        (SETTINGS,         "settings.json",        True,  0),
        (HISTORY_JSON,     "history.json",         True,  0),
        (FOLDERS_JSON,     "folders.json",         True,  0),
        (SHAPEE_FLAG,      "shapee_installed.flag",False, 0),
    ]

    all_ok = True
    for path, label, required, min_size in files:
        exists = os.path.exists(path)
        if not exists:
            status = "FAIL" if required else "WARN"
            _log("  %-30s  MISSING  [%s]" % (label, status))
            if required:
                all_ok = False
            continue

        size = os.path.getsize(path)
        size_ok = (size >= min_size) if min_size > 0 else True

        # JSON validation for json files
        if path.endswith(".json"):
            try:
                with open(path, "r") as f:
                    json.load(f)
                json_ok = True
            except Exception:
                json_ok = False
        else:
            json_ok = True

        ok = size_ok and json_ok
        _log("  %-30s  %7d bytes  [%s]" % (label, size, _pf(ok, warn=not required)))
        if not ok and required:
            all_ok = False
            if not size_ok:
                _log("    WARNING: File is smaller than expected (%d < %d)" % (size, min_size))
            if not json_ok:
                _log("    WARNING: File is not valid JSON")

    _record("Files", "PASS" if all_ok else "FAIL")

# ---------------------------------------------------------------------------
#  FINAL SUMMARY
# ---------------------------------------------------------------------------
def print_summary():
    _log_raw("")
    _log_raw("=" * 60)
    _log_raw("  DIAGNOSTIC SUMMARY")
    _log_raw("=" * 60)

    order = ["Environment", "Dependencies", "Blender", "Gemini API",
             "Server", "Pipeline", "Files"]

    for section in order:
        status = _section_results.get(section, "SKIP")
        pad = " " * max(0, 18 - len(section))
        _log_raw("  %s%s: %s" % (section, pad, status))

    _log_raw("")
    if _has_critical:
        _log_raw("  Overall Status: CRITICAL - fix the FAIL items above before using the app")
        _log_raw("")
        _log_raw("  Steps to fix:")
        if _section_results.get("Dependencies") == "FAIL":
            _log_raw("    1. Run install.bat to install missing Python packages")
        if _section_results.get("Blender") in ("FAIL", "WARN"):
            _log_raw("    2. Install Blender 5.0 from https://blender.org")
        if _section_results.get("Gemini API") == "FAIL":
            _log_raw("    3. Get free Gemini keys at https://aistudio.google.com/app/apikey")
            _log_raw("       Add them to settings.json under ai.gemini_keys")
        if _section_results.get("Files") == "FAIL":
            _log_raw("    4. Download the full project package - key files are missing")
        if _section_results.get("Server") == "FAIL":
            _log_raw("    5. Check logs/error.log for server startup errors")
    elif _has_warnings:
        _log_raw("  Overall Status: WARNINGS - app will work with degraded features")
        if _section_results.get("Blender") == "WARN":
            _log_raw("    - Blender not found: generation uses preset shapes only")
        if _section_results.get("Gemini API") == "WARN":
            _log_raw("    - Some Gemini keys failing: fewer retries available")
        if _section_results.get("Pipeline") == "WARN":
            _log_raw("    - Run install.bat to create missing directories")
    else:
        _log_raw("  Overall Status: ALL GOOD - system is ready to use")

    _log_raw("=" * 60)

# ---------------------------------------------------------------------------
#  MAIN
# ---------------------------------------------------------------------------
def main():
    _log_raw("=" * 60)
    _log_raw("  AI 3D Studio - System Diagnostics v5.0")
    _log_raw("  %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    _log_raw("  Project: %s" % BASE_DIR)
    _log_raw("=" * 60)

    check_environment()
    check_dependencies()
    check_blender()
    working_keys = check_gemini_keys()
    check_server()
    check_pipeline()
    check_files()
    print_summary()
    _flush_log()

    return 1 if _has_critical else 0


if __name__ == "__main__":
    try:
        code = main()
        sys.exit(code)
    except KeyboardInterrupt:
        _log_raw("\n  Diagnostics interrupted.")
        _flush_log()
        sys.exit(0)
    except Exception as e:
        _log_raw("\n  FATAL: Diagnostics tool crashed: %s" % e)
        _log_raw(traceback.format_exc())
        _flush_log()
        sys.exit(2)
