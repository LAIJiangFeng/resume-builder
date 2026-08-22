<!-- author: jf -->
# 数据库脚本

## 目录规则

- `bootstrap/`：手工建库脚本，不进入自动迁移。
- `migrations/mysql/`：MySQL Flyway 版本迁移。
- `migrations/postgresql/`：PostgreSQL + pgvector Flyway 版本迁移。
- `seeds/`：仅供本地开发手工执行的演示数据，生产部署禁止执行。

## 迁移规则

1. 新迁移使用 `V<日期><序号>__<英文描述>.sql` 命名。
2. 已经部署的迁移文件禁止修改，只能新增更高版本。
3. 迁移必须兼容重复部署和已有数据库，不得写入演示账号或测试数据。
4. 应用启动不执行这些 SQL，Docker 启动脚本和 CI/CD 通过独立 Flyway 容器执行。
5. MySQL 和 PostgreSQL 分别维护自己的 `flyway_schema_history`。

## 手工执行迁移

在仓库根目录执行：

```powershell
docker compose --profile spring-ai up -d mysql pgvector
docker compose --profile migration build flyway-mysql
docker compose --profile migration run --rm --no-deps flyway-mysql
docker compose --profile migration run --rm --no-deps flyway-pgvector
```

服务器部署使用 `scripts/deploy-database-migrations.sh`，该脚本会在迁移前备份 Compose 管理的数据库。

## 本地演示账号

需要演示账号时，在完成 MySQL 迁移后手工执行：

```powershell
Get-Content -Raw sql\seeds\mysql\local_demo_users.sql | docker compose exec -T mysql sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"'
```

生产环境禁止执行该脚本。
