<!-- author: jf -->
# Resume Builder 轻量 Harness Engineering 工作流

## 1. 目标

本工作流用最少必要上下文完成需求到归档的闭环。它约束交付结果，不绑定 MCP、Skill 或单一工具。

核心目标：

1. 先判断任务复杂度，简单修改直接处理，复杂任务再写 PRD 和代码。
2. 以仓库事实、验收证据和跨层数据流保证质量。
3. 用 Break Loop 阻止同类 Bug 在“修复、遗忘、复发”之间循环。
4. 将稳定经验写回 Spec，将任务产物统一归档。
5. 减少重复提问、重复长清单和无收益的工具调用。

具体强制规范以 `.workflow/specs/harness-lifecycle.md` 为准，任务路由以 `.workflow/specs/index.md` 为准。

## 2. 生命周期总览

```text
任务请求
    -> 直接修改：相关 Spec -> Implement -> 针对性验证 -> 交付
    -> 无法判断：询问一次是否创建 PRD
    -> 完整 Harness：Brainstorm -> PRD -> UI（可选）
                    -> Implement + Break Loop（Bug 修复时）
                    -> Quality Gate -> Submit / Review -> Archive + Spec
```

| 阶段 | 核心输入 | 最小输出 | 默认是否需要用户确认 |
| --- | --- | --- | --- |
| Route | 用户目标、影响面和风险 | 直接修改 / 询问 / 完整 Harness | 只有无法可靠判断时需要 |
| Brainstorm | 完整 Harness 的用户目标、现有实现、相关 Spec | 决策快照 | 只有关键歧义时需要 |
| PRD | 完整 Harness 的决策快照 | 范围、任务、验收、验证计划 | 需求清晰时自动进入实现 |
| UI | PRD 与现有设计系统 | 初步结构、状态、交互 | 可选阶段 |
| Implement | PRD 或直接修改记录、代码和规则 | 最小可维护实现 | 范围变化时需要 |
| Quality Gate | PRD 或直接修改记录、Spec、diff | 与风险匹配的验证证据 | 不需要 |
| Submit / Review | 质量结果、Git 状态 | 用户授权后的 Git / PR / Review 状态 | 完整 Harness 或用户要求时选择 |
| Archive | 完整 Harness 的全部实际结果 | 归档摘要与 Spec 条目 | 不需要 |

路由标准：

1. 文案、样式细节、局部交互、明确小修复、配置和文档校正通常直接修改。
2. 新功能、跨层契约、数据结构、权限安全、支付、复杂状态和高风险外部操作进入完整 Harness。
3. 介于两者之间时只询问一次是否创建 PRD；用户选择不创建后不得重复追问。
4. 直接修改实施中出现高风险扩展时暂停，并询问是否升级为 PRD。

## 3. 上下文装载顺序

默认只加载完成当前阶段所需的上下文：

1. `AGENTS.md`。
2. `.workflow/specs/index.md`、通用 Spec 和任务直接相关的专项 Spec。
3. 相关 README、目录和最小必要代码。
4. Brainstorm 已形成初步问题后，读取 `.workflow/specs/conventions.md` 和相关 Spec。
5. 进入实现后，以 PRD 或直接修改记录和当前 diff 为主，不重复加载无关背景。

完整 Harness 在 Brainstorm 中途读取 `.workflow/specs/`：先理解用户问题，再用 Spec 校正规范和历史经验，最后形成决策。直接修改车道只读取通用和任务相关 Spec，不创建 PRD 占位文档。

## 4. 任务车道

每个任务只选一个主车道；跨栈任务仍要确定源头层和适配层。

| 车道 | 主要目录 | 重点边界 |
| --- | --- | --- |
| 文档与规范 | `AGENTS.md`、`.workflow/specs/`、`docs/` | 单一入口、引用一致、避免重复规范 |
| 前端 | `src/api/`、`src/services/`、`src/stores/`、`src/components/` | API 定义、业务编排、状态和展示职责分离 |
| Python AI 后端 | `python-ai-backend/app/` | `api -> application -> domain <- infrastructure` |
| Spring AI 后端 | `spring-ai-backend/`、`sql/` | `controller -> service -> mapper`，业务 SQL 进 `mapper.xml` |
| 跨栈 | 前端与一个或两个后端 | 从字段、权限、错误和状态契约开始追踪 |

