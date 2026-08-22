<!-- author: jf -->
# 数据库与 SQL 强制规则

## 1. 规则定位

本文档用于定义 `resume-builder` 仓库的数据库、SQL、Mapper、pgvector 与会话存储约束。

适用于以下场景：

1. 修改 `spring-ai-backend/` 中的 Mapper、Service、Config、Entity、DTO 或数据库访问链路。
2. 修改 `python-ai-backend/` 中的持久化、向量库或会话存储相关实现。
3. 新增或调整 `sql/` 下建表、索引、初始化脚本。
4. 涉及 MySQL、PostgreSQL、pgvector、MyBatis、Spring AI `VectorStore` / `PgVectorStore` 的任何任务。

## 2. 运行期 SQL 禁止规则

1. 后端运行代码中禁止写死 PostgreSQL、MySQL 或其他数据库 SQL 字符串。
2. 禁止在运行代码中直接写入 `SELECT`、`INSERT`、`UPDATE`、`DELETE`、`CREATE`、`ALTER`、`DROP`、索引初始化等 SQL 语句。
3. 禁止在 Controller、Service、Config、Repository、启动流程或其他运行时代码中拼接并执行业务 SQL 或一次性建表 SQL。

## 3. MySQL 与 MyBatis 规则

1. MySQL 如确需自定义业务 SQL，必须写在 `mapper.xml` 文件中。
2. MySQL 自定义业务 SQL 不允许直接写在 Mapper 接口注解里，例如 `@Select`、`@Update`、`@Insert`、`@Delete`。
3. Spring AI 后端 Java `mapper/` 目录只允许存放带 `@Mapper` 的 Mapper 接口。
4. MyBatis 查询投影、结果行对象、Row / Projection 类必须放入 `entity/`。
5. 对外 API 请求、响应、事件模型必须放入 `dto/`，不得直接复用 `entity/` 作为前端契约。

## 4. PostgreSQL 与 pgvector 规则

1. PostgreSQL 仅用于向量存储相关能力。
2. PostgreSQL 不用于 AI 面试会话表、消息表等业务会话数据存储。
3. PostgreSQL + pgvector 向量库存储与相似度检索必须优先使用 Spring AI `VectorStore` / `PgVectorStore` 提供的 `add`、`similaritySearch` 等能力。
4. 禁止在后端代码中手写 pgvector 插入、检索、建表或索引 SQL。
5. 禁止 Spring AI `PgVectorStore` 自动建表；Spring AI 后端必须保持 `initializeSchema(false)`。
6. pgvector 表必须由开发者手工执行 `sql/pgvector_rag_schema.sql` 创建。

## 5. 一次性 SQL 文件规则

1. 建表、索引、初始化等一次性 SQL 必须写入仓库根目录 `sql/` 下的独立 `.sql` 文件。
2. 禁止把一次性 SQL 写进 Java、Python、配置类、启动逻辑或 README 示例中替代正式 SQL 文件。
3. 禁止在应用启动流程中执行项目自写的一次性 SQL。
4. 表结构初始化由开发者手工执行。

## 6. AI 面试会话存储规则

1. AI 面试会话存储数据库固定为 MySQL。
2. PostgreSQL 仅用于向量存储相关能力，不用于会话表存储。
3. 会话建表脚本仅保留一份：`sql/interview_schema.sql`。
4. MySQL 面试会话表和 pgvector RAG 向量表都禁止应用启动自动建表。
5. 表结构必须由开发者手工执行 `sql/interview_schema.sql` 与 `sql/pgvector_rag_schema.sql`。

## 7. 数据库操作工具规则

1. 需要直接访问数据库时，优先使用仓库规则指定的 `usql`。
2. 数据库连接信息必须从项目配置中查找。
3. 禁止在代码、文档或命令中硬编码敏感连接信息、账号、密码或密钥。

## 8. 职责边界

1. 数据库规则只定义数据存储、SQL、Mapper、pgvector 和会话存储边界。
2. 后端目录、Spring AI 后端分层、Python AI 后端依赖方向分别由对应专项规则定义。
3. 当数据库规则与目录职责同时适用时，必须同时满足两类约束，不得用数据库规则绕开目录边界。
