// author: jf
package com.resumebuilder.springaibackend.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.resumebuilder.springaibackend.dto.UserResumeCreateRequest;
import com.resumebuilder.springaibackend.dto.UserResumeResponse;
import com.resumebuilder.springaibackend.dto.UserResumeSummaryResponse;
import com.resumebuilder.springaibackend.dto.UserResumeUpdateRequest;
import com.resumebuilder.springaibackend.entity.UserResumeEntity;
import com.resumebuilder.springaibackend.mapper.UserResumeMapper;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class UserResumeService {

    private static final String DEFAULT_RESUME_NAME = "我的简历";
    private static final int MAX_RESUME_NAME_LENGTH = 80;

    private final UserResumeMapper userResumeMapper;
    private final ObjectMapper objectMapper;

    public UserResumeService(UserResumeMapper userResumeMapper, ObjectMapper objectMapper) {
        this.userResumeMapper = userResumeMapper;
        this.objectMapper = objectMapper;
    }

    public List<UserResumeSummaryResponse> listResumes(String userId) {
        return userResumeMapper.selectByUserId(requireUserId(userId)).stream()
                .map(this::toSummaryResponse)
                .toList();
    }

    public UserResumeResponse getResume(String userId, String resumeId) {
        return toResponse(requireOwnedResume(userId, resumeId));
    }

    @Transactional
    public UserResumeResponse createResume(String userId, UserResumeCreateRequest request) {
        String safeUserId = requireUserId(userId);
        lockUser(safeUserId);
        boolean firstResume = userResumeMapper.countByUserId(safeUserId) == 0;
        UserResumeEntity entity = new UserResumeEntity();
        entity.setResumeId(UUID.randomUUID().toString());
        entity.setUserId(safeUserId);
        entity.setResumeName(normalizeName(request == null ? null : request.name(), DEFAULT_RESUME_NAME));
        entity.setResumeDataJson(writeData(request == null ? null : request.data()));
        entity.setActive(firstResume ? 1 : 0);
        userResumeMapper.insert(entity);
        return toResponse(requireOwnedResume(safeUserId, entity.getResumeId()));
    }

    @Transactional
    public UserResumeResponse updateResume(String userId, String resumeId, UserResumeUpdateRequest request) {
        UserResumeEntity current = requireOwnedResume(userId, resumeId);
        current.setResumeName(normalizeName(request == null ? null : request.name(), current.getResumeName()));
        current.setResumeDataJson(writeData(request == null ? null : request.data()));
        if (userResumeMapper.updateOwned(current) == 0) {
            throw resumeNotFound();
        }
        return toResponse(requireOwnedResume(userId, resumeId));
    }

    @Transactional
    public UserResumeResponse activateResume(String userId, String resumeId) {
        String safeUserId = requireUserId(userId);
        lockUser(safeUserId);
        UserResumeEntity current = requireOwnedResume(safeUserId, resumeId);
        if (!isActive(current)) {
            userResumeMapper.deactivateAll(current.getUserId());
            if (userResumeMapper.activateOwned(current.getUserId(), current.getResumeId()) == 0) {
                throw resumeNotFound();
            }
        }
        return toResponse(requireOwnedResume(current.getUserId(), current.getResumeId()));
    }

    @Transactional
    public UserResumeResponse duplicateResume(String userId, String resumeId) {
        String safeUserId = requireUserId(userId);
        lockUser(safeUserId);
        UserResumeEntity source = requireOwnedResume(safeUserId, resumeId);
        UserResumeCreateRequest request = new UserResumeCreateRequest(
                buildCopyName(source.getResumeName()),
                readData(source.getResumeDataJson())
        );
        return createResume(source.getUserId(), request);
    }

    @Transactional
    public void deleteResume(String userId, String resumeId) {
        String safeUserId = requireUserId(userId);
        lockUser(safeUserId);
        UserResumeEntity target = requireOwnedResume(safeUserId, resumeId);
        if (userResumeMapper.countByUserId(target.getUserId()) <= 1) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "至少需要保留一份简历");
        }
        if (userResumeMapper.deleteOwned(target.getUserId(), target.getResumeId()) == 0) {
            throw resumeNotFound();
        }
        if (isActive(target)) {
            List<UserResumeEntity> remaining = userResumeMapper.selectByUserId(target.getUserId());
            if (remaining.isEmpty()) {
                throw new ResponseStatusException(HttpStatus.CONFLICT, "至少需要保留一份简历");
            }
            userResumeMapper.deactivateAll(target.getUserId());
            userResumeMapper.activateOwned(target.getUserId(), remaining.getFirst().getResumeId());
        }
    }

    private UserResumeEntity requireOwnedResume(String userId, String resumeId) {
        UserResumeEntity entity = userResumeMapper.selectOwnedById(requireUserId(userId), requireResumeId(resumeId));
        if (entity == null) {
            throw resumeNotFound();
        }
        return entity;
    }

    private void lockUser(String userId) {
        if (userResumeMapper.lockUser(userId) == null) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "登录账号不存在");
        }
    }

    private UserResumeSummaryResponse toSummaryResponse(UserResumeEntity entity) {
        return new UserResumeSummaryResponse(
                entity.getResumeId(),
                entity.getResumeName(),
                isActive(entity),
                entity.getCreatedAt(),
                entity.getUpdatedAt()
        );
    }

    private UserResumeResponse toResponse(UserResumeEntity entity) {
        return new UserResumeResponse(
                entity.getResumeId(),
                entity.getResumeName(),
                readData(entity.getResumeDataJson()),
                isActive(entity),
                entity.getCreatedAt(),
                entity.getUpdatedAt()
        );
    }

    private String normalizeName(String name, String fallback) {
        String safeName = name == null ? "" : name.trim();
        if (safeName.isBlank()) {
            safeName = fallback == null ? "" : fallback.trim();
        }
        if (safeName.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "简历名称不能为空");
        }
        if (safeName.length() > MAX_RESUME_NAME_LENGTH) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "简历名称不能超过 80 个字符");
        }
        return safeName;
    }

    private String buildCopyName(String sourceName) {
        String suffix = " - 副本";
        String safeSource = normalizeName(sourceName, DEFAULT_RESUME_NAME);
        if (safeSource.length() + suffix.length() <= MAX_RESUME_NAME_LENGTH) {
            return safeSource + suffix;
        }
        return safeSource.substring(0, MAX_RESUME_NAME_LENGTH - suffix.length()) + suffix;
    }

    private String writeData(JsonNode data) {
        JsonNode safeData = data == null || data.isNull() ? objectMapper.createObjectNode() : data;
        if (!safeData.isObject()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "简历数据必须是 JSON 对象");
        }
        try {
            return objectMapper.writeValueAsString(safeData);
        } catch (JsonProcessingException ex) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "简历数据不是有效的 JSON 对象", ex);
        }
    }

    private JsonNode readData(String rawData) {
        if (rawData == null || rawData.isBlank()) {
            return objectMapper.createObjectNode();
        }
        try {
            JsonNode data = objectMapper.readTree(rawData);
            return data != null && data.isObject() ? data : objectMapper.createObjectNode();
        } catch (JsonProcessingException ex) {
            ObjectNode fallback = objectMapper.createObjectNode();
            fallback.put("invalidStoredData", true);
            return fallback;
        }
    }

    private boolean isActive(UserResumeEntity entity) {
        return Integer.valueOf(1).equals(entity.getActive());
    }

    private String requireUserId(String userId) {
        String safeUserId = userId == null ? "" : userId.trim();
        if (safeUserId.isBlank()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "请先登录后再管理简历");
        }
        return safeUserId;
    }

    private String requireResumeId(String resumeId) {
        String safeResumeId = resumeId == null ? "" : resumeId.trim();
        if (safeResumeId.isBlank() || safeResumeId.length() > 64) {
            throw resumeNotFound();
        }
        return safeResumeId;
    }

    private ResponseStatusException resumeNotFound() {
        return new ResponseStatusException(HttpStatus.NOT_FOUND, "简历不存在");
    }
}
