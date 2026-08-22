@echo off
REM author: jf
setlocal EnableExtensions

REM Stop the current stack first so Spring AI and Python AI do not run together.
set "COMPOSE_ENV="
set "COMPOSE_ENV_FILE=.env"
if exist ".env" (
  echo [INFO] Using .env for Docker Compose variables.
) else if exist ".env.docker" (
  set "COMPOSE_ENV=--env-file .env.docker"
  set "COMPOSE_ENV_FILE=.env.docker"
  echo [INFO] Using .env.docker for Docker Compose variables.
) else (
  set "COMPOSE_ENV_FILE="
  echo [WARN] .env and .env.docker were not found. Compose defaults will be used.
)

call :load_env "%COMPOSE_ENV_FILE%"
call :normalize_host_urls

docker compose down
if errorlevel 1 exit /b %errorlevel%

call :ensure_build_images
if errorlevel 1 exit /b %errorlevel%

set "DB_SERVICES="
call :is_port_listening %MYSQL_PORT%
if not errorlevel 1 (
  echo [WARN] Host port %MYSQL_PORT% is already in use. Skipping MySQL container.
  echo [INFO] Python AI backend will use host.docker.internal:%MYSQL_PORT%.
  set "PYTHON_MYSQL_DATASOURCE_URL=mysql+pymysql://%MYSQL_DATASOURCE_USERNAME%:%MYSQL_DATASOURCE_PASSWORD%@host.docker.internal:%MYSQL_PORT%/%MYSQL_DATABASE%"
) else (
  set "DB_SERVICES=%DB_SERVICES% mysql"
)

if "%PYTHON_PGVECTOR_DATASOURCE_URL%"=="" if not "%PGVECTOR_DATASOURCE_URL%"=="" set "PYTHON_PGVECTOR_DATASOURCE_URL=%PGVECTOR_DATASOURCE_URL%"
call :is_external_pgvector_url PYTHON_PGVECTOR_DATASOURCE_URL
if not errorlevel 1 (
  echo [INFO] Using configured external or host pgvector URL. Skipping pgvector container.
  call :disable_pgvector_service
) else (
  call :is_port_listening %PGVECTOR_PORT%
  if not errorlevel 1 (
    echo [WARN] Host port %PGVECTOR_PORT% is already in use. Skipping pgvector container.
    echo [INFO] Python AI backend will use host.docker.internal:%PGVECTOR_PORT%.
    if "%PYTHON_PGVECTOR_DATASOURCE_URL%"=="" set "PYTHON_PGVECTOR_DATASOURCE_URL=postgresql+psycopg://%PGVECTOR_DATASOURCE_USERNAME%:%PGVECTOR_DATASOURCE_PASSWORD%@host.docker.internal:%PGVECTOR_PORT%/%POSTGRES_DB%"
    call :is_compose_pgvector_url PYTHON_PGVECTOR_DATASOURCE_URL
    if not errorlevel 1 set "PYTHON_PGVECTOR_DATASOURCE_URL=postgresql+psycopg://%PGVECTOR_DATASOURCE_USERNAME%:%PGVECTOR_DATASOURCE_PASSWORD%@host.docker.internal:%PGVECTOR_PORT%/%POSTGRES_DB%"
    call :disable_pgvector_service
  ) else (
    set "DB_SERVICES=%DB_SERVICES% pgvector"
  )
)

call :ensure_database_images
if errorlevel 1 exit /b %errorlevel%

if not "%DB_SERVICES%"=="" (
  echo [INFO] Starting database containers:%DB_SERVICES%
  docker compose %COMPOSE_ENV% --profile python-ai up --build -d %DB_SERVICES%
  if errorlevel 1 exit /b %errorlevel%
  call :initialize_started_databases
  if errorlevel 1 exit /b %errorlevel%
) else (
  echo [INFO] No Docker database containers were started. Skipping automatic SQL initialization.
)

echo [INFO] 正在使用 Docker 启动 Python AI 后端。
docker compose %COMPOSE_ENV% --profile python-ai up --build -d --no-deps python-ai-backend
if errorlevel 1 exit /b %errorlevel%

