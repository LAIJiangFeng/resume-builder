<!-- author: jf -->
# 版本化数据库迁移与自动部署

## 1. 背景与问题

当前 GitHub Actions 只拉取代码并重新执行 Docker Compose，没有执行 `sql/` 下的数据库脚本。新服务器或新数据卷虽然会创建数据库，但不会创建登录、简历、面试和 RAG 表；同时现有 SQL 混合了建库、表结构、升级和演示数据，不能安全地在每次部署中全量执行。

## 2. 目标

1. 使用独立 Flyway 容器在部署阶段执行 MySQL 和 PostgreSQL 版本化迁移。
2. 新库自动建立完整结构，已有数据库只执行尚未登记的迁移。
3. 数据库迁移失败时阻止新版本应用部署，并保留原有应用容器。
4. 将建库、版本迁移和本地演示数据按用途分目录存放。
5. 保持 Spring AI `PgVectorStore.initializeSchema(false)`，禁止应用启动自动建表。

## 3. 范围

1. 调整 `sql/` 目录结构和现有 SQL 文件。
2. 在 Docker Compose 中增加 MySQL 与 PostgreSQL Flyway 迁移服务。
3. 增加服务器数据库迁移脚本，并接入 GitHub Actions 部署流程。
4. 调整 Windows Docker 启动脚本，使其使用相同的版本化迁移入口。
5. 更新数据库 Spec、后端 Spec、README 和环境变量示例。

## 4. 非目标

1. 不在 Spring AI 或 Python AI 应用启动过程中执行项目 SQL。
2. 不自动执行演示账号、测试数据或破坏性清理脚本。
3. 不自动回滚已执行的数据库 DDL；失败后采用修复迁移继续前进。
4. 不修改业务接口、前端交互或数据库访问代码。
5. 本任务不直接操作生产数据库。

## 5. 决策记录

1. Flyway 固定使用经过验证的镜像版本，不能使用浮动 `latest` 标签。
2. 迁移目录固定为 `sql/migrations/mysql/` 与 `sql/migrations/postgresql/`。
3. 迁移文件使用 `V<日期><序号>__<英文描述>.sql`，已执行文件禁止修改。
4. 建库脚本放入 `sql/bootstrap/`，不进入 Flyway。
5. 演示数据放入 `sql/seeds/`，生产部署不执行。
6. 已有非空数据库使用 `baselineVersion=0`，随后执行全部兼容迁移。
7. 初始迁移必须兼容新库与当前旧库，缺失字段和索引通过条件 DDL 补齐。
8. 部署先启动数据库、执行迁移，再更新应用；迁移失败时不执行应用更新。
9. 部署不再预先执行 `docker compose down`，避免迁移失败造成已有服务被提前停止。

## 6. SQL 目录

```text
sql/
├─ README.md
├─ bootstrap/
│  ├─ mysql_database_schema.sql
│  └─ create_pgvector_resume_builder_database.sql
├─ migrations/
│  ├─ mysql/
│  │  ├─ V2026082301__create_auth_tables.sql
│  │  ├─ V2026082302__create_interview_tables.sql
│  │  ├─ V2026082303__create_user_resume_table.sql
│  │  └─ V2026082304__optimize_user_resume_sort_index.sql
│  └─ postgresql/
│     └─ V2026082301__create_rag_schema.sql
└─ seeds/
   └─ mysql/
      └─ local_demo_users.sql
```

## 7. 部署流程

1. GitHub Actions 完成前端构建检查。
2. 服务器拉取最新 `main`。
3. 启动 Compose 管理的 MySQL 和 pgvector，并等待健康状态。
4. 在服务器本地保存数据库备份并按保留天数清理旧备份。
5. Flyway 分别执行 MySQL 和 PostgreSQL 待处理迁移。
6. 迁移成功后构建并更新 Spring AI 与前端容器。
7. 输出 Compose 状态并检查 Spring AI 容器健康状态。

## 8. 任务清单

- [已完成] 建立功能分支和 PRD。
- [已完成] 重构 SQL 目录并拆分生产结构与演示数据。
- [已完成] 将旧库升级脚本改为可重复判断的版本迁移。
- [已完成] 增加 Flyway Compose 服务和环境变量。
- [已完成] 增加部署迁移脚本并接入 GitHub Actions。
- [已完成] 更新 Windows Docker 启动脚本。
- [已完成] 更新 Spec、README 和后端说明。
- [已完成] 完成新库、旧库、重复执行和失败门禁验证。

