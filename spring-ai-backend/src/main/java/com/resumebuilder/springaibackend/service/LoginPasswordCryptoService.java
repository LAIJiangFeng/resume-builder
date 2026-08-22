// author: jf
package com.resumebuilder.springaibackend.service;

import com.resumebuilder.springaibackend.dto.AuthLoginKeyResponse;
import com.resumebuilder.springaibackend.dto.AuthLoginRequest;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.spec.MGF1ParameterSpec;
import java.util.Arrays;
import java.util.Base64;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.regex.Pattern;
import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.OAEPParameterSpec;
import javax.crypto.spec.PSource;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

@Service
public class LoginPasswordCryptoService {

    private static final String LOGIN_ALGORITHM = "RSA-OAEP-256+A256GCM";
    private static final String RSA_TRANSFORMATION = "RSA/ECB/OAEPWithSHA-256AndMGF1Padding";
    private static final String AES_TRANSFORMATION = "AES/GCM/NoPadding";
    private static final int RSA_KEY_SIZE = 2048;
    private static final int AES_KEY_LENGTH = 32;
    private static final int GCM_IV_LENGTH = 12;
    private static final int GCM_TAG_LENGTH_BITS = 128;
    private static final long REQUEST_TTL_MILLIS = 120_000L;
    private static final long MAX_FUTURE_SKEW_MILLIS = 30_000L;
    private static final long REPLAY_ENTRY_TTL_MILLIS = REQUEST_TTL_MILLIS + MAX_FUTURE_SKEW_MILLIS;
    private static final int MAX_REPLAY_CACHE_ENTRIES = 10_000;
    private static final Pattern BASE64URL_PATTERN = Pattern.compile("^[A-Za-z0-9_-]+$");

    private final KeyPair keyPair;
    private final String keyId;
    private final String publicKey;
    private final Map<String, Long> consumedRequestIds = new ConcurrentHashMap<>();

    public LoginPasswordCryptoService() {
        this.keyPair = generateKeyPair();
        byte[] encodedPublicKey = keyPair.getPublic().getEncoded();
        this.keyId = createKeyId(encodedPublicKey);
        this.publicKey = Base64.getEncoder().encodeToString(encodedPublicKey);
    }

    public AuthLoginKeyResponse getLoginKey() {
        return new AuthLoginKeyResponse(LOGIN_ALGORITHM, keyId, publicKey);
    }

    public String decryptPassword(AuthLoginRequest request) {
        String normalizedUsername = normalizeUsername(request.username());
        validateRequestMetadata(request, normalizedUsername);
        consumeRequestId(request.requestId(), request.issuedAt());

        byte[] aesKey = null;
        try {
            byte[] encryptedKey = decodeBase64Url(request.encryptedKey());
            byte[] iv = decodeBase64Url(request.iv());
            byte[] encryptedPassword = decodeBase64Url(request.encryptedPassword());
            if (iv.length != GCM_IV_LENGTH || encryptedPassword.length < GCM_TAG_LENGTH_BITS / Byte.SIZE) {
                throw invalidEncryptedRequest();
            }

            Cipher rsaCipher = Cipher.getInstance(RSA_TRANSFORMATION);
            OAEPParameterSpec oaepParameterSpec = new OAEPParameterSpec(
                    "SHA-256",
                    "MGF1",
                    MGF1ParameterSpec.SHA256,
                    PSource.PSpecified.DEFAULT
            );
            rsaCipher.init(Cipher.DECRYPT_MODE, keyPair.getPrivate(), oaepParameterSpec);
            aesKey = rsaCipher.doFinal(encryptedKey);
            if (aesKey.length != AES_KEY_LENGTH) {
                throw invalidEncryptedRequest();
            }

            Cipher aesCipher = Cipher.getInstance(AES_TRANSFORMATION);
            aesCipher.init(
                    Cipher.DECRYPT_MODE,
                    new SecretKeySpec(aesKey, "AES"),
                    new GCMParameterSpec(GCM_TAG_LENGTH_BITS, iv)
            );
            aesCipher.updateAAD(buildAdditionalData(normalizedUsername, request));
            byte[] decryptedPassword = aesCipher.doFinal(encryptedPassword);
            try {
                return decodeUtf8Password(decryptedPassword);
            } finally {
                Arrays.fill(decryptedPassword, (byte) 0);
            }
        } catch (GeneralSecurityException | RuntimeException ex) {
            throw invalidEncryptedRequest();
        } finally {
            if (aesKey != null) {
                Arrays.fill(aesKey, (byte) 0);
            }
        }
    }

