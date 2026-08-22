// author: jf
package com.resumebuilder.springaibackend.controller;

import com.resumebuilder.springaibackend.dto.AuthEmailCodeRequest;
import com.resumebuilder.springaibackend.dto.AuthEmailCodeResponse;
import com.resumebuilder.springaibackend.dto.AuthLoginRequest;
import com.resumebuilder.springaibackend.dto.AuthLoginResponse;
import com.resumebuilder.springaibackend.dto.AuthLoginKeyResponse;
import com.resumebuilder.springaibackend.dto.AuthPasswordResetRequest;
import com.resumebuilder.springaibackend.dto.AuthRegisterRequest;
import com.resumebuilder.springaibackend.service.AuthService;
import com.resumebuilder.springaibackend.service.LoginPasswordCryptoService;
import jakarta.validation.Valid;
import org.springframework.http.CacheControl;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthService authService;
    private final LoginPasswordCryptoService loginPasswordCryptoService;

    public AuthController(AuthService authService, LoginPasswordCryptoService loginPasswordCryptoService) {
        this.authService = authService;
        this.loginPasswordCryptoService = loginPasswordCryptoService;
    }

    @GetMapping("/login-key")
    public ResponseEntity<AuthLoginKeyResponse> getLoginKey() {
        return ResponseEntity.ok()
                .cacheControl(CacheControl.noStore())
                .body(loginPasswordCryptoService.getLoginKey());
    }

    @PostMapping("/login")
    public AuthLoginResponse login(@Valid @RequestBody AuthLoginRequest request) {
        return authService.login(request);
    }

    @PostMapping("/email-code")
    public AuthEmailCodeResponse sendEmailCode(@Valid @RequestBody AuthEmailCodeRequest request) {
        return authService.sendRegistrationEmailCode(request);
    }

    @PostMapping("/password-reset/email-code")
    public AuthEmailCodeResponse sendPasswordResetEmailCode(@Valid @RequestBody AuthEmailCodeRequest request) {
        return authService.sendPasswordResetEmailCode(request);
    }

    @PostMapping("/register")
    public AuthLoginResponse register(@Valid @RequestBody AuthRegisterRequest request) {
        return authService.register(request);
    }

    @PostMapping("/password-reset")
    public void resetPassword(@Valid @RequestBody AuthPasswordResetRequest request) {
        authService.resetPassword(request);
    }
}
