#!/usr/bin/env bash
# author: jf

set -Eeuo pipefail
umask 077

REPOSITORY_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPOSITORY_ROOT"

read_dotenv_value() {
  local key="$1"

  [[ -f .env ]] || return 0
  awk -v key="$key" '
    index($0, key "=") == 1 {
      sub("^[^=]*=", "")
      sub("\\r$", "")
      print
      exit
    }
  ' .env
}

load_setting() {
  local name="$1"
  local default_value="$2"
  local value="${!name-}"

  if [[ -z "$value" ]]; then
    value="$(read_dotenv_value "$name")"
  fi

  if [[ "$value" == \"*\" && "$value" == *\" ]]; then
    value="${value:1:${#value}-2}"
  elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
    value="${value:1:${#value}-2}"
  fi

  printf -v "$name" '%s' "${value:-$default_value}"
}

require_boolean() {
  local name="$1"
  local value="${!name}"

  case "$value" in
    true|false) ;;
    *)
      echo "[错误] $name 只能设置为 true 或 false。" >&2
      exit 1
      ;;
  esac
}

wait_for_healthy() {
  local service="$1"
  local container_id
  local health_status
  local elapsed=0

  container_id="$(docker compose --profile "$DEPLOY_PROFILE" ps -q "$service")"
  if [[ -z "$container_id" ]]; then
    echo "[错误] 未找到数据库服务容器：$service。" >&2
    return 1
  fi

  while (( elapsed < MIGRATION_WAIT_TIMEOUT_SECONDS )); do
    health_status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_id")"
    case "$health_status" in
      healthy|running)
        echo "[信息] 数据库服务已就绪：$service。"
        return 0
        ;;
      unhealthy|exited|dead)
        echo "[错误] 数据库服务状态异常：$service=$health_status。" >&2
        return 1
        ;;
    esac
    sleep 2
    elapsed=$((elapsed + 2))
  done

  echo "[错误] 等待数据库服务超时：$service。" >&2
  return 1
}

backup_mysql() {
  local target="$DATABASE_BACKUP_DIR/mysql-$BACKUP_TIMESTAMP.sql.gz"
  local temporary="$target.tmp"

  echo "[信息] 正在备份 MySQL。"
  docker compose --profile "$DEPLOY_PROFILE" exec -T mysql sh -c \
    'exec mysqldump --single-transaction --quick --routines --triggers --events --no-tablespaces --set-gtid-purged=OFF -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' \
    | gzip -c > "$temporary"
  mv "$temporary" "$target"
  echo "[信息] MySQL 备份已保存：$target。"
}

backup_postgresql() {
  local target="$DATABASE_BACKUP_DIR/postgresql-$BACKUP_TIMESTAMP.dump"
  local temporary="$target.tmp"

  echo "[信息] 正在备份 PostgreSQL。"
  docker compose --profile "$DEPLOY_PROFILE" exec -T pgvector sh -c \
    'PGPASSWORD="$POSTGRES_PASSWORD" exec pg_dump --format=custom --no-owner --no-privileges --username="$POSTGRES_USER" "$POSTGRES_DB"' \
    > "$temporary"
  mv "$temporary" "$target"
  echo "[信息] PostgreSQL 备份已保存：$target。"
}

load_setting DEPLOY_PROFILE spring-ai
load_setting MIGRATION_MANAGED_MYSQL true
load_setting MIGRATION_MANAGED_POSTGRESQL true
load_setting DATABASE_BACKUP_ENABLED true
load_setting DATABASE_BACKUP_DIR ../resume-builder-database-backups
load_setting DATABASE_BACKUP_RETENTION_DAYS 14
load_setting MIGRATION_WAIT_TIMEOUT_SECONDS 180

require_boolean MIGRATION_MANAGED_MYSQL
require_boolean MIGRATION_MANAGED_POSTGRESQL
require_boolean DATABASE_BACKUP_ENABLED

if ! [[ "$DATABASE_BACKUP_RETENTION_DAYS" =~ ^[0-9]+$ ]]; then
  echo "[错误] DATABASE_BACKUP_RETENTION_DAYS 必须是非负整数。" >&2
  exit 1