echo.
echo [INFO] Python AI 后端 Docker 服务已启动。
echo [INFO] 本地前端：http://localhost:%FRONTEND_PORT%
echo [INFO] Health: http://localhost:%BACKEND_PORT%/health
echo [INFO] If a database container was skipped, make sure the host database has run sql/interview_schema.sql and sql/pgvector_rag_schema.sql.
echo.
docker compose %COMPOSE_ENV% ps
echo.
docker compose %COMPOSE_ENV% logs --tail=80 python-ai-backend
if errorlevel 1 exit /b %errorlevel%

echo.
echo [INFO] 前端未自动启动，请在新终端手动执行：
echo [INFO] npm run dev -- --host 127.0.0.1 --port %FRONTEND_PORT% --strictPort
exit /b 0

:load_env
set "FRONTEND_PORT=3000"
set "BACKEND_PORT=8999"
set "BACKEND_PORT_SET=0"
set "SERVER_PORT=8999"
set "MYSQL_PORT=3306"
set "MYSQL_DATABASE=resume-builder"
set "MYSQL_ROOT_PASSWORD=root"
set "MYSQL_DATASOURCE_USERNAME=root"
set "MYSQL_DATASOURCE_PASSWORD=root"
set "POSTGRES_DB=resume-builder"
set "POSTGRES_USER=pgvector"
set "POSTGRES_PASSWORD=pgvector"
set "PGVECTOR_PORT=5433"
set "PGVECTOR_DATASOURCE_USERNAME=pgvector"
set "PGVECTOR_DATASOURCE_PASSWORD=pgvector"
set "PGVECTOR_DATASOURCE_URL="
set "PYTHON_PGVECTOR_DATASOURCE_URL="
set "NODE_IMAGE=node:22-alpine"
set "NGINX_IMAGE=nginx:alpine"
set "PYTHON_IMAGE=python:3.11-slim"
set "MYSQL_IMAGE=mysql:8.4"
set "PGVECTOR_IMAGE=pgvector/pgvector:pg17"
if "%~1"=="" exit /b 0
if not exist "%~1" exit /b 0
for /f "usebackq tokens=1,* delims==" %%A in ("%~1") do (
  if "%%A"=="FRONTEND_PORT" set "FRONTEND_PORT=%%B"
  if "%%A"=="BACKEND_PORT" set "BACKEND_PORT=%%B"
  if "%%A"=="BACKEND_PORT" set "BACKEND_PORT_SET=1"
  if "%%A"=="SERVER_PORT" set "SERVER_PORT=%%B"
  if "%%A"=="MYSQL_PORT" set "MYSQL_PORT=%%B"
  if "%%A"=="MYSQL_DATABASE" set "MYSQL_DATABASE=%%B"
  if "%%A"=="MYSQL_ROOT_PASSWORD" set "MYSQL_ROOT_PASSWORD=%%B"
  if "%%A"=="MYSQL_DATASOURCE_USERNAME" set "MYSQL_DATASOURCE_USERNAME=%%B"
  if "%%A"=="MYSQL_DATASOURCE_PASSWORD" set "MYSQL_DATASOURCE_PASSWORD=%%B"
  if "%%A"=="POSTGRES_DB" set "POSTGRES_DB=%%B"
  if "%%A"=="POSTGRES_USER" set "POSTGRES_USER=%%B"
  if "%%A"=="POSTGRES_PASSWORD" set "POSTGRES_PASSWORD=%%B"
  if "%%A"=="PGVECTOR_PORT" set "PGVECTOR_PORT=%%B"
  if "%%A"=="PGVECTOR_DATASOURCE_USERNAME" set "PGVECTOR_DATASOURCE_USERNAME=%%B"
  if "%%A"=="PGVECTOR_DATASOURCE_PASSWORD" set "PGVECTOR_DATASOURCE_PASSWORD=%%B"
  if "%%A"=="PGVECTOR_DATASOURCE_URL" set "PGVECTOR_DATASOURCE_URL=%%B"
  if "%%A"=="PYTHON_PGVECTOR_DATASOURCE_URL" set "PYTHON_PGVECTOR_DATASOURCE_URL=%%B"
  if "%%A"=="OPENAI_BASE_URL" set "OPENAI_BASE_URL=%%B"
  if "%%A"=="OPENAI_CHAT_BASE_URL" set "OPENAI_CHAT_BASE_URL=%%B"
  if "%%A"=="OPENAI_EMBEDDING_BASE_URL" set "OPENAI_EMBEDDING_BASE_URL=%%B"
  if "%%A"=="OPENAI_VISION_BASE_URL" set "OPENAI_VISION_BASE_URL=%%B"
  if "%%A"=="OPENAI_REALTIME_BASE_URL" set "OPENAI_REALTIME_BASE_URL=%%B"
  if "%%A"=="OLLAMA_EMBEDDING_BASE_URL" set "OLLAMA_EMBEDDING_BASE_URL=%%B"
  if "%%A"=="NODE_IMAGE" set "NODE_IMAGE=%%B"
  if "%%A"=="NGINX_IMAGE" set "NGINX_IMAGE=%%B"
  if "%%A"=="PYTHON_IMAGE" set "PYTHON_IMAGE=%%B"
  if "%%A"=="MYSQL_IMAGE" set "MYSQL_IMAGE=%%B"
  if "%%A"=="PGVECTOR_IMAGE" set "PGVECTOR_IMAGE=%%B"
)
if "%BACKEND_PORT_SET%"=="0" set "BACKEND_PORT=%SERVER_PORT%"
exit /b 0

