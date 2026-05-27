from server import app, build_fallback_glb, load_folders, load_history, startup_health_check, start_key_resurrection, ROCKET_GLB
import os
import threading

def initialize():
    print("[WSGI-INIT] Setting up directories...")
    from server import setup_dirs
    setup_dirs()
    print("[WSGI-INIT] Loading folders & history...")
    load_folders()
    load_history()
    print("[WSGI-INIT] Doing startup checks...")
    startup_health_check()
    print("[WSGI-INIT] Starting Gemini key resurrection thread...")
    start_key_resurrection()

    # Create a valid placeholder GLB if no generated model exists yet.
    if not os.path.exists(ROCKET_GLB):
        with open(ROCKET_GLB, "wb") as f:
            f.write(build_fallback_glb("#888888"))

# We run initialize once when this script is loaded.
initialize()

if __name__ == "__main__":
    app.run()
