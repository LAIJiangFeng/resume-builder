// author: jf
package com.resumebuilder.springaibackend.service;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.resumebuilder.springaibackend.dto.InterviewSessionDetailResponse;
import com.resumebuilder.springaibackend.dto.InterviewSessionSummaryResponse;
import com.resumebuilder.springaibackend.dto.InterviewTurnRequest;
import com.resumebuilder.springaibackend.dto.InterviewTurnRequest.InterviewHistoryItem;
import com.resumebuilder.springaibackend.dto.InterviewTurnRequest.InterviewHistoryScore;
import com.resumebuilder.springaibackend.dto.InterviewTurnRequest.ResumeSnapshot;
import com.resumebuilder.springaibackend.dto.InterviewTurnResponse;
import com.resumebuilder.springaibackend.dto.InterviewTurnResponse.FinalEvaluation;
import com.resumebuilder.springaibackend.dto.InterviewTurnResponse.InterviewTurnScore;
import com.resumebuilder.springaibackend.entity.InterviewSessionEntity;
import com.resumebuilder.springaibackend.entity.InterviewSessionMessageEntity;
import com.resumebuilder.springaibackend.entity.InterviewSessionSummaryRow;
import com.resumebuilder.springaibackend.mapper.InterviewSessionMapper;
import com.resumebuilder.springaibackend.mapper.InterviewSessionMessageMapper;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class InterviewSessionStoreService {

    private static final int DEFAULT_DURATION_MINUTES = 60;

    private final InterviewSessionMapper sessionMapper;
    private final InterviewSessionMessageMapper messageMapper;
    private final ObjectMapper objectMapper;

    public InterviewSessionStoreService(
            InterviewSessionMapper sessionMapper,
            InterviewSessionMessageMapper messageMapper,
            ObjectMapper objectMapper
    ) {
        this.sessionMapper = sessionMapper;
        this.messageMapper = messageMapper;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public void saveTurn(String sessionId, String userId, InterviewTurnRequest request, InterviewTurnResponse response) {
        String safeSessionId = safeText(sessionId);
        String safeUserId = safeText(userId);
        if (safeSessionId.isBlank()) {
            return;
        }
        if (safeUserId.isBlank()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "请先登录后再保存面试会话");
        }

        FinalEvaluation finalEvaluation = response.finalEvaluation();
        InterviewSessionEntity entity = sessionMapper.selectById(safeSessionId);
        boolean isNew = entity == null;
        if (isNew) {
            entity = new InterviewSessionEntity();
            entity.setSessionId(safeSessionId);
            entity.setCreatedAt(LocalDateTime.now());
        } else if (!safeUserId.equals(safeText(entity.getUserId()))) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "未找到面试会话");
        }

        entity.setUserId(safeUserId);
        entity.setMode(normalizeMode(request.mode()));
        entity.setStatus(resolveStatus(request.command(), response.nextAction()));
        entity.setDurationMinutes(normalizeDuration(request.durationMinutes()));
        entity.setElapsedSeconds(normalizeElapsedSeconds(request.elapsedSeconds()));
        entity.setMemorySummary(normalizeMemorySummary(response.memorySummary()));
        entity.setFinalEvaluationJson(toJson(finalEvaluation));
        entity.setResumeSnapshotJson(toJson(request.resumeSnapshot()));
        entity.setTotalScore(finalEvaluation == null ? null : clampScore(finalEvaluation.totalScore()));
        entity.setPassed(finalEvaluation == null ? null : (finalEvaluation.passed() ? 1 : 0));
        entity.setUpdatedAt(LocalDateTime.now());

        if (isNew) {
            sessionMapper.insert(entity);
        } else {
            sessionMapper.updateById(entity);
        }

        messageMapper.delete(Wrappers.lambdaQuery(InterviewSessionMessageEntity.class)
                .eq(InterviewSessionMessageEntity::getSessionId, safeSessionId));

        List<StoredMessage> storedMessages = rebuildMessages(request, response);
        for (int i = 0; i < storedMessages.size(); i++) {
            StoredMessage message = storedMessages.get(i);
            InterviewSessionMessageEntity messageEntity = new InterviewSessionMessageEntity();
            messageEntity.setSessionId(safeSessionId);
            messageEntity.setSeqNo(i + 1);
            messageEntity.setRole(message.role());
            messageEntity.setContent(message.content());
            messageEntity.setScore(message.score());
            messageEntity.setScoreComment(message.scoreComment());
            messageMapper.insert(messageEntity);
        }
    }

    public List<InterviewSessionSummaryResponse> listSessions(String userId, int limit) {
        String safeUserId = safeText(userId);
        if (safeUserId.isBlank()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "请先登录后再查看面试历史");
        }
        int safeLimit = Math.max(1, Math.min(limit, 100));

        List<InterviewSessionSummaryRow> sessions = sessionMapper.selectSessionSummaries(safeUserId, safeLimit);
        List<InterviewSessionSummaryResponse> result = new ArrayList<>(sessions.size());

        for (InterviewSessionSummaryRow session : sessions) {
            Boolean passed = session.getPassed() == null ? null : session.getPassed() == 1;
            result.add(new InterviewSessionSummaryResponse(
                    session.getSessionId(),
                    normalizeMode(session.getMode()),
                    safeText(session.getStatus()),
                    session.getDurationMinutes() == null ? DEFAULT_DURATION_MINUTES : session.getDurationMinutes(),
                    session.getElapsedSeconds() == null ? 0 : session.getElapsedSeconds(),
                    toSafeInt(session.getMessageCount()),
                    session.getTotalScore(),
                    passed,
                    truncateText(safeText(session.getLastMessageContent()), 80),
                    session.getCreatedAt(),
                    session.getUpdatedAt()
            ));
        }
        return result;
    }

    public InterviewSessionDetailResponse getSessionDetail(String userId, String sessionId) {
        String safeUserId = safeText(userId);
        String safeSessionId = safeText(sessionId);
        if (safeUserId.isBlank()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "请先登录后再查看面试详情");
        }
        if (safeSessionId.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "sessionId 不能为空");
        }

        InterviewSessionEntity session = sessionMapper.selectById(safeSessionId);
        if (session == null || !safeUserId.equals(safeText(session.getUserId()))) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "未找到面试会话");
        }

        List<InterviewSessionMessageEntity> messageEntities = messageMapper.selectList(
                Wrappers.lambdaQuery(InterviewSessionMessageEntity.class)
                        .eq(InterviewSessionMessageEntity::getSessionId, safeSessionId)
                        .orderByAsc(InterviewSessionMessageEntity::getSeqNo)
        );

        List<InterviewSessionDetailResponse.InterviewMessageItem> messages = new ArrayList<>(messageEntities.size());
        for (InterviewSessionMessageEntity item : messageEntities) {
            InterviewTurnScore score = item.getScore() == null
                    ? null
                    : new InterviewTurnScore(clampScore(item.getScore()), safeText(item.getScoreComment()));

            messages.add(new InterviewSessionDetailResponse.InterviewMessageItem(
                    normalizeRole(item.getRole()),
                    safeText(item.getContent()),
                    score
            ));
        }

        return new InterviewSessionDetailResponse(
                session.getSessionId(),
                normalizeMode(session.getMode()),
                safeText(session.getStatus()),
                session.getDurationMinutes() == null ? DEFAULT_DURATION_MINUTES : session.getDurationMinutes(),
                session.getElapsedSeconds() == null ? 0 : session.getElapsedSeconds(),
                normalizeMemorySummary(session.getMemorySummary()),
                fromJson(session.getFinalEvaluationJson(), FinalEvaluation.class),
                fromJson(session.getResumeSnapshotJson(), ResumeSnapshot.class),
                messages,
                session.getCreatedAt(),
                session.getUpdatedAt()
        );
    }

    private List<StoredMessage> rebuildMessages(InterviewTurnRequest request, InterviewTurnResponse response) {
        List<StoredMessage> merged = new ArrayList<>();

        List<InterviewHistoryItem> history = request.history() == null ? List.of() : request.history();
        for (InterviewHistoryItem item : history) {
            if (item == null) {
                continue;
            }
            String content = safeText(item.content());
            if (content.isBlank()) {
                continue;
            }
            InterviewHistoryScore score = item.score();
            Integer scoreValue = score == null ? null : clampScore(score.score());
            String scoreComment = score == null ? "" : safeText(score.comment());
            merged.add(new StoredMessage(normalizeRole(item.role()), content, scoreValue, scoreComment));
        }

        String command = safeText(request.command()).toLowerCase(Locale.ROOT);
        String userInput = safeText(request.userInput());
        if ("continue".equals(command) && !userInput.isBlank()) {
            StoredMessage lastMessage = merged.isEmpty() ? null : merged.getLast();
            boolean duplicated = lastMessage != null
                    && "user".equals(lastMessage.role())
                    && userInput.equals(lastMessage.content());
            if (!duplicated) {
                merged.add(new StoredMessage("user", userInput, null, ""));
            }
        }

        String assistantReply = safeText(response.assistantReply());
        if (!assistantReply.isBlank()) {
            InterviewTurnScore turnScore = response.turnScore();
            Integer scoreValue = turnScore == null ? null : clampScore(turnScore.score());
            String scoreComment = turnScore == null ? "" : safeText(turnScore.comment());
            merged.add(new StoredMessage("assistant", assistantReply, scoreValue, scoreComment));
        }

        return merged;
    }

    private String resolveStatus(String command, String nextAction) {
        String safeCommand = safeText(command).toLowerCase(Locale.ROOT);
        String safeNextAction = safeText(nextAction).toLowerCase(Locale.ROOT);
        if ("finish".equals(safeCommand) || "finish".equals(safeNextAction)) {
            return "finished";
        }
        return "active";
    }

    private int normalizeDuration(Integer durationMinutes) {
        if (durationMinutes == null || durationMinutes <= 0) {
            return DEFAULT_DURATION_MINUTES;
        }
        return Math.min(durationMinutes, 180);
    }

    private int normalizeElapsedSeconds(Integer elapsedSeconds) {
        if (elapsedSeconds == null || elapsedSeconds < 0) {
            return 0;
        }
        return elapsedSeconds;
    }

    private String normalizeMode(String mode) {
        return "interviewer".equalsIgnoreCase(safeText(mode)) ? "interviewer" : "candidate";
    }

    private String normalizeRole(String role) {
        return "assistant".equalsIgnoreCase(safeText(role)) ? "assistant" : "user";
    }

    private int clampScore(Integer value) {
        if (value == null) {
            return 0;
        }
        return Math.max(0, Math.min(100, value));
    }

    private int toSafeInt(Long value) {
        if (value == null || value <= 0) {
            return 0;
        }
        return value > Integer.MAX_VALUE ? Integer.MAX_VALUE : value.intValue();
    }

    private String normalizeMemorySummary(String text) {
        return truncateText(safeText(text).replaceAll("\\s+", " "), 600);
    }

    private String truncateText(String text, int maxLen) {
        String value = safeText(text);
        if (value.length() <= maxLen) {
            return value;
        }
        return value.substring(0, Math.max(0, maxLen - 3)) + "...";
    }

    private String safeText(String text) {
        return text == null ? "" : text.trim();
    }

    private String toJson(Object value) {
        if (value == null) {
            return null;
        }
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception ignore) {
            return null;
        }
    }

    private <T> T fromJson(String raw, Class<T> type) {
        String safeRaw = safeText(raw);
        if (safeRaw.isBlank()) {
            return null;
        }
        try {
            return objectMapper.readValue(safeRaw, type);
        } catch (Exception ignore) {
            return null;
        }
    }

    private record StoredMessage(String role, String content, Integer score, String scoreComment) {
    }
}