:normalize_host_urls
call :normalize_one_url OPENAI_BASE_URL
call :normalize_one_url OPENAI_CHAT_BASE_URL
call :normalize_one_url OPENAI_EMBEDDING_BASE_URL
call :normalize_one_url OPENAI_VISION_BASE_URL
call :normalize_one_url OPENAI_REALTIME_BASE_URL
call :normalize_one_url OLLAMA_EMBEDDING_BASE_URL
call :normalize_one_url PGVECTOR_DATASOURCE_URL
call :normalize_one_url PYTHON_PGVECTOR_DATASOURCE_URL
exit /b 0

:normalize_one_url
call set "CURRENT_VALUE=%%%~1%%"
if "%CURRENT_VALUE%"=="" exit /b 0
set "NORMALIZED_VALUE=%CURRENT_VALUE:localhost=host.docker.internal%"
set "NORMALIZED_VALUE=%NORMALIZED_VALUE:127.0.0.1=host.docker.internal%"
if not "%NORMALIZED_VALUE%"=="%CURRENT_VALUE%" (
  set "%~1=%NORMALIZED_VALUE%"
  echo [INFO] Rewrote %~1 for Docker host access.
)
exit /b 0

:is_external_pgvector_url
call set "CURRENT_VALUE=%%%~1%%"
if "%CURRENT_VALUE%"=="" exit /b 1
call :is_compose_pgvector_url %~1
if not errorlevel 1 exit /b 1
exit /b 0

:is_compose_pgvector_url
call set "CURRENT_VALUE=%%%~1%%"
if "%CURRENT_VALUE%"=="" exit /b 1
if not "%CURRENT_VALUE://pgvector:=%"=="%CURRENT_VALUE%" exit /b 0
if not "%CURRENT_VALUE:@pgvector:=%"=="%CURRENT_VALUE%" exit /b 0
exit /b 1

:remove_skipped_service
docker compose %COMPOSE_ENV% --profile python-ai rm -sf %~1 >nul 2>nul
exit /b 0

:disable_pgvector_service
set "PGVECTOR_PROFILE_SPRING_AI=host-pgvector-disabled"
set "PGVECTOR_PROFILE_PYTHON_AI=host-pgvector-disabled"
call :remove_skipped_service pgvector
exit /b 0

:initialize_started_databases
for %%S in (%DB_SERVICES%) do (
  if "%%S"=="mysql" call :initialize_mysql
  if errorlevel 1 exit /b 1
  if "%%S"=="pgvector" call :initialize_pgvector
  if errorlevel 1 exit /b 1
)
exit /b 0

