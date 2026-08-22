// author: jf
package com.resumebuilder.springaibackend.dto;

public record AuthEmailCodeResponse(
        long cooldownSeconds,
        long expiresInSeconds
) {
}
