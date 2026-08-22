// author: jf
package com.resumebuilder.springaibackend.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record AuthRegisterRequest(
        @NotBlank(message = "邮箱不能为空")
        @Email(message = "请输入正确的邮箱地址")
        @Size(max = 254, message = "邮箱不能超过 254 个字符")
        String email,
        @NotBlank(message = "邮箱验证码不能为空")
        @Pattern(regexp = "\\d{6}", message = "邮箱验证码必须是 6 位数字")
        String verificationCode,
        @NotBlank(message = "密码不能为空")
        @Size(min = 8, message = "密码至少需要 8 个字符")
        String password,
        @NotBlank(message = "姓名不能为空")
        @Size(max = 64, message = "姓名不能超过 64 个字符")
        String displayName
) {
}