:initialize_mysql
echo [INFO] Waiting for MySQL container to become healthy.
call :wait_for_healthy resume-builder-mysql 120
if errorlevel 1 exit /b 1
if not exist "sql\mysql_database_schema.sql" (
  echo [ERROR] Missing sql\mysql_database_schema.sql.
  exit /b 1
)
if not exist "sql\interview_schema.sql" (
  echo [ERROR] Missing sql\interview_schema.sql.
  exit /b 1
)
echo [INFO] Initializing MySQL database and interview tables.
docker exec -i resume-builder-mysql mysql -uroot "-p%MYSQL_ROOT_PASSWORD%" < sql\mysql_database_schema.sql
if errorlevel 1 exit /b 1
docker exec -i resume-builder-mysql mysql -uroot "-p%MYSQL_ROOT_PASSWORD%" "%MYSQL_DATABASE%" < sql\interview_schema.sql
if errorlevel 1 exit /b 1
exit /b 0

:initialize_pgvector
echo [INFO] Waiting for pgvector container to become healthy.
call :wait_for_healthy resume-builder-pgvector 120
if errorlevel 1 exit /b 1
if not exist "sql\create_pgvector_resume_builder_database.sql" (
  echo [ERROR] Missing sql\create_pgvector_resume_builder_database.sql.
  exit /b 1
)
if not exist "sql\pgvector_rag_schema.sql" (
  echo [ERROR] Missing sql\pgvector_rag_schema.sql.
  exit /b 1
)
echo [INFO] Initializing pgvector database and RAG tables.
docker exec resume-builder-pgvector psql -v ON_ERROR_STOP=1 -U "%POSTGRES_USER%" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '%POSTGRES_DB%'" | findstr /R /C:"1" >nul
if errorlevel 1 (
  docker exec -i resume-builder-pgvector psql -v ON_ERROR_STOP=1 -U "%POSTGRES_USER%" -d postgres < sql\create_pgvector_resume_builder_database.sql
  if errorlevel 1 exit /b 1
) else (
  echo [INFO] pgvector database %POSTGRES_DB% already exists. Skipping database creation.
)
docker exec -i resume-builder-pgvector psql -v ON_ERROR_STOP=1 -U "%POSTGRES_USER%" -d "%POSTGRES_DB%" < sql\pgvector_rag_schema.sql
if errorlevel 1 exit /b 1
exit /b 0

:wait_for_healthy
set "WAIT_CONTAINER=%~1"
set "WAIT_LIMIT=%~2"
set "WAIT_COUNT=0"
:wait_for_healthy_loop
set "WAIT_STATUS="
for /f "delims=" %%H in ('docker inspect -f "{{.State.Health.Status}}" "%WAIT_CONTAINER%" 2^>nul') do set "WAIT_STATUS=%%H"
if "%WAIT_STATUS%"=="healthy" exit /b 0
if %WAIT_COUNT% GEQ %WAIT_LIMIT% (
  echo [ERROR] Container %WAIT_CONTAINER% did not become healthy.
  exit /b 1
)
set /a WAIT_COUNT+=1 >nul
timeout /t 1 /nobreak >nul
goto wait_for_healthy_loop

:ensure_build_images
set "MISSING_IMAGES=0"
call :ensure_image PYTHON_IMAGE
if not "%MISSING_IMAGES%"=="0" exit /b 1
exit /b 0

:ensure_database_images
set "MISSING_IMAGES=0"
for %%S in (%DB_SERVICES%) do (
  if "%%S"=="mysql" call :ensure_image MYSQL_IMAGE
  if "%%S"=="pgvector" call :ensure_image PGVECTOR_IMAGE
)
if not "%MISSING_IMAGES%"=="0" exit /b 1
exit /b 0

:ensure_image
call set "IMAGE_VALUE=%%%~1%%"
if "%IMAGE_VALUE%"=="" exit /b 0
docker image inspect "%IMAGE_VALUE%" >nul 2>nul
if not errorlevel 1 exit /b 0
echo [INFO] Pulling Docker image for %~1: %IMAGE_VALUE%
docker pull "%IMAGE_VALUE%"
if errorlevel 1 (
  echo.
  echo [ERROR] Cannot pull required Docker image: %IMAGE_VALUE%
  echo [ERROR] If Docker Hub is unreachable, set %~1 in .env to a reachable registry mirror image.
  echo [ERROR] You can also docker pull or docker load this image manually, then rerun this script.
  set "MISSING_IMAGES=1"
)
exit /b 0

:is_port_listening
powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Get-NetTCPConnection -LocalPort %~1 -State Listen -ErrorAction SilentlyContinue) { exit 0 }; exit 1"
exit /b %errorlevel%
