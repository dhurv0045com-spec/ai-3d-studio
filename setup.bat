@echo off
setlocal EnableDelayedExpansion
cd /d "C:\Users\user\Desktop\ai-3d-project"

echo ============================================================
echo  AI 3D Studio - Setup V2
echo ============================================================
echo.

set CREATED=0
set SKIPPED=0

:: ─────────────────────────────────────────────────────────────
:: Step 1 — Create required directories
:: ─────────────────────────────────────────────────────────────
echo [Step 1] Creating required directories ...
for %%d in (
    "models"
    "models\cache"
    "models\presets"
    "logs"
    "static"
    "storage"
    "storage\users"
    "storage\users\user"
    "storage\users\user\default"
    "storage\users\user\vehicles"
    "storage\users\user\creatures"
    "storage\users\user\buildings"
    "storage\users\user\misc"
) do (
    if not exist %%d (
        mkdir %%d >nul 2>&1
        echo        CREATED: %%d
        set /a CREATED+=1
    ) else (
        echo        EXISTS : %%d
        set /a SKIPPED+=1
    )
)
echo.

:: ─────────────────────────────────────────────────────────────
:: Step 2 — Create default JSON / log files if absent
:: ─────────────────────────────────────────────────────────────
echo [Step 2] Creating default data files ...

:: history.json → []
if not exist "history.json" (
    echo []>"history.json"
    echo        CREATED: history.json
    set /a CREATED+=1
) else (
    echo        EXISTS : history.json
    set /a SKIPPED+=1
)

:: folders.json → ["default","vehicles","creatures","buildings","misc"]
if not exist "folders.json" (
    echo ["default","vehicles","creatures","buildings","misc"]>"folders.json"
    echo        CREATED: folders.json
    set /a CREATED+=1
) else (
    echo        EXISTS : folders.json
    set /a SKIPPED+=1
)

:: storage\users\user\index.json → []
if not exist "storage\users\user\index.json" (
    echo []>"storage\users\user\index.json"
    echo        CREATED: storage\users\user\index.json
    set /a CREATED+=1
) else (
    echo        EXISTS : storage\users\user\index.json
    set /a SKIPPED+=1
)

:: logs\server.log → empty
if not exist "logs\server.log" (
    type nul>"logs\server.log"
    echo        CREATED: logs\server.log
    set /a CREATED+=1
) else (
    echo        EXISTS : logs\server.log
    set /a SKIPPED+=1
)

:: logs\generation.log → empty
if not exist "logs\generation.log" (
    type nul>"logs\generation.log"
    echo        CREATED: logs\generation.log
    set /a CREATED+=1
) else (
    echo        EXISTS : logs\generation.log
    set /a SKIPPED+=1
)

:: logs\error.log → empty
if not exist "logs\error.log" (
    type nul>"logs\error.log"
    echo        CREATED: logs\error.log
    set /a CREATED+=1
) else (
    echo        EXISTS : logs\error.log
    set /a SKIPPED+=1
)

:: state.json → V2 schema
if not exist "state.json" (
    python -c "import json; json.dump({'status':'idle','prompt':'','step':'','progress':0,'service':'','model_used':'','error':'','log':[],'last_model':'','cached':False},open('state.json','w'),indent=2)" >nul 2>&1
    if errorlevel 1 (
        :: Fallback without python
        (
            echo {
            echo   "status": "idle",
            echo   "prompt": "",
            echo   "step": "",
            echo   "progress": 0,
            echo   "service": "",
            echo   "model_used": "",
            echo   "error": "",
            echo   "log": [],
            echo   "last_model": "",
            echo   "cached": false
            echo }
        )>"state.json"
    )
    echo        CREATED: state.json (V2 schema)
    set /a CREATED+=1
) else (
    echo        EXISTS : state.json
    set /a SKIPPED+=1
)
echo.

:: ─────────────────────────────────────────────────────────────
:: Step 3 — Install Python dependencies
:: ─────────────────────────────────────────────────────────────
echo [Step 3] Installing Python dependencies ...
pip install flask pystray pillow --quiet
if errorlevel 1 (
    echo        WARNING: pip install reported an error. Check output above.
) else (
    echo        DONE   : flask, pystray, pillow installed / up-to-date
)
echo.

:: ─────────────────────────────────────────────────────────────
:: Step 4 — Check Blender (non-fatal)
:: ─────────────────────────────────────────────────────────────
echo [Step 4] Checking Blender at expected path ...
if exist "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" (
    echo        FOUND  : Blender 5.0
) else (
    echo        NOT FOUND: C:\Program Files\Blender Foundation\Blender 5.0\blender.exe
    echo        (non-fatal — 3D generation will be unavailable until Blender is installed)
)
echo.

:: ─────────────────────────────────────────────────────────────
:: Step 5 — Check static\index.html (non-fatal)
:: ─────────────────────────────────────────────────────────────
echo [Step 5] Checking static\index.html ...
if exist "static\index.html" (
    echo        FOUND  : static\index.html
) else (
    echo        NOT FOUND: static\index.html
    echo        (non-fatal — front-end will not load until index.html is present)
)
echo.

:: ─────────────────────────────────────────────────────────────
:: Step 6 — Summary
:: ─────────────────────────────────────────────────────────────
echo [Step 6] Setup Summary
echo        Files / folders created : !CREATED!
echo        Already existed (skipped): !SKIPPED!
echo.
echo ============================================================
echo  Setup complete. Run tray_launcher.pyw to start.
echo ============================================================
echo.
pause
endlocal
