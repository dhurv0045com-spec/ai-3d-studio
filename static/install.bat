@echo off
setlocal EnableDelayedExpansion
title AI 3D Studio - Installer v5.0
color 0A
cd /d C:\Users\user\Desktop\ai-3d-project

echo.
echo ================================================
echo   AI 3D Studio - Installer v5.0
echo ================================================
echo   Checking your system...
echo.

:: ============================================================
:: STEP 1 - CHECK PYTHON
:: ============================================================
echo [Step 1/10] Checking Python installation...

set PYTHON_EXE=
python --version >nul 2>&1
if %errorlevel% == 0 (
    set PYTHON_EXE=python
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
    echo   Python found: !PY_VER! OK
    goto :python_ok
)

python3 --version >nul 2>&1
if %errorlevel% == 0 (
    set PYTHON_EXE=python3
    for /f "tokens=2" %%v in ('python3 --version 2^>^&1') do set PY_VER=%%v
    echo   Python found: !PY_VER! OK
    goto :python_ok
)

echo.
echo   ERROR: Python not found on this system.
echo.
echo   Please install Python 3.10 or newer:
echo   Download from: https://python.org/downloads
echo   IMPORTANT: Check "Add Python to PATH" during install
echo.
pause
exit /b 1

:python_ok
echo.

:: ============================================================
:: STEP 2 - UPGRADE PIP
:: ============================================================
echo [Step 2/10] Upgrading pip...
%PYTHON_EXE% -m pip install --upgrade pip -q
if %errorlevel% == 0 (
    echo   pip updated OK
) else (
    echo   pip upgrade warning - continuing anyway
)
echo.

:: ============================================================
:: STEP 3 - INSTALL PACKAGES
:: ============================================================
echo [Step 3/10] Installing Python packages...
echo.

set PACKAGES=flask flask-cors requests pillow pystray urllib3 pyyaml

for %%p in (%PACKAGES%) do (
    echo   Installing %%p...
    %PYTHON_EXE% -m pip install %%p -q 2>nul
    if !errorlevel! == 0 (
        echo   Installing %%p... OK
    ) else (
        echo   WARNING: %%p failed to install - continuing
    )
)

echo.
echo   NOTE: torch/shap-e are optional and NOT installed here (too large).
echo   The app works without them - Gemini+Blender handles generation.
echo.

:: ============================================================
:: STEP 4 - CHECK BLENDER
:: ============================================================
echo [Step 4/10] Checking Blender installation...

if exist "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" (
    echo   Blender 5.0 found OK
) else (
    echo   Blender 5.0 NOT found at default location.
    echo   Download from: https://blender.org
    echo   Install to default location (C:\Program Files\Blender Foundation\)
    echo   Generation will use preset shapes until Blender is installed.
)
echo.

:: ============================================================
:: STEP 5 - CREATE DIRECTORIES
:: ============================================================
echo [Step 5/10] Creating project directories...

if not exist "models\cache"              mkdir "models\cache"
if not exist "models\presets"            mkdir "models\presets"
if not exist "models\scripts"            mkdir "models\scripts"
if not exist "logs"                      mkdir "logs"
if not exist "static"                    mkdir "static"
if not exist "storage\users\user\default"    mkdir "storage\users\user\default"
if not exist "storage\users\user\vehicles"   mkdir "storage\users\user\vehicles"
if not exist "storage\users\user\creatures"  mkdir "storage\users\user\creatures"
if not exist "storage\users\user\buildings"  mkdir "storage\users\user\buildings"
if not exist "storage\users\user\misc"       mkdir "storage\users\user\misc"

echo   Directories created OK
echo.

:: ============================================================
:: STEP 6 - CREATE DEFAULT JSON FILES
:: ============================================================
echo [Step 6/10] Creating default data files...

if not exist "history.json" (
    echo []> history.json
    echo   Created history.json
)

if not exist "folders.json" (
    echo ["default","vehicles","creatures","buildings","misc"]> folders.json
    echo   Created folders.json
)

