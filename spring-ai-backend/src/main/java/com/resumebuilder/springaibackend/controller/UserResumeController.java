// author: jf
package com.resumebuilder.springaibackend.controller;

import com.resumebuilder.springaibackend.dto.AuthUserContext;
import com.resumebuilder.springaibackend.dto.UserResumeCreateRequest;
import com.resumebuilder.springaibackend.dto.UserResumeResponse;
import com.resumebuilder.springaibackend.dto.UserResumeSummaryResponse;
import com.resumebuilder.springaibackend.dto.UserResumeUpdateRequest;
import com.resumebuilder.springaibackend.service.AuthService;
import com.resumebuilder.springaibackend.service.UserResumeService;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/resumes")
public class UserResumeController {

    private final AuthService authService;
    private final UserResumeService userResumeService;

    public UserResumeController(AuthService authService, UserResumeService userResumeService) {
        this.authService = authService;
        this.userResumeService = userResumeService;
    }

    @GetMapping
    public List<UserResumeSummaryResponse> list(
            @RequestHeader(value = "Authorization", required = false) String authorization
    ) {
        return userResumeService.listResumes(requireUser(authorization).userId());
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public UserResumeResponse create(
            @RequestHeader(value = "Authorization", required = false) String authorization,
            @Valid @RequestBody(required = false) UserResumeCreateRequest request
    ) {
        return userResumeService.createResume(requireUser(authorization).userId(), request);
    }

    @GetMapping("/{resumeId}")
    public UserResumeResponse get(
            @RequestHeader(value = "Authorization", required = false) String authorization,
            @PathVariable String resumeId
    ) {
        return userResumeService.getResume(requireUser(authorization).userId(), resumeId);
    }

    @PutMapping("/{resumeId}")
    public UserResumeResponse update(
            @RequestHeader(value = "Authorization", required = false) String authorization,
            @PathVariable String resumeId,
            @Valid @RequestBody UserResumeUpdateRequest request
    ) {
        return userResumeService.updateResume(requireUser(authorization).userId(), resumeId, request);
    }

    @PostMapping("/{resumeId}/activate")
    public UserResumeResponse activate(
            @RequestHeader(value = "Authorization", required = false) String authorization,
            @PathVariable String resumeId
    ) {
        return userResumeService.activateResume(requireUser(authorization).userId(), resumeId);
    }

    @PostMapping("/{resumeId}/duplicate")
    @ResponseStatus(HttpStatus.CREATED)
    public UserResumeResponse duplicate(
            @RequestHeader(value = "Authorization", required = false) String authorization,
            @PathVariable String resumeId
    ) {
        return userResumeService.duplicateResume(requireUser(authorization).userId(), resumeId);
    }

    @DeleteMapping("/{resumeId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(
            @RequestHeader(value = "Authorization", required = false) String authorization,
            @PathVariable String resumeId
    ) {
        userResumeService.deleteResume(requireUser(authorization).userId(), resumeId);
    }

    private AuthUserContext requireUser(String authorization) {
        return authService.requireUser(authorization);
    }
}
