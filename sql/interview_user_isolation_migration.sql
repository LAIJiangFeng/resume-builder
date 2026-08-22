-- author: jf
-- 手工执行：用于给已存在的 AI 面试会话表补齐用户隔离字段和索引。
-- 注意：历史数据统一归属到演示普通用户 user-001，新增会话仍由登录 token 派生真实用户。

SET @column_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'interview_sessions'
      AND COLUMN_NAME = 'user_id'
);

SET @add_user_id_column_sql := IF(
    @column_exists = 0,
    'ALTER TABLE interview_sessions ADD COLUMN user_id VARCHAR(64) NOT NULL DEFAULT ''user-001'' COMMENT ''登录用户 ID'' AFTER session_id',
    'SELECT 1'
);

PREPARE add_user_id_column_stmt FROM @add_user_id_column_sql;
EXECUTE add_user_id_column_stmt;
DEALLOCATE PREPARE add_user_id_column_stmt;

SET @index_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'interview_sessions'
      AND INDEX_NAME = 'idx_interview_sessions_user_updated_at'
);

SET @add_user_updated_index_sql := IF(
    @index_exists = 0,
    'ALTER TABLE interview_sessions ADD INDEX idx_interview_sessions_user_updated_at (user_id, updated_at)',
    'SELECT 1'
);

PREPARE add_user_updated_index_stmt FROM @add_user_updated_index_sql;
EXECUTE add_user_updated_index_stmt;
DEALLOCATE PREPARE add_user_updated_index_stmt;
