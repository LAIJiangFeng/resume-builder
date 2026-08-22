-- author: jf
-- 手工执行：为 PostgreSQL + pgvector 实例创建 RAG 使用的数据库。
-- 执行位置：请先连接管理库（例如 postgres），再执行本脚本。
-- 后续步骤：建库完成后，再把 sql/pgvector_rag_schema.sql 导入到 "resume-builder"。
-- 注意：数据库名包含连字符，SQL 中必须使用双引号。
-- 如果数据库已存在，本脚本会报错；此时可跳过本脚本，直接执行后续表结构脚本。

CREATE DATABASE "resume-builder"
WITH OWNER = pgvector
ENCODING = 'UTF8'
TEMPLATE = template0;
