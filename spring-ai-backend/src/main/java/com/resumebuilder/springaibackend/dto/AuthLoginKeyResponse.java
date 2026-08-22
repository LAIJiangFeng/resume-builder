// author: jf
package com.resumebuilder.springaibackend.dto;

public record AuthLoginKeyResponse(
        String algorithm,
        String keyId,
        String publicKey
) {
}
