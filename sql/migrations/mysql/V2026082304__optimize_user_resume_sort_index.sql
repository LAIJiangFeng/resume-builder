-- author: jf
-- 兼容旧版简历表：先补充新排序索引，再移除旧索引。

SET @new_resume_sort_index_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'user_resumes'
      AND INDEX_NAME = 'idx_user_resumes_user_sort'
);

SET @add_resume_sort_index_sql := IF(
    @new_resume_sort_index_exists = 0,
    'ALTER TABLE user_resumes ADD INDEX idx_user_resumes_user_sort (user_id, is_active, updated_at, created_at)',
    'SELECT 1'
);

PREPARE add_resume_sort_index_stmt FROM @add_resume_sort_index_sql;
EXECUTE add_resume_sort_index_stmt;
DEALLOCATE PREPARE add_resume_sort_index_stmt;

SET @old_resume_sort_index_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'user_resumes'
      AND INDEX_NAME = 'idx_user_resumes_user_updated'
);

SET @drop_old_resume_sort_index_sql := IF(
    @old_resume_sort_index_exists > 0,
    'ALTER TABLE user_resumes DROP INDEX idx_user_resumes_user_updated',
    'SELECT 1'
);

PREPARE drop_old_resume_sort_index_stmt FROM @drop_old_resume_sort_index_sql;
EXECUTE drop_old_resume_sort_index_stmt;
DEALLOCATE PREPARE drop_old_resume_sort_index_stmt;
