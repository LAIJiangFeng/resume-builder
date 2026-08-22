<!-- author: jf -->
# Python AI Backend 强制规则

## 1. 规则定位

本文档用于定义 `python-ai-backend/` 的功能背景、目标职责、目录边界、依赖方向和模块协作规则。

凡涉及 `python-ai-backend/` 的新增、修改、重构、迁移和目录调整，默认都必须遵守本文件。

注意：

- 本文档应按强制规则理解，不视为普通说明文档。
- 目录结构可以分阶段落地，但依赖方向和层级边界不能被破坏。
- 如果当前实现与本文档冲突，应优先调整实现；若确需例外，应先更新规则文档，再改代码。
- 涉及数据库、SQL、pgvector 或会话存储时，必须同步遵守数据库与 SQL 强制规则。
- 涉及验证或测试代码边界时，必须同步遵守测试与验证强制规则。

---

## 2. 后端功能背景

`python-ai-backend` 的存在目的，不是单纯提供几个 AI 接口，而是为当前简历编辑与 AI 面试产品提供一套边界清晰、便于扩展、能够逐步替换现有实现的 Python AI 服务层。

它主要承接以下业务能力：

1. 简历优化问答
   - 提供普通问答和流式问答。
   - 支持对输出内容做结构清洗、简历内容净化和分段输出。

2. AI 面试
   - 支持面试轮次推进、会话历史管理、阶段控制、评分和总结。
   - 支持候选人模式与面试官模式。
   - 支持流式输出和会话详情查询。

3. RAG 检索
   - 支持知识文档入库。
   - 支持基于向量召回的上下文检索和回答生成。

4. 语音相关能力
   - 支持音频转写。
   - 支持 Realtime 临时密钥下发。

5. 与前端契约兼容
   - 对外继续提供 `/api/ai/*` 风格接口。
   - 在前端不大改的前提下，逐步替换或并行现有后端实现。

---

## 3. 后端设计目标

这套后端结构需要解决的核心问题，不是“目录好看”，而是下面四件事：

1. 让 HTTP 层、业务层、领域规则、外部依赖分开。
2. 让大模型、数据库、向量库、语音服务都可以替换，不把业务逻辑绑死在具体实现上。
3. 让面试、聊天、RAG、语音这些能力既能独立演进，又能共享通用能力。
4. 让新同学看到目录后，不打开实现也能判断代码应该放哪里。

---

## 4. 总体分层原则

依赖方向必须固定为：

```text
api -> application -> domain
                    ^
                    |
            infrastructure
```

含义如下：

- `api` 只能面向 HTTP。
- `application` 负责用例编排，不关心 FastAPI 细节。
- `domain` 只表达业务规则，不关心数据库、OpenAI、LangChain、FastAPI。
- `infrastructure` 提供外部依赖实现，通过端口接入 `application`。

明确禁止的依赖方向：

- `domain` 直接 import `FastAPI`、`OpenAI SDK`、`pgvector`、`MySQL`。
- `application` 直接依赖 `api.schemas`。
- `api.routes` 直接拼装数据库查询或直接调用外部模型。
- `infrastructure` 夹带核心业务分支判断。

---

## 5. 典型请求链路

### 5.1 Chat

```text
chat_routes.py
  -> chat_mapper.py
  -> run_chat.py / stream_chat.py
  -> llm_port.py
  -> openai_chat_adapter.py
  -> 返回 API schema
```

### 5.2 RAG

```text
rag_routes.py
  -> rag_mapper.py
  -> run_rag_query.py / ingest_rag_documents.py
  -> rag_retrieval_service.py
  -> vector_store_port.py
  -> vector_store_adapter.py
```

### 5.3 Interview

```text
interview_routes.py
  -> interview_mapper.py
  -> generate_interview_turn.py
  -> interview_session_service.py
  -> interview_flow_service.py
  -> llm_port.py / vector_store_port.py / agent_runtime_port.py
  -> interview_session_repository.py
  -> NDJSON/SSE 输出
```

### 5.4 Audio

