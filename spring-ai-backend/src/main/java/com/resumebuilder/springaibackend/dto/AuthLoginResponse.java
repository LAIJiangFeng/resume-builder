// author: jf
package com.resumebuilder.springaibackend.dto;

public record AuthLoginResponse(
        String accessToken,
        AuthUserResponse user
) {
}
