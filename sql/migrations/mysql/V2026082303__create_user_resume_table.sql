-- author: jf
-- 创建账号隔离的多简历表。

CREATE TABLE IF NOT EXISTS user_resumes (
    resume_id VARCHAR(64) NOT NULL COMMENT '简历 ID',
    user_id VARCHAR(64) NOT NULL COMMENT '所属用户 ID',
    resume_name VARCHAR(80) NOT NULL COMMENT '简历名称',
    resume_data_json JSON NOT NULL COMMENT '完整简历数据',
    is_active TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否为当前简历',
    active_user_id VARCHAR(64)
        GENERATED ALWAYS AS (CASE WHEN is_active = 1 THEN user_id ELSE NULL END) STORED
        COMMENT '用于约束账号唯一当前简历',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (resume_id),
    UNIQUE KEY uk_user_resumes_active_user (active_user_id),
    KEY idx_user_resumes_user_sort (user_id, is_active, updated_at, created_at),
    CONSTRAINT fk_user_resumes_user
        FOREIGN KEY (user_id) REFERENCES auth_users (user_id),
    CONSTRAINT chk_user_resumes_active CHECK (is_active IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='账号简历库';