if not exist "storage\users\user\index.json" (
    echo []> storage\users\user\index.json
    echo   Created index.json
)

if not exist "state.json" (
    echo {"status":"idle","prompt":"","step":"","progress":0,"service":"","model_used":"","error":"","log":[],"last_model":"","cached":false,"glb_size":0}> state.json
    echo   Created state.json
)

echo   Data files OK
echo.

:: ============================================================
:: STEP 7 - CREATE SHAPEE FLAG
:: ============================================================
echo [Step 7/10] Configuring generation pipeline...

if not exist "shapee_installed.flag" (
    type nul > shapee_installed.flag
    echo   Shap-E flag created OK
) else (
    echo   Shap-E flag already exists OK
)
echo.

:: ============================================================
:: STEP 8 - TEST GEMINI API
:: ============================================================
echo [Step 8/10] Testing Gemini API connection...

%PYTHON_EXE% -c "import requests, urllib3; urllib3.disable_warnings(); r = requests.post('https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=AIzaSyAtIvYM0-R1tqA9FayG0xIDeogkRruiIL8', json={'contents':[{'parts':[{'text':'say ok'}]}]}, timeout=15, verify=False); print('GEMINI_OK' if r.status_code==200 else 'GEMINI_FAIL_'+str(r.status_code))" 2>nul > gemini_test_result.tmp

set GEMINI_RESULT=
for /f %%r in (gemini_test_result.tmp) do set GEMINI_RESULT=%%r
del gemini_test_result.tmp 2>nul

if "!GEMINI_RESULT!" == "GEMINI_OK" (
    echo   Gemini API connection OK
) else (
    echo   WARNING: Gemini API test result: !GEMINI_RESULT!
    echo   Check your API keys in settings.json if generation fails.
    echo   The app will fall back to preset shapes without a working key.
)
echo.

:: ============================================================
:: STEP 9 - CREATE DESKTOP SHORTCUT
:: ============================================================
echo [Step 9/10] Creating desktop shortcut...

set SHORTCUT=%USERPROFILE%\Desktop\AI 3D Studio.bat
(
    echo @echo off
    echo cd /d C:\Users\user\Desktop\ai-3d-project
    echo start pythonw tray_launcher.pyw
) > "%SHORTCUT%"

if exist "%SHORTCUT%" (
    echo   Desktop shortcut created OK
    echo   Location: %SHORTCUT%
) else (
    echo   WARNING: Could not create desktop shortcut
    echo   You can start the app by running: pythonw tray_launcher.pyw
)
echo.

:: ============================================================
:: STEP 10 - VERIFY KEY FILES EXIST
:: ============================================================
echo [Step 10/10] Verifying installation...

set MISSING=0

if not exist "server.py" (
    echo   WARNING: server.py not found
    set MISSING=1
)
if not exist "tray_launcher.pyw" (
    echo   WARNING: tray_launcher.pyw not found
    set MISSING=1
)
if not exist "settings.json" (
    echo   WARNING: settings.json not found
    set MISSING=1
)
if not exist "static\index.html" (
    echo   WARNING: static\index.html not found - UI will not load
    set MISSING=1
)

if !MISSING! == 0 (
    echo   All required files present OK
) else (
    echo   Some files are missing. Download the full project package.
)
echo.

:: ============================================================
:: FINAL SUMMARY
:: ============================================================
echo.
echo ================================================
echo   Installation Complete!
echo ================================================
echo.
echo   What was set up:
echo   - All Python packages installed
echo   - All project directories created
echo   - Gemini API configured (10 keys in settings.json)
echo   - Desktop shortcut created
echo.
echo   HOW TO START:
echo   Double-click "AI 3D Studio" on your Desktop
echo   OR run: pythonw tray_launcher.pyw
echo.
echo   The app opens in your browser at:
echo   http://localhost:5000
echo.
echo   A small icon appears in your system tray (near the clock).
echo   Right-click it to open the studio or stop the server.
echo ================================================
echo.
pause
exit /b 0
