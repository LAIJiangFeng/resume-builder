<!-- author: jf -->
# Spring AI Backend 强制规则

## 1. 规则定位

本文档用于定义 `spring-ai-backend/` 的功能目标、目录结构、职责边界与开发限制。

`spring-ai-backend/` 的目标不是做一个泛化的 Java 示例工程，而是打造一个**基于 Java 的 AI 后端**，服务当前简历编辑、简历优化、AI 面试、RAG、语音与 Realtime 等业务场景，并与当前前端保持稳定联调能力。

凡涉及 `spring-ai-backend/` 的新增、修改、重构、迁移和目录调整，默认都必须遵守本文档。

注意：
- 本文档属于仓库级强制规则，不视为普通说明文档。
- 本文档采用“**基于当前结构强化约束**”原则：优先固定现有目录职责，不强制一步演进为 DDD、六边形架构或多模块工程。
- 如当前实现与本文档冲突，后续调整应优先向本文档靠拢；如确需例外，应先更新规则文档，再改代码。
- 涉及数据库、SQL、Mapper、pgvector 或会话存储时，必须同步遵守数据库与 SQL 强制规则。
- 涉及验证或测试代码边界时，必须同步遵守测试与验证强制规则。

---

## 2. 后端目标能力

`spring-ai-backend/` 需要承接并持续演进以下 AI 后端能力：

1. 聊天问答
   - 普通问答。
   - 流式问答（SSE）。
   - 输出清洗与内容净化。

2. AI 面试
   - 面试回合推进。
   - 会话保存、会话列表与会话详情查询。
   - 面试流式输出（NDJSON 或等价流式格式）。

3. RAG
   - 文档入库。
   - 基于向量检索的上下文召回与回答生成。

4. 音频能力
   - 音频转写。

5. Realtime 能力
   - Realtime 临时密钥或等价会话凭据签发。

6. 与前端契约兼容
   - 对外继续提供 `/api/ai/*` 风格接口。
   - 在前端尽量少改动的前提下承接已有功能。

---

## 3. 当前强制目录结构

`spring-ai-backend/` 必须围绕当前工程结构演进，顶层目录约束如下：

```text
spring-ai-backend/
├─ pom.xml
├─ README
├─ .env.example
├─ docker-compose.yml
├─ ../sql/
│  ├─ bootstrap/
│  ├─ migrations/
│  │  ├─ mysql/
│  │  └─ postgresql/
│  └─ seeds/
├─ src/main/java/com/resumebuilder/springaibackend/
│  ├─ controller/
│  ├─ service/
│  ├─ mapper/
│  ├─ entity/
│  ├─ dto/
│  ├─ config/
│  ├─ exception/
│  ├─ cleaner/
│  ├─ client/
│  ├─ vector/
│  ├─ embedding/
│  ├─ ocr/
│  ├─ realtime/
│  ├─ parser/
│  └─ chunking/
└─ src/main/resources/
   ├─ application.yml
   └─ mapper/
      └─ *.xml
```

补充说明：
- Java 包根路径固定为 `com.resumebuilder.springaibackend`。
- `service/` 只能存放真正带 `@Service` 注解、且承担业务用例编排职责的类。
- 非 `@Service` 文件禁止放入 `service/`；即使被 Service 依赖，也必须按功能职责放入外层职责目录。
- 允许在现有目录下继续细分子包，例如 `service/interview`、`dto/rag`、`mapper/interview`、`client/openai`、`vector/pgvector`。
- 允许使用本文档明确列出的外层职责目录：`client/`、`vector/`、`embedding/`、`ocr/`、`realtime/`、`parser/`、`chunking/`。
- **禁止**在没有规则支撑的情况下随意新增新的平级大目录，例如 `manager`、`core`、`common`、`helper`、`util`、`domain`、`application`、`infrastructure`。
- 如确需新增新的平级目录，必须先更新本文档，再落代码。

---

## 4. 分层依赖原则

当前结构下，依赖方向必须尽量保持清晰：

```text
controller -> service -> mapper -> entity
              |         |
              |         -> mapper.xml
              |
              -> cleaner / client / vector / embedding / ocr / realtime / parser / chunking / config / datasource
```

