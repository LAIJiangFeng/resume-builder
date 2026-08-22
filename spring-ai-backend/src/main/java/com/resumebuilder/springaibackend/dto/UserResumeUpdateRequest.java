// author: jf
package com.resumebuilder.springaibackend.dto;

import com.fasterxml.jackson.databind.JsonNode;
import jakarta.validation.constraints.Size;

public record UserResumeUpdateRequest(
        @Size(max = 80, message = "简历名称不能超过 80 个字符") String name,
        JsonNode data
) {
}
