<!-- author: jf -->
# Learnings

## 2026-05-01 M1 Docker 双后端互斥部署

<spec-entry id="learning-20260501-docker-dual-backend" category="learning" source="maestro-execute">
Spring AI 后端套件与 Python AI 后端套件共享同一前端契约时，Docker 入口应通过互斥 profile 和启动脚本表达选择关系。Nginx 可使用 Docker 网络别名 `backend` 代理当前套件后端，但 README 和脚本必须明确禁止同时启用两套 profile，避免端口和代理目标冲突。
</spec-entry>

<spec-entry id="learning-20260501-docker-sql-init" category="learning" source="maestro-execute">
数据库初始化策略必须与仓库规则保持一致：MySQL 业务表和 pgvector RAG 表不由应用启动自动创建；Docker 与 CI/CD 应在应用启动前通过独立 Flyway 容器执行版本迁移，迁移失败时不得继续更新应用。
</spec-entry>

## 2026-08-23 版本化数据库迁移

<spec-entry id="learning-20260823-versioned-database-migrations" category="database" source="versioned-database-migrations">
已有数据库接入自动迁移时，应把建库、版本迁移和本地种子数据分目录隔离，以 `baselineVersion=0` 登记旧库并让兼容迁移继续前进。已执行迁移必须保持不可变，生产迁移不得包含演示账号；部署必须先备份、再迁移、最后更新应用，且禁止在迁移前执行会停止现有应用的全栈 `down`。
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

## 2026-08-29 Python 双后端认证对齐

<spec-entry id="learning-20260829-python-auth-parity" category="security" source="python-auth-feature-parity">
双后端共用同一前端时，认证对齐不能只补路由名称：必须同时对齐请求模型、状态码语义、登录密文协议、令牌载荷、密码版本失效、验证码摘要、行锁事务、限流和未知账号防枚举响应。Python 侧认证编排应进入 `application`，密码学、SMTP 和 ORM 仓储分别由端口接入 `infrastructure`；Docker Compose 还必须把同一组认证与邮箱环境变量显式传给两套后端，避免本地可用而容器缺配置。
</spec-entry>
