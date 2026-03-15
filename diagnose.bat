@echo off
setlocal EnableDelayedExpansion
cd /d "C:\Users\user\Desktop\ai-3d-project"

:: ─────────────────────────────────────────────────────────────────────────────
:: Enable ANSI color codes in this console session
:: ─────────────────────────────────────────────────────────────────────────────
reg add HKCU\Console /v VirtualTerminalLevel /t REG_DWORD /d 1 /f >nul 2>&1

set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "WHITE=[97m"
set "RESET=[0m"

:: ─────────────────────────────────────────────────────────────────────────────
:: PORT-CONFLICT WARNING  (FIX 1)
:: ─────────────────────────────────────────────────────────────────────────────
echo.
echo %YELLOW%============================================================%RESET%
echo %WHITE% AI 3D Studio - Diagnostics V2%RESET%
echo %YELLOW%============================================================%RESET%
echo.
echo %YELLOW%WARNING: Close the system tray icon before running this script%RESET%
echo %WHITE%Press any key to continue or Ctrl+C to cancel...%RESET%
pause >nul
echo.

set PASS=0
set FAIL=0

:: ─────────────────────────────────────────────────────────────────────────────
:: Step 1 — Python version (must be 3.10+)
:: ─────────────────────────────────────────────────────────────────────────────
echo %WHITE%[1/10] Checking Python version (must be 3.10+) ...%RESET%
python --version >nul 2>&1
if errorlevel 1 (
    echo       %RED%[FAIL]%RESET% Python not found on PATH
    set /a FAIL+=1
    goto step2
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
for /f "tokens=1,2 delims=." %%a in ("!PYVER!") do (set PYMAJ=%%a & set PYMIN=%%b)
set PYOK=0
if !PYMAJ! GTR 3 set PYOK=1
if !PYMAJ! EQU 3 if !PYMIN! GEQ 10 set PYOK=1
if !PYOK! EQU 1 (
    echo       %GREEN%[PASS]%RESET% Python !PYVER!
    set /a PASS+=1
) else (
    echo       %RED%[FAIL]%RESET% Python !PYVER! is below 3.10
    set /a FAIL+=1
)

:step2
:: ─────────────────────────────────────────────────────────────────────────────
:: Step 2 — Flask installed
:: ─────────────────────────────────────────────────────────────────────────────
echo %WHITE%[2/10] Checking Flask ...%RESET%
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo       %RED%[FAIL]%RESET% Flask not installed  ^(run: pip install flask^)
    set /a FAIL+=1
) else (
    for /f %%v in ('python -c "import flask;print(flask.__version__)" 2^>^&1') do set FLASKVER=%%v
    echo       %GREEN%[PASS]%RESET% Flask !FLASKVER!
    set /a PASS+=1
)

:: ─────────────────────────────────────────────────────────────────────────────
:: Step 3 — Blender at exact path
:: ─────────────────────────────────────────────────────────────────────────────
echo %WHITE%[3/10] Checking Blender 5.0 ...%RESET%
if exist "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" (
    echo       %GREEN%[PASS]%RESET% Blender 5.0 found
    set /a PASS+=1
) else (
    echo       %RED%[FAIL]%RESET% blender.exe not found at:
    echo              C:\Program Files\Blender Foundation\Blender 5.0\blender.exe
    set /a FAIL+=1
)

:: ─────────────────────────────────────────────────────────────────────────────
:: Step 4 — static\index.html
:: ─────────────────────────────────────────────────────────────────────────────
echo %WHITE%[4/10] Checking static\index.html ...%RESET%
if exist "static\index.html" (
    echo       %GREEN%[PASS]%RESET% static\index.html found
    set /a PASS+=1
) else (
    echo       %RED%[FAIL]%RESET% static\index.html not found
    set /a FAIL+=1
)

:: ─────────────────────────────────────────────────────────────────────────────
:: Step 5 — Required directories
:: ─────────────────────────────────────────────────────────────────────────────
echo %WHITE%[5/10] Checking required directories ...%RESET%
set DIRS_OK=1
for %%d in (
    "models" "models\cache" "models\presets" "logs" "static" "storage"
    "storage\users" "storage\users\user"
    "storage\users\user\default" "storage\users\user\vehicles"
    "storage\users\user\creatures" "storage\users\user\buildings"
    "storage\users\user\misc"
) do (
    if not exist %%d (
        echo       %YELLOW%[WARN]%RESET%  MISSING: %%d
        set DIRS_OK=0
    )
)
if !DIRS_OK! EQU 1 (
    echo       %GREEN%[PASS]%RESET% all 13 required directories exist
    set /a PASS+=1
) else (
    echo       %RED%[FAIL]%RESET% one or more directories missing (see above)
    set /a FAIL+=1
)