## 9. 验收标准

1. 全新 MySQL 数据卷迁移后存在账号、邮箱验证码、简历、面试会话和面试消息表。
2. 全新 PostgreSQL 数据卷迁移后存在 `vector`、`pgcrypto` 扩展和 `rag_document_chunks` 表。
3. 模拟旧 MySQL 结构迁移后补齐 `user_id` 和新版简历排序索引。
4. 同一迁移连续执行两次时，第二次显示无待执行迁移且结构不重复。
5. Flyway 历史表记录每个版本及校验和，修改已执行迁移时验证失败。
6. 生产迁移不会插入或覆盖 `admin-001`、`user-001` 演示账号。
7. 任一迁移失败时部署脚本返回非零，且不会继续更新应用容器。
8. GitHub Actions 不再直接 `docker compose down` 后无条件启动全部服务。
9. Windows Docker 启动脚本与 CI/CD 使用同一迁移目录和 Flyway 服务。
10. README 和 Spec 不再引用旧的根目录 SQL 路径。

## 10. 验证计划

1. 使用临时 Docker 容器和独立数据卷验证 MySQL 与 PostgreSQL 全新迁移。
2. 使用一次性命令构造旧版 MySQL 表结构，再运行迁移并查询字段和索引。
3. 重复执行 Flyway `migrate` 并读取 `flyway_schema_history`。
4. 使用临时修改副本验证校验和与失败门禁，不修改仓库测试代码。
5. 执行 Docker Compose 配置解析、Shell 语法检查、Batch 静态检查和 `git diff --check`。
6. 执行 `npm run build`，确认部署相关调整未破坏现有前端构建。

## 11. 风险与回滚

1. MySQL DDL 不能保证事务回滚，迁移必须保持可恢复和向前修复。
2. 破坏性字段调整采用扩展、兼容发布、收缩三阶段，禁止与依赖新结构的代码同批直接删除旧结构。
3. 数据库备份只用于人工恢复，不在 CI/CD 中自动覆盖生产数据库。
4. 外部数据库必须显式配置 Flyway URL；未配置时不得误连 Compose 默认数据库。
5. 实施失败时只回退本分支文件，不操作生产数据库和现有数据卷。

## 12. 当前状态

- 分支：`feat/versioned-database-migrations`。
- UI 设计：不适用。
- 数据库执行：未执行生产数据库；已使用独立临时容器验证全新与旧版数据库迁移。
- 本地执行边界：一次 WSL 环境变量门禁验证误触发默认 Compose 数据库迁移；MySQL 迁移前为空库，pgvector 的 RAG 表为 0 行，迁移前备份保存在仓库同级 `resume-builder-database-backups/`，本次启动的 MySQL 容器已移除。
- Code Review：用户选择跳过；提交、推送和 PR 已执行，PR 为 `#27`。

## 13. 最终验收结果

1. 全新 MySQL：通过，5 张业务表和 4 条成功迁移记录均存在。
2. 全新 PostgreSQL：通过，`vector`、`pgcrypto`、RAG 表和迁移记录均存在。
3. 旧 MySQL 升级：通过，建立 `0` 版本基线，补齐 `user_id`、邮箱长度和新版排序索引，旧简历数据保留。
4. 重复执行：通过，MySQL 与 PostgreSQL 第二次均显示无待执行迁移。
5. 校验和防篡改：通过，修改临时副本后 `validate` 返回校验和不一致。
6. 演示数据隔离：通过，全新生产迁移后 `admin-001` 与 `user-001` 账号数量为 0。
7. 失败门禁：通过，部署脚本使用严格错误退出，外部数据库 URL 配置错误返回非零，工作流只在迁移脚本成功后更新应用。
8. CI/CD 顺序：通过，部署前不再执行 `docker compose down`。
9. Windows 启动脚本：通过静态控制流检查，均调用相同 Flyway 服务和迁移目录；未端到端执行，避免停止当前本地套件。
10. 文档与规范：通过，已清除旧根目录 SQL 路径。
11. 静态与构建：`docker compose config`、ShellCheck、Actionlint、`npm run build`、`git diff --check` 均通过。
12. 数据库客户端：本机未安装 `usql`，隔离验证改用临时数据库容器自带客户端完成。
