// author: jf
package com.resumebuilder.springaibackend.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.resumebuilder.springaibackend.config.AppProperties;
import com.resumebuilder.springaibackend.dto.RagSource;
import com.resumebuilder.springaibackend.dto.InterviewStreamEvent;
import com.resumebuilder.springaibackend.dto.InterviewTurnRequest;
import com.resumebuilder.springaibackend.dto.InterviewTurnRequest.InterviewHistoryItem;
import com.resumebuilder.springaibackend.dto.InterviewTurnRequest.ResumeSnapshot;
import com.resumebuilder.springaibackend.dto.InterviewTurnResponse;
import com.resumebuilder.springaibackend.dto.InterviewTurnResponse.FinalEvaluation;
import com.resumebuilder.springaibackend.dto.InterviewTurnResponse.InterviewTurnScore;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.UUID;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.messages.AssistantMessage;
import org.springframework.ai.chat.messages.Message;
import org.springframework.ai.chat.messages.SystemMessage;
import org.springframework.ai.chat.messages.UserMessage;
import org.springframework.ai.chat.prompt.Prompt;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import reactor.core.Disposable;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Sinks;

@Service
public class InterviewTurnService {

    private static final Logger log = LoggerFactory.getLogger(InterviewTurnService.class);

    private static final String CANDIDATE_SYSTEM_PROMPT = """
            你是一名专业、严格、但表达友善的技术面试官。
            当前模式：用户是候选人，你负责提问、追问和评分。
            规则：
            1) 第一轮仅允许候选人进行 1-2 分钟自我介绍。
            2) 每一轮只提出 1 个主问题或 1 个追问。
            3) 必须基于简历内容提问，不得脱离简历。
            4) 流程按开场、高频基础技能、项目逐个深挖、场景题、工作经历核验、总结推进。
            5) 技能题优先围绕 Java 后端高频面试点，项目题重点追问技术细节、方案取舍、问题处理和量化结果。
            6) 每轮输出都要维护 memorySummary（不超过 220 中文字符），记录已确认信息、暴露短板和下一步追问方向。
            7) turnScore 必须基于本轮回答表现，不得因为简历写得好默认高分。
            8) 回答空泛、缺少技术细节、量化不清或参与度说不明白时，turnScore 不得高于 75 分。
            9) 回答跑题、前后矛盾、关键事实说不清或真实性存疑时，turnScore 不得高于 60 分。
            10) turnScore.comment 必须指出主要加分点或扣分点，避免空泛鼓励。
            11) 结束轮必须输出 finalEvaluation，总分权重为项目经历 70%、专业技能 20%、工作经历 5%、教育经历 5%，通过线为 90 分。
            12) 只输出一个 JSON 对象，不要 markdown，不要额外解释。
            13) assistantReply 必须是 JSON 的第一个字段。
            14) 全程使用中文。
            JSON 结构：
            {
              "assistantReply": "string",
              "phase": "opening|skills|work|projects|scenario|written|summary",
              "nextAction": "continue|finish",
              "turnScore": {"score": number, "comment": "string"} | null,
              "memorySummary": "string",
              "finalEvaluation": {
                "projectScore": number,
                "skillScore": number,
                "workScore": number,
                "educationScore": number,
                "totalScore": number,
                "passed": boolean,
                "summary": "string",
                "improvements": ["string"]
              } | null
            }
            """;

    private final ChatClient chatClient;
    private final ObjectMapper objectMapper;
    private final InterviewSessionStoreService interviewSessionStoreService;
    private final RagService ragService;
    private final AppProperties appProperties;
    private final ThreadPoolTaskExecutor interviewRagTaskExecutor;

    public InterviewTurnService(
            ChatClient chatClient,
            ObjectMapper objectMapper,
            InterviewSessionStoreService interviewSessionStoreService,
            RagService ragService,
            AppProperties appProperties,
            @Qualifier("interviewRagTaskExecutor") ThreadPoolTaskExecutor interviewRagTaskExecutor
    ) {
        this.chatClient = chatClient;
        this.objectMapper = objectMapper;
        this.interviewSessionStoreService = interviewSessionStoreService;
        this.ragService = ragService;
        this.appProperties = appProperties;
        this.interviewRagTaskExecutor = interviewRagTaskExecutor;
    }

