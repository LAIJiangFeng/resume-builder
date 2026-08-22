// author: jf
package com.resumebuilder.springaibackend.dto;

public record AuthUserContext(String userId, String role) {

    private static final int MAX_USER_ID_LENGTH = 64;

    public AuthUserContext {
        userId = userId == null ? "" : userId.trim();
        role = role == null ? "user" : role.trim();
        if (userId.length() > MAX_USER_ID_LENGTH) {
            throw new IllegalArgumentException("用户 ID 长度不能超过 64 个字符");
        }
        if (!"admin".equals(role)) {
            role = "user";
        }
    }

    public boolean isAdmin() {
        return "admin".equals(role);
    }
}
