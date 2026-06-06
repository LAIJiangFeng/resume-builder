<!-- author: jf -->
# AI 执行入口

本文件只保留仓库协作入口和必要限制；具体细则以 `.rules/` 下规则文档为准。

## 必须遵守

1. 对话必须使用中文。
2. 处理本仓库任务前，必须先阅读并遵守 `.rules/` 下与任务相关的规则文档。
3. `.rules/` 下新增规则默认同样属于仓库级强制规则；如规则索引未及时更新，也不得绕过。
4. 新增或修改文件时，除 `mapper.xml` 外必须标记作者为 `jf`，且禁止出现作者为 `ai` 的标识。
5. 新增或修改代码中的注释必须使用中文。
6. 禁止新增或修改测试代码、测试脚本、fixture 或 mock 文件，详见 `.rules/testing-rules.md`。
7. 修改或设计 UI 界面时，优先使用 `UI-Ux-Pro-Max` Skill，第二选择才是 `Frontend Design` Skill，详见 `.rules/frontend-mandatory-rules.md`。

## Harness 触发门禁

1. 用户要求新增、修改、修复、优化或调整功能时，默认必须触发 Harness 流程；典型说法包括“改功能”“加功能”“修一下”“优化一下”“调整页面”“接接口”“改接口”“改存储”“改提示词”。
2. 触发 Harness 后，禁止直接进入代码修改；必须先读取 `.rules/harness-mcp-workflow-rules.md`，输出任务拆分、验收细节和需求文档安排。
3. 涉及前端、后端、数据库、OpenAI、PR / Issue / Review 或 UI 的任务，还必须同步读取对应专项规则。
4. 用户明确要求“不走 Harness”或“只做一次性小改”时，仍必须说明跳过原因，并保留必要的验证说明。

## Rules 索引

| 规则文件 | 作用 | 什么时候用 |
| --- | --- | --- |
| `.rules/global-rules.md` | 定义中文交互、任务执行边界、Git、数据库访问工具和全局优先级。 | 所有任务默认读取，尤其是涉及执行方式、分支、提交或数据库操作时。 |
| `.rules/git-rules.md` | 定义 Git 分支英文命名、分支前缀、提交信息和提交说明 Markdown 文档规范。 | 创建分支、准备提交、编写提交说明文档、处理 PR 或版本控制协作时读取。 |
| `.rules/code-conventions.md` | 定义通用代码规范、命名、翻译文本、安全、性能、文档维护和测试策略边界。 | 涉及代码、文案、提示文本、接口命名、文档维护或质量收尾时读取。 |
| `.rules/testing-rules.md` | 定义测试代码禁令、允许验证方式、前后端验证边界和交付验证说明。 | 所有新增、修改、修复、重构、规则调整、提交前检查和验证任务都要读取。 |
| `.rules/database-rules.md` | 定义 MySQL、PostgreSQL、pgvector、Mapper SQL、一次性 SQL、会话存储和数据库访问工具规则。 | 涉及数据库、SQL、Mapper、`sql/`、pgvector、RAG 向量表或 AI 面试会话存储时读取。 |
| `.rules/frontend-mandatory-rules.md` | 定义前端产品目标、目录边界、UI 设计、API / Service 分层和前端验证要求。 | 修改 `src/` 下页面、组件、模板、样式、服务、接口或状态管理时读取。 |
| `.rules/backend-mandatory-rules.md` | 定义后端通用产品目标、目录扩展、文件职责、分层边界和后端协作要求。 | 涉及 `python-ai-backend/`、`spring-ai-backend/`、后端接口、AI 能力编排或目录调整时读取。 |
| `.rules/python-ai-backend-mandatory-rules.md` | 定义 `python-ai-backend/` 的分层架构、依赖方向、业务链路、流程注释和内置提示词语言要求。 | 修改 Python AI 后端接口、用例、领域、基础设施、RAG、音频、Realtime 或提示词时读取。 |
| `.rules/spring-ai-backend-mandatory-rules.md` | 定义 `spring-ai-backend/` 的目录职责、Spring AI 分层、SQL 存放、pgvector、Mapper 和内置提示词要求。 | 修改 Java AI 后端、Spring AI、Mapper、`mapper.xml`、`sql/`、pgvector、RAG、面试会话或 Realtime 时读取。 |
| `.rules/harness-mcp-workflow-rules.md` | 定义 Harness 与 MCP 使用顺序、新功能拆分、验收细节、需求文档、Playwright / GitHub / OpenAI 文档使用边界。 | 涉及新功能、行为变更、多步骤优化、OpenAI 能力、前端交互验证、PR / Issue / Review 或知识回写时读取。 |
| `.rules/code-review-rules.md` | 定义提交前 `code-review` 询问、执行、修复确认和 `code-review-fix` 边界。 | 准备提交、处理代码审查、修复审查问题或用户要求 review 时读取。 |

## 协作参考

- `docs/harness-engineering-workflow.md`：仓库级 Harness Engineering 工作流，适用于任务路由、知识回写、熵治理与跨前后端协作。
