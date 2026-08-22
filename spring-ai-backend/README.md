<!-- author: jf -->
# spring-ai-backend

Spring Boot 3 + Spring AI 后端服务，提供聊天、流式输出、Realtime 临时密钥、AI 面试会话、知识库统一上传、图片 OCR 与 RAG 检索能力。

## 技术栈

- Java 21
- Spring Boot 3
- Spring AI
- MyBatis-Plus
- MySQL
- PostgreSQL + pgvector

## 快速开始

### 前置依赖

- JDK `21`
- Maven `3.9+`
- Docker Desktop / Docker Compose
- 可用的 OpenAI 或 OpenAI-compatible API Key；如启用默认实时语音链路，还需要 DashScope API Key
- 已开启 SMTP 服务并生成授权码的 QQ 邮箱，用于发送注册验证码

### 1. 准备 `.env`

复制 `spring-ai-backend/.env.example` 为 `spring-ai-backend/.env`，至少确认以下配置：

```bash
OPENAI_API_KEY=your_api_key_here
MYSQL_DATASOURCE_URL=jdbc:mysql://127.0.0.1:3306/resume-builder?useUnicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai&useSSL=false&allowPublicKeyRetrieval=true
MYSQL_DATASOURCE_USERNAME=root
MYSQL_DATASOURCE_PASSWORD=root
PGVECTOR_DATASOURCE_URL=jdbc:postgresql://127.0.0.1:5433/resume-builder
PGVECTOR_DATASOURCE_USERNAME=pgvector
PGVECTOR_DATASOURCE_PASSWORD=pgvector
SERVER_PORT=8999
APP_CORS_ALLOWED_ORIGINS=http://localhost:5173
MAIL_USERNAME=your_qq_number@qq.com
MAIL_AUTHORIZATION_CODE=your_qq_smtp_authorization_code
APP_AUTH_EMAIL_CODE_SECRET=replace_with_a_separate_random_secret
```

`MAIL_AUTHORIZATION_CODE` 必须填写 QQ 邮箱“设置 > 账号 > POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV 服务”中生成的 SMTP 授权码，不能填写 QQ 登录密码。真实邮箱与授权码只写入本地 `spring-ai-backend/.env`，不要提交到仓库。

### 2. 启动数据库并迁移

在仓库根目录执行：

```bash
docker compose --profile spring-ai up -d mysql pgvector
docker compose --profile migration build flyway-mysql
docker compose --profile migration run --rm --no-deps flyway-mysql
docker compose --profile migration run --rm --no-deps flyway-pgvector
```

迁移文件位于 `sql/migrations/`，应用启动不会自动建表。需要本地演示账号时，再手工执行 `sql/seeds/mysql/local_demo_users.sql`。

### 3. 启动后端

在 `spring-ai-backend/` 目录执行：

```bash
mvn spring-boot:run
```

默认地址：`http://localhost:8999`

健康检查：`GET http://localhost:8999/health`

## 配置说明

### 必填最小配置

```bash
OPENAI_API_KEY=your_api_key_here
MYSQL_DATASOURCE_URL=jdbc:mysql://127.0.0.1:3306/resume-builder?useUnicode=true&characterEncoding=UTF-8&serverTimezone=Asia/Shanghai&useSSL=false&allowPublicKeyRetrieval=true
MYSQL_DATASOURCE_USERNAME=root
MYSQL_DATASOURCE_PASSWORD=root
PGVECTOR_DATASOURCE_URL=jdbc:postgresql://127.0.0.1:5433/resume-builder
PGVECTOR_DATASOURCE_USERNAME=pgvector
PGVECTOR_DATASOURCE_PASSWORD=pgvector
SERVER_PORT=8999
APP_CORS_ALLOWED_ORIGINS=http://localhost:5173
MAIL_USERNAME=your_qq_number@qq.com
MAIL_AUTHORIZATION_CODE=your_qq_smtp_authorization_code
APP_AUTH_EMAIL_CODE_SECRET=replace_with_a_separate_random_secret
```

### 可选分路配置

