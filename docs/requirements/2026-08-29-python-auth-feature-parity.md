<!-- author: jf -->
# Python 后端认证与邮箱能力对齐

## 1. 背景与问题

当前前端认证流程以 Spring 后端契约为准，注册必须先发送邮箱验证码，找回密码也依赖邮箱验证码。Python 后端目前只有加密登录和不带验证码的旧注册接口：`POST /api/auth/register` 仍接收 `username`，缺少注册验证码、密码重置和 SMTP 邮件能力，导致切换到 Python 后端后无法通过当前页面完成注册和找回密码，且重置密码后已有令牌不能立即失效。

## 2. 目标

1. 让 Python 后端完整兼容当前前端认证接口和字段契约。
2. 对齐 Spring 后端的邮箱注册验证码、密码重置验证码、冷却时间、有效期和失败次数限制。
3. 保留现有 RSA-OAEP + AES-GCM 加密登录，不允许退回明文密码接口。
4. 密码重置后立即使旧访问令牌失效。
5. 本地启动和 Docker 启动均能读取与 Spring 后端一致的邮箱环境变量。
6. 将认证业务从 FastAPI 依赖层下沉到 application/domain，并通过端口访问 SMTP、加密和数据库实现。

## 3. 范围

1. Python 认证请求与响应 Schema、认证路由和错误映射。
2. Python 认证应用服务、领域模型、业务异常和基础认证策略。
3. 登录密文解密、访问令牌签发与校验的基础设施适配器。
4. QQ SMTP 邮箱验证码发送适配器，包含纯文本和 HTML 邮件。
5. 基于 SQLAlchemy ORM 的认证用户与邮箱验证码仓储。
6. Python 配置、Docker Compose 环境变量传递、环境变量示例、启动依赖检查和后端说明文档。
7. 复用现有 `auth_users` 与 `auth_email_verification_codes` 表，不新增数据库结构。

## 4. 非目标

1. 不修改前端页面和前端认证契约。
2. 不修改 Spring 后端认证行为。
3. 不增加 DashScope WebSocket 语音桥接；本次只解决认证与邮箱能力差异。
4. 不改变现有密码摘要格式，不在本次引入密码哈希数据库迁移。
5. 不创建或修改测试代码、测试脚本、fixture 或 mock 文件。
6. 不自动写入演示账号，不操作生产数据库。

## 5. Brainstorm 结论与方案决策

### 5.1 已确认事实

1. 前端依赖以下接口：
   - `GET /api/auth/login-key`
   - `POST /api/auth/login`
   - `POST /api/auth/email-code`
   - `POST /api/auth/register`
   - `POST /api/auth/password-reset/email-code`
   - `POST /api/auth/password-reset`
2. Python 后端已有前两个接口和旧版注册接口，后三项邮箱能力缺失。
3. MySQL 迁移已经包含认证用户表和邮箱验证码表，本任务无需新增迁移。
4. Python 依赖已包含 `cryptography`、`PyMySQL` 和 `SQLAlchemy`，SMTP 可使用 Python 标准库实现。
5. 现有认证业务集中在 `app/api/deps/auth.py`，不符合仓库要求的 API、application、domain、infrastructure 分层。

### 5.2 评估方案

1. **前端绕过邮箱或恢复旧注册参数**：改动小，但会削弱安全能力并造成双后端契约继续分叉，否决。
2. **直接在 FastAPI 路由中复制 Spring 逻辑并继续写原生 SQL**：实现快，但业务逻辑留在 API 层且违反数据库访问规范，否决。
3. **建立认证应用服务和端口，使用 SQLAlchemy ORM 与 SMTP 适配器复用现有表**：改动范围较大，但能保证前端契约一致、事务边界明确，并修复现有分层问题，采用。

## 6. 接口与行为契约

### 6.1 发送注册验证码

`POST /api/auth/email-code`

请求：

```json
{
  "email": "user@example.com"
}
```

成功响应：

```json
{
  "cooldownSeconds": 60,
  "expiresInSeconds": 600
}
```