```text
audio_routes.py
  -> audio_mapper.py
  -> transcribe_audio.py
  -> audio_transcription_port.py
  -> openai_audio_adapter.py
```

### 5.5 Realtime

```text
realtime_routes.py
  -> realtime_mapper.py
  -> create_realtime_client_secret.py
  -> realtime_secret_port.py
  -> openai_realtime_adapter.py
```

---

## 6. 目标目录树

```text
python-ai-backend/
├─ pyproject.toml
├─ README
├─ .env.example
├─ .gitignore
├─ scripts/
│  ├─ start_local.py
│  └─ check_env.py
├─ docs/
│  ├─ architecture 文档
│  └─ api 文档
└─ app/
   ├─ __init__.py
   ├─ main.py
   ├─ bootstrap/
   │  ├─ __init__.py
   │  ├─ container.py
   │  └─ dependencies.py
   ├─ api/
   │  ├─ __init__.py
   │  ├─ deps/
   │  ├─ routes/
   │  ├─ schemas/
   │  ├─ mappers/
   │  └─ errors/
   ├─ application/
   │  ├─ __init__.py
   │  ├─ dto/
   │  ├─ use_cases/
   │  ├─ services/
   │  └─ ports/
   ├─ domain/
   │  ├─ __init__.py
   │  ├─ models/
   │  ├─ services/
   │  ├─ policies/
   │  └─ exceptions/
   ├─ infrastructure/
   │  ├─ __init__.py
   │  ├─ config/
   │  ├─ persistence/
   │  ├─ llm/
   │  ├─ agents/
   │  ├─ text/
   │  └─ factories/
   └─ shared/
      ├─ __init__.py
      ├─ constants/
      ├─ streaming/
      ├─ utils/
      └─ types/
```

---

## 7. 顶层目录说明

### 7.1 `pyproject.toml`

职责：

- 定义 Python 项目依赖和构建配置。
- 作为 Python 子项目的单一工程入口。

边界：

- 只存项目配置，不承载业务说明。

### 7.2 `README`

职责：

- 说明如何启动、如何配置环境变量、如何联调。

边界：

- 只做使用说明，不承载详细设计和模块边界。

### 7.3 `.env.example`

职责：

- 提供最小可用环境变量模板。

边界：

- 不写真实密钥。
- 不写业务逻辑说明。

### 7.4 `scripts/`

职责：

- 放本地启动、环境检查、一次性辅助脚本。

边界：

- 不放业务代码。
- 不替代正式应用入口。

### 7.5 `docs/`

职责：

- 放架构说明、接口说明、迁移说明等文档。

边界：

- 不放可执行业务逻辑。

---

## 8. `app/` 目录总职责

`app/` 是 Python 后端实际运行代码的根目录。

它的边界是：

- 所有业务运行代码都从这里进入。
- 所有 HTTP、用例、领域、基础设施实现都在这一层分区。
- 不应把与运行无关的临时脚本、数据库脚本、测试夹具塞进这里。

---

## 9. `app/main.py`

职责：

- 创建 FastAPI 应用。
- 注册中间件、异常处理器、CORS、健康检查和路由。

边界：

- 不写业务逻辑。
- 不直接 new 各种复杂服务对象。
- 不直接访问数据库或外部模型。

---

## 10. `bootstrap/` 边界

### 10.1 目录职责

`bootstrap/` 负责“组装”，也就是把配置、端口实现、仓储、用例绑定起来。

它解决的是“系统如何启动和注入依赖”的问题，不解决业务本身的问题。

### 10.2 子目录职责

#### `container.py`

职责：

- 创建依赖容器。
- 把 `Settings`、Repository、Adapter、Use Case 组装起来。

边界：

- 不写业务规则。

#### `dependencies.py`

职责：

- 给 FastAPI `Depends` 提供统一入口。

边界：

- 不在这里写业务逻辑和数据库语句。

---

## 11. `api/` 边界

### 11.1 目录职责

`api/` 只面向 HTTP 世界。

它只负责：

- 接收请求。
- 校验输入。
- 调用 use case。
- 把结果转成响应。
- 把异常转成标准 HTTP 错误。