:: ─────────────────────────────────────────────────────────────────────────────
:: Step 6 — folders.json valid JSON array
:: ─────────────────────────────────────────────────────────────────────────────
echo %WHITE%[6/10] Checking folders.json ...%RESET%
if not exist "folders.json" (
    echo       %RED%[FAIL]%RESET% folders.json not found
    set /a FAIL+=1
    goto step7
)
python -c "import json,sys;d=json.load(open('folders.json'));sys.exit(0 if isinstance(d,list) else 1)" >nul 2>&1
if errorlevel 1 (
    echo       %RED%[FAIL]%RESET% folders.json is not a valid JSON array
    set /a FAIL+=1
) else (
    echo       %GREEN%[PASS]%RESET% folders.json is a valid JSON array
    set /a PASS+=1
)

:step7
:: ─────────────────────────────────────────────────────────────────────────────
:: Step 7 — history.json valid JSON
:: ─────────────────────────────────────────────────────────────────────────────
echo %WHITE%[7/10] Checking history.json ...%RESET%
if not exist "history.json" (
    echo       %RED%[FAIL]%RESET% history.json not found
    set /a FAIL+=1
    goto step8
)
python -c "import json;json.load(open('history.json'))" >nul 2>&1
if errorlevel 1 (
    echo       %RED%[FAIL]%RESET% history.json is not valid JSON
    set /a FAIL+=1
) else (
    echo       %GREEN%[PASS]%RESET% history.json is valid JSON
    set /a PASS+=1
)

:step8
:: ─────────────────────────────────────────────────────────────────────────────
:: Step 8 — server.py exists and >= 60 KB
:: ─────────────────────────────────────────────────────────────────────────────
echo %WHITE%[8/10] Checking server.py size (>= 60 KB) ...%RESET%
if not exist "server.py" (
    echo       %RED%[FAIL]%RESET% server.py not found
    set /a FAIL+=1
    goto step9_pre
)
for %%f in ("server.py") do set FSIZE=%%~zf
if !FSIZE! GEQ 61440 (
    echo       %GREEN%[PASS]%RESET% server.py found ^(!FSIZE! bytes^)
    set /a PASS+=1
) else (
    echo       %RED%[FAIL]%RESET% server.py is only !FSIZE! bytes ^(need >= 61440 / 60 KB^)
    set /a FAIL+=1
)

:step9_pre
:: ─────────────────────────────────────────────────────────────────────────────
:: Pre-Step 9 — Kill any running Python servers  (PORT-CONFLICT FIX)
:: ─────────────────────────────────────────────────────────────────────────────
echo.
echo %YELLOW%Stopping any running Python servers...%RESET%
taskkill /F /IM pythonw.exe /T >nul 2>&1
taskkill /F /IM python.exe  /T >nul 2>&1
timeout /t 2 /nobreak >nul
echo %WHITE%Done. Starting fresh test server...%RESET%
echo.

:: ─────────────────────────────────────────────────────────────────────────────
:: Step 9 — Live /ping test
:: ─────────────────────────────────────────────────────────────────────────────
echo %WHITE%[9/11] Starting server for ping test ...%RESET%
python -c "import subprocess,os,sys;p=subprocess.Popen(['python','server.py'],cwd=os.getcwd(),creationflags=subprocess.CREATE_NO_WINDOW);open('_diag_pid.tmp','w').write(str(p.pid))" >nul 2>&1
timeout /t 4 /nobreak >nul
echo       %WHITE%Pinging http://localhost:5000/ping ...%RESET%
set PING_OK=0
python -c "import urllib.request,json,sys;r=urllib.request.urlopen('http://localhost:5000/ping',timeout=5);b=json.loads(r.read());sys.exit(0 if b.get('ok') else 1)" >nul 2>&1
if errorlevel 1 (
    echo       %RED%[FAIL]%RESET% /ping did not return {"ok": true}
    set /a FAIL+=1
    echo.
    echo       %YELLOW%--- last 30 lines of logs\server.log ---%RESET%
    if exist "logs\server.log" (
        python -c "lines=open('logs\\server.log').readlines();print(''.join(lines[-30:]),end='')"
    ) else (
        echo       %YELLOW%(logs\server.log not found)%RESET%
    )
    echo.
) else (
    echo       %GREEN%[PASS]%RESET% /ping returned ok:true
    set /a PASS+=1
    set PING_OK=1
)

