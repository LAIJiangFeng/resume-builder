// author: jf
package com.resumebuilder.springaibackend.service;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.resumebuilder.springaibackend.dto.AuthEmailCodeRequest;
import com.resumebuilder.springaibackend.dto.AuthEmailCodeResponse;
import com.resumebuilder.springaibackend.dto.AuthLoginRequest;
import com.resumebuilder.springaibackend.dto.AuthLoginResponse;
import com.resumebuilder.springaibackend.dto.AuthPasswordResetRequest;
import com.resumebuilder.springaibackend.dto.AuthRegisterRequest;
import com.resumebuilder.springaibackend.dto.AuthUserContext;
import com.resumebuilder.springaibackend.dto.AuthUserResponse;
import com.resumebuilder.springaibackend.entity.AuthUserEntity;
import com.resumebuilder.springaibackend.mapper.AuthUserMapper;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.Base64;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.UUID;
import java.util.regex.Pattern;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class AuthService {

    private static final String TOKEN_TYPE = "Bearer ";
    private static final String HMAC_ALGORITHM = "HmacSHA256";
    private static final String TOKEN_ALGORITHM = "HS256";
    private static final String LOCAL_DEMO_TOKEN_SECRET = "resume-builder-local-demo-auth-secret";
    private static final String REGISTER_USER_ROLE = "user";
    private static final List<String> REGISTER_USER_PERMISSIONS = List.of("resume_optimize", "ai_interview");
    private static final Pattern EMAIL_PATTERN = Pattern.compile(
            "^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?(?:\\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$",
            Pattern.CASE_INSENSITIVE
    );

    private final AuthUserMapper authUserMapper;
    private final EmailVerificationService emailVerificationService;
    private final LoginPasswordCryptoService loginPasswordCryptoService;
    private final byte[] tokenSecret;
    private final long tokenTtlSeconds;

    public AuthService(
            AuthUserMapper authUserMapper,
            EmailVerificationService emailVerificationService,
            LoginPasswordCryptoService loginPasswordCryptoService,
            @Value("${app.auth.token-secret:}") String configuredSecret,
            @Value("${app.auth.token-ttl-seconds:43200}") long configuredTokenTtlSeconds
    ) {
        this.authUserMapper = authUserMapper;
        this.emailVerificationService = emailVerificationService;
        this.loginPasswordCryptoService = loginPasswordCryptoService;
        this.tokenSecret = resolveTokenSecret(configuredSecret);
        this.tokenTtlSeconds = Math.max(300L, configuredTokenTtlSeconds);
    }

    public AuthLoginResponse login(AuthLoginRequest request) {
        String username = normalizeUsername(request.username());
        String password = loginPasswordCryptoService.decryptPassword(request);
        AuthUserEntity account = authUserMapper.selectEnabledByUsername(username);
        if (account == null || !verifyPassword(password, account.getPasswordHash())) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "账号或密码错误");
        }
        return new AuthLoginResponse(createToken(account), toUserResponse(account));
    }

    public AuthEmailCodeResponse sendRegistrationEmailCode(AuthEmailCodeRequest request) {
        String email = normalizeUsername(request.email());
        validateEmail(email);
        if (authUserMapper.selectByUsername(email) != null) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "该邮箱已注册，请直接登录");
        }
        return emailVerificationService.sendRegistrationCode(email);
    }

    public AuthEmailCodeResponse sendPasswordResetEmailCode(AuthEmailCodeRequest request) {
        String email = normalizeUsername(request.email());
        validateEmail(email);
        if (authUserMapper.selectEnabledByUsername(email) == null) {
            return emailVerificationService.getCodeDeliveryWindow();
        }
        return emailVerificationService.sendPasswordResetCode(email);
    }

    @Transactional
    public AuthLoginResponse register(AuthRegisterRequest request) {
        String email = normalizeUsername(request.email());
        String displayName = normalizeDisplayName(request.displayName());
        String password = request.password() == null ? "" : request.password();

        validateEmail(email);
        if (password.length() < 8) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "密码至少需要 8 位");
        }
        if (displayName.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "姓名不能为空");
        }
        if (displayName.length() > 64) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "姓名不能超过 64 个字符");
        }
        if (authUserMapper.selectByUsername(email) != null) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "该邮箱已注册，请直接登录");
        }
        emailVerificationService.verifyForRegistration(email, request.verificationCode());

        AuthUserEntity account = new AuthUserEntity();
        account.setUserId(createRegisterUserId());
        account.setUsername(email);
        account.setPasswordHash(sha256(password));
        account.setDisplayName(displayName);
        account.setRole(REGISTER_USER_ROLE);
        account.setPermissionsJson(JSON.toJSONString(REGISTER_USER_PERMISSIONS));
        account.setEnabled(1);

        try {
            authUserMapper.insertUser(account);
        } catch (DuplicateKeyException ex) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "该邮箱已注册，请直接登录", ex);
        }
        emailVerificationService.consume(email);
        return new AuthLoginResponse(createToken(account), toUserResponse(account));
    }

    @Transactional
    public void resetPassword(AuthPasswordResetRequest request) {
        String email = normalizeUsername(request.email());
        String newPassword = request.newPassword() == null ? "" : request.newPassword();
        validateEmail(email);
        if (newPassword.length() < 8 || newPassword.length() > 128) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "新密码长度必须在 8 到 128 位之间");
        }

        emailVerificationService.verifyForPasswordReset(email, request.verificationCode());
        AuthUserEntity account = authUserMapper.selectEnabledByUsername(email);
        if (account == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "邮箱或验证码无效，请重新获取验证码");
        }
        int updatedRows = authUserMapper.updatePasswordHash(account.getUserId(), sha256(newPassword));
        if (updatedRows != 1) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "密码重置失败，请重新获取验证码后再试");
        }
        emailVerificationService.consume(email);
    }

    public AuthUserContext requireUser(String authorizationHeader) {
        String token = extractBearerToken(authorizationHeader);
        AuthUserEntity account = verifyToken(token);
        return new AuthUserContext(account.getUserId(), normalizeRole(account.getRole()));
    }

    public AuthUserContext requireAdmin(String authorizationHeader) {
        AuthUserContext userContext = requireUser(authorizationHeader);
        if (!userContext.isAdmin()) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "只有管理员可以维护知识库");
        }
        return userContext;
    }

    private String createToken(AuthUserEntity account) {
        long issuedAt = Instant.now().getEpochSecond();
        long expiresAt = issuedAt + tokenTtlSeconds;

        JSONObject header = new JSONObject();
        header.put("alg", TOKEN_ALGORITHM);
        header.put("typ", "JWT");

        JSONObject payload = new JSONObject();
        payload.put("sub", account.getUserId());
        payload.put("username", normalizeUsername(account.getUsername()));
        payload.put("displayName", account.getDisplayName());
        payload.put("role", normalizeRole(account.getRole()));
        payload.put("permissions", parsePermissions(account.getPermissionsJson()));
        payload.put("pwdv", createPasswordVersion(account.getPasswordHash()));
        payload.put("iat", issuedAt);
        payload.put("exp", expiresAt);

        String encodedHeader = encodeJson(header);
        String encodedPayload = encodeJson(payload);
        String signingInput = encodedHeader + "." + encodedPayload;
        return signingInput + "." + sign(signingInput);
    }

    private AuthUserEntity verifyToken(String token) {
        String[] parts = token.split("\\.");
        if (parts.length != 3) {
            throw invalidToken();
        }

        String signingInput = parts[0] + "." + parts[1];
        byte[] expected = sign(signingInput).getBytes(StandardCharsets.UTF_8);
        byte[] actual = parts[2].getBytes(StandardCharsets.UTF_8);
        if (!MessageDigest.isEqual(expected, actual)) {
            throw invalidToken();
        }

        JSONObject payload;
        try {
            payload = JSON.parseObject(new String(decode(parts[1]), StandardCharsets.UTF_8));
        } catch (RuntimeException ex) {
            throw invalidToken();
        }

        long expiresAt = payload.getLongValue("exp");
        if (expiresAt <= Instant.now().getEpochSecond()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "登录已过期，请重新登录");
        }

        AuthUserEntity account = authUserMapper.selectEnabledByUsername(normalizeUsername(payload.getString("username")));
        if (account == null || !account.getUserId().equals(payload.getString("sub"))) {
            throw invalidToken();
        }
        String expectedPasswordVersion = createPasswordVersion(account.getPasswordHash());
        String actualPasswordVersion = payload.getString("pwdv");
        if (actualPasswordVersion == null || !MessageDigest.isEqual(
                expectedPasswordVersion.getBytes(StandardCharsets.UTF_8),
                actualPasswordVersion.getBytes(StandardCharsets.UTF_8)
        )) {
            throw invalidToken();
        }
        return account;
    }

    private String extractBearerToken(String authorizationHeader) {
        String rawHeader = authorizationHeader == null ? "" : authorizationHeader.trim();
        if (rawHeader.length() <= TOKEN_TYPE.length()
                || !rawHeader.regionMatches(true, 0, TOKEN_TYPE, 0, TOKEN_TYPE.length())) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "请先登录后再使用 AI 能力");
        }
        String token = rawHeader.substring(TOKEN_TYPE.length()).trim();
        if (token.isBlank()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "请先登录后再使用 AI 能力");
        }
        return token;
    }

    private String sign(String signingInput) {
        try {
            Mac mac = Mac.getInstance(HMAC_ALGORITHM);
            mac.init(new SecretKeySpec(tokenSecret, HMAC_ALGORITHM));
            return encode(mac.doFinal(signingInput.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception ex) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "登录凭据签发失败");
        }
    }

    private String createPasswordVersion(String passwordHash) {
        String safePasswordHash = passwordHash == null ? "" : passwordHash.trim().toLowerCase(Locale.ROOT);
        return sign("password-version:" + safePasswordHash);
    }

    private String encodeJson(JSONObject jsonObject) {
        return encode(JSON.toJSONString(jsonObject).getBytes(StandardCharsets.UTF_8));
    }

    private String encode(byte[] rawBytes) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(rawBytes);
    }

    private byte[] decode(String encoded) {
        return Base64.getUrlDecoder().decode(encoded);
    }

    private byte[] resolveTokenSecret(String configuredSecret) {
        String safeSecret = configuredSecret == null ? "" : configuredSecret.trim();
        if (!safeSecret.isBlank()) {
            return safeSecret.getBytes(StandardCharsets.UTF_8);
        }
        return LOCAL_DEMO_TOKEN_SECRET.getBytes(StandardCharsets.UTF_8);
    }

    private ResponseStatusException invalidToken() {
        return new ResponseStatusException(HttpStatus.UNAUTHORIZED, "登录凭据无效，请重新登录");
    }

    private String normalizeUsername(String username) {
        return (username == null ? "" : username.trim()).toLowerCase(Locale.ROOT);
    }

    private String normalizeDisplayName(String displayName) {
        return displayName == null ? "" : displayName.trim();
    }

    private void validateEmail(String email) {
        if (email.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "邮箱不能为空");
        }
        if (email.length() > 254 || !EMAIL_PATTERN.matcher(email).matches()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请输入正确的邮箱地址");
        }
    }

    private String createRegisterUserId() {
        return REGISTER_USER_ROLE + "-" + UUID.randomUUID();
    }

    private AuthUserResponse toUserResponse(AuthUserEntity account) {
        return new AuthUserResponse(
                account.getUserId(),
                normalizeUsername(account.getUsername()),
                account.getDisplayName(),
                normalizeRole(account.getRole()),
                parsePermissions(account.getPermissionsJson())
        );
    }

    private boolean verifyPassword(String rawPassword, String storedPasswordHash) {
        String expectedHash = sha256(rawPassword == null ? "" : rawPassword);
        String safeStoredHash = storedPasswordHash == null ? "" : storedPasswordHash.trim().toLowerCase(Locale.ROOT);
        return MessageDigest.isEqual(
                expectedHash.getBytes(StandardCharsets.UTF_8),
                safeStoredHash.getBytes(StandardCharsets.UTF_8)
        );
    }

    private String sha256(String rawValue) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] rawHash = digest.digest(rawValue.getBytes(StandardCharsets.UTF_8));
            StringBuilder builder = new StringBuilder(rawHash.length * 2);
            for (byte item : rawHash) {
                builder.append(String.format("%02x", item));
            }
            return builder.toString();
        } catch (NoSuchAlgorithmException ex) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "密码处理失败");
        }
    }

    private String normalizeRole(String role) {
        return "admin".equals(normalizeUsername(role)) ? "admin" : "user";
    }

    private List<String> parsePermissions(String permissionsJson) {
        String safeJson = permissionsJson == null ? "" : permissionsJson.trim();
        if (safeJson.isBlank()) {
            return Collections.emptyList();
        }
        try {
            JSONArray array = JSON.parseArray(safeJson);
            return array.stream()
                    .map(String::valueOf)
                    .filter(item -> !item.isBlank())
                    .toList();
        } catch (RuntimeException ex) {
            return Collections.emptyList();
        }
    }
}