它不负责：

- 做核心业务判断。
- 直接访问数据库。
- 直接调 OpenAI、LangChain、pgvector、MySQL。

### 11.2 `api/deps/`

职责：

- 管理路由层依赖。

边界：

- 只做 route 依赖注入，不做服务编排。

### 11.3 `api/routes/`

职责：

- 每个文件对应一类接口。
- 定义 URL、请求方法、返回 schema。

推荐拆分：

- `chat_routes.py`
- `rag_routes.py`
- `interview_routes.py`
- `audio_routes.py`
- `realtime_routes.py`

边界：

- 只调用 use case。
- 不直接拼业务对象。
- 不写数据库查询。

### 11.4 `api/schemas/`

职责：

- 定义 HTTP request/response 的 Pydantic 模型。

边界：

- 它只服务 API 契约。
- 不能把它当成 application 或 domain 的通用对象。

### 11.5 `api/mappers/`

职责：

- 在 API schema 和 application DTO 之间转换。

边界：

- 只做数据映射，不做业务决策。

### 11.6 `api/errors/`

职责：

- 统一把领域异常、应用异常转成 HTTP 响应。

边界：

- 不在这里创建业务异常。

---

## 12. `application/` 边界

### 12.1 目录职责

`application/` 是用例层。

它的职责是：

- 表达系统“要完成什么用例”。
- 协调领域服务、仓储端口、外部能力端口。
- 控制一次请求内的业务流程。

它不负责：

- HTTP 协议细节。
- 领域核心规则定义。
- 外部依赖的具体实现。

### 12.2 `application/dto/`

职责：

- 定义 use case 输入输出对象。

边界：

- 它是 application 内部契约，不直接暴露给前端。

### 12.3 `application/use_cases/`

职责：

- 一文件一个业务用例。

典型用例：

- `run_chat.py`
- `stream_chat.py`
- `run_rag_query.py`
- `ingest_rag_documents.py`
- `generate_interview_turn.py`
- `list_interview_sessions.py`
- `get_interview_session_detail.py`
- `transcribe_audio.py`
- `create_realtime_client_secret.py`

边界：

- 只负责单个用例编排。
- 不承载太多跨用例复用逻辑。

### 12.4 `application/services/`

职责：

- 放多个 use case 共享的编排服务。

典型场景：

- 会话装载与保存。
- 流式响应格式拼装。

边界：

- 不应演变成“大而全的 app_service.py”。

### 12.5 `application/ports/`

职责：

- 定义 application 依赖的外部能力接口。

典型端口：

- `llm_port.py`
- `vector_store_port.py`
- `interview_session_repository.py`
- `audio_transcription_port.py`
- `realtime_secret_port.py`
- `agent_runtime_port.py`

边界：

- 这里只有抽象接口，不写具体实现。

---

## 13. `domain/` 边界

### 13.1 目录职责

`domain/` 是业务核心层。

它负责：

- 定义业务对象。
- 定义业务规则。
- 定义业务状态变化逻辑。

它不负责：

- 知道 HTTP 是什么。
- 知道数据库表怎么存。
- 知道 OpenAI、LangChain、AutoGen 的 SDK 怎么调用。

### 13.2 `domain/models/`

职责：

- 核心实体和值对象。

例如：

- `InterviewSession`
- `InterviewMessage`
- `RagDocument`
- `RagSource`
- `Score`

边界：

- 保持业务语义纯净，不夹带数据库字段实现细节。

### 13.3 `domain/services/`

职责：

- 放不能只靠单个实体表达的业务规则。

例如：

- 面试流程推进。
- RAG 检索结果组织。
- 简历段落清洗判定。

边界：

- 只处理业务规则，不直接调具体 SDK。

### 13.4 `domain/policies/`

职责：

- 存放可以独立替换和复用的规则策略。

例如：

- `score_policy.py`
- `sanitize_policy.py`

边界：

- 策略只表达规则，不做基础设施调用。

### 13.5 `domain/exceptions/`

职责：

- 定义领域异常。

边界：

- 只定义业务错误，不带 HTTP 状态码语义。

