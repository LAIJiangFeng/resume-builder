-- author: jf
-- 创建 Spring AI 与 Python 后端共用的 RAG 向量表。

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS rag_document_chunks (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding vector NOT NULL,
    source_id VARCHAR(255) NOT NULL DEFAULT '',
    chunk_index INTEGER NOT NULL DEFAULT 0,
    original_filename VARCHAR(255) NOT NULL DEFAULT '',
    original_content_type VARCHAR(255) NOT NULL DEFAULT '',
    source_type VARCHAR(32) NOT NULL DEFAULT '',
    ingest_source VARCHAR(64) NOT NULL DEFAULT '',
    embedding_model VARCHAR(128) NOT NULL DEFAULT '',
    embedding_dimensions INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE rag_document_chunks
    ADD COLUMN IF NOT EXISTS content TEXT;

ALTER TABLE rag_document_chunks
    ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE rag_document_chunks
    ADD COLUMN IF NOT EXISTS embedding vector;

ALTER TABLE rag_document_chunks
    ADD COLUMN IF NOT EXISTS source_id VARCHAR(255) NOT NULL DEFAULT '';

ALTER TABLE rag_document_chunks
    ADD COLUMN IF NOT EXISTS chunk_index INTEGER NOT NULL DEFAULT 0;

ALTER TABLE rag_document_chunks
    ADD COLUMN IF NOT EXISTS original_filename VARCHAR(255) NOT NULL DEFAULT '';

ALTER TABLE rag_document_chunks
    ADD COLUMN IF NOT EXISTS original_content_type VARCHAR(255) NOT NULL DEFAULT '';

ALTER TABLE rag_document_chunks
    ADD COLUMN IF NOT EXISTS source_type VARCHAR(32) NOT NULL DEFAULT '';

ALTER TABLE rag_document_chunks
    ADD COLUMN IF NOT EXISTS ingest_source VARCHAR(64) NOT NULL DEFAULT '';

ALTER TABLE rag_document_chunks
    ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(128) NOT NULL DEFAULT '';

ALTER TABLE rag_document_chunks
    ADD COLUMN IF NOT EXISTS embedding_dimensions INTEGER NOT NULL DEFAULT 0;

ALTER TABLE rag_document_chunks
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE rag_document_chunks
    ALTER COLUMN id DROP DEFAULT;

ALTER TABLE rag_document_chunks
    ALTER COLUMN id TYPE TEXT
    USING id::text;

ALTER TABLE rag_document_chunks
    ALTER COLUMN id SET DEFAULT gen_random_uuid()::text;

ALTER TABLE rag_document_chunks
    ALTER COLUMN metadata TYPE JSONB
    USING COALESCE(metadata::jsonb, '{}'::jsonb);

ALTER TABLE rag_document_chunks
    ALTER COLUMN metadata SET DEFAULT '{}'::jsonb;

ALTER TABLE rag_document_chunks
    ALTER COLUMN embedding TYPE vector
    USING embedding::vector;

UPDATE rag_document_chunks
SET source_id = ''
WHERE source_id IS NULL;

UPDATE rag_document_chunks
SET chunk_index = 0
WHERE chunk_index IS NULL;

UPDATE rag_document_chunks
SET original_filename = ''
WHERE original_filename IS NULL;

UPDATE rag_document_chunks
SET original_content_type = ''
WHERE original_content_type IS NULL;

UPDATE rag_document_chunks
SET source_type = ''
WHERE source_type IS NULL;

UPDATE rag_document_chunks
SET ingest_source = ''
WHERE ingest_source IS NULL;

UPDATE rag_document_chunks
SET embedding_model = ''
WHERE embedding_model IS NULL;

UPDATE rag_document_chunks
SET embedding_dimensions = vector_dims(embedding)
WHERE embedding IS NOT NULL
  AND COALESCE(embedding_dimensions, 0) <= 0;

ALTER TABLE rag_document_chunks
    ALTER COLUMN source_id SET DEFAULT '';

ALTER TABLE rag_document_chunks
    ALTER COLUMN chunk_index SET DEFAULT 0;

ALTER TABLE rag_document_chunks
    ALTER COLUMN original_filename SET DEFAULT '';

ALTER TABLE rag_document_chunks
    ALTER COLUMN original_content_type SET DEFAULT '';

ALTER TABLE rag_document_chunks
    ALTER COLUMN source_type SET DEFAULT '';

ALTER TABLE rag_document_chunks
    ALTER COLUMN ingest_source SET DEFAULT '';

ALTER TABLE rag_document_chunks
    ALTER COLUMN embedding_model SET DEFAULT '';

ALTER TABLE rag_document_chunks
    ALTER COLUMN embedding_dimensions SET DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_rag_document_chunks_source_id
    ON rag_document_chunks (source_id);

CREATE INDEX IF NOT EXISTS idx_rag_document_chunks_created_at
    ON rag_document_chunks (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_rag_document_chunks_metadata
    ON rag_document_chunks
    USING GIN (metadata);

CREATE INDEX IF NOT EXISTS idx_rag_document_chunks_embedding_profile
    ON rag_document_chunks (embedding_model, embedding_dimensions);
