@echo off
setlocal EnableExtensions
REM author: jf

set "BACKEND_DIR=%~dp0python-ai-backend"
cd /d "%BACKEND_DIR%" || (
  echo [ERROR] python-ai-backend directory not found.
  pause
  exit /b 1
)

set "WORK_TMP=%BACKEND_DIR%\.tmp\python-installer-tmp"
if not exist "%WORK_TMP%" mkdir "%WORK_TMP%" >nul 2>&1
set "TMP=%WORK_TMP%"
set "TEMP=%WORK_TMP%"
set "UV_HTTP_TIMEOUT=15"
echo [INFO] Python temporary directory: %WORK_TMP%

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python is not installed or not in PATH.
  pause
  exit /b 1
)

where uv >nul 2>&1
if errorlevel 1 (
  echo [ERROR] uv is not installed or not in PATH.
  echo [HINT] Install uv first, then rerun this script:
  echo [HINT]   powershell -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 ^| iex"
  pause
  exit /b 1
)

set "VENV_PY=.venv\Scripts\python.exe"
set "VENV_PY_ABS=%BACKEND_DIR%\.venv\Scripts\python.exe"
set "RUN_PY=%VENV_PY%"

echo [1/7] Preparing virtual environment...
set "RECREATE_VENV=0"
if not exist ".venv\pyvenv.cfg" set "RECREATE_VENV=1"
if not exist "%VENV_PY%" set "RECREATE_VENV=1"
if "%RECREATE_VENV%"=="0" (
  "%VENV_PY%" -V >nul 2>&1
  if errorlevel 1 (
    echo [WARN] Existing virtual environment is broken, recreating...
    set "RECREATE_VENV=1"
  )
)
if "%RECREATE_VENV%"=="1" (
  call :recreate_venv
  if errorlevel 1 (
    echo [ERROR] Failed to create/repair virtual environment via uv.
    pause
    exit /b 1
  )
) else (
  echo [INFO] Reusing existing virtual environment.
)

echo [2/7] Checking core dependencies...
"%VENV_PY%" -c "import fastapi,uvicorn,pydantic,pymysql,pypdf,docx,cryptography,sqlalchemy" >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Core dependencies are missing in .venv, but auto-install is disabled.
  echo [HINT] Install dependencies manually, for example:
  echo [HINT]   uv pip install --python "%VENV_PY_ABS%" -r requirements.txt
  pause
  exit /b 1
)

echo [3/7] Checking optional embedding dependencies...
if exist "requirements-optional.txt" (
  REM Optional check must not block backend startup.
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$proc = Start-Process -FilePath '%VENV_PY_ABS%' -ArgumentList '-c','import llama_index.embeddings.openai, llama_index.embeddings.ollama' -PassThru -WindowStyle Hidden; if (-not ($proc | Wait-Process -Timeout 12 -ErrorAction SilentlyContinue)) { try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}; exit 2 }; exit $proc.ExitCode"
  if errorlevel 2 (
    echo [WARN] Optional embedding dependency check timed out after 12s, skipped.
    echo [WARN] This does not block startup. If embedding fails later, run:
    echo [WARN]   "%VENV_PY_ABS%" -c "import llama_index.embeddings.openai, llama_index.embeddings.ollama"
  ) else (
    if errorlevel 1 (
      echo [WARN] Optional embedding dependencies are missing.
      echo [WARN] Auto-install is disabled. If needed, install manually:
      echo [WARN]   uv pip install --python "%VENV_PY_ABS%" -r requirements-optional.txt
    ) else (
      echo [3/7] Optional embedding dependencies already installed.
    )
  )
) else (
  echo [3/7] requirements-optional.txt not found, skipping optional AI dependencies.
)

if not exist ".env" (
  echo [4/7] Creating .env from .env.example...
  copy /Y ".env.example" ".env" >nul
) else (
  echo [4/7] Reusing existing .env...
)

echo [5/7] Cleaning old listener on port 8999 if present...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop-python-backend.ps1" -Port 8999
if errorlevel 1 (
  echo [ERROR] Failed to free port 8999.
  echo [HINT] If the script says the listener is stale, reboot Windows once and rerun this bat.
  pause
  exit /b 1
)

echo [6/7] Validating runtime entrypoint...
if /I not "%RUN_PY%"=="python" if not exist "%VENV_PY%" (
  echo [ERROR] Virtual environment python executable not found: %VENV_PY%
  pause
  exit /b 1
)

echo [7/7] Starting python-ai-backend on http://127.0.0.1:8999
echo Runtime check: http://127.0.0.1:8999/health/runtime
if /I "%RUN_PY%"=="python" (
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8999 --app-dir "%BACKEND_DIR%"
) else (
  "%VENV_PY%" -m uvicorn app.main:app --host 127.0.0.1 --port 8999 --app-dir "%BACKEND_DIR%"
)

echo.
echo Backend process exited.
pause
exit /b %errorlevel%

:recreate_venv
echo [INFO] Recreating virtual environment via uv...
if exist ".venv" (
  echo [INFO] Existing .venv detected, trying to release file locks...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-Process python,python3 -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue; Start-Sleep -Milliseconds 300" >nul 2>&1
  echo [INFO] Removing old .venv...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Test-Path '.venv') { attrib -R -S -H '.venv' /S /D > $null 2>&1; Remove-Item -Recurse -Force '.venv' }" >nul 2>&1
  if exist ".venv" (
    echo [ERROR] Could not remove .venv. Close terminals/editors using this folder and retry.
    exit /b 1
  )
)
uv venv .venv
exit /b %errorlevel%