fi

if ! [[ "$MIGRATION_WAIT_TIMEOUT_SECONDS" =~ ^[1-9][0-9]*$ ]]; then
  echo "[错误] MIGRATION_WAIT_TIMEOUT_SECONDS 必须是正整数。" >&2
  exit 1
fi

MYSQL_MIGRATION_URL="${FLYWAY_MYSQL_URL-}"
POSTGRES_MIGRATION_URL="${FLYWAY_POSTGRES_URL-}"
if [[ -z "$MYSQL_MIGRATION_URL" ]]; then
  MYSQL_MIGRATION_URL="$(read_dotenv_value FLYWAY_MYSQL_URL)"
fi
if [[ -z "$POSTGRES_MIGRATION_URL" ]]; then
  POSTGRES_MIGRATION_URL="$(read_dotenv_value FLYWAY_POSTGRES_URL)"
fi

if [[ "$MIGRATION_MANAGED_MYSQL" == false && ( -z "$MYSQL_MIGRATION_URL" || "$MYSQL_MIGRATION_URL" == *"//mysql:"* ) ]]; then
  echo "[错误] 外部 MySQL 必须显式配置不指向默认 mysql 服务的 FLYWAY_MYSQL_URL。" >&2
  exit 1
fi

if [[ "$MIGRATION_MANAGED_POSTGRESQL" == false && ( -z "$POSTGRES_MIGRATION_URL" || "$POSTGRES_MIGRATION_URL" == *"//pgvector:"* ) ]]; then
  echo "[错误] 外部 PostgreSQL 必须显式配置不指向默认 pgvector 服务的 FLYWAY_POSTGRES_URL。" >&2
  exit 1
fi

if [[ "$DATABASE_BACKUP_ENABLED" == true && ( "$MIGRATION_MANAGED_MYSQL" == false || "$MIGRATION_MANAGED_POSTGRESQL" == false ) ]]; then
  echo "[错误] 自动备份只支持 Compose 管理的数据库；外部数据库需先独立备份并显式关闭 DATABASE_BACKUP_ENABLED。" >&2
  exit 1
fi

trap 'echo "[错误] 数据库迁移失败，应用容器未更新。" >&2' ERR

database_services=()
if [[ "$MIGRATION_MANAGED_MYSQL" == true ]]; then
  database_services+=(mysql)
fi
if [[ "$MIGRATION_MANAGED_POSTGRESQL" == true ]]; then
  database_services+=(pgvector)
fi

if (( ${#database_services[@]} > 0 )); then
  echo "[信息] 正在启动数据库服务：${database_services[*]}。"
  docker compose --profile "$DEPLOY_PROFILE" up -d "${database_services[@]}"
fi

if [[ "$MIGRATION_MANAGED_MYSQL" == true ]]; then
  wait_for_healthy mysql
fi
if [[ "$MIGRATION_MANAGED_POSTGRESQL" == true ]]; then
  wait_for_healthy pgvector
fi

if [[ "$DATABASE_BACKUP_ENABLED" == true ]]; then
  BACKUP_TIMESTAMP="$(date '+%Y%m%d-%H%M%S')"
  mkdir -p "$DATABASE_BACKUP_DIR"
  backup_mysql
  backup_postgresql
  find "$DATABASE_BACKUP_DIR" -maxdepth 1 -type f \
    \( -name 'mysql-*.sql.gz' -o -name 'postgresql-*.dump' \) \
    -mtime "+$DATABASE_BACKUP_RETENTION_DAYS" -delete
else
  echo "[警告] 已显式关闭数据库自动备份。"
fi

echo "[信息] 正在构建固定版本的 Flyway 运行镜像。"
docker compose --profile migration build flyway-mysql

echo "[信息] 正在执行 MySQL 版本迁移。"
docker compose --profile migration run --rm --no-deps flyway-mysql

echo "[信息] 正在执行 PostgreSQL 版本迁移。"
docker compose --profile migration run --rm --no-deps flyway-pgvector

echo "[信息] 数据库版本迁移全部完成。"
