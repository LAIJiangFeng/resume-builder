// author: jf
package com.resumebuilder.springaibackend.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record AuthPasswordResetRequest(
        @NotBlank(message = "邮箱不能为空")
        @Email(message = "请输入正确的邮箱地址")
        String email,
        @NotBlank(message = "邮箱验证码不能为空")
        @Pattern(regexp = "\\d{6}", message = "邮箱验证码必须是 6 位数字")
        String verificationCode,
        @NotBlank(message = "新密码不能为空")
        @Size(min = 8, max = 128, message = "新密码长度必须在 8 到 128 位之间")
        String newPassword
) {
}
