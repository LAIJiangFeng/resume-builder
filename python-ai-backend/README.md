<!-- author: jf -->
# python-ai-backend

基于 FastAPI 的 Python AI 后端，提供邮箱注册与密码重置、加密登录、聊天、AI 面试、RAG、图片 OCR、会话存储，以及与前端共享的 Realtime client-secret 能力。

## 作用说明

- `/api/auth/*` 与当前前端和 Spring 后端保持同一认证契约。
- 注册、密码重置验证码通过 QQ SMTP 发送，验证码摘要存储到 MySQL。
- 对外继续提供 `/api/ai/*` 风格接口。
- AI 面试会话与消息历史存储到 MySQL。
- RAG 向量检索使用 PostgreSQL + pgvector。
- AI 面试语音优先通过 `/api/ai/realtime/client-secret` 获取临时密钥，由前端使用 WebRTC 接入 Realtime；不可用时前端自动回退到浏览器语音识别。

## 快速启动

### 前置依赖

- Python `3.11+`
- `uv`
- MySQL
- PostgreSQL + pgvector
- QQ 邮箱 SMTP 授权码（需要注册和密码重置功能时）

### 1. 启动数据库并迁移

在仓库根目录执行：

```bash
docker compose --profile python-ai up -d mysql pgvector
docker compose --profile migration build flyway-mysql
docker compose --profile migration run --rm --no-deps flyway-mysql
docker compose --profile migration run --rm --no-deps flyway-pgvector
```

迁移文件位于 `sql/migrations/`，应用启动不会自动建表。需要本地演示账号时，再手工执行 `sql/seeds/mysql/local_demo_users.sql`。

### 2. 准备环境变量

复制 `python-ai-backend/.env.example` 为 `python-ai-backend/.env`，至少确认以下配置：

```bash
SERVER_PORT=8999
APP_CORS_ALLOWED_ORIGINS=http://localhost:5173
APP_AUTH_TOKEN_SECRET=replace_with_a_random_token_secret
APP_AUTH_EMAIL_CODE_SECRET=replace_with_a_separate_random_secret

MAIL_HOST=smtp.qq.com
MAIL_PORT=465
MAIL_USERNAME=your_qq_number@qq.com
MAIL_AUTHORIZATION_CODE=your_qq_smtp_authorization_code

OPENAI_API_KEY=your_openai_api_key_here
OPENAI_CHAT_MODEL=gpt-5.4

EMBEDDING_PROVIDER=openai
OPENAI_EMBEDDING_BASE_URL=https://api.openai.com
OPENAI_EMBEDDING_API_KEY=your_embedding_api_key_here
OPENAI_EMBEDDING_MODEL=text-embedding-3-large

OPENAI_REALTIME_BASE_URL=https://api.openai.com
OPENAI_REALTIME_API_KEY=your_openai_api_key_here
OPENAI_REALTIME_CLIENT_SECRETS_PATH=/v1/realtime/client_secrets
OPENAI_REALTIME_CALLS_PATH=/v1/realtime/calls
OPENAI_REALTIME_TRANSCRIPTION_MODEL=gpt-4o-transcribe
OPENAI_REALTIME_LANGUAGE=zh

MYSQL_DATASOURCE_URL=mysql+pymysql://root:root@127.0.0.1:3306/resume-builder
MYSQL_DATASOURCE_USERNAME=root
MYSQL_DATASOURCE_PASSWORD=root

PGVECTOR_DATASOURCE_URL=postgresql+psycopg://pgvector:pgvector@127.0.0.1:5433/resume-builder
PGVECTOR_DATASOURCE_USERNAME=pgvector
PGVECTOR_DATASOURCE_PASSWORD=pgvector
```

### 3. 安装依赖

在 `python-ai-backend/` 目录执行：

```bash
uv venv .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
uv pip install --python .venv\Scripts\python.exe -r requirements-optional.txt
```

### 4. 启动后端

在仓库根目录执行：

```bash
start-python-backend.bat
```

