-- author: jf
-- 创建登录用户和邮箱验证码表；生产迁移不写入演示账号。

CREATE TABLE IF NOT EXISTS auth_users (
    user_id          VARCHAR(64)   NOT NULL COMMENT '登录用户 ID',
    username         VARCHAR(254)  NOT NULL COMMENT '登录邮箱或演示账号',
    password_hash    CHAR(64)      NOT NULL COMMENT 'SHA-256 密码摘要',
    display_name     VARCHAR(64)   NOT NULL COMMENT '用户展示名称',
    role             VARCHAR(32)   NOT NULL COMMENT '角色：admin / user',
    permissions_json JSON          NOT NULL COMMENT 'AI 能力权限列表',
    enabled          TINYINT(1)    NOT NULL DEFAULT 1 COMMENT '是否启用',
    created_at       TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at       TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (user_id),
    UNIQUE KEY uk_auth_users_username (username),
    KEY idx_auth_users_role_enabled (role, enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='登录用户与角色权限表';

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='邮箱注册与密码重置验证码表';
