<!-- author: jf -->
# 通用约束摘要

## 仓库约束

- 修改仓库文件前，先读取 `AGENTS.md`、`.workflow/specs/index.md`、`global.md`、本摘要和任务相关 Spec。
- New or modified files must mark author as `jf`; `mapper.xml` is the only documented exception.
- Do not add or modify test code, test fixtures, mocks, `*.test.*`, `*.spec.*`, `tests`, `src/test`, or `__tests__` content.
- Comments and logs in code should be Chinese; identifiers should be English and use normal language conventions.
- Use existing validation commands only when appropriate; do not create temporary project files for validation.

## Frontend

- Frontend work must stay aligned to resume editing, AI resume optimization, AI interview, template preview, and knowledge-base flows.
- Keep code within the existing `src/api`, `src/assets`, `src/components`, `src/config`, `src/constants`, `src/services`, `src/stores`, and `src/templates` structure.
- `api/` defines request boundaries; business orchestration belongs in `services/` or the appropriate state/service layer.
- Visible UI or interaction changes require `npm run lint` and browser-level or equivalent manual interaction verification when the environment supports it; no named browser tool is mandatory.
- Preserve the established product visual language unless a task explicitly changes the design system.

## Spring AI Backend

- `controller/` only adapts HTTP requests and responses; it must not access mappers, data sources, model clients, vector stores, or SQL directly.
- `service/` only contains true `@Service` business orchestration classes.
- Non-business support code belongs in the documented outer directories: `client/`, `vector/`, `embedding/`, `ocr/`, `realtime/`, `parser/`, `chunking/`, `config/`, `exception/`, `cleaner/`, `mapper/`, `entity/`, or `dto/`.
- Java mapper interfaces must be `@Mapper`; custom MySQL SQL belongs in `src/main/resources/mapper/*.xml`.
- Runtime Java code must not hardcode PostgreSQL, MySQL, pgvector, DDL, or business SQL strings.
- Built-in backend prompts sent to AI models must be written in Chinese.

## Python AI Backend

- Preserve the dependency direction `api -> application -> domain <- infrastructure`.
- `api/` handles FastAPI routes, schemas, mappers, and HTTP error adaptation only.
- `application/` contains use cases, shared application services, DTOs, and ports.
- `domain/` contains business models, policies, domain services, and exceptions without FastAPI, database, or SDK dependencies.
- `infrastructure/` contains concrete configuration, persistence, LLM, agent, text, and factory implementations behind application ports.
- Python backend business flows require detailed Chinese process comments covering intent, steps, branches, error handling, outputs, and side effects.
- Built-in Python backend prompts sent to AI models must be written in Chinese.

## Database

- MySQL is the fixed store for AI interview sessions and messages.
- PostgreSQL + pgvector is reserved for RAG vector storage and similarity search.
- Manual database creation SQL belongs in `sql/bootstrap/`; version migrations belong in the matching `sql/migrations/<database>/` directory.
- Application startup must not run project-authored SQL; Docker launchers and CI/CD run version migrations through an independent Flyway container before starting applications.
- Applied migrations are immutable, and production migrations must never execute files under `sql/seeds/`.
- Spring AI `PgVectorStore` must keep schema initialization disabled.

## Workflow

- 修改任务先按复杂度路由，不默认创建 PRD：低风险局部修改和细节优化直接实现并针对性验证；新功能、跨层契约、数据结构、权限安全和高风险任务进入完整 Harness。
- 无法可靠判断是否需要 PRD 时只询问一次；用户选择不创建后直接修改，除非实施中出现新的高风险范围。
- 完整 Harness 使用 Brainstorm、PRD、可选 UI、实现与 Break Loop、Quality Gate、提交 / PR 与可选 Review、Archive；直接修改车道不要求阶段化产物和独立归档。
- Brainstorm 先理解问题，再按相关性读取 `.workflow/specs/`，最后形成决策；禁止为省事全量载入所有 Spec。
- MCP、Skill、CLI、浏览器和人工检查都是可选手段，不得把指定工具作为阶段门禁。
- 可选工具按 `.workflow/lifecycle-plugins.json` 注入；每个 Hook 只加载解析结果中的插件，不全量读取 Skill 或 MCP 说明。
- Bug 修复后只记录可泛化的根因类别、失败原因和预防机制；任务流水不得写入 Spec。
- 完整 Harness 提交前一次性询问提交授权和 Review 选择；直接修改只在用户要求提交或 Review 时询问。
- 完整 Harness 完成后在 `.workflow/archive/` 生成简洁归档；直接修改默认不归档，只有产生稳定经验时才写回最相关的 Spec。
