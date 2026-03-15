# tray_launcher.pyw  -  AI 3D Studio  -  VERSION 5.0
# Run with: pythonw tray_launcher.pyw  (no console window)
#
# Features:
#   - Dynamic icon: green=idle, amber=generating, red=error
#   - Status polling every 2s from /status endpoint
#   - History count polling every 30s from /history endpoint
#   - Auto-restart server once on crash, error dialog on second crash
#   - Log rotation: server.log at 5MB, generation.log at 2MB
#   - Reads host/port from settings.json
#   - All strings ASCII only, no emoji

import sys
import os
import subprocess
import threading
import webbrowser
import time
import ctypes
import socket
import json
import signal
import datetime

try:
    from PIL import Image, ImageDraw
    import pystray
    from pystray import MenuItem as Item, Menu
except ImportError as _e:
    ctypes.windll.user32.MessageBoxW(
        0,
        "Required packages missing: pystray, pillow\n\n"
        "Run install.bat to set up the application.",
        "AI 3D Studio - Missing Packages",
        0x10
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
#  PATHS
# ---------------------------------------------------------------------------
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
SETTINGS    = os.path.join(BASE_DIR, "settings.json")
SERVER_PY   = os.path.join(BASE_DIR, "server.py")
LOG_DIR     = os.path.join(BASE_DIR, "logs")
SERVER_LOG  = os.path.join(LOG_DIR, "server.log")
GEN_LOG     = os.path.join(LOG_DIR, "generation.log")
ERR_LOG     = os.path.join(LOG_DIR, "error.log")
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")

# ---------------------------------------------------------------------------
#  LOAD SETTINGS
# ---------------------------------------------------------------------------
def _load_settings():
    defaults = {"host": "127.0.0.1", "port": 5000}
    try:
        with open(SETTINGS, "r", encoding="utf-8") as f:
            s = json.load(f)
        srv = s.get("server", {})
        return {
            "host": srv.get("host", defaults["host"]),
            "port": int(srv.get("port", defaults["port"])),
        }
    except Exception:
        return defaults

_cfg        = _load_settings()
HOST        = _cfg["host"]
PORT        = _cfg["port"]
STUDIO_URL  = "http://%s:%d" % (HOST, PORT)
STATUS_URL  = STUDIO_URL + "/status"
PING_URL    = STUDIO_URL + "/ping"
HISTORY_URL = STUDIO_URL + "/history"

MAX_CRASHES   = 2
POLL_INTERVAL = 2       # seconds between status polls
HIST_INTERVAL = 30      # seconds between history count polls
STARTUP_TRIES = 40      # x 500ms = 20 seconds max wait
LOG_MAX_SERVER = 5 * 1024 * 1024   # 5 MB
LOG_MAX_GEN    = 2 * 1024 * 1024   # 2 MB

# ---------------------------------------------------------------------------
#  LOGGING (tray-side, not server-side)
# ---------------------------------------------------------------------------
def _ts():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _tray_log(msg, level="INFO"):
    os.makedirs(LOG_DIR, exist_ok=True)
    line = "[%s] %-5s TRAY: %s\n" % (_ts(), level, msg)
    try:
        with open(SERVER_LOG, "a", encoding="ascii", errors="replace") as f:
            f.write(line)
    except Exception:
        pass

def _tray_err(msg):
    _tray_log(msg, "ERROR")
    os.makedirs(LOG_DIR, exist_ok=True)
    line = "[%s] ERROR TRAY: %s\n" % (_ts(), msg)
    try:
        with open(ERR_LOG, "a", encoding="ascii", errors="replace") as f:
            f.write(line)
    except Exception:
        pass

# ---------------------------------------------------------------------------
#  LOG ROTATION
# ---------------------------------------------------------------------------
def _rotate_log(path, max_bytes):
    """Rename path -> path.1 if file exceeds max_bytes."""
    try:
        if os.path.exists(path) and os.path.getsize(path) > max_bytes:
            backup = path + ".1"
            if os.path.exists(backup):
                os.remove(backup)
            os.rename(path, backup)
            _tray_log("Rotated log: %s" % os.path.basename(path))
    except Exception as e:
        _tray_err("Log rotation failed for %s: %s" % (path, e))

def rotate_logs():
    _rotate_log(SERVER_LOG, LOG_MAX_SERVER)
    _rotate_log(GEN_LOG,    LOG_MAX_GEN)

# ---------------------------------------------------------------------------
#  DYNAMIC ICON BUILDER
# ---------------------------------------------------------------------------
# Center dot colors by app status
_DOT_COLORS = {
    "idle":       (0, 255, 170),    # green
    "generating": (245, 158, 11),   # amber
    "done":       (0, 255, 170),    # green
    "error":      (244, 63, 94),    # red
    "starting":   (245, 158, 11),   # amber
    "stopped":    (120, 120, 120),  # grey
}

def _make_icon(app_status="idle"):
    img  = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = 16, 16

    bg          = (1, 6, 16, 255)
    outer_color = (0, 212, 255)      # cyan
    inner_color = (124, 58, 237)     # purple
    dot_rgb     = _DOT_COLORS.get(app_status, _DOT_COLORS["idle"])
    dot_color   = (dot_rgb[0], dot_rgb[1], dot_rgb[2], 255)

    draw.rectangle([0, 0, 31, 31], fill=bg)
    # Outer ring (14px radius, 3px thick)
    draw.ellipse([cx-14, cy-14, cx+14, cy+14], outline=outer_color, width=3)
    # Inner ring (9px radius, 2px thick)
    draw.ellipse([cx-9,  cy-9,  cx+9,  cy+9],  outline=inner_color, width=2)
    # Center dot (4px radius)
    draw.ellipse([cx-4,  cy-4,  cx+4,  cy+4],  fill=dot_color)

    return img

# ---------------------------------------------------------------------------
#  GLOBAL STATE
# ---------------------------------------------------------------------------
_lock           = threading.Lock()
_app_status     = "stopped"      # idle / generating / done / error / stopped / starting
_progress       = 0
_last_service   = ""
_last_prompt    = ""
_model_count    = 0
_crash_count    = 0
_server_proc    = None
_tray_icon      = None
_monitor_active = False

def _set_status(status, progress=0, service="", prompt=""):
    global _app_status, _progress, _last_service, _last_prompt
    with _lock:
        _app_status   = status
        _progress     = progress
        _last_service = service
        if prompt:
            _last_prompt = prompt

def _get_status():
    with _lock:
        return _app_status, _progress, _last_service, _last_prompt, _model_count

# ---------------------------------------------------------------------------
#  ICON AND MENU REFRESH
# ---------------------------------------------------------------------------
def _refresh_icon():
    global _tray_icon
    if _tray_icon is None:
        return
    try:
        st, _, _, _, _ = _get_status()
        _tray_icon.icon = _make_icon(st)
    except Exception:
        pass

def _status_label():
    st, prog, svc, _, _ = _get_status()
    if st == "generating":
        return "Status: Generating... [%d%%]" % prog
    if st == "done":
        label = "Status: Done"
        if svc:
            label += " - " + svc
        return label
    if st == "error":
        return "Status: Error"
    if st == "starting":
        return "Status: Starting..."
    if st == "stopped":
        return "Status: Stopped"
    return "Status: Idle"

def _model_count_label():
    with _lock:
        cnt = _model_count
    return "Models: %d" % cnt

def _last_prompt_label():
    with _lock:
        p = _last_prompt
    if not p:
        return "Last: (none)"
    if len(p) > 32:
        p = p[:29] + "..."
    return "Last: " + p

# ---------------------------------------------------------------------------
#  SERVER MANAGEMENT
# ---------------------------------------------------------------------------
def _start_server():
    global _server_proc
    rotate_logs()
    os.makedirs(LOG_DIR, exist_ok=True)
    log_f = open(SERVER_LOG, "a", encoding="ascii", errors="replace")
    try:
        _server_proc = subprocess.Popen(
            [sys.executable, SERVER_PY],
            cwd=BASE_DIR,
            creationflags=0x08000000,   # CREATE_NO_WINDOW
            stdout=log_f,
            stderr=log_f
        )
        _tray_log("Server started (pid=%d)" % _server_proc.pid)
        return True
    except Exception as e:
        _tray_err("Failed to start server: %s" % e)
        return False

def _stop_server():
    global _server_proc
    if _server_proc is None:
        return
    try:
        _server_proc.terminate()
        _server_proc.wait(timeout=5)
    except Exception:
        try:
            _server_proc.kill()
        except Exception:
            pass
    _tray_log("Server stopped")
    _server_proc = None

def _wait_for_server():
    """Poll /ping up to STARTUP_TRIES times (500ms each). Return True if responds."""
    for i in range(STARTUP_TRIES):
        time.sleep(0.5)
        try:
            import urllib.request
            with urllib.request.urlopen(PING_URL, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
    return False

# ---------------------------------------------------------------------------
#  STATUS POLLING THREAD
# ---------------------------------------------------------------------------
def _poll_status():
    """Background thread: poll /status every 2s, /history every 30s."""
    global _model_count
    last_hist_poll = 0.0

    while _monitor_active:
        # Poll status
        try:
            import urllib.request
            with urllib.request.urlopen(STATUS_URL, timeout=2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            _set_status(
                status  = data.get("status", "idle"),
                progress= int(data.get("progress", 0)),
                service = data.get("service", ""),
                prompt  = data.get("prompt", "")
            )
            _refresh_icon()
        except Exception:
            pass

        # Poll history count every 30s
        now = time.time()
        if now - last_hist_poll >= HIST_INTERVAL:
            last_hist_poll = now
            try:
                import urllib.request
                with urllib.request.urlopen(HISTORY_URL, timeout=3) as resp:
                    hist = json.loads(resp.read().decode("utf-8"))
                with _lock:
                    _model_count = len(hist)
            except Exception:
                # Fall back to reading history.json directly
                try:
                    with open(HISTORY_FILE, "r") as f:
                        hist = json.load(f)
                    with _lock:
                        _model_count = len(hist)
                except Exception:
                    pass

        time.sleep(POLL_INTERVAL)

# ---------------------------------------------------------------------------
#  CRASH MONITOR THREAD
# ---------------------------------------------------------------------------
def _monitor_crashes():
    """Watch server subprocess. Restart once on crash. Fatal dialog on second."""
    global _crash_count, _server_proc, _monitor_active, _tray_icon
    while _monitor_active:
        time.sleep(3)
        if not _monitor_active:
            break
        if _server_proc is None:
            continue
        if _server_proc.poll() is not None:
            _crash_count += 1
            _tray_err("Server crashed (count=%d)" % _crash_count)
            _set_status("error")
            _refresh_icon()

            if _crash_count < MAX_CRASHES:
                _tray_log("Restarting server (attempt %d)" % _crash_count)
                time.sleep(2)
                _start_server()
                _set_status("starting")
                _refresh_icon()
                if _wait_for_server():
                    _set_status("idle")
                    _refresh_icon()
                    webbrowser.open(STUDIO_URL)
            else:
                _monitor_active = False
                _tray_err("Server crashed %d times - giving up" % MAX_CRASHES)
                ctypes.windll.user32.MessageBoxW(
                    0,
                    "AI 3D Studio crashed %d times.\n\n"
                    "Check logs\\error.log for details.\n\n"
                    "Common causes:\n"
                    "  - Missing Python packages (run install.bat)\n"
                    "  - Port 5000 blocked by another app\n"
                    "  - server.py has a syntax error" % MAX_CRASHES,
                    "AI 3D Studio - Fatal Error",
                    0x10
                )
                if _tray_icon:
                    _tray_icon.stop()
                sys.exit(1)

# ---------------------------------------------------------------------------
#  TRAY ACTIONS
# ---------------------------------------------------------------------------
def _action_open(icon=None, item=None):
    webbrowser.open(STUDIO_URL)
    _tray_log("Browser opened by user")

def _action_restart(icon=None, item=None):
    global _crash_count
    _tray_log("Manual restart requested")
    _set_status("starting")
    _refresh_icon()
    _stop_server()
    _crash_count = 0
    time.sleep(1)
    _start_server()
    if _wait_for_server():
        _set_status("idle")
        _refresh_icon()
        webbrowser.open(STUDIO_URL)
    else:
        _set_status("error")
        _refresh_icon()

def _action_restart_thread(icon=None, item=None):
    t = threading.Thread(target=_action_restart, daemon=True)
    t.start()

def _open_file(path, label):
    os.makedirs(LOG_DIR, exist_ok=True)
    if not os.path.exists(path):
        try:
            open(path, "w").close()
        except Exception:
            pass
    try:
        os.startfile(path)
        _tray_log("%s opened" % label)
    except Exception as e:
        _tray_err("Could not open %s: %s" % (label, e))

def _action_server_log(icon=None, item=None):
    _open_file(SERVER_LOG, "Server Log")

def _action_gen_log(icon=None, item=None):
    _open_file(GEN_LOG, "Generation Log")

def _action_err_log(icon=None, item=None):
    _open_file(ERR_LOG, "Error Log")

def _action_diagnostics(icon=None, item=None):
    diag = os.path.join(BASE_DIR, "test_apis.py")
    if os.path.exists(diag):
        try:
            subprocess.Popen(
                [sys.executable, diag],
                cwd=BASE_DIR,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            _tray_log("Diagnostics launched")
        except Exception as e:
            _tray_err("Could not launch diagnostics: %s" % e)
    else:
        ctypes.windll.user32.MessageBoxW(
            0,
            "test_apis.py not found in project directory.",
            "AI 3D Studio - Diagnostics",
            0x40
        )

def _action_quit(icon=None, item=None):
    global _monitor_active
    _tray_log("User quit")
    _monitor_active = False
    _stop_server()
    if _tray_icon:
        _tray_icon.stop()
    sys.exit(0)

# ---------------------------------------------------------------------------
#  SIGNAL HANDLERS
# ---------------------------------------------------------------------------
def _handle_signal(sig, frame):
    _tray_log("Signal %d received - shutting down" % sig)
    _action_quit()

signal.signal(signal.SIGTERM, _handle_signal)
try:
    signal.signal(signal.SIGBREAK, _handle_signal)
except AttributeError:
    pass

# ---------------------------------------------------------------------------
#  TRAY MENU BUILDER
# ---------------------------------------------------------------------------
def _build_menu():
    return Menu(
        Item("AI 3D Studio v5.0",  None, enabled=False),
        Menu.SEPARATOR,
        Item(lambda item: _status_label(),       None, enabled=False),
        Item(lambda item: _model_count_label(),  None, enabled=False),
        Item(lambda item: _last_prompt_label(),  None, enabled=False),
        Menu.SEPARATOR,
        Item("Open Studio",         _action_open),
        Item("New Generation",      _action_open),
        Menu.SEPARATOR,
        Item("Restart Server",      _action_restart_thread),
        Menu.SEPARATOR,
        Item("View Server Log",     _action_server_log),
        Item("View Generation Log", _action_gen_log),
        Item("View Error Log",      _action_err_log),
        Menu.SEPARATOR,
        Item("Run Diagnostics",     _action_diagnostics),
        Menu.SEPARATOR,
        Item("Quit",                _action_quit),
    )

# ---------------------------------------------------------------------------
#  MAIN
# ---------------------------------------------------------------------------
def main():
    global _tray_icon, _monitor_active

    os.makedirs(LOG_DIR, exist_ok=True)
    _tray_log("=== tray_launcher v5.0 starting ===")

    # Check port conflict
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        result = s.connect_ex((HOST, PORT))
        s.close()
        if result == 0:
            _tray_err("Port %d already in use" % PORT)
            ctypes.windll.user32.MessageBoxW(
                0,
                "Port %d is already in use.\n\n"
                "Another instance of AI 3D Studio may already be running.\n"
                "Check your system tray or Task Manager." % PORT,
                "AI 3D Studio - Port Conflict",
                0x30
            )
            sys.exit(1)
    except Exception:
        pass

    # Create icon with starting state
    _set_status("starting")
    _tray_icon = pystray.Icon(
        name  = "AI3DStudio",
        icon  = _make_icon("starting"),
        title = "AI 3D Studio - Starting...",
        menu  = _build_menu()
    )

    # Start server
    _tray_log("Starting server.py...")
    if not _start_server():
        ctypes.windll.user32.MessageBoxW(
            0,
            "Could not start server.py.\n\n"
            "Make sure Python is installed and server.py exists in:\n"
            + BASE_DIR,
            "AI 3D Studio - Startup Error",
            0x10
        )
        sys.exit(1)

    # Wait for server to respond
    def _startup_sequence():
        global _monitor_active
        _tray_log("Waiting for server to respond...")
        alive = _wait_for_server()
        if alive:
            _tray_log("Server responding at " + STUDIO_URL)
            _set_status("idle")
            _tray_icon.icon  = _make_icon("idle")
            _tray_icon.title = "AI 3D Studio - Running"
            webbrowser.open(STUDIO_URL)
        else:
            _tray_err("Server did not respond after %d attempts" % STARTUP_TRIES)
            _set_status("error")
            _tray_icon.icon  = _make_icon("error")
            _tray_icon.title = "AI 3D Studio - Error"
            ctypes.windll.user32.MessageBoxW(
                0,
                "Server failed to start within 20 seconds.\n\n"
                "Check logs\\error.log for details.",
                "AI 3D Studio - Startup Timeout",
                0x10
            )
            return

        # Start background threads
        _monitor_active = True

        t_poll = threading.Thread(target=_poll_status, daemon=True)
        t_poll.start()

        t_crash = threading.Thread(target=_monitor_crashes, daemon=True)
        t_crash.start()

    startup_t = threading.Thread(target=_startup_sequence, daemon=True)
    startup_t.start()

    # Run tray (blocks until stopped)
    _tray_icon.run()


if __name__ == "__main__":
    main()