    public Flux<InterviewStreamEvent> handleStream(InterviewTurnRequest request, String userId) {
        Sinks.Many<InterviewStreamEvent> sink = Sinks.many().unicast().onBackpressureBuffer();
        StringBuilder rawBuilder = new StringBuilder();
        StringBuilder lastAssistantReply = new StringBuilder();
        String sessionId = resolveSessionId(request);
        String ragContext = resolveInterviewRagContext(request);

        Disposable disposable = chatClient.prompt(new Prompt(buildMessages(request, ragContext))).stream().content()
                .subscribe(
                        chunk -> {
                            if (chunk == null || chunk.isEmpty()) {
                                return;
                            }
                            rawBuilder.append(chunk);
                            String partial = extractAssistantReplyFromPartialJson(rawBuilder.toString());
                            if (partial != null && !partial.isBlank() && !partial.equals(lastAssistantReply.toString())) {
                                lastAssistantReply.setLength(0);
                                lastAssistantReply.append(partial);
                                sink.tryEmitNext(new InterviewStreamEvent("chunk", partial));
                            }
                        },
                        error -> {
                            sink.tryEmitNext(new InterviewStreamEvent("error", safeText(error.getMessage())));
                            sink.tryEmitComplete();
                        },
                        () -> {
                            InterviewTurnResponse normalized = normalizeTurnResponse(rawBuilder.toString());
                            InterviewTurnResponse finalResponse = attachSessionId(normalized, sessionId);
                            try {
                                interviewSessionStoreService.saveTurn(sessionId, userId, request, finalResponse);
                            } catch (Exception ex) {
                                sink.tryEmitNext(new InterviewStreamEvent("error", safeText(ex.getMessage())));
                                sink.tryEmitComplete();
                                return;
                            }

                            String finalAssistantReply = safeText(finalResponse.assistantReply());
                            if (!finalAssistantReply.isBlank() && !finalAssistantReply.equals(lastAssistantReply.toString())) {
                                sink.tryEmitNext(new InterviewStreamEvent("chunk", finalAssistantReply));
                            }
                            sink.tryEmitNext(new InterviewStreamEvent("done", toJson(finalResponse)));
                            sink.tryEmitComplete();
                        }
                );

        return sink.asFlux().doOnCancel(disposable::dispose);
    }

    private List<Message> buildMessages(InterviewTurnRequest request, String ragContext) {
        String mode = normalizeMode(request.mode());
        String command = normalizeCommand(request.command());

        List<Message> messages = new ArrayList<>();
        messages.add(new SystemMessage(systemPrompt(mode, extractJobTitle(request.resumeSnapshot()))));

        List<InterviewHistoryItem> history = request.history() == null ? List.of() : request.history();
        int window = "start".equals(command) ? 4 : 8;
        int from = Math.max(0, history.size() - window);
        for (InterviewHistoryItem item : history.subList(from, history.size())) {
            if (item == null) {
                continue;
            }
            String role = safeText(item.role()).toLowerCase(Locale.ROOT);
            String content = truncateText(safeText(item.content()), 700);
            if (content.isBlank()) {
                continue;
            }
            if ("assistant".equals(role)) {
                messages.add(new AssistantMessage(content));
            } else {
                messages.add(new UserMessage(content));
            }
        }

        messages.add(new UserMessage(buildUserPrompt(request, mode, command, ragContext)));
        return messages;
    }

