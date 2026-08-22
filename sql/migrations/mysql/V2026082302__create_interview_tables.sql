-- author: jf
-- 创建 AI 面试表，并为旧表补齐账号隔离字段和索引。

CREATE TABLE IF NOT EXISTS interview_sessions (
    session_id            VARCHAR(64)  NOT NULL COMMENT '会话 ID',
    user_id               VARCHAR(64)  NOT NULL DEFAULT 'user-001' COMMENT '登录用户 ID',
    mode                  VARCHAR(32)  NOT NULL COMMENT 'candidate / interviewer',
    status                VARCHAR(32)  NOT NULL COMMENT 'active / finished',
    duration_minutes      INT          NOT NULL DEFAULT 60 COMMENT '面试时长（分钟）',
    elapsed_seconds       INT          NOT NULL DEFAULT 0 COMMENT '已进行秒数',
    memory_summary        VARCHAR(1024)     NULL COMMENT '会话记忆摘要',
    final_evaluation_json LONGTEXT          NULL COMMENT '最终评价 JSON',
    resume_snapshot_json  LONGTEXT          NULL COMMENT '简历快照 JSON',
    total_score           INT               NULL COMMENT '总分',
    passed                TINYINT(1)        NULL COMMENT '是否通过：1 通过，0 未通过',
    created_at            DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at            DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (session_id),
    KEY idx_interview_sessions_user_updated_at (user_id, updated_at),
    KEY idx_interview_sessions_updated_at (updated_at),
    KEY idx_interview_sessions_status_updated_at (status, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI 面试会话主表';

SET @interview_user_column_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'interview_sessions'
      AND COLUMN_NAME = 'user_id'
);

SET @add_interview_user_column_sql := IF(
    @interview_user_column_exists = 0,
    'ALTER TABLE interview_sessions ADD COLUMN user_id VARCHAR(64) NOT NULL DEFAULT ''user-001'' COMMENT ''登录用户 ID'' AFTER session_id',
    'SELECT 1'
);

PREPARE add_interview_user_column_stmt FROM @add_interview_user_column_sql;
EXECUTE add_interview_user_column_stmt;
DEALLOCATE PREPARE add_interview_user_column_stmt;

SET @interview_user_index_exists := (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'interview_sessions'
      AND INDEX_NAME = 'idx_interview_sessions_user_updated_at'
);

SET @add_interview_user_index_sql := IF(
    @interview_user_index_exists = 0,
    'ALTER TABLE interview_sessions ADD INDEX idx_interview_sessions_user_updated_at (user_id, updated_at)',
    'SELECT 1'
);

PREPARE add_interview_user_index_stmt FROM @add_interview_user_index_sql;
EXECUTE add_interview_user_index_stmt;
DEALLOCATE PREPARE add_interview_user_index_stmt;

CREATE TABLE IF NOT EXISTS interview_session_messages (
    id            BIGINT       NOT NULL AUTO_INCREMENT COMMENT '主键',
    session_id    VARCHAR(64)  NOT NULL COMMENT '所属会话 ID',
    seq_no        INT          NOT NULL COMMENT '会话内消息顺序号',
    role          VARCHAR(32)  NOT NULL COMMENT 'user / assistant',
    content       LONGTEXT     NOT NULL COMMENT '消息内容',
    score         INT               NULL COMMENT '本轮评分',
    score_comment VARCHAR(1024)     NULL COMMENT '评分点评',
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '消息创建时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_interview_session_messages_session_seq (session_id, seq_no),
    KEY idx_interview_session_messages_session_created_at (session_id, created_at),
    CONSTRAINT fk_interview_session_messages_session
        FOREIGN KEY (session_id) REFERENCES interview_sessions (session_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI 面试会话消息表';