---

## 14. `infrastructure/` 边界

### 14.1 目录职责

`infrastructure/` 负责所有外部依赖的具体实现。

包括：

- 配置读取
- MySQL 持久化
- pgvector 检索
- OpenAI / LangChain / Realtime 调用
- AutoGen 适配
- 一些技术性文本处理工具

它不负责：

- 定义核心业务规则。
- 控制系统用例流程。

### 14.2 `infrastructure/config/`

职责：

- 管理环境变量、配置对象、日志配置。

边界：

- 不写业务逻辑。

### 14.3 `infrastructure/persistence/mysql/`

职责：

- 承接面试会话存储。
- 实现 `InterviewSessionRepository`。

边界：

- 只负责会话业务数据落库。
- 不负责向量检索。

重要约束：

- 根据项目约束，AI 面试会话存储固定走 MySQL。

### 14.4 `infrastructure/persistence/pgvector/`

职责：

- 实现向量存储与相似度检索。

边界：

- 只用于 RAG。
- 不用于会话表存储。

### 14.5 `infrastructure/llm/`

职责：

- 实现大模型调用适配。

典型实现：

- `openai_chat_adapter.py`
- `langchain_chat_adapter.py`
- `openai_audio_adapter.py`
- `openai_realtime_adapter.py`

边界：

- 只负责技术接入。
- 不负责业务分支判断。

### 14.6 `infrastructure/agents/`

职责：

- 实现多 Agent 或 AutoGen 适配。

边界：

- 它是能力实现层，不是业务流程层。

### 14.7 `infrastructure/text/`

职责：

- 放技术性文本清洗工具，例如 markdown cleaner。

边界：

- 如果是纯业务规则，应回到 `domain/services` 或 `domain/policies`。

### 14.8 `infrastructure/factories/`

职责：

- 负责创建 adapter 或 repository 的实例。

边界：

- 只负责装配和选择，不写业务规则。

---

## 15. `shared/` 边界

### 15.1 目录职责

`shared/` 存放跨层复用、且不属于某一单独业务域的通用能力。

### 15.2 `shared/constants/`

职责：

- 放默认值、常量定义。

边界：

- 不能积累业务流程逻辑。

### 15.3 `shared/streaming/`

职责：

- 统一 SSE、NDJSON 等输出格式工具。

边界：

- 只做传输格式封装，不做业务判断。

### 15.4 `shared/utils/`

职责：

- 放时间、文本等无业务归属的通用方法。

边界：

- 禁止把杂乱业务逻辑都塞进这里。

### 15.5 `shared/types/`

职责：

- 放跨模块公用类型定义。

边界：

- 不放领域实体。

---

## 16. 按业务能力划分的模块归属

### 16.1 Chat 能力

- API 层：`api/routes/chat_routes.py`
- 用例层：`application/use_cases/run_chat.py`、`stream_chat.py`
- 领域层：`domain/services/resume_section_clean_service.py`
- 基础设施层：`infrastructure/llm/openai_chat_adapter.py`

### 16.2 Interview 能力

- API 层：`api/routes/interview_routes.py`
- 用例层：`application/use_cases/generate_interview_turn.py`
- 共享编排：`application/services/interview_session_service.py`
- 领域层：`domain/models/*`、`domain/services/interview_flow_service.py`
- 持久化：`infrastructure/persistence/mysql/session_repository.py`
- 外部能力：`infrastructure/llm/*`、`infrastructure/agents/*`

### 16.3 RAG 能力

- API 层：`api/routes/rag_routes.py`
- 用例层：`run_rag_query.py`、`ingest_rag_documents.py`
- 领域层：`domain/services/rag_retrieval_service.py`
- 基础设施层：`infrastructure/persistence/pgvector/vector_store_adapter.py`

### 16.4 Audio 能力

- API 层：`api/routes/audio_routes.py`
- 用例层：`application/use_cases/transcribe_audio.py`
- 基础设施层：`infrastructure/llm/openai_audio_adapter.py`

### 16.5 Realtime 能力

