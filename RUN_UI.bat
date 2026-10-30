@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title AccountSignal - run the dashboard

rem ---- find python -------------------------------------------------------
set "PY=python"
where python >nul 2>&1 || set "PY=py -3"
%PY% --version >nul 2>&1
if errorlevel 1 (
  echo.
  echo   ERROR: Python was not found on PATH. Install Python 3 and try again.
  echo.
  pause
  exit /b 1
)

echo.
echo  ==========================================================
echo   ACCOUNTSIGNAL - EY India Account Intelligence
echo  ==========================================================
echo.
echo   [1]  Built site      python  ^-^>  http://localhost:3100
echo        the finished dashboard. No Node needed. Use this on
echo        the office laptop / to show the manager.
echo.
echo   [2]  Dev server      npm run dev  ^-^>  http://localhost:3000
echo        live reload while you edit the UI code.
echo.
echo   [3]  Both at once    3100 (built)  +  3000 (dev)
echo.
set "C="
set /p "C=  Choose [1/2/3] (default 1): "
if "%C%"=="" set "C=1"

if "%C%"=="1" goto static
if "%C%"=="2" goto dev
if "%C%"=="3" goto both
echo   Not an option.
pause
exit /b 1

rem ---- 1: static ---------------------------------------------------------
:static
if not exist "webapp\out\index.html" goto nobuild
echo.
echo   Serving webapp\out at http://localhost:3100   (Ctrl+C to stop)
start "" http://localhost:3100
%PY% webapp\serve_nocache.py 3100
goto end

rem ---- 2: dev ------------------------------------------------------------
:dev
call :needmodules
if errorlevel 1 exit /b 1
echo.
echo   Starting Next.js dev server at http://localhost:3000  (Ctrl+C to stop)
cd webapp
call npm run dev
goto end

rem ---- 3: both -----------------------------------------------------------
:both
if not exist "webapp\out\index.html" goto nobuild
call :needmodules
if errorlevel 1 exit /b 1
echo.
echo   Opening two windows:
echo     built site  http://localhost:3100
echo     dev server  http://localhost:3000
start "AccountSignal - built site" cmd /k %PY% "%~dp0webapp\serve_nocache.py" 3100
start "AccountSignal - dev server" cmd /k "cd /d "%~dp0webapp" && npm run dev"
timeout /t 6 /nobreak >nul
start "" http://localhost:3100
start "" http://localhost:3000
goto end

rem ---- helpers -----------------------------------------------------------
:needmodules
where npm >nul 2>&1
if errorlevel 1 (
  echo.
  echo   ERROR: npm was not found. Node.js is required for the dev server.
  echo          Use option [1] instead - the built site needs no Node.
  echo.
  pause
  exit /b 1
)
if not exist "webapp\node_modules\next" (
  echo.
  echo   node_modules missing - installing once ^(needs internet^)...
  cd webapp
  call npm install
  cd ..
  if not exist "webapp\node_modules\next" (
    echo   npm install failed. Use option [1] - the built site needs no Node.
    pause
    exit /b 1
  )
)
exit /b 0

:nobuild
echo.
echo   webapp\out is missing - the site has not been built yet.
echo   Build it once with:   cd webapp ^&^& npm install ^&^& npm run build
echo.
pause
exit /b 1

:end
echo.
echo   Stopped.
pause
