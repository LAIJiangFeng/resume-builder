<!-- author: jf -->
# Learnings

## 2026-05-01 M1 Docker 双后端互斥部署

<spec-entry id="learning-20260501-docker-dual-backend" category="learning" source="maestro-execute">
Spring AI 后端套件与 Python AI 后端套件共享同一前端契约时，Docker 入口应通过互斥 profile 和启动脚本表达选择关系。Nginx 可使用 Docker 网络别名 `backend` 代理当前套件后端，但 README 和脚本必须明确禁止同时启用两套 profile，避免端口和代理目标冲突。
</spec-entry>

<spec-entry id="learning-20260501-docker-sql-init" category="learning" source="maestro-execute">
数据库初始化策略必须与仓库规则保持一致：MySQL 面试会话表和 pgvector RAG 表不由应用启动自动创建，Docker 一键部署也应保留手工执行 `sql/interview_schema.sql` 与 `sql/pgvector_rag_schema.sql` 的步骤。
</spec-entry>

## 2026-08-15 轻量 Harness 生命周期

<spec-entry id="learning-20260815-lightweight-harness" category="workflow" source="harness-lifecycle">
Harness 应强制需求、实现、验证、审查选择和归档结果，而不应强制指定 MCP、Skill 或浏览器工具。Brainstorm 先理解问题，再按相关性读取 Spec；实现后的 Quality Gate 负责全面证据检查；只有 Bug 修复才执行 Break Loop。这样能保留交付闭环，同时减少全量上下文、重复清单、无收益工具调用和阶段确认产生的 Token 消耗。
</spec-entry>

## 2026-08-15 规范目录迁移边界

<spec-entry id="learning-20260815-spec-migration-boundary" category="workflow" source="rules-to-spec-migration">
迁移仓库规范目录时，必须把文件搬迁、入口路由、内部交叉引用和版本控制忽略边界作为同一个原子变更。若只删除旧目录而没有放开新 Spec 目录，提交后会丢失全部规范；应验证旧目录不存在、新 Spec 可跟踪、其他运行期目录仍被忽略，并保留历史需求文档中的旧路径作为当时事实。
</spec-entry>

## 2026-08-15 生命周期插件注册边界

<spec-entry id="learning-20260815-lifecycle-plugin-registry" category="workflow" source="lifecycle-plugin-registry">
生命周期工具应通过声明式注册表按 Hook、标签、激活方式、优先级和授权状态选择，解析器只返回待注入能力，不直接调用工具。项目 Skill 使用仓库相对入口，运行时 Skill 使用逻辑名称，MCP 只保存服务器名；每个 Hook 限制自动插件数量，显式选择仍不得绕过禁用和授权门禁。PowerShell 解析可选标签数组时必须先过滤空值和空白，不能假设缺失属性转换后就是空集合，并应验证 `anyTags` 或 `allTags` 缺失的场景。这样既能保留可插拔能力，又能避免全量加载工具说明、泄露本机配置、错误跳过条件插件或把工具变成流程门禁。
</spec-entry>

## 2026-08-15 PRD 复杂度路由

<spec-entry id="learning-20260815-prd-complexity-routing" category="workflow" source="harness-lifecycle">
PRD 应由影响面和风险触发，而不是由“发生代码修改”触发。目标、范围和验收清晰的低风险局部修改可直接实现并针对性验证；新功能、跨层契约、数据结构、权限安全和高风险状态流程进入完整 Harness。无法可靠分类时只询问一次是否创建 PRD，用户选择不创建后不得重复追问；若直接修改过程中出现新的高风险范围，再暂停并重新路由。
</spec-entry>