## 5. Break Loop 操作卡

只有修复 Bug、同类问题复发或修复尝试失败时填写：

```md
## Break Loop

- 根因类别：
- 触发条件与影响：
- 之前为什么没有修好：不适用 / 具体原因
- 本次如何修到根因：
- 验证证据：
- 预防机制：
- Spec 回写位置：
```

复盘重点是机制，不是过程流水账。只有能约束未来任务的结论才进入 `.workflow/specs/`。

## 6. Quality Gate 操作卡

完整 Harness 的质量检查覆盖以下适用维度，并为每项记录 `通过`、`不通过` 或 `未执行`。直接修改车道只执行与改动风险相关的必要检查，不输出无关维度的占位结果：

1. PRD 或直接修改记录、验收和非目标符合性。
2. diff 范围、语法、格式、静态检查、安全和错误处理。
3. 类型检查、编译或构建。
4. 仓库已有且规则允许的测试、手工或一次性验证。
5. 前端到后端、业务层、存储和回显的跨层数据流。
6. 现有组件、Service、DTO、Mapper、校验和常量复用。
7. 命名、接口、配置、双后端、文档和交互一致性。
8. 长会话中 PRD 或直接修改记录、Spec 与当前 diff 的漂移检查。

本仓库禁止新增或修改测试代码。Quality Gate 中的“测试”必须遵守 `.workflow/specs/testing.md`。

## 7. 工具选择

工具选择只回答一个问题：它是否能以合理成本提供当前阶段缺失的事实或证据。

可插拔工具统一注册在 `.workflow/lifecycle-plugins.json`。进入标准 Hook 时使用 `.workflow/scripts/resolve-lifecycle-plugins.ps1` 按任务标签、显式选择和授权解析，只加载返回的 Skill 入口或 MCP provider，具体协议见 `.workflow/specs/lifecycle-plugins.md`。

1. UI 阶段可按需使用设计类 Skill、MCP、浏览器、图片工具或现有设计系统。
2. 外部 API 和时效性事实可使用官方文档、可靠本地依赖信息或合适的文档工具。
3. 页面验证可使用任意可用浏览器工具或人工环境，不绑定 Playwright。
4. PR 与远程状态可使用 GitHub 工具、CLI 或本地加远程证据组合。
5. Code Review 可使用仓库 Skill、其他审查工具或直接审查。

工具不可用不是自动失败；必要证据缺失才是未完成风险。

## 8. 提交与 Review

完整 Harness 的 Quality Gate 后一次性向用户确认。直接修改车道只有在用户要求提交、推送、PR 或 Review 时才询问：

1. 是否授权 commit、push 和创建 PR，以及具体范围。
2. 是否跳过 Review、仅 Review，或 Review 后按预授权严重级别修复。

Review 修复后重跑受影响的 Quality Gate。未经授权不得执行远程操作，也不得把 Review Skill 当成强制门禁。

## 9. 归档与 Spec

完整 Harness 完成后创建 `.workflow/archive/YYYY-MM-DD-<topic>/summary.md`，记录 PRD / 设计路径、实现范围、质量证据、Break Loop、Review、Git / PR 状态和残余风险。直接修改车道默认不创建独立归档。

为了降低重复和 Token 消耗：

1. 权威 PRD 和设计文档保留原位，归档只引用路径。
2. 临时分析、质量和 Review 产物需要保留时放入归档目录。
3. `.workflow/specs/` 只保存可泛化的适用条件、机制和预防方式。
4. 对话结尾只报告关键结果，不重新粘贴 PRD 或完整归档。

## 10. 项目完成定义

1. 实际改动与 PRD 或轻量任务记录一致。
2. 必要验收和 Quality Gate 已通过，未执行项已披露。
3. Bug 修复已在触发时完成 Break Loop。
4. 完整 Harness 中用户已决定是否 Review；直接修改仅在用户要求时询问。Git / PR 操作均有明确授权。
5. 完整 Harness 已生成归档摘要；直接修改仅在用户要求或存在需保留产物时归档。可复用经验按适用条件写入 Spec。
