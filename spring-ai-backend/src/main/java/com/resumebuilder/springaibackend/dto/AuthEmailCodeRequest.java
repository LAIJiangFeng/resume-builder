// author: jf
package com.resumebuilder.springaibackend.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record AuthEmailCodeRequest(
        @NotBlank(message = "邮箱不能为空")
        @Email(message = "请输入正确的邮箱地址")
        @Size(max = 254, message = "邮箱不能超过 254 个字符")
        String email
) {
}
