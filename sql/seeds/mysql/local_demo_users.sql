-- author: jf
-- 仅供本地开发：创建或重置演示管理员和普通用户。
-- 生产环境禁止执行本文件。

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
