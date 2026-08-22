// author: jf
package com.resumebuilder.springaibackend.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;

public record AuthLoginRequest(
        @NotBlank(message = "登录账号不能为空")
        @Size(max = 254, message = "登录账号不能超过 254 个字符")
        String username,
        @NotBlank(message = "登录密钥标识不能为空")
        @Size(max = 128, message = "登录密钥标识不能超过 128 个字符")
        String keyId,
        @NotBlank(message = "登录加密密钥不能为空")
        @Size(max = 1024, message = "登录加密密钥不能超过 1024 个字符")
        String encryptedKey,
        @NotBlank(message = "登录加密随机数不能为空")
        @Size(max = 64, message = "登录加密随机数不能超过 64 个字符")
        String iv,
        @NotBlank(message = "登录密码密文不能为空")
        @Size(max = 4096, message = "登录密码密文不能超过 4096 个字符")
        String encryptedPassword,
        @NotNull(message = "登录请求时间不能为空")
        @Positive(message = "登录请求时间无效")
        Long issuedAt,
        @NotBlank(message = "登录请求标识不能为空")
        @Size(max = 64, message = "登录请求标识不能超过 64 个字符")
        String requestId
) {
}
