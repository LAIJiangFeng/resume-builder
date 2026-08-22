@echo off
REM author: jf
setlocal EnableExtensions

REM 先停止当前套件，避免 Spring AI 与 Python AI 同时运行。
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
  echo [INFO] Spring AI backend will use host.docker.internal:%MYSQL_PORT%.
  set "SPRING_MYSQL_DATASOURCE_URL=jdbc:mysql://host.docker.internal:%MYSQL_PORT%/%MYSQL_DATABASE%?useUnicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai&useSSL=false&allowPublicKeyRetrieval=true"
  call :is_compose_mysql_url FLYWAY_MYSQL_URL
  if not errorlevel 1 set "FLYWAY_MYSQL_URL=jdbc:mysql://host.docker.internal:%MYSQL_PORT%/%MYSQL_DATABASE%?useUnicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai&useSSL=false&allowPublicKeyRetrieval=true"
  if "%FLYWAY_MYSQL_URL%"=="" set "FLYWAY_MYSQL_URL=jdbc:mysql://host.docker.internal:%MYSQL_PORT%/%MYSQL_DATABASE%?useUnicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai&useSSL=false&allowPublicKeyRetrieval=true"
) else (
  set "DB_SERVICES=%DB_SERVICES% mysql"
  if "%FLYWAY_MYSQL_URL%"=="" set "FLYWAY_MYSQL_URL=jdbc:mysql://mysql:3306/%MYSQL_DATABASE%?useUnicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai&useSSL=false&allowPublicKeyRetrieval=true"
)

if "%SPRING_PGVECTOR_DATASOURCE_URL%"=="" if not "%PGVECTOR_DATASOURCE_URL%"=="" set "SPRING_PGVECTOR_DATASOURCE_URL=%PGVECTOR_DATASOURCE_URL%"
call :is_external_pgvector_url SPRING_PGVECTOR_DATASOURCE_URL
if not errorlevel 1 (
  echo [INFO] Using configured external or host pgvector URL. Skipping pgvector container.
  call :configure_spring_external_postgres_migration
  call :disable_pgvector_service
) else (
  call :is_port_listening %PGVECTOR_PORT%
  if not errorlevel 1 (
    echo [WARN] Host port %PGVECTOR_PORT% is already in use. Skipping pgvector container.
    echo [INFO] Spring AI backend will use host.docker.internal:%PGVECTOR_PORT%.
    if "%SPRING_PGVECTOR_DATASOURCE_URL%"=="" set "SPRING_PGVECTOR_DATASOURCE_URL=jdbc:postgresql://host.docker.internal:%PGVECTOR_PORT%/%POSTGRES_DB%"
    call :is_compose_pgvector_url SPRING_PGVECTOR_DATASOURCE_URL
    if not errorlevel 1 set "SPRING_PGVECTOR_DATASOURCE_URL=jdbc:postgresql://host.docker.internal:%PGVECTOR_PORT%/%POSTGRES_DB%"
    call :is_compose_pgvector_url FLYWAY_POSTGRES_URL
    if not errorlevel 1 set "FLYWAY_POSTGRES_URL=jdbc:postgresql://host.docker.internal:%PGVECTOR_PORT%/%POSTGRES_DB%"
    if "%FLYWAY_POSTGRES_URL%"=="" set "FLYWAY_POSTGRES_URL=jdbc:postgresql://host.docker.internal:%PGVECTOR_PORT%/%POSTGRES_DB%"
    call :disable_pgvector_service
  ) else (
    set "DB_SERVICES=%DB_SERVICES% pgvector"
    if "%FLYWAY_POSTGRES_URL%"=="" set "FLYWAY_POSTGRES_URL=jdbc:postgresql://pgvector:5432/%POSTGRES_DB%"
  )
)

