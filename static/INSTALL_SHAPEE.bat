@echo off
:: ============================================================
:: install_shapee.bat
:: AI 3D Studio — Shap-E AI Engine Installer
:: Run this ONCE to install the 3D generation engine.
:: Double-click from File Explorer. No tech knowledge needed.
:: ============================================================

title AI 3D Studio — Installing Shap-E AI Engine
color 0B

echo.
echo  =====================================================
echo   AI 3D Studio — Shap-E AI Engine Installer
echo  =====================================================
echo.
echo  This will install the AI engine that generates 3D models.
echo  It may take 5-15 minutes depending on your internet speed.
echo  Please do NOT close this window during installation.
echo.
echo  Press any key to begin...
pause > nul

:: ────────────────────────────────────────────────────────────
:: STEP 1 OF 6 — Check Python is available
:: ────────────────────────────────────────────────────────────
echo.
echo  [Step 1 of 6] Checking Python is installed...
echo  -----------------------------------------------

python --version > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ERROR: Python was not found on this computer.
    echo.
    echo  Please install Python 3.13 from https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  OK — Found %PYVER%

:: ────────────────────────────────────────────────────────────
:: STEP 2 OF 6 — Check pip is available
:: ────────────────────────────────────────────────────────────
echo.
echo  [Step 2 of 6] Checking pip (package installer)...
echo  ---------------------------------------------------

pip --version > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ERROR: pip was not found. Trying to install it...
    python -m ensurepip --upgrade
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo  ERROR: Could not install pip automatically.
        echo  Please reinstall Python and check "pip" during setup.
        echo.
        pause
        exit /b 1
    )
)

for /f "tokens=*" %%v in ('pip --version 2^>^&1') do set PIPVER=%%v
echo  OK — Found %PIPVER%

:: ────────────────────────────────────────────────────────────
:: STEP 3 OF 6 — Install PyTorch (CPU version — no GPU needed)
:: This is the largest download (~200 MB). Please be patient.
:: ────────────────────────────────────────────────────────────
echo.
echo  [Step 3 of 6] Installing PyTorch (CPU version)...
echo  ---------------------------------------------------
echo  This is the biggest download (~200 MB). Please wait...
echo.

pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ERROR: PyTorch installation failed.
    echo.
    echo  Possible reasons:
    echo    - No internet connection
    echo    - Firewall blocking the download
    echo    - Not enough disk space (need ~1 GB free)
    echo.
    echo  Please fix the issue above and run this installer again.
    echo.
    pause
    exit /b 1
)

echo.
echo  OK — PyTorch installed successfully!

:: ────────────────────────────────────────────────────────────
:: STEP 4 OF 6 — Install Shap-E
:: ────────────────────────────────────────────────────────────
echo.
echo  [Step 4 of 6] Installing Shap-E AI engine...
echo  ----------------------------------------------

pip install shap-e

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ERROR: Shap-E installation failed.
    echo  Please check your internet connection and try again.
    echo.
    pause
    exit /b 1
)

echo  OK — Shap-E installed!

:: ────────────────────────────────────────────────────────────
:: STEP 5 OF 6 — Install trimesh (needed for GLB/3D export)
:: ────────────────────────────────────────────────────────────
echo.
echo  [Step 5 of 6] Installing trimesh (3D file export)...
echo  ------------------------------------------------------

pip install trimesh

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ERROR: trimesh installation failed.
    echo  GLB file export may not work without it.
    echo  Please run:  pip install trimesh
    echo  ...and try again.
    echo.
    pause
    exit /b 1
)

echo  OK — trimesh installed!

:: ────────────────────────────────────────────────────────────
:: STEP 6 OF 6 — Test that the import works
:: ────────────────────────────────────────────────────────────
echo.
echo  [Step 6 of 6] Testing Shap-E import...
echo  ----------------------------------------

python -c "import shap_e; print('Shap-E OK')" 2>&1

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  WARNING: Shap-E installed but the import test failed.
    echo  This may be a known issue with some Python environments.
    echo  Try closing this window and re-running the test manually:
    echo.
    echo      python -c "import shap_e; print('Shap-E OK')"
    echo.
    pause
    exit /b 1
)

:: ────────────────────────────────────────────────────────────
:: SUCCESS — Write flag file so server knows Shap-E is ready
:: ────────────────────────────────────────────────────────────
echo.

:: Write shapee_installed.flag in the same folder as this .bat file
set "SCRIPT_DIR=%~dp0"
echo installed > "%SCRIPT_DIR%shapee_installed.flag"

echo  =====================================================
echo   SUCCESS! Shap-E AI Engine is installed and ready.
echo  =====================================================
echo.
echo  What was installed:
echo    - PyTorch (CPU)   — core AI framework
echo    - Shap-E          — 3D model generation AI
echo    - trimesh         — 3D file (GLB) export
echo.
echo  You can now use AI 3D generation inside the app.
echo  Start the app by double-clicking: tray_launcher.pyw
echo.

:end
echo  Press any key to close this window...
pause > nul
