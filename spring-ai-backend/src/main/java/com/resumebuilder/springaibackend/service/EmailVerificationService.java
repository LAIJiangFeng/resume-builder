// author: jf
package com.resumebuilder.springaibackend.service;

import com.resumebuilder.springaibackend.dto.AuthEmailCodeResponse;
import com.resumebuilder.springaibackend.entity.AuthEmailVerificationEntity;
import com.resumebuilder.springaibackend.mapper.AuthEmailVerificationMapper;
import jakarta.mail.MessagingException;
import jakarta.mail.internet.MimeMessage;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.HexFormat;
import java.util.Locale;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.mail.MailException;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class EmailVerificationService {

    private static final Logger log = LoggerFactory.getLogger(EmailVerificationService.class);
    private static final String HMAC_ALGORITHM = "HmacSHA256";
    private static final String REGISTRATION_PURPOSE = "registration";
    private static final String PASSWORD_RESET_PURPOSE = "password-reset";
    private static final int VERIFICATION_CODE_BOUND = 1_000_000;

    private final AuthEmailVerificationMapper verificationMapper;
    private final JavaMailSender mailSender;
    private final SecureRandom secureRandom = new SecureRandom();
    private final byte[] codeSecret;
    private final String smtpUsername;
    private final boolean mailConfigured;
    private final boolean codeSecretConfigured;
    private final long cooldownSeconds;
    private final long expirySeconds;
    private final int maxFailedAttempts;

    public EmailVerificationService(
            AuthEmailVerificationMapper verificationMapper,
            JavaMailSender mailSender,
            @Value("${spring.mail.username:}") String configuredUsername,
            @Value("${spring.mail.password:}") String configuredPassword,
            @Value("${app.auth.email-verification.code-secret:}") String configuredCodeSecret,
            @Value("${app.auth.email-verification.cooldown-seconds:60}") long configuredCooldownSeconds,
            @Value("${app.auth.email-verification.expiry-seconds:600}") long configuredExpirySeconds,
            @Value("${app.auth.email-verification.max-failed-attempts:5}") int configuredMaxFailedAttempts
    ) {
        this.verificationMapper = verificationMapper;
        this.mailSender = mailSender;
        this.smtpUsername = configuredUsername == null ? "" : configuredUsername.trim();
        this.mailConfigured = !this.smtpUsername.isBlank()
                && configuredPassword != null
                && !configuredPassword.isBlank();
        String safeCodeSecret = configuredCodeSecret == null ? "" : configuredCodeSecret.trim();
        this.codeSecretConfigured = !safeCodeSecret.isBlank();
        this.codeSecret = safeCodeSecret.getBytes(StandardCharsets.UTF_8);
        this.cooldownSeconds = Math.max(30L, configuredCooldownSeconds);
        this.expirySeconds = Math.max(this.cooldownSeconds, configuredExpirySeconds);
        this.maxFailedAttempts = Math.max(1, configuredMaxFailedAttempts);
    }

    @Transactional
    public AuthEmailCodeResponse sendRegistrationCode(String email) {
        return sendCode(email, REGISTRATION_PURPOSE);
    }

    @Transactional
    public AuthEmailCodeResponse sendPasswordResetCode(String email) {
        return sendCode(email, PASSWORD_RESET_PURPOSE);
    }

    public AuthEmailCodeResponse getCodeDeliveryWindow() {
        ensureMailConfigured();
        return new AuthEmailCodeResponse(cooldownSeconds, expirySeconds);
    }

    private AuthEmailCodeResponse sendCode(String email, String purpose) {
        ensureMailConfigured();
        LocalDateTime now = LocalDateTime.now();
        AuthEmailVerificationEntity existing = verificationMapper.selectByEmailForUpdate(email);
        if (existing != null && existing.getResendAvailableAt() != null
                && existing.getResendAvailableAt().isAfter(now)) {
            long remainingSeconds = Math.max(
                    1L,
                    Duration.between(now, existing.getResendAvailableAt()).toSeconds()
            );
            throw new ResponseStatusException(
                    HttpStatus.TOO_MANY_REQUESTS,
                    "验证码发送过于频繁，请在 " + remainingSeconds + " 秒后重试"
            );
        }

        String code = generateCode();
        AuthEmailVerificationEntity verification = new AuthEmailVerificationEntity();
        verification.setEmail(email);
        verification.setCodeHash(hashCode(email, code, purpose));
        verification.setExpiresAt(now.plusSeconds(expirySeconds));
        verification.setResendAvailableAt(now.plusSeconds(cooldownSeconds));
        verification.setFailedAttempts(0);
        try {
            if (existing == null) {
                verificationMapper.insertCode(verification);
            } else {
                verificationMapper.updateCode(verification);
            }
        } catch (DuplicateKeyException ex) {
            throw new ResponseStatusException(
                    HttpStatus.TOO_MANY_REQUESTS,
                    "验证码发送过于频繁，请稍后重试",
                    ex
            );
        }
        sendVerificationEmail(email, code, purpose);
        return getCodeDeliveryWindow();
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW, noRollbackFor = ResponseStatusException.class)
    public void verifyForRegistration(String email, String verificationCode) {
        verifyCode(email, verificationCode, REGISTRATION_PURPOSE, "注册");
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW, noRollbackFor = ResponseStatusException.class)
    public void verifyForPasswordReset(String email, String verificationCode) {
        verifyCode(email, verificationCode, PASSWORD_RESET_PURPOSE, "重置密码");
    }

    private void verifyCode(String email, String verificationCode, String purpose, String actionLabel) {
        LocalDateTime now = LocalDateTime.now();
        AuthEmailVerificationEntity verification = verificationMapper.selectByEmailForUpdate(email);
        if (verification == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请先获取" + actionLabel + "验证码");
        }

        int failedAttempts = verification.getFailedAttempts() == null ? 0 : verification.getFailedAttempts();
        if (failedAttempts >= maxFailedAttempts) {
            verificationMapper.deleteByEmail(email);
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "验证码错误次数过多，请重新获取");
        }
        if (verification.getExpiresAt() == null || !verification.getExpiresAt().isAfter(now)) {
            verificationMapper.deleteByEmail(email);
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "验证码已过期，请重新获取");
        }

        String actualHash = hashCode(
                email,
                verificationCode == null ? "" : verificationCode.trim(),
                purpose
        );
        String storedHash = verification.getCodeHash() == null ? "" : verification.getCodeHash();
        if (!MessageDigest.isEqual(
                actualHash.getBytes(StandardCharsets.UTF_8),
                storedHash.getBytes(StandardCharsets.UTF_8)
        )) {
            int nextFailedAttempts = failedAttempts + 1;
            if (nextFailedAttempts >= maxFailedAttempts) {
                verificationMapper.deleteByEmail(email);
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "验证码错误次数过多，请重新获取");
            }
            verificationMapper.incrementFailedAttempts(email);
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST,
                    "邮箱验证码不正确，还可尝试 " + (maxFailedAttempts - nextFailedAttempts) + " 次"
            );
        }
    }

    public void consume(String email) {
        verificationMapper.deleteByEmail(email);
    }

    private void ensureMailConfigured() {
        if (!mailConfigured) {
            throw new ResponseStatusException(
                    HttpStatus.SERVICE_UNAVAILABLE,
                    "QQ 邮箱发送服务未配置，请先设置 MAIL_USERNAME 和 MAIL_AUTHORIZATION_CODE"
            );
        }
        if (!codeSecretConfigured) {
            throw new ResponseStatusException(
                    HttpStatus.SERVICE_UNAVAILABLE,
                    "邮箱验证码安全配置缺失，请先设置 APP_AUTH_EMAIL_CODE_SECRET"
            );
        }
    }

    private String generateCode() {
        return String.format(Locale.ROOT, "%06d", secureRandom.nextInt(VERIFICATION_CODE_BOUND));
    }

    private String hashCode(String email, String code, String purpose) {
        try {
            Mac mac = Mac.getInstance(HMAC_ALGORITHM);
            mac.init(new SecretKeySpec(codeSecret, HMAC_ALGORITHM));
            byte[] digest = mac.doFinal((purpose + ":" + email + ":" + code).getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest);
        } catch (GeneralSecurityException ex) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR, "验证码安全处理失败", ex);
        }
    }

    private void sendVerificationEmail(String email, String code, String purpose) {
        long validMinutes = Math.max(1L, expirySeconds / 60L);
        boolean passwordReset = PASSWORD_RESET_PURPOSE.equals(purpose);
        String emailSubject = passwordReset
                ? "Resume Studio 重置密码验证码"
                : "Resume Studio 邮箱注册验证码";
        MimeMessage message = mailSender.createMimeMessage();
        try {
            MimeMessageHelper helper = new MimeMessageHelper(message, true, StandardCharsets.UTF_8.name());
            helper.setFrom(smtpUsername);
            helper.setTo(email);
            helper.setSubject(emailSubject);
            helper.setText(
                    buildVerificationEmailText(code, validMinutes, passwordReset),
                    buildVerificationEmailHtml(code, validMinutes, passwordReset)
            );
            mailSender.send(message);
        } catch (MessagingException | MailException ex) {
            log.error("发送邮箱验证码邮件失败，请检查 QQ 邮箱 SMTP 配置", ex);
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "验证码邮件发送失败，请稍后重试", ex);
        }
    }

    private String buildVerificationEmailText(String code, long validMinutes, boolean passwordReset) {
        String actionText = passwordReset
                ? "你正在重置 Resume Studio 登录密码。"
                : "你正在注册 Resume Studio。";
        return actionText + "\n\n"
                + "邮箱验证码：" + code + "\n"
                + "验证码在 " + validMinutes + " 分钟内有效，请勿转发给他人。\n\n"
                + "如果不是你本人操作，请忽略此邮件。";
    }

    private String buildVerificationEmailHtml(String code, long validMinutes, boolean passwordReset) {
        String actionBadge = passwordReset ? "密码安全验证" : "邮箱身份验证";
        String actionTitle = passwordReset ? "重置你的登录密码" : "完成你的账号注册";
        String actionDescription = passwordReset
                ? "你好，你正在重置 Resume Studio 登录密码。请在重置页面输入下面的 6 位验证码："
                : "你好，你正在注册 Resume Studio。请在注册页面输入下面的 6 位验证码：";
        return """
                <!doctype html>
                <html lang="zh-CN">
                <head>
                  <meta charset="UTF-8">
                  <meta name="viewport" content="width=device-width, initial-scale=1.0">
                  <title>{{EMAIL_SUBJECT}}</title>
                </head>
                <body style="margin:0;padding:0;background:#f3f6fb;color:#172033;font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif;">
                  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="width:100%;background:#f3f6fb;">
                    <tr>
                      <td align="center" style="padding:36px 16px;">
                        <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" style="width:100%;max-width:600px;border:1px solid #dfe7f2;border-radius:24px;background:#ffffff;box-shadow:0 18px 46px rgba(23,32,51,0.10);overflow:hidden;">
                          <tr>
                            <td style="padding:30px 34px;background:#172033;">
                              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                                <tr>
                                  <td width="54" valign="middle">
                                    <div style="width:44px;height:44px;border-radius:13px;background:#2f6feb;color:#ffffff;font-size:17px;font-weight:700;line-height:44px;text-align:center;letter-spacing:-1px;">RS</div>
                                  </td>
                                  <td valign="middle">
                                    <div style="color:#ffffff;font-size:18px;font-weight:700;line-height:1.3;">Resume Studio</div>
                                    <div style="margin-top:4px;color:#aebbd0;font-size:12px;line-height:1.4;letter-spacing:0.08em;">BUILD · REFINE · INTERVIEW</div>
                                  </td>
                                </tr>
                              </table>
                            </td>
                          </tr>
                          <tr>
                            <td style="padding:38px 34px 16px;">
                              <div style="display:inline-block;padding:6px 10px;border-radius:999px;background:#edf4ff;color:#2f6feb;font-size:12px;font-weight:700;line-height:1;">{{ACTION_BADGE}}</div>
                              <h1 style="margin:20px 0 10px;color:#172033;font-size:26px;font-weight:700;line-height:1.35;letter-spacing:-0.02em;">{{ACTION_TITLE}}</h1>
                              <p style="margin:0;color:#5e6b80;font-size:15px;line-height:1.8;">{{ACTION_DESCRIPTION}}</p>
                            </td>
                          </tr>
                          <tr>
                            <td style="padding:14px 34px 22px;">
                              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border:1px solid #cfe0ff;border-radius:18px;background:#f6f9ff;">
                                <tr>
                                  <td align="center" style="padding:27px 20px 24px;">
                                    <div style="margin-bottom:10px;color:#718096;font-size:11px;font-weight:700;line-height:1.2;letter-spacing:0.16em;">VERIFICATION CODE</div>
                                    <div style="color:#1f5ed4;font-family:Consolas,'Courier New',monospace;font-size:38px;font-weight:700;line-height:1.2;letter-spacing:0.24em;white-space:nowrap;">{{CODE}}</div>
                                    <div style="margin-top:12px;color:#5e6b80;font-size:13px;line-height:1.5;">验证码将在 <strong style="color:#172033;">{{VALID_MINUTES}} 分钟</strong>后失效</div>
                                  </td>
                                </tr>
                              </table>
                            </td>
                          </tr>
                          <tr>
                            <td style="padding:0 34px 34px;">
                              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border-radius:14px;background:#fff8e8;">
                                <tr>
                                  <td width="42" valign="top" style="padding:16px 0 16px 16px;">
                                    <div style="width:26px;height:26px;border:1px solid #f0c96a;border-radius:50%;color:#9a6a00;font-size:14px;font-weight:700;line-height:26px;text-align:center;">!</div>
                                  </td>
                                  <td style="padding:16px 16px 16px 8px;color:#735719;font-size:13px;line-height:1.65;">
                                    请勿向任何人转发验证码。Resume Studio 工作人员不会通过电话、聊天或邮件向你索取此验证码。
                                  </td>
                                </tr>
                              </table>
                              <p style="margin:22px 0 0;color:#7b8799;font-size:13px;line-height:1.7;">如果这不是你的操作，无需进行任何处理，忽略本邮件即可。</p>
                            </td>
                          </tr>
                          <tr>
                            <td style="padding:20px 34px;border-top:1px solid #edf1f6;background:#f9fbfd;color:#8b96a8;font-size:12px;line-height:1.7;text-align:center;">
                              此邮件由 Resume Studio 系统自动发送，请勿直接回复。<br>
                              专注简历表达，准备每一次重要面试。
                            </td>
                          </tr>
                        </table>
                        <div style="padding-top:18px;color:#9aa5b5;font-size:11px;line-height:1.6;">© 2026 Resume Studio</div>
                      </td>
                    </tr>
                  </table>
                </body>
                </html>
                """
                .replace("{{EMAIL_SUBJECT}}", passwordReset
                        ? "Resume Studio 重置密码验证码"
                        : "Resume Studio 邮箱注册验证码")
                .replace("{{ACTION_BADGE}}", actionBadge)
                .replace("{{ACTION_TITLE}}", actionTitle)
                .replace("{{ACTION_DESCRIPTION}}", actionDescription)
                .replace("{{CODE}}", code)
                .replace("{{VALID_MINUTES}}", Long.toString(validMinutes));
    }
}