约束：邮箱已注册返回 `409`；冷却期内重复发送返回 `429`；SMTP 或验证码密钥未配置返回 `503`。

### 6.2 注册

`POST /api/auth/register`

请求字段固定为 `email`、`verificationCode`、`password`、`displayName`。验证码正确且未过期时创建普通用户，默认权限为 `resume_optimize` 与 `ai_interview`，成功后直接返回登录会话。

### 6.3 发送密码重置验证码

`POST /api/auth/password-reset/email-code`

已注册且启用的邮箱发送验证码。未知邮箱仍返回相同发送窗口但不发送邮件，避免泄露账号是否存在。

### 6.4 重置密码

`POST /api/auth/password-reset`

验证码正确时更新密码摘要并消费验证码；新密码长度限制为 8 至 128 位。访问令牌包含密码版本签名，更新密码后旧令牌校验失败。

### 6.5 验证码安全约束

1. 验证码为加密安全随机生成的 6 位数字。
2. 数据库只保存 `HMAC-SHA256(purpose:email:code)`，不保存明文验证码。
3. 注册和密码重置使用不同 purpose，验证码不可跨用途复用。
4. 默认冷却 60 秒、有效期 600 秒、最多失败 5 次，均可通过环境变量配置并设置安全下限。
5. 失败次数和过期删除必须提交；验证码成功使用后必须删除。
6. SMTP 发送失败时回滚本次验证码写入，避免用户收到不可重发的无效状态。

## 7. 配置契约

Python 本地 `.env` 和 Docker 环境变量支持：

- `APP_AUTH_EMAIL_CODE_SECRET`
- `APP_AUTH_EMAIL_CODE_COOLDOWN_SECONDS`
- `APP_AUTH_EMAIL_CODE_EXPIRY_SECONDS`
- `APP_AUTH_EMAIL_CODE_MAX_FAILED_ATTEMPTS`
- `MAIL_HOST`
- `MAIL_PORT`
- `MAIL_USERNAME`
- `MAIL_AUTHORIZATION_CODE`
- `MAIL_CONNECTION_TIMEOUT_MILLIS`
- `MAIL_TIMEOUT_MILLIS`
- `MAIL_WRITE_TIMEOUT_MILLIS`

变量名、默认值和含义与 Spring 后端保持一致。真实密钥和邮箱授权码只允许写入被 Git 忽略的 `.env`，不得写入源码、示例或日志。

## 8. 实施任务

- [x] 增加认证领域模型、业务异常和 application DTO/端口。
- [x] 增加认证应用服务，覆盖登录、注册、验证码、密码重置和鉴权。
- [x] 迁移登录加密与令牌逻辑到 infrastructure 适配器。
- [x] 增加 QQ SMTP 邮件适配器。
- [x] 增加 SQLAlchemy ORM 认证仓储并移除认证模块中的运行时原生 SQL。
- [x] 对齐 FastAPI Schema、路由、依赖和错误响应。
- [x] 补齐 Settings、Compose、环境变量示例和启动依赖检查。
- [x] 更新 Python 后端说明和 API 摘要。
- [x] 完成 Quality Gate 并记录未验证项。

## 9. 验收标准

1. 当前前端可以在不做任何改动的情况下调用 Python 后端完成发送注册验证码、注册并自动登录。
2. Python 注册接口不再接收旧 `username` 契约；额外字段按现有严格 Schema 返回校验错误。
3. 邮箱已注册、验证码冷却、验证码错误、验证码过期和错误次数耗尽分别返回与 Spring 语义一致的状态码和中文提示。
4. 未注册邮箱请求密码重置验证码时返回正常窗口且不发送邮件。
5. 密码重置成功后可以使用新密码登录，旧密码不能登录，重置前令牌失效。
6. 登录仍要求前端 RSA-OAEP + AES-GCM 密文请求，并保留时效和 requestId 防重放校验。
7. 验证码数据库记录不包含明文；SMTP 失败不留下新的冷却记录。
8. 本地 Python `.env.example` 与根目录 `.env.docker.example` 均包含完整邮箱配置，Compose 会把变量传入 Python 容器。
9. 认证仓储使用 SQLAlchemy ORM，不在新增认证运行时代码中拼接 SQL。
10. Python 代码可编译、应用可导入、静态检查和差异检查通过；不得新增或修改测试文件。