明确要求如下：

- `controller` 只面向 HTTP，不直接处理数据库、向量检索或模型 SDK 细节。
- `service` 负责业务编排，是当前结构下的主要业务层，但目录内只能放真正 `@Service` 业务编排类。
- `mapper` 只负责持久化访问，不承载业务流程。
- `entity` 只表达数据库持久化对象，不承担接口出参职责。
- `config` 只做配置装配与 Bean 创建，不写业务规则。
- `cleaner` 只做文本/Markdown/输出清洗，不写 HTTP 或数据库逻辑。
- `client`、`vector`、`embedding`、`ocr`、`realtime`、`parser`、`chunking` 是外层职责目录，用于承接非业务编排的支撑实现。

明确禁止的依赖与行为：

- `controller` 直接注入 `Mapper`、`JdbcTemplate`、`DataSource`、`ChatClient`、`VectorStore` 或其他底层客户端。
- `controller` 直接拼接 SQL、直接访问数据库、直接调用外部模型 SDK。
- `mapper` 依赖 `service`、`controller`。
- `entity` 作为 Controller 的入参或直接响应给前端。
- `config` 中编写业务分支、业务流程、提示词拼接、数据清洗逻辑。

---

## 5. 目录职责边界

### 5.1 `controller/`

职责：
- 定义 `/api/ai/*` 接口。
- 接收请求、做参数校验、调用 `service`、返回 HTTP 响应。
- 处理流式返回的 HTTP 包装，例如 SSE、NDJSON。

边界：
- 不写核心业务判断。
- 不访问数据库。
- 不直接调用 OpenAI、Spring AI、pgvector、JDBC 等底层能力。
- 不承载长 Prompt、长 SQL、复杂状态推进逻辑。

### 5.2 `service/`

职责：
- 承接当前结构下的核心业务编排。
- 按能力拆分聊天、面试、RAG、音频、Realtime 等服务。
- 串联 AI 调用、数据存储、向量检索、文本清洗等步骤。

强制定位：
- `service/` 只允许存放真正带 `@Service` 注解、且以业务用例或流程编排为核心职责的类。
- 没有 `@Service` 注解的 Java 文件一律不得放入 `service/`。
- `@Service` 只是进入 `service/` 的必要条件，不是充分条件；如果主要职责不是业务编排，必须放到对应外层职责目录。
- 即使被业务 Service 依赖，SDK client、HTTP client support、provider adapter、VectorStore 适配、pgvector repository、Embedding provider、OCR 实现、WebSocket handler、parser、chunker、support/helper 类也不得放入 `service/`。

边界：
- 一个 Service 应围绕单一业务能力或单一职责展开，禁止演变为“全能大服务”。
- 当一个类同时承担聊天、RAG、面试、转写、持久化等多种职责时，应拆分。
- Service 可以依赖 `mapper`、`entity`、`cleaner`、`config` 和必要的外层职责目录实现，但禁止写死任何 PostgreSQL、MySQL 或其他数据库 SQL 字符串。
- MySQL 自定义业务 SQL 必须下沉到 `mapper.xml`，不能写在 Service 中。
- PostgreSQL + pgvector 的向量写入和检索必须通过 Spring AI `VectorStore` / `PgVectorStore`，不能在 Service 或 Repository 中手写 pgvector SQL。

### 5.3 `mapper/`

职责：
- 定义 MyBatis / MyBatis-Plus 持久化接口。
- 面向数据库表和查询结果做映射。
- Java `mapper/` 目录只允许存放带 `@Mapper` 的 Mapper 接口。

边界：
- 不写业务编排。
- 不写 HTTP 逻辑。
- 不依赖 `service`。
- 不存放 MyBatis 查询投影、结果行对象、Row/Projection 类；这类持久化结果对象必须放入 `entity/`，对外 API 模型才放入 `dto/`。

强制限制：
- 业务 SQL（Mapper 自定义 SQL）必须写在 `src/main/resources/mapper/*.xml` 中。
- **禁止**在 Mapper 接口中使用 `@Select`、`@Update`、`@Insert`、`@Delete` 等注解承载业务 SQL。

