<!-- author: jf -->
# 版本化数据库迁移归档

## 产物

- PRD：`docs/requirements/2026-08-22-versioned-database-migrations.md`
- SQL：`sql/bootstrap/`、`sql/migrations/`、`sql/seeds/`
- 部署入口：`scripts/deploy-database-migrations.sh`
- UI 设计：不适用

## 实现结果

- 使用固定版本 Flyway 镜像和独立 `migration` profile 管理 MySQL、PostgreSQL 迁移。
- CI/CD 在备份和迁移成功后才更新应用，不再预先停止现有应用。
- Windows Docker 启动脚本使用相同迁移服务；生产迁移与本地演示数据隔离。
- 数据库、Spring 后端和通用规范已切换为版本化迁移规则。

## Quality Gate

- 通过：全新 MySQL、全新 PostgreSQL、旧 MySQL 基线升级、重复执行、校验和、防演示数据写入和备份命令验证。
- 通过：Compose 解析、Flyway 镜像构建、ShellCheck、Actionlint、前端构建、作者标记和差异检查。
- 未执行：Windows 一键脚本端到端启动，原因是脚本会停止当前本地 Compose 套件；已完成标签、调用链和 Compose 入口静态检查。
- 未执行：生产数据库迁移和生产部署。
- 工具降级：本机没有 `usql`，隔离验证使用临时容器自带数据库客户端。

## 执行边界

- 一次 WSL 环境变量门禁验证误触发默认本地 Compose 数据库迁移；MySQL 迁移前为空库，pgvector RAG 表为 0 行。
- 迁移前备份保存在仓库同级 `resume-builder-database-backups/`；本次启动的 MySQL 容器已停止并移除，既有数据卷未删除。

## Break Loop

不适用，本任务为版本化迁移能力建设，不是缺陷修复。

## Git 状态

- 分支：`feat/versioned-database-migrations`
- Code Review：用户选择跳过。
- commit、push：已执行，功能提交为 `0f02b1a`。
- PR：`#27`，`https://github.com/LAIJiangFeng/resume-builder/pull/27`。

## Spec 回写

- `.workflow/specs/database.md`
- `.workflow/specs/conventions.md`
- `.workflow/specs/spring-ai-backend.md`
- `.workflow/specs/learnings.md`
