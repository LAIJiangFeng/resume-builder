<!-- author: jf -->
# Spec 索引

`.workflow/specs/` 是本仓库唯一的长期规范目录。任务采用渐进读取，不得默认把全部 Spec 放入上下文。

## 必读顺序

所有仓库任务先读取：

1. `AGENTS.md`
2. `.workflow/specs/index.md`
3. `.workflow/specs/global.md`
4. `.workflow/specs/conventions.md`

随后只读取与当前任务匹配的专项 Spec。

## 任务路由

| Spec | 适用场景 |
| --- | --- |
| `harness-lifecycle.md` | 变更任务复杂度路由、直接修改、新功能、跨层优化、Bug 修复、提交 / PR / Review 或知识回写 |
| `lifecycle-plugins.md` | 注册、选择或调用 MCP、Skill 以及扩展生命周期 Hook |
| `code-conventions.md` | 代码、文案、提示文本、接口命名、文档维护或质量收尾 |
| `testing.md` | 任何新增、修改、修复、重构、规则调整和交付验证 |
| `git.md` | 分支、提交、提交说明、推送、PR 和版本控制协作 |
| `code-review.md` | 代码审查、审查结果修复或提交前 Review 选择 |
| `database.md` | 数据库、SQL、Mapper、pgvector、RAG 向量表或面试会话存储 |
| `frontend.md` | `src/` 下页面、组件、模板、样式、API、Service 或状态管理 |
| `backend.md` | 任一后端接口、AI 编排、目录职责或跨后端协作 |
| `python-ai-backend.md` | `python-ai-backend/` 的接口、用例、领域、基础设施、RAG、音频、Realtime 或提示词 |
| `spring-ai-backend.md` | `spring-ai-backend/`、Spring AI、Mapper、SQL、pgvector、RAG、会话或 Realtime |
| `learnings.md` | Brainstorm 中检索与当前问题同类的历史经验；完成后写入可泛化经验 |

## 组合规则

1. 前端任务读取 `harness-lifecycle.md`、`code-conventions.md`、`testing.md` 和 `frontend.md`。
2. Python 后端任务读取 `harness-lifecycle.md`、`code-conventions.md`、`testing.md`、`backend.md` 和 `python-ai-backend.md`。
3. Spring 后端任务读取 `harness-lifecycle.md`、`code-conventions.md`、`testing.md`、`backend.md` 和 `spring-ai-backend.md`。
4. 数据库或 SQL 任务在对应技术栈组合上增加 `database.md`。
5. 提交或 Review 任务增加 `git.md` 和 `code-review.md`。
6. 跨栈任务只组合实际涉及的专项 Spec，并先确认源头层与适配层。
7. 任一阶段需要 MCP 或 Skill 时增加 `lifecycle-plugins.md`，按注册表解析，不全量读取插件说明。

## 维护边界

1. 稳定、可复用的规范写入最接近业务或技术边界的 Spec。
2. 一次性任务事实、日志、临时路径和执行流水不得写入 Spec。
3. 新增 Spec 时必须补充本索引；调整现有规范时同步检查 `AGENTS.md` 和相关交叉引用。
4. `.rules/` 不再使用，也不得重新创建为平行规范入口。
