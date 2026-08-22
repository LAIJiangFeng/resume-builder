<!-- author: jf -->
# AI 执行入口

本文件只保留仓库协作入口和必要限制；完整规范统一存放在 `.workflow/specs/`。

## 必须遵守

1. 对话必须使用中文。
2. 处理本仓库任务前，必须先读取 `.workflow/specs/index.md`、`.workflow/specs/global.md` 和 `.workflow/specs/conventions.md`，再按索引读取与任务相关的 Spec。
3. `.workflow/specs/` 下新增规范默认同样属于仓库级强制规范；如索引未及时更新，也不得绕过。
4. 新增或修改文件时，除 `mapper.xml` 外必须标记作者为 `jf`，且禁止出现作者为 `ai` 的标识。
5. 新增或修改代码中的注释必须使用中文。
6. 禁止新增或修改测试代码、测试脚本、fixture 或 mock 文件，详见 `.workflow/specs/testing.md`。
7. 修改或设计 UI 界面时，先遵守现有设计系统和 `.workflow/specs/frontend.md`；设计类 Skill、MCP 或其他工具仅按需选用，不得作为强制前置门禁。

## Harness 路由门禁

1. 用户要求新增、修改、修复、优化或调整功能时，先按 `.workflow/specs/harness-lifecycle.md` 判断走“直接修改”还是“完整 Harness”，不得默认强制创建 PRD。
2. 目标、范围和验收清晰，且属于低风险、可回退的局部修改或细节优化时，直接读取相关 Spec、修改并执行针对性验证；不创建 PRD，不要求输出完整阶段文档。
3. 新功能、跨模块或跨层契约、数据库结构、权限安全、高风险状态流程、范围不清或用户明确要求 PRD 时，进入完整 Harness，经过 Brainstorm 后生成包含验收标准的 PRD。
4. 无法可靠判断复杂度，或直接修改与完整 Harness 都合理时，只询问一次用户是否创建 PRD；优先使用可用的弹窗选项，用户选择“不创建”后直接修改，不得重复追问。
5. 涉及前端、后端、数据库、OpenAI、PR / Issue / Review 或 UI 的任务，仍需读取对应专项 Spec；跳过 PRD 不等于跳过安全、授权和必要验证。
6. 直接修改过程中若发现范围扩大到完整 Harness 条件，应停止扩展并询问是否升级为 PRD，不得静默扩大改动。
7. Harness 和直接修改车道都不强制调用指定 MCP、Skill、浏览器或其他工具；进入需要插件增强的 Hook 时，按 `.workflow/lifecycle-plugins.json` 和 `.workflow/specs/lifecycle-plugins.md` 解析，只调用已选择、可用且已获必要授权的插件。

## Spec 入口

- `.workflow/specs/index.md`：规范索引、必读项和任务路由。
- `.workflow/specs/conventions.md`：低 Token 通用约束摘要。
- `.workflow/specs/harness-lifecycle.md`：复杂度路由、直接修改车道以及完整 Harness 的 PRD、Quality Gate、可选 Review 和归档。
- `.workflow/lifecycle-plugins.json`：MCP 与 Skill 的生命周期插件注册表。
- `.workflow/specs/lifecycle-plugins.md`：插件 Hook、选择、授权、降级和扩展协议。
- `docs/harness-engineering-workflow.md`：仓库级 Harness Engineering 协作参考。