    private String systemPrompt(String mode, String jobTitle) {
        if ("interviewer".equals(mode)) {
            String role = jobTitle.isBlank() ? "技术岗位" : jobTitle;
            return """
                    你在一场模拟面试中扮演候选人。
                    当前模式：用户是面试官，你是候选人。
                    回答必须与简历事实保持一致，不能编造与简历冲突的信息。
                    回答要具体、完整、逻辑一致，并提前考虑面试官下一轮可能追问的细节。
                    如果面试官质疑真实性、指出回答不清楚或表达不满意，必须先复盘上一轮问题，再给出更稳妥的改进版回答。
                    每轮都要维护 memorySummary（不超过 220 中文字符）。
                    只输出一个 JSON 对象，不要 markdown，不要额外解释。
                    assistantReply 必须是 JSON 的第一个字段。
                    全程使用中文。
                    候选人目标岗位：""" + role + "\n"
                    + "JSON 结构：\n"
                    + "{\n"
                    + "  \"assistantReply\": \"string\",\n"
                    + "  \"phase\": \"opening|skills|work|projects|scenario|written|summary\",\n"
                    + "  \"nextAction\": \"continue|finish\",\n"
                    + "  \"turnScore\": null,\n"
                    + "  \"memorySummary\": \"string\",\n"
                    + "  \"finalEvaluation\": {\n"
                    + "    \"projectScore\": number,\n"
                    + "    \"skillScore\": number,\n"
                    + "    \"workScore\": number,\n"
                    + "    \"educationScore\": number,\n"
                    + "    \"totalScore\": number,\n"
                    + "    \"passed\": boolean,\n"
                    + "    \"summary\": \"string\",\n"
                    + "    \"improvements\": [\"string\"]\n"
                    + "  } | null\n"
                    + "}";
        }
        return CANDIDATE_SYSTEM_PROMPT;
    }

    private String buildUserPrompt(InterviewTurnRequest request, String mode, String command, String ragContext) {
        int durationMinutes = request.durationMinutes() == null || request.durationMinutes() <= 0 ? 60 : request.durationMinutes();
        int elapsedSeconds = request.elapsedSeconds() == null || request.elapsedSeconds() < 0 ? 0 : request.elapsedSeconds();
        int elapsedMin = elapsedSeconds / 60;
        int remainMin = Math.max(durationMinutes - elapsedMin, 0);

        String commandLine;
        if ("start".equals(command)) {
            commandLine = "candidate".equals(mode)
                    ? "现在开始面试。先请候选人进行 1-2 分钟自我介绍。"
                    : "现在开始面试。先给出简短开场，然后等待面试官提问。";
        } else if ("finish".equals(command)) {
            commandLine = "现在结束面试，并给出最终评估。";
        } else {
            commandLine = "本轮用户输入：" + (safeText(request.userInput()).isBlank() ? "（空）" : safeText(request.userInput()));
        }

        List<String> sections = new ArrayList<>(List.of(
                "角色关系：" + ("candidate".equals(mode) ? "你是面试官" : "你是候选人"),
                "目标时长：" + durationMinutes + " 分钟，已用：" + elapsedMin + " 分钟，剩余：" + remainMin + " 分钟。",
                "命令：" + command,
                commandLine,
                "",
                "记忆摘要（优先参考）：",
                normalizeMemorySummaryText(safeText(request.memorySummary())).isBlank()
                        ? "（无）"
                        : normalizeMemorySummaryText(safeText(request.memorySummary())),
                "",
                "简历快照：",
                buildResumeDigest(request.resumeSnapshot()),
                "",
                "请仅输出一个 JSON 对象。"
        ));

        if (StringUtils.hasText(ragContext)) {
            sections.add("");
            sections.add("知识库参考资料（仅在与简历和当前轮次相关时使用，不可编造）：");
            sections.add(ragContext);
        }
        return String.join("\n", sections);
    }

