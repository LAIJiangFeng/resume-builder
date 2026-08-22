// author: jf
package com.resumebuilder.springaibackend.dto;

import java.time.LocalDateTime;

public record UserResumeSummaryResponse(
        String resumeId,
        String name,
        boolean active,
        LocalDateTime createdAt,
        LocalDateTime updatedAt
) {
}
