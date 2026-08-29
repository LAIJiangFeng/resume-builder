# author: jf
from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage

from app.application.ports.auth_mail_port import AuthMailPort
from app.domain.exceptions.auth_exceptions import AuthServiceUnavailableError
from app.domain.models.auth import AuthEmailPurpose


class SmtpAuthMailAdapter(AuthMailPort):
    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        authorization_code: str,
        connection_timeout_seconds: float,
        io_timeout_seconds: float,
    ) -> None:
        self._host = str(host or "").strip() or "smtp.qq.com"
        self._port = max(1, int(port))
        self._username = str(username or "").strip()
        self._authorization_code = str(authorization_code or "").strip()
        self._connection_timeout_seconds = max(1.0, float(connection_timeout_seconds))
        self._io_timeout_seconds = max(1.0, float(io_timeout_seconds))

    def ensure_configured(self) -> None:
        if not self._username or not self._authorization_code.strip():
            raise AuthServiceUnavailableError(
                "QQ 邮箱发送服务未配置，请先设置 MAIL_USERNAME 和 MAIL_AUTHORIZATION_CODE"
            )

    def send_verification_code(
        self,
        *,
        email: str,
        code: str,
        purpose: AuthEmailPurpose,
        valid_minutes: int,
    ) -> None:
        self.ensure_configured()
        password_reset = purpose is AuthEmailPurpose.PASSWORD_RESET
        subject = (
            "Resume Studio 重置密码验证码"
            if password_reset
            else "Resume Studio 邮箱注册验证码"
        )
        message = EmailMessage()
        message["From"] = self._username
        message["To"] = email
        message["Subject"] = subject
        message.set_content(
            self._build_text(code, valid_minutes, password_reset), charset="utf-8"
        )
        message.add_alternative(
            self._build_html(code, valid_minutes, password_reset, subject),
            subtype="html",
            charset="utf-8",
        )

        try:
            with smtplib.SMTP_SSL(
                self._host,
                self._port,
                timeout=self._connection_timeout_seconds,
                context=ssl.create_default_context(),
            ) as smtp:
                if smtp.sock is not None:
                    smtp.sock.settimeout(self._io_timeout_seconds)
                smtp.login(self._username, self._authorization_code)
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            # 对外不暴露 SMTP 地址、账号或服务端原始响应。
            raise AuthServiceUnavailableError("验证码邮件发送失败，请稍后重试") from exc

    @staticmethod
    def _build_text(code: str, valid_minutes: int, password_reset: bool) -> str:
        action_text = (
            "你正在重置 Resume Studio 登录密码。"
            if password_reset
            else "你正在注册 Resume Studio。"
        )
        return (
            f"{action_text}\n\n"
            f"邮箱验证码：{code}\n"
            f"验证码在 {valid_minutes} 分钟内有效，请勿转发给他人。\n\n"
            "如果不是你本人操作，请忽略此邮件。"
        )

    @staticmethod
    def _build_html(
        code: str, valid_minutes: int, password_reset: bool, subject: str
    ) -> str:
        action_badge = "密码安全验证" if password_reset else "邮箱身份验证"
        action_title = "重置你的登录密码" if password_reset else "完成你的账号注册"
        action_description = (
            "你好，你正在重置 Resume Studio 登录密码。请在重置页面输入下面的 6 位验证码："
            if password_reset
            else "你好，你正在注册 Resume Studio。请在注册页面输入下面的 6 位验证码："
        )
        return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{subject}</title>
</head>
<body style="margin:0;padding:0;background:#f3f6fb;color:#172033;font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="width:100%;background:#f3f6fb;">
    <tr>
      <td align="center" style="padding:36px 16px;">
        <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0" style="width:100%;max-width:600px;border:1px solid #dfe7f2;border-radius:24px;background:#ffffff;overflow:hidden;">
          <tr>
            <td style="padding:30px 34px;background:#172033;">
              <div style="color:#ffffff;font-size:18px;font-weight:700;line-height:1.3;">Resume Studio</div>
              <div style="margin-top:4px;color:#aebbd0;font-size:12px;line-height:1.4;letter-spacing:0.08em;">BUILD · REFINE · INTERVIEW</div>
            </td>
          </tr>
          <tr>
            <td style="padding:38px 34px 16px;">
              <div style="display:inline-block;padding:6px 10px;border-radius:999px;background:#edf4ff;color:#2f6feb;font-size:12px;font-weight:700;">{action_badge}</div>
              <h1 style="margin:20px 0 10px;color:#172033;font-size:26px;font-weight:700;line-height:1.35;">{action_title}</h1>
              <p style="margin:0;color:#5e6b80;font-size:15px;line-height:1.8;">{action_description}</p>
            </td>
          </tr>
          <tr>
            <td style="padding:14px 34px 22px;">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border:1px solid #cfe0ff;border-radius:18px;background:#f6f9ff;">
                <tr>
                  <td align="center" style="padding:27px 20px 24px;">
                    <div style="margin-bottom:10px;color:#718096;font-size:11px;font-weight:700;letter-spacing:0.16em;">VERIFICATION CODE</div>
                    <div style="color:#1f5ed4;font-family:Consolas,'Courier New',monospace;font-size:38px;font-weight:700;line-height:1.2;letter-spacing:0.24em;white-space:nowrap;">{code}</div>
                    <div style="margin-top:12px;color:#5e6b80;font-size:13px;line-height:1.5;">验证码将在 <strong style="color:#172033;">{valid_minutes} 分钟</strong>后失效</div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:0 34px 34px;color:#735719;font-size:13px;line-height:1.65;">
              请勿向任何人转发验证码。Resume Studio 工作人员不会向你索取此验证码。
              <p style="margin:22px 0 0;color:#7b8799;">如果这不是你的操作，无需进行任何处理，忽略本邮件即可。</p>
            </td>
          </tr>
          <tr>
            <td style="padding:20px 34px;border-top:1px solid #edf1f6;background:#f9fbfd;color:#8b96a8;font-size:12px;line-height:1.7;text-align:center;">
              此邮件由 Resume Studio 系统自动发送，请勿直接回复。
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