## 10. Quality Gate 计划

1. 执行 Python `compileall` 和应用导入检查。
2. 执行仓库前端 `npm run lint`，确认跨端契约文件未被意外破坏。
3. 使用一次性命令检查 FastAPI 路由和 OpenAPI Schema，不写测试文件。
4. 对可用的本地 MySQL 执行只针对认证接口的受控冒烟验证；不得删除或覆盖既有账号数据。
5. 不自动发送真实验证码邮件；若未进行真实 SMTP 投递，明确记录为人工验收项。
6. 执行作者标记检查、`git diff --check` 和变更文件范围检查。

## 11. 风险与回滚

1. SMTP 是同步外部依赖，发送期间会占用当前同步请求线程；通过连接和读写超时限制阻塞时间。
2. 邮箱验证码表以邮箱为主键，同一邮箱同时只能保留一个用途的验证码，行为与 Spring 后端保持一致。
3. 多进程部署时登录 RSA 公钥和防重放缓存按进程隔离；前端每次登录重新获取公钥，当前单容器部署不受影响。
4. 若实施失败，只回退本任务涉及的 Python 认证、配置与文档文件，不回退或覆盖现有前端分页改动和 `package-lock.json` 本地改动。
5. 本任务不修改数据库结构，回滚代码不会要求数据库 DDL 回滚。

## 12. 当前状态

- 状态：实现与自动 Quality Gate 已完成；用户选择跳过 Review，并授权提交、推送及创建 PR。真实邮箱注册和密码重置保留人工验收。
- 分支：`feat/python-auth-and-pdf-pagination`。
- UI 设计：不适用。
- 数据库迁移：不需要，复用现有认证表。
- 生命周期插件：本任务不依赖外部调研、UI 或远程协作插件。
- 本地配置：已基于现有 Spring `.env` 与 Python 模板生成被 Git 忽略的 `python-ai-backend/.env`，未输出真实密钥。

## 13. Quality Gate 结果

1. Python `compileall` 与 FastAPI 应用导入通过，六个认证路由均已注册。
2. Ruff 对本任务 Python 文件的静态检查通过。
3. 本地 MySQL 认证仓储只读访问和验证码 `SELECT ... FOR UPDATE` 路径通过，未修改既有账号或验证码数据。
4. FastAPI 受控 HTTP 冒烟通过：登录公钥、非法邮箱 `400`、旧注册契约 `400`、未知账号重置防枚举、管理员加密登录、requestId 重放拒绝、令牌访问简历接口。
5. 当前运行中的 Spring 后端与 Python 实现完成双向令牌兼容验证：Spring 签发令牌可由 Python 校验，Python 签发令牌可访问 Spring 受保护接口。
6. Python 本地认证与邮箱环境变量完整、无占位值、两段安全密钥不同，`.env` 处于 Git 忽略状态。
7. Docker Compose `python-ai + migration` 配置解析、Python 后端镜像构建、镜像内 OpenAPI 路由与认证 HTTP 冒烟均通过。
8. 已修复本地启动脚本在 `.venv` 不存在时跳过创建的批处理分支缺陷；Python 3.11 虚拟环境、核心依赖和可选 AI 依赖已就绪，临时端口运行时健康检查通过。
9. 前端 `npm run lint`、`npm run build`、作者标记、文件体积和 `git diff --check` 均通过；`PreviewPanel.vue` 的 scoped 样式已原样拆分至 `PreviewPanel.css`，两个文件均满足行数上限。
10. 未自动发送真实验证码邮件，也未执行会修改现有账号密码的重置验证；这两项保留给用户在页面进行人工验收。
11. 未新增或修改测试代码、测试脚本、fixture 或 mock 文件。