- Chat：`OPENAI_CHAT_BASE_URL`、`OPENAI_CHAT_API_KEY`、`OPENAI_CHAT_MODEL`
- Realtime ASR：默认 `REALTIME_ASR_PROVIDER=dashscope`，使用 `DASHSCOPE_API_KEY`、`DASHSCOPE_REALTIME_BASE_URL`、`DASHSCOPE_REALTIME_MODEL`、`DASHSCOPE_REALTIME_LANGUAGE`、`DASHSCOPE_REALTIME_SAMPLE_RATE`、`DASHSCOPE_REALTIME_VAD_THRESHOLD`、`DASHSCOPE_REALTIME_VAD_SILENCE_DURATION_MS`、`DASHSCOPE_REALTIME_OPEN_TIMEOUT_SECONDS`
- OpenAI Realtime：当 `REALTIME_ASR_PROVIDER=openai` 时，使用 `OPENAI_REALTIME_BASE_URL`、`OPENAI_REALTIME_API_KEY`、`OPENAI_REALTIME_CLIENT_SECRETS_PATH`、`OPENAI_REALTIME_CALLS_PATH`、`OPENAI_REALTIME_TRANSCRIPTION_MODEL`、`OPENAI_REALTIME_LANGUAGE`、`OPENAI_REALTIME_TIMEOUT_SECONDS`
- Embedding：`EMBEDDING_PROVIDER`、`EMBEDDING_DIMENSIONS`、`OPENAI_EMBEDDING_*`、`OLLAMA_EMBEDDING_*`
- Vision OCR：`OPENAI_VISION_BASE_URL`、`OPENAI_VISION_API_KEY`、`OPENAI_VISION_MODEL`、`OPENAI_VISION_DETAIL`
- 邮箱验证：QQ SMTP 固定使用 `smtp.qq.com:465` SSL，注册和密码重置共用发送配置，需配置 `MAIL_USERNAME`、`MAIL_AUTHORIZATION_CODE` 和独立的 `APP_AUTH_EMAIL_CODE_SECRET`

说明：

- `*_BASE_URL` 可以按 Python 后端习惯保留到服务根地址，也可以带 `/v1`；Spring RestClient 会在默认 `*_PATH=/v1/...` 场景下自动去重，避免请求到重复 `/v1/v1/...`。
- 默认实时语音对齐 DashScope realtime ASR：前端先请求 `POST /api/ai/realtime/client-secret`，收到 `provider=dashscope` 后连接后端 `/ws/ai/realtime-asr`，Spring 后端再使用 `DASHSCOPE_API_KEY` 桥接到 DashScope。
- `DASHSCOPE_REALTIME_MODEL` 默认 `qwen3-asr-flash-realtime`，音频格式为 `pcm`，默认采样率 `16000`，默认语言 `zh`，默认 VAD 为 `threshold=0.2`、`silence_duration_ms=800`。
- `OPENAI_REALTIME_TIMEOUT_SECONDS` 默认 `120`，仅在 `REALTIME_ASR_PROVIDER=openai` 时用于创建 OpenAI Realtime 临时密钥的上游 HTTP 请求超时。
- `EMBEDDING_PROVIDER=openai` 时，知识库向量化使用 `OPENAI_EMBEDDING_BASE_URL`、`OPENAI_EMBEDDING_API_KEY`、`OPENAI_EMBEDDING_MODEL`。
- `EMBEDDING_PROVIDER=ollama` 时，知识库向量化使用本地 `OLLAMA_EMBEDDING_BASE_URL`、`OLLAMA_EMBEDDING_MODEL`、`OLLAMA_EMBEDDING_TIMEOUT_SECONDS`；启动前需先执行 `ollama pull <模型名>`。
- `EMBEDDING_DIMENSIONS=0` 时会按常见模型自动推断维度；自定义 Ollama embedding 模型时应填写真实维度，避免向量检索链路出现维度不一致。
- `.env` 会通过 `spring.config.import` 自动加载，并兼容从 `spring-ai-backend/` 目录、仓库根目录或 IDE 工作目录启动。

## 与前端联调

前端代理默认转发到 `http://localhost:8999`，因此联调时建议保持 `SERVER_PORT=8999`。

## API 摘要

AI 能力基础路径：`/api/ai`

- `POST /chat`
- `POST /chat/stream`
- `POST /realtime/client-secret`
- `WS /ws/ai/realtime-asr`（`REALTIME_ASR_PROVIDER=dashscope` 时由前端连接，用于桥接 DashScope realtime ASR）
- `POST /interview/turn/stream`
- `GET /interview/sessions?limit=20`
- `GET /interview/sessions/{sessionId}`
- `POST /rag/documents`
- `POST /rag/query`
- `POST /rag/upload`

认证基础路径：`/api/auth`

- `POST /email-code`：向注册邮箱发送 6 位验证码
- `POST /register`：使用邮箱、验证码和密码注册
- `POST /login`：使用注册邮箱或保留的演示账号登录
- `POST /password-reset/email-code`：向已注册邮箱发送密码重置验证码
- `POST /password-reset`：使用邮箱验证码设置新密码

## 数据库迁移

- `sql/migrations/mysql/`：账号、简历和面试表迁移。
- `sql/migrations/postgresql/`：pgvector RAG 表迁移。
- `sql/bootstrap/`：非 Docker 数据库的手工建库脚本。
- `sql/seeds/`：仅供本地使用的演示数据。

已执行迁移禁止修改，只能新增更高版本；Spring 后端继续保持 `PgVectorStore.initializeSchema(false)`。

## 常见问题

- 启动报数据库连接失败时，优先检查 `.env` 与 `docker-compose.yml` 是否一致。
- 遇到 CORS 问题时，确认 `APP_CORS_ALLOWED_ORIGINS` 包含前端地址。
- 上游 401/403 时，确认对应 `OPENAI_*_API_KEY` 已正确配置。
