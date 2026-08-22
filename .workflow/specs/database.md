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
6. pgvector 表必须由部署阶段的独立 Flyway 容器执行 `sql/migrations/postgresql/` 中的版本迁移创建。

## 5. 版本迁移与 SQL 文件规则

1. 手工建库脚本只允许放入 `sql/bootstrap/`，不进入 Flyway 迁移历史。
2. MySQL 版本迁移固定放入 `sql/migrations/mysql/`，PostgreSQL 版本迁移固定放入 `sql/migrations/postgresql/`。
3. 本地演示数据只允许放入 `sql/seeds/`，生产部署禁止执行。
4. 迁移文件必须使用 `V<日期><序号>__<英文描述>.sql` 命名，并兼容全新数据库和当前已上线结构。
5. 已经执行的迁移文件禁止修改、重命名或删除；后续调整只能新增更高版本迁移。
6. 已有非空数据库统一以 `baselineVersion=0` 接入 Flyway，后续执行仓库内全部版本迁移。
7. 应用启动流程禁止执行项目 SQL；Docker 启动脚本和 CI/CD 只能通过独立 Flyway 容器执行迁移。
8. 生产迁移不得插入、覆盖或重置演示账号、测试数据和本地种子数据。
9. CI/CD 必须先备份数据库再迁移；任一迁移失败时不得继续更新应用容器。

## 6. AI 面试会话存储规则

1. AI 面试会话存储数据库固定为 MySQL。
2. PostgreSQL 仅用于向量存储相关能力，不用于会话表存储。
3. 会话结构迁移只允许存放在 `sql/migrations/mysql/`，不得在其他目录保留可独立执行的重复建表脚本。
4. MySQL 面试会话表和 pgvector RAG 向量表都禁止应用启动自动建表。
5. 表结构由 Docker 启动脚本或 CI/CD 在应用启动前通过 Flyway 执行。

## 7. 数据库操作工具规则

1. 需要直接访问数据库时，优先使用仓库规则指定的 `usql`。
2. 数据库连接信息必须从项目配置中查找。
3. 禁止在代码、文档或命令中硬编码敏感连接信息、账号、密码或密钥。

## 8. 职责边界

1. 数据库规则只定义数据存储、SQL、Mapper、pgvector 和会话存储边界。
2. 后端目录、Spring AI 后端分层、Python AI 后端依赖方向分别由对应专项规则定义。
3. 当数据库规则与目录职责同时适用时，必须同时满足两类约束，不得用数据库规则绕开目录边界。
