<!-- author: jf -->
# 生命周期插件注入规范

## 1. 规范定位

本规范定义 MCP 与 Skill 如何可插拔地注入轻量 Harness。插件是阶段增强能力，不是阶段完成条件；任务是否完成仍由适用的 PRD 或直接修改记录、验收标准和 Quality Gate 证据决定。

固定文件：

1. 注册表：`.workflow/lifecycle-plugins.json`
2. Schema：`.workflow/lifecycle-plugins.schema.json`
3. 解析器：`.workflow/scripts/resolve-lifecycle-plugins.ps1`

## 2. 标准 Hook

| Hook | 注入目的 |
| --- | --- |
| `brainstorm.context` | 远程协作或仓库外上下文 |
| `brainstorm.research` | 最新外部事实调研 |
| `brainstorm.enrich` | 领域能力增强需求梳理 |
| `prd.enrich` | 专业能力补充 PRD |
| `ui.design` | 可选 UI 设计与原型 |
| `implement.support` | 实现阶段的组件或领域支持 |
| `break_loop.analyze` | Bug 根因和预防机制增强 |
| `quality_gate.verify` | 浏览器、运行时或外部验证证据 |
| `submit.review` | 用户选择后的代码审查 |
| `submit.review_fix` | 用户授权后的审查修复 |
| `submit.remote` | 用户授权后的远程 PR / Issue 协作 |
| `archive.preference` | 用户明确要求的个人偏好记录 |

新增 Hook 必须使用 `<阶段>.<动作>` 小写命名，并在注册表 `hooks` 中声明。阶段仅允许 `brainstorm`、`prd`、`ui`、`implement`、`break_loop`、`quality_gate`、`submit`、`archive`。

## 3. 插件状态

1. `enabled=false`：完全不参与解析，即使显式选择也不调用。
2. `activation=always`：进入对应 Hook 即可自动选择，仍受自动数量上限约束。
3. `activation=conditional`：任务标签满足 `anyTags` 和 `allTags` 后自动选择。
4. `activation=manual`：只有 `RequestedPlugins` 显式包含插件 ID 时选择。
5. `requiresAuthorization=true`：无论自动还是显式选择，只有已有明确用户授权并传入 `-Authorized` 才能选择。
6. 所有默认插件都是可选增强；不得通过配置把 MCP 或 Skill 变成验收门禁。

## 4. 标签协议

标签使用小写 kebab-case，只表达当前任务真实语义。常用标签：

1. 协作：`github`、`issue`、`pr`、`remote`、`review`、`review-fix`。
2. 调研：`external-research`、`latest`、`web-research`。
3. UI：`frontend`、`ui`、`interaction`、`browser`、`ui-design`、`visual-design`、`redesign`。
4. 设计工具：`pencil`、`pen`、`stitch`、`ui-prototype`、`shadcn`、`component-library`。
5. 简历领域：`resume-template`、`image`、`resume-project`、`backend-resume`、`interview-coaching`。
6. 偏好：`personal-preference`、`remember`。

每个 Hook 只传入与该阶段相关的少量标签，不得为了提高命中率把标签表全量传入。

## 5. 解析与调用

解析示例：

```powershell
# UI 设计自动选择
& .\.workflow\scripts\resolve-lifecycle-plugins.ps1 `
  -Hook ui.design `
  -Tags ui,ui-design

# 用户选择 Code Review
& .\.workflow\scripts\resolve-lifecycle-plugins.ps1 `
  -Hook submit.review `
  -RequestedPlugins skill.code-review

# 用户授权修复审查问题
& .\.workflow\scripts\resolve-lifecycle-plugins.ps1 `
  -Hook submit.review_fix `
  -RequestedPlugins skill.code-review-fix `
  -Authorized
```

执行协议：

1. 解析器按 `priority` 降序选择，自动插件数量受 `maxAutomaticPluginsPerHook` 限制。
2. 显式插件默认绕过自动数量上限，但不会绕过 `enabled` 和授权门禁。
3. 返回项 `kind=skill` 且 `source=project` 时，只读取 `entry` 指向的 `SKILL.md`；`source=runtime` 时通过当前运行时技能注册表解析 `runtime://<provider>`。入口不可用时走 `fallback`。
4. 返回项 `kind=mcp` 时，使用 `provider` 对应的 MCP；运行时不可用时走 `fallback`。
5. `unresolvedRequestedPlugins` 非空时根据 `reason` 处理：`not_registered`、`disabled`、`hook_not_supported`、`authorization_required` 或 `not_selected`；不能静默换成其他副作用插件。
6. 工具调用完成后只保留结论、证据路径和未验证项，不复制完整工具过程。

## 6. 当前默认映射

1. GitHub、Tavily 用于 Brainstorm 或远程提交上下文。
2. Modern Web UI Designer、Pencil、Stitch、Shadcn 用于可选 UI 与组件支持。
3. Playwright 用于前端 Quality Gate；Node REPL 保持手动后备。
4. Code Review、Code Review Fix、PR Review Fix 均保持手动，其中修复类插件必须授权。
5. Resume Template From Image 可按 `resume-template + image` 自动注入 UI 和实现阶段。
6. Resume Backend Project Optimizer 与 Resume Interview Coach 保持手动领域增强。
7. OpenAI Docs、UI UX Pro Max、Frontend Design 与 Quality Test 作为运行时 Skill 注册，不保存本机绝对路径。
8. Memory 只允许在用户明确要求记录个人长期偏好时手动注入；项目知识写入 Spec。
9. Figma 默认关闭，启用前需确认运行时可用和授权状态。

## 7. 扩展插件

新增或调整插件时：

1. 在注册表新增唯一 `id`，格式为 `mcp.<name>` 或 `skill.<name>`。
2. 项目 Skill 使用 `source=project` 并配置项目相对路径 `entry`；运行时 Skill 使用 `source=runtime`，由 Agent 的技能注册表按 `provider` 解析，不写本机绝对路径。
3. 选择已有 Hook；确需新增 Hook 时同时更新注册表 `hooks` 和本规范。
4. 设置最小标签、合理优先级和明确降级，不存储 URL、token、apiKey、secret 或环境变量值。
5. 使用解析器验证自动、手动、授权和无匹配场景。
6. 更新 `.workflow/specs/index.md` 仅在新增长期规范文件时需要，新增普通插件不改索引。

## 8. 安全与降级

1. 注册表只保存逻辑名称和项目相对路径，不保存连接凭据。
2. `fallback.type=plugin` 只能指向已注册插件；是否调用仍需重新检查目标插件的状态和授权。
3. `fallback.type=command` 或 `manual` 只是建议，不代表自动执行命令或人工验证已经完成。
4. 插件失败不得触发无限重试；尝试一次降级后仍失败，记录 `未执行` 和残余风险。
5. Git、PR、外部写入、Review 修复和长期偏好记录继续服从用户授权边界。