if "%FLYWAY_MYSQL_USER%"=="" set "FLYWAY_MYSQL_USER=root"
if "%FLYWAY_MYSQL_PASSWORD%"=="" set "FLYWAY_MYSQL_PASSWORD=%MYSQL_ROOT_PASSWORD%"
if "%FLYWAY_POSTGRES_USER%"=="" set "FLYWAY_POSTGRES_USER=%POSTGRES_USER%"
if "%FLYWAY_POSTGRES_PASSWORD%"=="" set "FLYWAY_POSTGRES_PASSWORD=%POSTGRES_PASSWORD%"

call :ensure_database_images
if errorlevel 1 exit /b %errorlevel%

if not "%DB_SERVICES%"=="" (
  echo [INFO] Starting database containers:%DB_SERVICES%
  docker compose %COMPOSE_ENV% --profile spring-ai up --build -d %DB_SERVICES%
  if errorlevel 1 exit /b %errorlevel%
  call :wait_for_started_databases
  if errorlevel 1 exit /b %errorlevel%
) else (
  echo [INFO] 未启动 Docker 数据库容器，将迁移已配置的外部数据库。
)

call :run_database_migrations
if errorlevel 1 exit /b %errorlevel%

echo [INFO] 正在使用 Docker 启动 Spring AI 后端。
docker compose %COMPOSE_ENV% --profile spring-ai up --build -d --no-deps spring-ai-backend
if errorlevel 1 exit /b %errorlevel%

echo.
echo [INFO] Spring AI 后端 Docker 服务已启动。
echo [INFO] 本地前端：http://localhost:%FRONTEND_PORT%
echo [INFO] Health: http://localhost:%BACKEND_PORT%/health
echo [INFO] 数据库迁移目录：sql/migrations/mysql 与 sql/migrations/postgresql。
echo.
docker compose %COMPOSE_ENV% ps
echo.
docker compose %COMPOSE_ENV% logs --tail=80 spring-ai-backend
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
set "POSTGRES_DB=resume-builder"
set "POSTGRES_USER=pgvector"
set "POSTGRES_PASSWORD=pgvector"
set "PGVECTOR_PORT=5433"
set "PGVECTOR_DATASOURCE_URL="
set "SPRING_PGVECTOR_DATASOURCE_URL="
set "FLYWAY_MYSQL_URL="
set "FLYWAY_MYSQL_USER="
set "FLYWAY_MYSQL_PASSWORD="
set "FLYWAY_POSTGRES_URL="
set "FLYWAY_POSTGRES_USER="
set "FLYWAY_POSTGRES_PASSWORD="
set "NODE_IMAGE=node:22-alpine"
set "NGINX_IMAGE=nginx:alpine"
set "MAVEN_IMAGE=maven:3.9.9-eclipse-temurin-21"
set "JRE_IMAGE=eclipse-temurin:21-jre-alpine"
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
  if "%%A"=="POSTGRES_DB" set "POSTGRES_DB=%%B"
  if "%%A"=="POSTGRES_USER" set "POSTGRES_USER=%%B"
  if "%%A"=="POSTGRES_PASSWORD" set "POSTGRES_PASSWORD=%%B"
  if "%%A"=="PGVECTOR_PORT" set "PGVECTOR_PORT=%%B"
  if "%%A"=="PGVECTOR_DATASOURCE_URL" set "PGVECTOR_DATASOURCE_URL=%%B"
  if "%%A"=="SPRING_PGVECTOR_DATASOURCE_URL" set "SPRING_PGVECTOR_DATASOURCE_URL=%%B"
  if "%%A"=="FLYWAY_MYSQL_URL" set "FLYWAY_MYSQL_URL=%%B"
  if "%%A"=="FLYWAY_MYSQL_USER" set "FLYWAY_MYSQL_USER=%%B"
  if "%%A"=="FLYWAY_MYSQL_PASSWORD" set "FLYWAY_MYSQL_PASSWORD=%%B"
  if "%%A"=="FLYWAY_POSTGRES_URL" set "FLYWAY_POSTGRES_URL=%%B"
  if "%%A"=="FLYWAY_POSTGRES_USER" set "FLYWAY_POSTGRES_USER=%%B"
  if "%%A"=="FLYWAY_POSTGRES_PASSWORD" set "FLYWAY_POSTGRES_PASSWORD=%%B"
  if "%%A"=="OPENAI_BASE_URL" set "OPENAI_BASE_URL=%%B"
  if "%%A"=="OPENAI_CHAT_BASE_URL" set "OPENAI_CHAT_BASE_URL=%%B"
  if "%%A"=="OPENAI_EMBEDDING_BASE_URL" set "OPENAI_EMBEDDING_BASE_URL=%%B"
  if "%%A"=="OPENAI_VISION_BASE_URL" set "OPENAI_VISION_BASE_URL=%%B"
  if "%%A"=="OPENAI_REALTIME_BASE_URL" set "OPENAI_REALTIME_BASE_URL=%%B"
  if "%%A"=="OLLAMA_EMBEDDING_BASE_URL" set "OLLAMA_EMBEDDING_BASE_URL=%%B"
  if "%%A"=="NODE_IMAGE" set "NODE_IMAGE=%%B"
  if "%%A"=="NGINX_IMAGE" set "NGINX_IMAGE=%%B"
  if "%%A"=="MAVEN_IMAGE" set "MAVEN_IMAGE=%%B"
  if "%%A"=="JRE_IMAGE" set "JRE_IMAGE=%%B"
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
call :normalize_one_url SPRING_PGVECTOR_DATASOURCE_URL
call :normalize_one_url FLYWAY_MYSQL_URL
call :normalize_one_url FLYWAY_POSTGRES_URL
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