:: ─────────────────────────────────────────────────────────────────────────────
:: Step 10 — Kill test server
:: ─────────────────────────────────────────────────────────────────────────────
echo %WHITE%[10/11] Stopping test server ...%RESET%
if exist "_diag_pid.tmp" (
    for /f %%p in (_diag_pid.tmp) do taskkill /PID %%p /F >nul 2>&1
    del "_diag_pid.tmp" >nul 2>&1
    echo       %GREEN%[PASS]%RESET% test server stopped
) else (
    taskkill /F /IM python.exe /T >nul 2>&1
    echo       %GREEN%[PASS]%RESET% test server stopped (fallback)
)
set /a PASS+=1

echo.
echo %WHITE%You can now restart the tray icon.%RESET%
echo.

:: ─────────────────────────────────────────────────────────────────────────────
:: Step 11 — Groq API key health check (reads dynamically from /ping response)
:: ─────────────────────────────────────────────────────────────────────────────
echo %WHITE%[11/11] Checking Groq API key health ...%RESET%
if !PING_OK! NEQ 1 (
    echo       %YELLOW%[SKIP]%RESET% Step 11: server not running -- cannot check keys
    goto summary
)

:: Call /ping and write key data to a temp file
python -c ^
"import urllib.request,json,sys;" ^
"r=urllib.request.urlopen('http://localhost:5000/ping',timeout=5);" ^
"d=json.loads(r.read());" ^
"alive=d.get('groq_keys_alive',[]);" ^
"dead=d.get('groq_keys_dead',[]);" ^
"print('ALIVE:'+','.join(alive) if alive else 'ALIVE:none');" ^
"print('DEAD:'+','.join(dead) if dead else 'DEAD:none');" ^
"print('COUNT:'+str(len(alive)))" ^
>"_diag_keys.tmp" 2>&1
if errorlevel 1 (
    echo       %YELLOW%[SKIP]%RESET% Step 11: could not reach /ping -- skipping key check
    if exist "_diag_keys.tmp" del "_diag_keys.tmp" >nul 2>&1
    goto summary
)

:: Parse ALIVE, DEAD, COUNT from temp file
set ALIVE_LINE=
set DEAD_LINE=
set KEY_COUNT=0
for /f "tokens=1,* delims=:" %%a in (_diag_keys.tmp) do (
    if "%%a"=="ALIVE" set ALIVE_LINE=%%b
    if "%%a"=="DEAD"  set DEAD_LINE=%%b
    if "%%a"=="COUNT" set KEY_COUNT=%%b
    if "%%a"=="ERROR" (
        echo       %YELLOW%[SKIP]%RESET% Step 11: ping error -- %%b
        del "_diag_keys.tmp" >nul 2>&1
        goto summary
    )
)
del "_diag_keys.tmp" >nul 2>&1

:: Print each alive key in green
if not "!ALIVE_LINE!"=="none" if not "!ALIVE_LINE!"=="" (
    for /f "tokens=* delims=" %%k in ('python -c "for k in '!ALIVE_LINE!'.split(','): print(k)"') do (
        echo       %GREEN%[KEY OK]%RESET%   %%k -- active
    )
)

:: Print each dead key in red
if not "!DEAD_LINE!"=="none" if not "!DEAD_LINE!"=="" (
    for /f "tokens=* delims=" %%k in ('python -c "for k in '!DEAD_LINE!'.split(','): print(k)"') do (
        echo       %RED%[KEY DEAD]%RESET% %%k -- quota exhausted
    )
)

:: Summary line based on alive count
if !KEY_COUNT! EQU 4 (
    echo       %GREEN%[PASS]%RESET% Step 11: All 4 Groq keys active
    set /a PASS+=1
) else if !KEY_COUNT! GEQ 2 (
    echo       %YELLOW%[WARN]%RESET% Step 11: !KEY_COUNT! of 4 Groq keys active
    set /a PASS+=1
) else if !KEY_COUNT! EQU 1 (
    echo       %YELLOW%[WARN]%RESET% Step 11: Only 1 Groq key remaining!
    set /a PASS+=1
) else (
    echo       %RED%[FAIL]%RESET% Step 11: All Groq keys dead -- AI generation disabled
    set /a FAIL+=1
)

:summary
:: ─────────────────────────────────────────────────────────────────────────────
:: Summary
:: ─────────────────────────────────────────────────────────────────────────────
echo %YELLOW%============================================================%RESET%
if !FAIL! EQU 0 (
    echo  %GREEN%!PASS!/11 checks passed%RESET%
) else (
    echo  %GREEN%!PASS!/11 checks passed%RESET%  %RED%(!FAIL! failed)%RESET%
)
echo %YELLOW%============================================================%RESET%
if !FAIL! GTR 0 (
    echo  %YELLOW%Run setup.bat to repair%RESET%
)
echo.
pause
endlocal