### 5.4 `entity/`

职责：
- 定义数据库实体与表映射对象。
- 承接 MySQL 会话表等持久化对象。

边界：
- 不直接作为 API 请求或响应模型。
- 不编写业务流程方法。
- 不承载 AI 调用、清洗逻辑、控制器逻辑。

### 5.5 `dto/`

职责：
- 定义接口请求、接口响应、流式事件、服务间轻量传输对象。
- 对外接口模型命名优先使用 `*Request`、`*Response`、`*Event`。

边界：
- 不写数据库映射注解。
- 不写业务逻辑。
- 不写控制器、Service、Mapper 行为。
- 不把 `entity` 直接混入为对外契约模型。

### 5.6 `config/`

职责：
- 管理应用配置、数据源、Spring Bean、属性绑定、向量库与 AI 客户端装配。

边界：
- 不写业务规则。
- 不做会话流程推进。
- 不在应用启动时执行项目自写的一次性建表 SQL。
- pgvector 禁止后端自动建表，Spring AI `PgVectorStore` 必须保持 `initializeSchema(false)`；表结构由应用启动前的独立 Flyway 容器执行 `sql/migrations/postgresql/` 中的版本迁移创建。
- 不在配置类中做复杂业务初始化。

### 5.7 `exception/`

职责：
- 定义异常类型、全局异常处理、统一错误响应映射。

边界：
- 不替代正常业务分支。
- 不做数据库操作。
- 不做 AI 调用。

### 5.8 `cleaner/`

职责：
- 放文本清洗、Markdown 清洗、模型输出净化、格式标准化等能力。

边界：
- 不放 HTTP 逻辑。
- 不放数据库访问。
- 不放面试回合状态机或 RAG 检索编排。

### 5.9 `client/`

职责：
- 放外部 HTTP、AI Provider、SDK、RestClient、WebSocket 上游接入支撑。
- 按 provider 或能力继续细分，例如 `client/openai`、`client/ollama`、`client/dashscope`。

边界：
- 不写业务编排。
- 不写数据库访问。
- 不放 Controller 或接口 DTO。
- 不把 provider 选择逻辑和业务流程混在一起。

### 5.10 `vector/`

职责：
- 放向量库访问、Spring AI `VectorStore` / `PgVectorStore` 适配、RAG 向量仓储封装。
- RAG 向量写入必须调用 `VectorStore.add`。
- RAG 相似度检索必须调用 `VectorStore.similaritySearch`。

边界：
- 不手写 pgvector 插入、检索、建表或索引 SQL。
- 不承载回答生成、上下文拼装等业务编排。
- 不存放 MySQL 会话持久化逻辑。

### 5.11 `embedding/`

职责：
- 放 Embedding 抽象、Embedding provider 选择、Spring AI `EmbeddingModel` adapter。
- 支持按配置在 OpenAI、Ollama 等 Embedding provider 间切换。

边界：
- 不写 RAG 问答业务编排。
- 不写 pgvector SQL。
- 不直接处理 HTTP 接口。

### 5.12 `ocr/`

职责：
- 放 OCR 能力接入、图片/文件识别、视觉模型 OCR 调用与结果解析支撑。

边界：
- 不写上传接口包装。
- 不写 RAG 入库编排。
- 不放通用 RestClient 基础类，通用上游调用支撑应放 `client/`。

### 5.13 `realtime/`

职责：
- 放 Realtime、语音 WebSocket handler、DashScope Realtime ASR 桥接、协议转换与音频流支撑。

边界：
- Realtime 凭据签发业务编排仍放 `service/`。
- 上游 HTTP / WebSocket client 通用支撑放 `client/`。
- 不写 Controller 或数据库访问。

### 5.14 `parser/`

职责：
- 放文档解析、文件内容提取、上传文件内容标准化等支撑能力。

边界：
- 不写 RAG 入库业务编排。
- 不写向量库保存或检索逻辑。

### 5.15 `chunking/`

职责：
- 放文本切块、分段策略、chunk metadata 构造等支撑能力。