- API 层：`api/routes/realtime_routes.py`
- 用例层：`application/use_cases/create_realtime_client_secret.py`
- 基础设施层：`infrastructure/llm/openai_realtime_adapter.py`

---

## 17. 当前重构时最容易越界的地方

下面这些是最需要明确切断的边界：

1. `application` 直接 import `api.schemas`
   - 应改为 `api -> mapper -> application.dto`

2. `domain` 直接依赖具体 `pgvector`、`LangChainClient`、`AutoGenAgentRuntime`
   - 应改为依赖 `ports`

3. `interview_app_service.py` 同时承担用例、流式输出、内存会话保存、状态组装
   - 应拆成多个 use case 和共享服务

4. 会话还保存在进程内存
   - 应迁到 `infrastructure/persistence/mysql/session_repository.py`

5. 一些文本清洗规则放在 infrastructure
   - 如果它是业务规则，应移到 `domain`

---

## 18. 目录边界判断口诀

当你不确定一个文件该放哪里时，可以按下面的顺序判断：

1. 它是不是 HTTP 请求或响应模型？
   - 是，放 `api`

2. 它是不是某个明确的业务用例入口？
   - 是，放 `application/use_cases`

3. 它是不是多个用例共享的编排动作？
   - 是，放 `application/services`

4. 它是不是业务规则、状态流转、实体和值对象？
   - 是，放 `domain`

5. 它是不是数据库、向量库、OpenAI、AutoGen、配置、日志的接入实现？
   - 是，放 `infrastructure`

6. 它是不是完全通用、没有业务归属的工具？
   - 是，放 `shared`

---

## 19. Python 后端流程注释规范（强制）

凡是在 `python-ai-backend/` 中编写、修改或重构后端代码，都必须为每个完整业务流程补充详细注释，不得省略。

强制要求如下：

1. 每个流程必须至少说明：
   - 入口意图（为什么需要这个流程）
   - 关键步骤（每一步做什么、依赖什么）
   - 关键分支（分支触发条件与处理策略）
   - 异常与兜底（失败时如何处理、如何返回）
   - 输出与副作用（返回值、状态变更、外部调用）

2. 注释必须解释“为什么这样做”和“业务含义”，不能只写“代码字面动作”。

3. 涉及跨层调用（`api -> application -> domain -> infrastructure`）时，必须在关键节点标明边界职责，避免后续维护误改层级。

4. 流式输出、会话状态推进、RAG 检索链路、音频转写、Realtime 密钥下发等核心流程，必须具备可让新同学快速接手的连续注释。

5. 缺少流程级详细注释的 Python 后端变更，视为不符合仓库规范，不得按“已完成”提交。

---

## 20. Python 后端内置提示词语言规范（强制）

凡是位于 `python-ai-backend/` 中、由后端代码内置并发送给 AI 模型的 `system prompt`、`instruction`、`prompt` 模板或同类提示词，必须使用中文编写，不得以内置英文提示词作为默认实现。
强制要求如下：
1. 适用范围包括但不限于：
   - LLM Chat system prompt
   - OCR 提示词
   - RAG 问答系统提示词
   - 面试流程中的内置角色提示词
   - 音频转写、结构化抽取、文本清洗等内置提示词模板
2. 如业务目标是处理英文简历、英文图片或其他非中文内容，也必须优先使用中文提示词描述任务约束，而不是直接写英文默认提示词。
3. 用户主动传入的原始文本、原始问题、原始文件内容不属于本规则限制范围；本规则只约束后端代码内置的提示词。
4. 新增或修改后端 AI 能力时，若发现内置提示词不是中文，应视为不符合仓库规范，不得按“已完成”提交。

---

## 21. 结论

这套目录结构的核心价值，不在于层数多，而在于边界明确：

- `api` 只做接口适配
- `application` 只做用例编排
- `domain` 只做业务规则
- `infrastructure` 只做外部实现
- `shared` 只做无业务归属的通用能力

后续重构 `python-ai-backend` 时，应优先保证边界正确，再追求目录细化。只要依赖方向干净，即使分阶段落地，也不会把系统继续做成“功能能跑但职责混杂”的结构。
