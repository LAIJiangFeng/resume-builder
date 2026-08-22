// author: jf
package com.resumebuilder.springaibackend.dto;

import java.util.List;

public record AuthUserResponse(
        String id,
        String username,
        String displayName,
        String role,
        List<String> permissions
) {
}