    private void validateRequestMetadata(AuthLoginRequest request, String normalizedUsername) {
        if (normalizedUsername.isBlank() || !constantTimeEquals(keyId, request.keyId())) {
            throw invalidEncryptedRequest();
        }

        long now = System.currentTimeMillis();
        long issuedAt = request.issuedAt();
        if (issuedAt < now - REQUEST_TTL_MILLIS || issuedAt > now + MAX_FUTURE_SKEW_MILLIS) {
            throw invalidEncryptedRequest();
        }

        try {
            UUID parsedRequestId = UUID.fromString(request.requestId());
            if (!parsedRequestId.toString().equals(request.requestId().toLowerCase(Locale.ROOT))) {
                throw invalidEncryptedRequest();
            }
        } catch (IllegalArgumentException ex) {
            throw invalidEncryptedRequest();
        }
    }

    private void consumeRequestId(String requestId, long issuedAt) {
        long now = System.currentTimeMillis();
        consumedRequestIds.entrySet().removeIf(entry -> entry.getValue() < now);
        if (consumedRequestIds.size() >= MAX_REPLAY_CACHE_ENTRIES) {
            throw new ResponseStatusException(HttpStatus.TOO_MANY_REQUESTS, "安全登录请求过多，请稍后重试");
        }

        long expiresAt = Math.max(now, issuedAt) + REPLAY_ENTRY_TTL_MILLIS;
        if (consumedRequestIds.putIfAbsent(requestId, expiresAt) != null) {
            throw invalidEncryptedRequest();
        }
    }

    private byte[] buildAdditionalData(String normalizedUsername, AuthLoginRequest request) {
        String additionalData = String.join(
                "\n",
                normalizedUsername,
                keyId,
                String.valueOf(request.issuedAt()),
                request.requestId()
        );
        return additionalData.getBytes(StandardCharsets.UTF_8);
    }

    private String decodeUtf8Password(byte[] decryptedPassword) throws GeneralSecurityException {
        String password = new String(decryptedPassword, StandardCharsets.UTF_8);
        if (!Arrays.equals(password.getBytes(StandardCharsets.UTF_8), decryptedPassword)) {
            throw new GeneralSecurityException("登录密码编码无效");
        }
        return password;
    }

    private byte[] decodeBase64Url(String value) {
        String safeValue = value == null ? "" : value.trim();
        if (safeValue.isBlank() || !BASE64URL_PATTERN.matcher(safeValue).matches()) {
            throw invalidEncryptedRequest();
        }
        return Base64.getUrlDecoder().decode(safeValue);
    }

    private boolean constantTimeEquals(String expected, String actual) {
        byte[] expectedBytes = expected.getBytes(StandardCharsets.UTF_8);
        byte[] actualBytes = (actual == null ? "" : actual).getBytes(StandardCharsets.UTF_8);
        return MessageDigest.isEqual(expectedBytes, actualBytes);
    }

    private KeyPair generateKeyPair() {
        try {
            KeyPairGenerator generator = KeyPairGenerator.getInstance("RSA");
            generator.initialize(RSA_KEY_SIZE);
            return generator.generateKeyPair();
        } catch (GeneralSecurityException ex) {
            throw new IllegalStateException("登录加密密钥初始化失败", ex);
        }
    }

    private String createKeyId(byte[] encodedPublicKey) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(encodedPublicKey);
            return Base64.getUrlEncoder().withoutPadding().encodeToString(Arrays.copyOf(digest, 18));
        } catch (NoSuchAlgorithmException ex) {
            throw new IllegalStateException("登录加密密钥标识生成失败", ex);
        }
    }

    private String normalizeUsername(String username) {
        return (username == null ? "" : username.trim()).toLowerCase(Locale.ROOT);
    }

    private ResponseStatusException invalidEncryptedRequest() {
        return new ResponseStatusException(HttpStatus.BAD_REQUEST, "登录加密请求无效，请重新提交");
    }
}