:is_compose_mysql_url
call set "CURRENT_VALUE=%%%~1%%"
if "%CURRENT_VALUE%"=="" exit /b 1
if not "%CURRENT_VALUE://mysql:=%"=="%CURRENT_VALUE%" exit /b 0
if not "%CURRENT_VALUE:@mysql:=%"=="%CURRENT_VALUE%" exit /b 0
exit /b 1

:configure_spring_external_postgres_migration
call :is_compose_pgvector_url FLYWAY_POSTGRES_URL
if not errorlevel 1 set "FLYWAY_POSTGRES_URL="
if "%FLYWAY_POSTGRES_URL%"=="" set "FLYWAY_POSTGRES_URL=%SPRING_PGVECTOR_DATASOURCE_URL%"
exit /b 0

:remove_skipped_service
docker compose %COMPOSE_ENV% --profile spring-ai rm -sf %~1 >nul 2>nul
exit /b 0

:disable_pgvector_service
set "PGVECTOR_PROFILE_SPRING_AI=host-pgvector-disabled"
set "PGVECTOR_PROFILE_PYTHON_AI=host-pgvector-disabled"
call :remove_skipped_service pgvector
exit /b 0

:wait_for_started_databases
for %%S in (%DB_SERVICES%) do (
  if "%%S"=="mysql" call :wait_for_healthy resume-builder-mysql 120
  if "%%S"=="pgvector" call :wait_for_healthy resume-builder-pgvector 120
  if errorlevel 1 exit /b 1
)
exit /b 0

:run_database_migrations
if not exist "sql\migrations\mysql" (
  echo [ERROR] 缺少 sql\migrations\mysql 迁移目录。
  exit /b 1
)
if not exist "sql\migrations\postgresql" (
  echo [ERROR] 缺少 sql\migrations\postgresql 迁移目录。
  exit /b 1
)
echo [INFO] 正在构建固定版本的 Flyway 运行镜像。
docker compose %COMPOSE_ENV% --profile migration build flyway-mysql
if errorlevel 1 exit /b 1
echo [INFO] 正在执行 MySQL 版本迁移。
docker compose %COMPOSE_ENV% --profile migration run --rm --no-deps flyway-mysql
if errorlevel 1 exit /b 1
echo [INFO] 正在执行 PostgreSQL 版本迁移。
docker compose %COMPOSE_ENV% --profile migration run --rm --no-deps flyway-pgvector
if errorlevel 1 exit /b 1
echo [INFO] 数据库版本迁移完成。
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
call :ensure_image MAVEN_IMAGE
call :ensure_image JRE_IMAGE
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