边界：
- 不写 RAG 问答编排。
- 不写向量库保存或检索逻辑。

### 5.16 `src/main/resources/`

职责：
- `application.yml`：应用配置。
- `mapper/*.xml`：Mapper 自定义 SQL。

边界：
- 不存放临时脚本。
- 不存放一次性建表 SQL。
- 手工建库、版本迁移和本地种子 SQL 必须分别放入仓库根目录 `sql/bootstrap/`、`sql/migrations/` 和 `sql/seeds/`。

---

## 6. 功能归属规则

当前 Spring AI 后端的能力应按下列方式归属：

### 6.1 Chat

- 接口放 `controller/`
- 请求响应模型放 `dto/`
- 聊天、流式输出、输出净化编排放 `service/`
- OpenAI / Ollama / 其他上游调用支撑放 `client/`
- 文本清洗细节放 `cleaner/`

### 6.2 Interview

- 面试接口放 `controller/`
- 面试请求、响应、流事件模型放 `dto/`
- 面试回合推进、会话编排放 `service/`
- 面试会话持久化放 `mapper/` + `entity/` + `mapper.xml`

### 6.3 RAG

- RAG 接口放 `controller/`
- RAG 请求响应模型放 `dto/`
- 检索编排、上下文拼装、回答生成放 `service/`
- 向量库写入、检索和 Spring AI `VectorStore` 封装放 `vector/`
- Embedding provider 选择、Embedding adapter 放 `embedding/`
- 文档解析、文件内容提取放 `parser/`
- 文本切块放 `chunking/`
- OCR 识别支撑放 `ocr/`
- 向量库配置与接入放 `config/`

### 6.4 Audio

- 音频转写接口放 `controller/`
- 音频请求响应模型放 `dto/`
- 转写调用编排放 `service/`
- 上游 ASR / OCR / 语音 provider 接入支撑按职责放 `client/`、`ocr/` 或 `realtime/`

### 6.5 Realtime

- Realtime 凭据接口放 `controller/`
- Realtime 请求响应模型放 `dto/`
- 凭据签发与上游调用编排放 `service/`
- WebSocket handler、DashScope Realtime ASR 桥接、协议转换放 `realtime/`
- 通用上游 client 支撑放 `client/`

---

## 7. 数据库与 SQL 强制约束

Spring AI 后端涉及数据库、SQL、Mapper、pgvector、一次性 SQL 与会话存储时，必须统一遵守数据库与 SQL 强制规则。

本文档只保留 Spring AI 后端目录职责与分层边界；数据库细则以数据库与 SQL 强制规则为准。

---

## 8. 目录扩展限制

在当前结构下，允许的扩展方式如下：

1. 在现有层内按业务能力拆子包，但必须符合目录本身职责
   - 例如 `service/chat/`、`service/interview/`、`dto/rag/`、`mapper/interview/`。
   - `service/` 子包仍只能放真正 `@Service` 业务编排类。

2. 在 `resources/mapper/` 中增加 XML
   - 用于承接新增 Mapper SQL。

3. 在对应数据库的 `sql/migrations/` 子目录中增加更高版本迁移
   - 仅用于 DDL、索引和兼容性数据迁移，已执行文件禁止修改。

4. 在本文档列出的外层职责目录中按 provider 或能力继续细分
   - 例如 `client/openai/`、`client/dashscope/`、`vector/pgvector/`、`embedding/ollama/`、`realtime/dashscope/`。

明确禁止：

- 未经规则更新，新增新的平级架构层，如 `domain/`、`application/`、`infrastructure/`、`adapter/`。
- 新增语义模糊的大杂烩目录，如 `common/`、`helper/`、`misc/`、`utils/`、`manager/`。
- 把非 `@Service` 支撑类放进 `service/`。
- 把 SDK client、provider adapter、repository、parser、chunker、WebSocket handler 等支撑实现伪装成 Service 后继续堆在 `service/`。
- 把所有能力继续堆进单个 `AiController` 或单个 `AiGatewayService` 而不做按能力拆分。

---

## 9. 新增文件放置判断口径

