// author: jf
package com.resumebuilder.springaibackend.dto;

import com.fasterxml.jackson.databind.JsonNode;
import java.time.LocalDateTime;

public record UserResumeResponse(
        String resumeId,
        String name,
        JsonNode data,
        boolean active,
        LocalDateTime createdAt,
        LocalDateTime updatedAt
) {
}