    private String resolveInterviewRagContext(InterviewTurnRequest request) {
        String retrievalQuery = buildInterviewRetrievalQuery(request);
        if (!StringUtils.hasText(retrievalQuery)) {
            return "";
        }

        double timeoutSeconds = Math.max(0.2D, appProperties.getInterviewRagTimeoutSeconds());
        int timeoutMillis = (int) Math.ceil(timeoutSeconds * 1000D);
        Future<List<RagSource>> future = null;
        try {
            future = interviewRagTaskExecutor.submit(
                    () -> ragService.searchSources(retrievalQuery, Math.max(1, appProperties.getInterviewRagTopK()))
            );
            List<RagSource> sources = filterSourcesBySimilarity(future.get(timeoutMillis, TimeUnit.MILLISECONDS));
            if (sources.isEmpty()) {
                return "";
            }
            return ragService.buildContext(sources);
        } catch (TimeoutException ex) {
            cancelFuture(future);
            log.warn("AI面试 RAG 检索超时，已取消后台任务并降级为无知识库上下文: {}", ex.getMessage());
            return "";
        } catch (InterruptedException ex) {
            cancelFuture(future);
            Thread.currentThread().interrupt();
            log.warn("AI面试 RAG 检索被中断，已取消后台任务并降级为无知识库上下文: {}", ex.getMessage());
            return "";
        } catch (ExecutionException ex) {
            log.warn("AI面试 RAG 检索失败，已降级为无知识库上下文: {}", ex.getCause() == null ? ex.getMessage() : ex.getCause().getMessage());
            return "";
        } catch (RuntimeException ex) {
            cancelFuture(future);
            log.warn("AI面试 RAG 检索失败，已降级为无知识库上下文: {}", ex.getMessage());
            return "";
        }
    }

    private void cancelFuture(Future<?> future) {
        if (future != null && !future.isDone()) {
            future.cancel(true);
        }
    }

    private String buildInterviewRetrievalQuery(InterviewTurnRequest request) {
        String mode = normalizeMode(request.mode());
        String command = normalizeCommand(request.command());
        String userInput = safeText(request.userInput());
        String resumeDigest = buildResumeDigest(request.resumeSnapshot());
        return String.join("\n",
                "面试模式：" + mode,
                "面试命令：" + command,
                "用户输入：" + (userInput.isBlank() ? "（空）" : userInput),
                "简历摘要：",
                resumeDigest
        ).trim();
    }

    private List<RagSource> filterSourcesBySimilarity(List<RagSource> sources) {
        List<RagSource> safeSources = sources == null ? List.of() : sources;
        double threshold = Math.max(0D, appProperties.getInterviewRagSimilarityThreshold());
        if (threshold <= 0D) {
            return safeSources;
        }
        return safeSources.stream()
                .filter(source -> extractSimilarity(source) >= threshold)
                .limit(Math.max(1, appProperties.getInterviewRagTopK()))
                .toList();
    }

    private double extractSimilarity(RagSource source) {
        if (source == null || source.metadata() == null) {
            return 0D;
        }
        Object value = source.metadata().get("similarity");
        if (value instanceof Number number) {
            return number.doubleValue();
        }
        try {
            return Double.parseDouble(String.valueOf(value));
        } catch (NumberFormatException ex) {
            return 0D;
        }
    }

    private String buildResumeDigest(ResumeSnapshot snapshot) {
        if (snapshot == null) {
            return "空";
        }
        StringBuilder sb = new StringBuilder();
        if (snapshot.basicInfo() != null) {
            sb.append("基础信息=")
                    .append("姓名:").append(safeText(snapshot.basicInfo().name())).append(",")
                    .append("岗位:").append(safeText(snapshot.basicInfo().jobTitle())).append(",")
                    .append("工作年限:").append(safeText(snapshot.basicInfo().workYears())).append(",")
                    .append("学历:").append(safeText(snapshot.basicInfo().educationLevel())).append("\n");
        }
        sb.append("技能=").append(truncateText(toPlainText(snapshot.skillsText()), 300)).append("\n");
        sb.append("工作经历数量=").append(snapshot.workList() == null ? 0 : snapshot.workList().size()).append("\n");
        sb.append("项目经历数量=").append(snapshot.projectList() == null ? 0 : snapshot.projectList().size()).append("\n");
        sb.append("教育经历数量=").append(snapshot.educationList() == null ? 0 : snapshot.educationList().size()).append("\n");
        if (!safeText(snapshot.selfIntro()).isBlank()) {
            sb.append("自我介绍=").append(truncateText(toPlainText(snapshot.selfIntro()), 300)).append("\n");
        }
        return sb.toString().trim();
    }