备用方式：

```powershell
.\start-python-backend.ps1 -Port 8999
```

默认地址：`http://127.0.0.1:8999`

健康检查：

- `GET /health`
- `GET /health/runtime`

## 环境变量说明

模板文件：`python-ai-backend/.env.example`

当前保留的关键变量分组：

- 认证：`APP_AUTH_TOKEN_*`、`APP_AUTH_EMAIL_CODE_*`
- 邮件：`MAIL_HOST`、`MAIL_PORT`、`MAIL_USERNAME`、`MAIL_AUTHORIZATION_CODE`、`MAIL_*_TIMEOUT_MILLIS`
- Chat：`OPENAI_BASE_URL`、`OPENAI_API_KEY`、`OPENAI_CHAT_*`
- Embedding：`EMBEDDING_PROVIDER`、`OPENAI_EMBEDDING_*`、`OLLAMA_EMBEDDING_*`
- Vision OCR：`OPENAI_VISION_*`
- Realtime：`OPENAI_REALTIME_*`
- MySQL：`MYSQL_DATASOURCE_*`
- pgvector：`PGVECTOR_DATASOURCE_*`
- RAG：`RAG_CHUNK_SIZE`、`RAG_CHUNK_OVERLAP`、`RAG_MAX_FILE_SIZE_MB`

说明：

- `SERVER_PORT` 建议保持 `8999`，与前端代理一致。
- `APP_AUTH_TOKEN_SECRET` 与 `APP_AUTH_EMAIL_CODE_SECRET` 必须使用两段不同的随机密钥。
- `MAIL_AUTHORIZATION_CODE` 填写 QQ 邮箱 SMTP 授权码，不是 QQ 登录密码。
- `APP_INTERVIEW_RAG_TOP_K`、`APP_INTERVIEW_RAG_SIMILARITY_THRESHOLD`、`APP_INTERVIEW_RAG_TIMEOUT_SECONDS` 仅用于 AI 面试链路。
- `OPENAI_REALTIME_*` 用于 `/api/ai/realtime/client-secret` 链路；前端会用返回的临时密钥和 Realtime 地址建立 WebRTC 连接。
- 当前 Python 后端不再提供 `/ws/ai/realtime-asr` 这类后端专属语音 WebSocket 桥接。

## 与 Spring 后端的关系

- `spring-ai-backend` 和 `python-ai-backend` 是同一前端对应的两套可选后端实现。
- 两者共享邮箱注册、密码重置、加密登录和访问令牌契约。
- 两者默认都监听 `8999`，联调时不要同时启动。

## API 摘要

认证接口：

- `GET /api/auth/login-key`
- `POST /api/auth/login`
- `POST /api/auth/email-code`
- `POST /api/auth/register`
- `POST /api/auth/password-reset/email-code`
- `POST /api/auth/password-reset`

AI 基础路径：`/api/ai`

- `POST /chat`
- `POST /chat/stream`
- `POST /interview/turn/stream`
- `GET /interview/sessions`
- `GET /interview/sessions/{sessionId}`
- `POST /rag/query`
- `POST /rag/documents`
- `POST /rag/upload`
- `POST /realtime/client-secret`

## 常见问题

- 后端启动失败时，先检查 `.env` 中的数据库连接和端口是否与容器一致。
- 验证码返回 `503` 时，检查 `APP_AUTH_EMAIL_CODE_SECRET`、`MAIL_USERNAME` 和 `MAIL_AUTHORIZATION_CODE`；SMTP 授权码不要填 QQ 登录密码。
- 浏览器提示获取实时语音会话失败时，先检查 `python-ai-backend/.env` 里的 `OPENAI_REALTIME_*` 或通用 `OPENAI_API_KEY` 是否已正确配置。
- 浏览器语音自动回退到免费识别时，通常是 `/api/ai/realtime/client-secret` 链路或上游 Realtime 配置异常，可先看 FastAPI 日志里的 realtime client-secret 错误。
