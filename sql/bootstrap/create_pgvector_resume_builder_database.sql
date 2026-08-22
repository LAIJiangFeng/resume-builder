-- author: jf
-- 手工建库：连接 PostgreSQL 管理库后创建 RAG 使用的数据库。
-- 数据库已存在时跳过本脚本，随后由 Flyway 执行版本迁移。

CREATE DATABASE "resume-builder"
WITH OWNER = pgvector
ENCODING = 'UTF8'
TEMPLATE = template0;
