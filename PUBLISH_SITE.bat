@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title AccountSignal - publish data to the live site

rem ---- git must exist ---------------------------------------------------
where git >nul 2>&1
if errorlevel 1 (
  echo.
  echo   ERROR: git was not found on PATH. Install Git for Windows and retry.
  echo.
  pause
  exit /b 1
)
if not exist ".git" (
  echo.
  echo   ERROR: this folder is not a git repository, so it cannot be published.
  echo.
  pause
  exit /b 1
)

echo.
echo  ==========================================================
echo   PUBLISH THE NEW NUMBERS TO THE LIVE SITE (Vercel)
echo  ==========================================================
echo.
echo   Every push to main makes Vercel rebuild the site (~2 min).
echo   Only  webapp\public\data.json  is committed here.
echo.
echo   [1] Refresh everything  ^(python app.py^), then publish.  SLOW
echo       Full re-scrape - 15-30 min, uses Apify credit.
echo.
echo   [2] Rebuild from the last scrape, then publish.        FAST
echo       Same numbers, freshly re-ranked - 1-2 min.
echo.
echo   [3] Publish the data.json already on disk.  No rebuild.
echo.
set "C="
set /p "C=  Choose [1/2/3] (default 2): "
if "%C%"=="" set "C=2"

if "%C%"=="1" goto full
if "%C%"=="2" goto quick
if "%C%"=="3" goto commit
echo   Not an option.
pause
exit /b 1

:full
set "PY=python"
where python >nul 2>&1 || set "PY=py -3"
%PY% app.py --no-open
if errorlevel 1 goto runfail
goto commit

:quick
set "PY=python"
where python >nul 2>&1 || set "PY=py -3"
%PY% app.py --skip-scrape --no-open
if errorlevel 1 goto runfail
goto commit

:commit
echo.
git status --porcelain -- webapp/public/data.json | findstr /r "." >nul
if errorlevel 1 (
  echo   webapp\public\data.json has no changes - nothing to publish.
  echo   The live site already matches this laptop.
  echo.
  pause
  exit /b 0
)
git add webapp/public/data.json
git commit -m "data refresh %DATE% %TIME%"
if errorlevel 1 goto fail
echo.
echo   Pushing to GitHub...
git push origin main
if errorlevel 1 goto pushfail
echo.
echo   Done. Vercel is rebuilding now - the live URL updates in ~2 min.
echo   Watch it at  https://vercel.com/dashboard
echo.
pause
exit /b 0

:runfail
echo.
echo   The pipeline reported an error - nothing was published.
echo.
pause
exit /b 1

:fail
echo.
echo   git commit failed - see the message above. Nothing was pushed.
echo.
pause
exit /b 1

:pushfail
echo.
echo   git push failed (usually a sign-in problem).
echo   Sign in to GitHub once with GitHub Desktop or VS Code, or use a
echo   Personal Access Token as the password, then try again - or push
echo   by hand:   git push origin main
echo.
pause
exit /b 1
