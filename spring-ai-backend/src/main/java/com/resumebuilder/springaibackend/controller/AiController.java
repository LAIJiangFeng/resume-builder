// author: jf
package com.resumebuilder.springaibackend.controller;

import com.resumebuilder.springaibackend.dto.ChatRequest;
import com.resumebuilder.springaibackend.dto.ChatResponse;
import com.resumebuilder.springaibackend.dto.AuthUserContext;
import com.resumebuilder.springaibackend.dto.RagIngestRequest;
import com.resumebuilder.springaibackend.dto.RagIngestResponse;
import com.resumebuilder.springaibackend.dto.RagQueryRequest;
import com.resumebuilder.springaibackend.dto.RagQueryResponse;
import com.resumebuilder.springaibackend.dto.RagUploadProgressEvent;
import com.resumebuilder.springaibackend.dto.RagUploadResponse;
import com.resumebuilder.springaibackend.dto.RealtimeClientSecretRequest;
import com.resumebuilder.springaibackend.dto.RealtimeClientSecretResponse;
import com.resumebuilder.springaibackend.dto.InterviewSessionDetailResponse;
import com.resumebuilder.springaibackend.dto.InterviewSessionSummaryResponse;
import com.resumebuilder.springaibackend.dto.InterviewStreamEvent;
import com.resumebuilder.springaibackend.dto.InterviewTurnRequest;
import com.resumebuilder.springaibackend.service.AiGatewayService;
import com.resumebuilder.springaibackend.service.AuthService;
import com.resumebuilder.springaibackend.service.RagService;
import com.resumebuilder.springaibackend.service.RealtimeSessionService;
import com.resumebuilder.springaibackend.service.InterviewSessionStoreService;
import com.resumebuilder.springaibackend.service.InterviewTurnService;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import reactor.core.publisher.Flux;

@RestController
@RequestMapping("/api/ai")
public class AiController {

    private final AiGatewayService aiGatewayService;
    private final InterviewTurnService interviewTurnService;
    private final RealtimeSessionService realtimeSessionService;
    private final InterviewSessionStoreService interviewSessionStoreService;
    private final RagService ragService;
    private final AuthService authService;

    public AiController(
            AiGatewayService aiGatewayService,
            InterviewTurnService interviewTurnService,
            RealtimeSessionService realtimeSessionService,
            InterviewSessionStoreService interviewSessionStoreService,
            RagService ragService,
            AuthService authService
    ) {
        this.aiGatewayService = aiGatewayService;
        this.interviewTurnService = interviewTurnService;
        this.realtimeSessionService = realtimeSessionService;
        this.interviewSessionStoreService = interviewSessionStoreService;
        this.ragService = ragService;
        this.authService = authService;
    }

    @PostMapping("/chat")
    public ChatResponse chat(
            @RequestHeader(value = "Authorization", required = false) String authorization,
            @Valid @RequestBody ChatRequest request
    ) {
        requireUser(authorization);
        boolean sanitize = Boolean.TRUE.equals(request.sanitizeOutput());
        return new ChatResponse(aiGatewayService.chat(request.message(), sanitize));
    }

    @PostMapping(value = "/chat/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<String>> streamChat(
            @RequestHeader(value = "Authorization", required = false) String authorization,
            @Valid @RequestBody ChatRequest request
    ) {
        requireUser(authorization);
        boolean sanitize = Boolean.TRUE.equals(request.sanitizeOutput());
        return aiGatewayService.streamChatWithSink(request.message(), sanitize)
                .map(chunk -> ServerSentEvent.<String>builder().event("chunk").data(chunk).build())
                .onErrorResume(ex -> Flux.just(
                        ServerSentEvent.<String>builder()
                                .event("error")
                                .data(ex.getMessage() == null ? "流式响应失败" : ex.getMessage())
                                .build()
                ));
    }

    @PostMapping("/realtime/client-secret")
    public RealtimeClientSecretResponse createRealtimeClientSecret(
            @RequestHeader(value = "Authorization", required = false) String authorization,
            @RequestBody(required = false) RealtimeClientSecretRequest request
    ) {
        requireUser(authorization);
        RealtimeClientSecretRequest safeRequest = request == null
                ? new RealtimeClientSecretRequest(null, null)
                : request;
        return realtimeSessionService.createClientSecret(safeRequest);
    }

    @PostMapping(value = "/interview/turn/stream", produces = MediaType.APPLICATION_NDJSON_VALUE)
    public Flux<InterviewStreamEvent> interviewTurnStream(
            @RequestHeader(value = "Authorization", required = false) String authorization,
            @Valid @RequestBody InterviewTurnRequest request
    ) {
        AuthUserContext userContext = requireUser(authorization);
        return interviewTurnService.handleStream(request, userContext.userId());
    }


    @GetMapping("/interview/sessions")
    public List<InterviewSessionSummaryResponse> listInterviewSessions(
            @RequestHeader(value = "Authorization", required = false) String authorization,
            @RequestParam(value = "limit", defaultValue = "20") Integer limit
    ) {
        AuthUserContext userContext = requireUser(authorization);
        return interviewSessionStoreService.listSessions(userContext.userId(), limit == null ? 20 : limit);
    }

    @GetMapping("/interview/sessions/{sessionId}")
    public InterviewSessionDetailResponse getInterviewSession(
            @RequestHeader(value = "Authorization", required = false) String authorization,
            @PathVariable String sessionId
    ) {
        AuthUserContext userContext = requireUser(authorization);
        return interviewSessionStoreService.getSessionDetail(userContext.userId(), sessionId);
    }
    @PostMapping("/rag/query")
    public RagQueryResponse ragQuery(
            @RequestHeader(value = "Authorization", required = false) String authorization,
            @Valid @RequestBody RagQueryRequest request
    ) {
        requireUser(authorization);
        return ragService.ragQuery(request);
    }

    @PostMapping("/rag/documents")
    public RagIngestResponse ingestDocuments(
            @RequestHeader(value = "Authorization", required = false) String authorization,
            @Valid @RequestBody RagIngestRequest request
    ) {
        requireAdmin(authorization);
        return new RagIngestResponse(ragService.ingestDocuments(request));
    }

    @PostMapping(value = "/rag/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public RagUploadResponse uploadRagAssets(
            @RequestHeader(value = "Authorization", required = false) String authorization,
            @RequestParam("files") List<MultipartFile> files
    ) {
        requireAdmin(authorization);
        return ragService.uploadFiles(files);
    }

    @PostMapping(
            value = "/rag/upload/stream",
            consumes = MediaType.MULTIPART_FORM_DATA_VALUE,
            produces = MediaType.TEXT_EVENT_STREAM_VALUE
    )
    public Flux<ServerSentEvent<RagUploadProgressEvent>> uploadRagAssetsStream(
            @RequestHeader(value = "Authorization", required = false) String authorization,
            @RequestParam("files") List<MultipartFile> files
    ) {
        requireAdmin(authorization);
        return ragService.uploadFilesStream(files)
                .map(event -> ServerSentEvent.<RagUploadProgressEvent>builder()
                        .event(event.event())
                        .data(event)
                        .build());
    }

    private AuthUserContext requireUser(String authorization) {
        return authService.requireUser(authorization);
    }

    private AuthUserContext requireAdmin(String authorization) {
        return authService.requireAdmin(authorization);
    }
}