当你不确定一个 Spring AI 后端文件该放哪里时，按下面顺序判断：

1. 它是不是 HTTP 接口、参数接收、响应返回、流式 HTTP 包装？
   - 是，放 `controller/`

2. 它是不是聊天、面试、RAG、转写、Realtime 的业务用例或流程编排逻辑，并且类本身需要 `@Service` 注解？
   - 是，放 `service/`
   - 不是 `@Service`，禁止放 `service/`

3. 它是不是外部 HTTP、AI Provider、RestClient、SDK、WebSocket 上游调用支撑？
   - 是，放 `client/`

4. 它是不是向量库写入、相似度检索、Spring AI `VectorStore` / `PgVectorStore` 封装？
   - 是，放 `vector/`
   - 必须使用 Spring AI `VectorStore` 的 `add`、`similaritySearch` 等能力
   - 禁止手写 pgvector SQL

5. 它是不是 Embedding 抽象、provider 选择、EmbeddingModel adapter？
   - 是，放 `embedding/`

6. 它是不是 OCR 识别、图片/文件识别、视觉模型 OCR 结果解析？
   - 是，放 `ocr/`

7. 它是不是 Realtime WebSocket handler、语音流协议桥接、DashScope Realtime ASR 支撑？
   - 是，放 `realtime/`

8. 它是不是文档解析、文件内容提取、上传文件内容标准化？
   - 是，放 `parser/`

9. 它是不是文本切块、chunk metadata 构造、分段策略？
   - 是，放 `chunking/`

10. 它是不是数据库访问接口或自定义 SQL？
   - 接口放 `mapper/`
   - MySQL 自定义 SQL 放 `src/main/resources/mapper/*.xml`
   - PostgreSQL + pgvector 向量库操作优先使用 Spring AI `VectorStore`，不新增后端代码 SQL

11. 它是不是表映射实体？
   - 是，放 `entity/`

12. 它是不是请求、响应、事件、轻量数据传输对象？
   - 是，放 `dto/`

13. 它是不是配置、属性、Bean、数据源或客户端装配？
   - 是，放 `config/`

14. 它是不是异常定义或统一异常处理？
   - 是，放 `exception/`

15. 它是不是文本净化、Markdown 清洗、输出规整？
   - 是，放 `cleaner/`

16. 如果以上都不是
   - 优先检查是否应归入现有目录的子包。
   - 仍无法归类时，先更新本文档，再新增目录。

---

## 10. Spring 后端内置提示词语言规范（强制）

凡是位于 `spring-ai-backend/` 中、由后端代码内置并发送给 AI 模型的 `system prompt`、`instruction`、`prompt` 模板或同类提示词，必须使用中文编写，不得以内置英文提示词作为默认实现。
强制要求如下：
1. 适用范围包括但不限于：
   - Chat 默认系统提示词
   - RAG 系统提示词
   - 面试角色与回合推进提示词
   - OCR、转写、抽取、清洗等内置提示词模板
2. 如业务目标是处理英文内容，也必须优先使用中文提示词表达规则、约束和输出要求，而不是直接写英文默认提示词。
3. 用户请求参数中主动传入的原始文本内容不属于本规则限制范围；本规则只约束后端代码内置提示词。
4. 新增或修改 Spring 后端 AI 能力时，若内置提示词不是中文，应视为不符合仓库规范，不得按“已完成”提交。

---

## 11. 结论

`spring-ai-backend/` 当前阶段的核心不是追求架构名词，而是先把**目录边界、功能归属、SQL 位置、数据库职责**固定住：

- `controller` 只做接口适配
- `service` 只放真正 `@Service` 业务编排类
- `mapper + mapper.xml` 只做持久化访问
- `entity` 只做数据库实体
- `dto` 只做数据传输模型
- `config` 只做配置与装配
- `exception` 只做异常处理
- `cleaner` 只做文本清洗
- `client / vector / embedding / ocr / realtime / parser / chunking` 只做对应功能支撑实现

只要边界清晰，`spring-ai-backend` 就能在不大改前端的前提下，持续演进成一个稳定、可维护、面向 AI 业务的 Java 后端。