    private InterviewTurnResponse normalizeTurnResponse(String rawContent) {
        InterviewTurnResponse fallback = new InterviewTurnResponse(
                safeText(rawContent).isBlank() ? "本轮回答为空，请重试。" : safeText(rawContent),
                "opening",
                "continue",
                null,
                null,
                "",
                ""
        );

        try {
            JsonNode root = objectMapper.readTree(extractJsonObject(rawContent));

            String assistantReply = safeText(root.path("assistantReply").asText(fallback.assistantReply()));
            if (assistantReply.isBlank()) {
                assistantReply = fallback.assistantReply();
            }

            String phase = safeText(root.path("phase").asText("opening"));
            if (phase.isBlank()) {
                phase = "opening";
            }

            String nextAction = "finish".equalsIgnoreCase(safeText(root.path("nextAction").asText())) ? "finish" : "continue";

            InterviewTurnScore turnScore = null;
            JsonNode turnScoreNode = root.path("turnScore");
            if (turnScoreNode.isObject()) {
                turnScore = new InterviewTurnScore(
                        clampScore(turnScoreNode.path("score")),
                        safeText(turnScoreNode.path("comment").asText())
                );
            }

            FinalEvaluation finalEvaluation = null;
            JsonNode finalNode = root.path("finalEvaluation");
            if (finalNode.isObject()) {
                List<String> improvements = new ArrayList<>();
                JsonNode improvementsNode = finalNode.path("improvements");
                if (improvementsNode.isArray()) {
                    improvementsNode.forEach(item -> {
                        String value = safeText(item.asText());
                        if (!value.isBlank()) {
                            improvements.add(value);
                        }
                    });
                }

                finalEvaluation = new FinalEvaluation(
                        clampScore(finalNode.path("projectScore")),
                        clampScore(finalNode.path("skillScore")),
                        clampScore(finalNode.path("workScore")),
                        clampScore(finalNode.path("educationScore")),
                        clampScore(finalNode.path("totalScore")),
                        finalNode.path("passed").asBoolean(false),
                        safeText(finalNode.path("summary").asText()),
                        improvements
                );
            }

            return new InterviewTurnResponse(
                    assistantReply,
                    phase,
                    nextAction,
                    turnScore,
                    finalEvaluation,
                    normalizeMemorySummaryText(safeText(root.path("memorySummary").asText())),
                    safeText(root.path("sessionId").asText())
            );
        } catch (Exception ignore) {
            String partial = extractAssistantReplyFromPartialJson(rawContent);
            String assistantReply = partial == null ? fallback.assistantReply() : partial;
            return new InterviewTurnResponse(assistantReply, fallback.phase(), fallback.nextAction(), null, null, "", "");
        }
    }

    private String toJson(InterviewTurnResponse response) {
        try {
            return objectMapper.writeValueAsString(response);
        } catch (Exception ex) {
            return "{\"assistantReply\":\"" + escapeJson(response.assistantReply())
                    + "\",\"phase\":\"" + escapeJson(response.phase())
                    + "\",\"nextAction\":\"" + escapeJson(response.nextAction())
                    + "\",\"turnScore\":null,\"finalEvaluation\":null,\"memorySummary\":\"\",\"sessionId\":\"\"}";
        }
    }

    private String escapeJson(String value) {
        return safeText(value)
                .replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t");
    }

    private String extractJsonObject(String raw) {
        String text = safeText(raw);
        Matcher fenced = Pattern.compile("```(?:json)?\\s*([\\s\\S]*?)```").matcher(text);
        if (fenced.find()) {
            return safeText(fenced.group(1));
        }

        int first = text.indexOf('{');
        int last = text.lastIndexOf('}');
        if (first >= 0 && last > first) {
            return text.substring(first, last + 1);
        }
        return text;
    }

