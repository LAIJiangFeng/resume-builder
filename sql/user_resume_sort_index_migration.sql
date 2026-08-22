-- author: jf
-- 优化账号简历列表排序，避免完整简历数据参与文件排序。

ALTER TABLE user_resumes
    DROP INDEX idx_user_resumes_user_updated,
    ADD INDEX idx_user_resumes_user_sort (user_id, is_active, updated_at, created_at);
