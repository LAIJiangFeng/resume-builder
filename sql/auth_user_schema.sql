-- author: jf
-- 手工执行：创建登录用户、邮箱验证码表，并初始化本地演示管理员与普通用户。

CREATE TABLE IF NOT EXISTS auth_users (
    user_id        VARCHAR(64)   NOT NULL COMMENT '登录用户 ID',
    username       VARCHAR(254)  NOT NULL COMMENT '登录邮箱或演示账号',
    password_hash  CHAR(64)      NOT NULL COMMENT 'SHA-256 密码摘要',
    display_name   VARCHAR(64)   NOT NULL COMMENT '用户展示名称',
    role           VARCHAR(32)   NOT NULL COMMENT '角色：admin / user',
    permissions_json JSON        NOT NULL COMMENT 'AI 能力权限列表',
    enabled        TINYINT(1)    NOT NULL DEFAULT 1 COMMENT '是否启用',
    created_at     TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at     TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (user_id),
    UNIQUE KEY uk_auth_users_username (username),
    KEY idx_auth_users_role_enabled (role, enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='登录用户与角色权限表';

-- 兼容已创建的旧表，将账号字段扩展为完整邮箱长度。
ALTER TABLE auth_users
    MODIFY COLUMN username VARCHAR(254) NOT NULL COMMENT '登录邮箱或演示账号';

CREATE TABLE IF NOT EXISTS auth_email_verification_codes (
    email               VARCHAR(254) NOT NULL COMMENT '待验证邮箱',
    code_hash           CHAR(64)     NOT NULL COMMENT '验证码 HMAC-SHA256 摘要',
    expires_at          DATETIME(6)  NOT NULL COMMENT '验证码过期时间',
    resend_available_at DATETIME(6)  NOT NULL COMMENT '允许再次发送时间',
    failed_attempts     INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '连续验证失败次数',
    created_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at          TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (email),
    KEY idx_auth_email_codes_expires_at (expires_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='邮箱注册验证码表';

INSERT INTO auth_users (
    user_id,
    username,
    password_hash,
    display_name,
    role,
    permissions_json,
    enabled
) VALUES
    (
        'admin-001',
        'admin',
        '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9',
        '知识库管理员',
        'admin',
        JSON_ARRAY('resume_optimize', 'ai_interview', 'knowledge_admin'),
        1
    ),
    (
        'user-001',
        'user',
        'e606e38b0d8c19b24cf0ee3808183162ea7cd63ff7912dbb22b5e803286b4446',
        '求职用户',
        'user',
        JSON_ARRAY('resume_optimize', 'ai_interview'),
        1
    )
ON DUPLICATE KEY UPDATE
    username = VALUES(username),
    password_hash = VALUES(password_hash),
    display_name = VALUES(display_name),
    role = VALUES(role),
    permissions_json = VALUES(permissions_json),
    enabled = VALUES(enabled),
    updated_at = CURRENT_TIMESTAMP;