    private String extractAssistantReplyFromPartialJson(String raw) {
        String text = safeText(raw);
        int keyIndex = text.indexOf("\"assistantReply\"");
        if (keyIndex < 0) {
            return null;
        }

        int colonIndex = text.indexOf(':', keyIndex + "\"assistantReply\"".length());
        if (colonIndex < 0) {
            return null;
        }

        int start = skipWhitespace(text, colonIndex + 1);
        if (start < 0 || start >= text.length() || text.charAt(start) != '"') {
            return null;
        }

        StringBuilder encoded = new StringBuilder();
        boolean escaped = false;
        for (int i = start + 1; i < text.length(); i++) {
            char ch = text.charAt(i);
            if (!escaped && ch == '"') {
                break;
            }
            encoded.append(ch);
            escaped = !escaped && ch == '\\';
        }
        return decodePartialJsonString(encoded.toString());
    }

    private int skipWhitespace(String text, int fromIndex) {
        for (int i = Math.max(0, fromIndex); i < text.length(); i++) {
            if (!Character.isWhitespace(text.charAt(i))) {
                return i;
            }
        }
        return -1;
    }

    private String decodePartialJsonString(String raw) {
        StringBuilder output = new StringBuilder();
        for (int i = 0; i < raw.length(); i++) {
            char ch = raw.charAt(i);
            if (ch != '\\') {
                output.append(ch);
                continue;
            }
            if (i + 1 >= raw.length()) {
                break;
            }
            char next = raw.charAt(i + 1);
            switch (next) {
                case 'n' -> {
                    output.append('\n');
                    i++;
                }
                case 'r' -> {
                    output.append('\r');
                    i++;
                }
                case 't' -> {
                    output.append('\t');
                    i++;
                }
                case '"', '\\', '/' -> {
                    output.append(next);
                    i++;
                }
                default -> {
                    output.append(next);
                    i++;
                }
            }
        }
        return output.toString();
    }

    private int clampScore(JsonNode node) {
        if (node == null || !node.isNumber()) {
            return 0;
        }
        return Math.max(0, Math.min(100, node.asInt()));
    }

    private String normalizeMode(String mode) {
        return "interviewer".equalsIgnoreCase(safeText(mode)) ? "interviewer" : "candidate";
    }

    private String normalizeCommand(String command) {
        String normalized = safeText(command).toLowerCase(Locale.ROOT);
        if ("start".equals(normalized) || "finish".equals(normalized)) {
            return normalized;
        }
        return "continue";
    }

    private String resolveSessionId(InterviewTurnRequest request) {
        String command = normalizeCommand(request.command());
        if ("start".equals(command)) {
            return UUID.randomUUID().toString();
        }

        String sessionId = safeText(request.sessionId());
        if (!sessionId.isBlank()) {
            return sessionId;
        }
        return UUID.randomUUID().toString();
    }

    private InterviewTurnResponse attachSessionId(InterviewTurnResponse response, String sessionId) {
        return new InterviewTurnResponse(
                response.assistantReply(),
                response.phase(),
                response.nextAction(),
                response.turnScore(),
                response.finalEvaluation(),
                response.memorySummary(),
                safeText(sessionId)
        );
    }

    private String extractJobTitle(ResumeSnapshot snapshot) {
        if (snapshot == null || snapshot.basicInfo() == null) {
            return "";
        }
        return safeText(snapshot.basicInfo().jobTitle());
    }

    private String toPlainText(String text) {
        return safeText(text)
                .replaceAll("(?i)<br\\s*/?>", "\\n")
                .replaceAll("(?i)</?(p|div|li|ul|ol|h[1-6])[^>]*>", "\\n")
                .replaceAll("<[^>]*>", "")
                .replace("&nbsp;", " ")
                .replace("&lt;", "<")
                .replace("&gt;", ">")
                .replace("&amp;", "&")
                .replaceAll("\\n{3,}", "\\n\\n")
                .trim();
    }

    private String truncateText(String text, int maxLen) {
        String value = safeText(text);
        if (value.length() <= maxLen) {
            return value;
        }
        return value.substring(0, Math.max(0, maxLen - 3)) + "...";
    }

    private String normalizeMemorySummaryText(String content) {
        return truncateText(safeText(content).replaceAll("\\s+", " "), 600);
    }

    private String safeText(String text) {
        return text == null ? "" : text.trim();
    }
}
