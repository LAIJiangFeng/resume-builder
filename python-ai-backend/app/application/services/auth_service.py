# author: jf
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta
from uuid import uuid4

from app.application.dto.auth_dto import (
    AuthEmailCodeWindow,
    AuthEncryptedLoginCommand,
    AuthLoginKey,
    AuthPasswordResetCommand,
    AuthRegisterCommand,
    AuthSession,
    AuthUserContext,
)
from app.application.ports.auth_mail_port import AuthMailPort
from app.application.ports.auth_security_port import AuthSecurityPort
from app.application.ports.auth_user_repository import (
    AuthRepositoryTransaction,
    AuthUserRepository,
)
from app.domain.exceptions.auth_exceptions import (
    AuthConflictError,
    AuthForbiddenError,
    AuthRateLimitError,
    AuthServiceUnavailableError,
    AuthUnauthorizedError,
    AuthValidationError,
)
from app.domain.models.auth import AuthAccount, AuthEmailPurpose, AuthEmailVerification

_TOKEN_TYPE = "Bearer "
_MAX_USER_ID_LENGTH = 64
_REGISTER_USER_ROLE = "user"
_REGISTER_USER_PERMISSIONS = ("resume_optimize", "ai_interview")
_EMAIL_PATTERN = re.compile(
    r"^[A-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?"
    r"(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$",
    re.IGNORECASE,
)


class AuthService:
    def __init__(
        self,
        *,
        repository: AuthUserRepository,
        security: AuthSecurityPort,
        mail_sender: AuthMailPort,
        email_code_secret: str,
        email_code_cooldown_seconds: int,
        email_code_expiry_seconds: int,
        email_code_max_failed_attempts: int,
    ) -> None:
        self._repository = repository
        self._security = security
        self._mail_sender = mail_sender
        safe_code_secret = str(email_code_secret or "").strip()
        self._email_code_secret = safe_code_secret.encode("utf-8")
        self._email_code_secret_configured = bool(safe_code_secret)
        self._email_code_cooldown_seconds = max(30, int(email_code_cooldown_seconds))
        self._email_code_expiry_seconds = max(60, int(email_code_expiry_seconds))
        self._email_code_max_failed_attempts = max(
            1, int(email_code_max_failed_attempts)
        )

    def get_login_key(self) -> AuthLoginKey:
        return self._security.get_login_key()

    def login(self, command: AuthEncryptedLoginCommand) -> AuthSession:
        username = self._normalize_username(command.username)
        password = self._security.decrypt_login_password(command)
        with self._repository.transaction() as transaction:
            account = transaction.find_by_username(username, enabled_only=True)
        if account is None or not self._security.verify_password(
            password, account.password_hash
        ):
            raise AuthUnauthorizedError("账号或密码错误")
        return self._create_session(account)

    def send_registration_email_code(self, email: str) -> AuthEmailCodeWindow:
        normalized_email = self._normalize_username(email)
        self._validate_email(normalized_email)
        with self._repository.transaction() as transaction:
            existing_account = transaction.find_by_username(
                normalized_email, enabled_only=False
            )
        if existing_account is not None:
            raise AuthConflictError("该邮箱已注册，请直接登录")
        return self._send_email_code(normalized_email, AuthEmailPurpose.REGISTRATION)

    def send_password_reset_email_code(self, email: str) -> AuthEmailCodeWindow:
        normalized_email = self._normalize_username(email)
        self._validate_email(normalized_email)
        with self._repository.transaction() as transaction:
            existing_account = transaction.find_by_username(
                normalized_email, enabled_only=True
            )
        if existing_account is None:
            # 未注册邮箱仍返回相同窗口，避免通过接口枚举账号。
            self._ensure_email_verification_configured()
            return self._code_window()
        return self._send_email_code(normalized_email, AuthEmailPurpose.PASSWORD_RESET)

    def register(self, command: AuthRegisterCommand) -> AuthSession:
        email = self._normalize_username(command.email)
        password = str(command.password or "")
        display_name = str(command.display_name or "").strip()
        self._validate_email(email)
        self._ensure_email_code_secret_configured()
        if len(password) < 8:
            raise AuthValidationError("密码至少需要 8 位")
        if not display_name:
            raise AuthValidationError("姓名不能为空")
        if len(display_name) > 64:
            raise AuthValidationError("姓名不能超过 64 个字符")

        verification_error: AuthValidationError | None = None
        account: AuthAccount | None = None
        with self._repository.transaction() as transaction:
            if transaction.find_by_username(email, enabled_only=False) is not None:
                raise AuthConflictError("该邮箱已注册，请直接登录")
            verification_error = self._verify_code(
                transaction,
                email=email,
                verification_code=command.verification_code,
                purpose=AuthEmailPurpose.REGISTRATION,
                action_label="注册",
            )
            if verification_error is None:
                account = AuthAccount(
                    id=f"{_REGISTER_USER_ROLE}-{uuid4()}",
                    username=email,
                    password_hash=self._security.hash_password(password),
                    display_name=display_name,
                    role=_REGISTER_USER_ROLE,
                    permissions=_REGISTER_USER_PERMISSIONS,
                )
                transaction.create_user(account)
                transaction.delete_verification(email)

        # 验证失败次数或过期删除需要先提交，再把业务错误返回给调用方。
        if verification_error is not None:
            raise verification_error
        if account is None:
            raise AuthConflictError("注册失败，请重新获取验证码后再试")
        return self._create_session(account)

    def reset_password(self, command: AuthPasswordResetCommand) -> None:
        email = self._normalize_username(command.email)
        new_password = str(command.new_password or "")
        self._validate_email(email)
        self._ensure_email_code_secret_configured()
        if len(new_password) < 8 or len(new_password) > 128:
            raise AuthValidationError("新密码长度必须在 8 到 128 位之间")

        verification_error: AuthValidationError | None = None
        with self._repository.transaction() as transaction:
            verification_error = self._verify_code(
                transaction,
                email=email,
                verification_code=command.verification_code,
                purpose=AuthEmailPurpose.PASSWORD_RESET,
                action_label="重置密码",
            )
            if verification_error is None:
                account = transaction.find_by_username(email, enabled_only=True)
                if account is None:
                    raise AuthValidationError("邮箱或验证码无效，请重新获取验证码")
                updated = transaction.update_password_hash(
                    account.id,
                    self._security.hash_password(new_password),
                )
                if not updated:
                    raise AuthConflictError("密码重置失败，请重新获取验证码后再试")
                transaction.delete_verification(email)

        if verification_error is not None:
            raise verification_error

    def require_user(self, authorization_header: str | None) -> AuthUserContext:
        token = self._extract_bearer_token(authorization_header)
        claims = self._security.decode_access_token(token)
        with self._repository.transaction() as transaction:
            account = transaction.find_by_username(claims.username, enabled_only=True)
        if (
            account is None
            or account.id != claims.user_id
            or len(account.id) > _MAX_USER_ID_LENGTH
        ):
            raise self._invalid_token()

        expected_password_version = self._security.create_password_version(
            account.password_hash
        )
        if not hmac.compare_digest(expected_password_version, claims.password_version):
            raise self._invalid_token()
        return AuthUserContext(
            user_id=account.id, role=self._normalize_role(account.role)
        )

    def require_admin(self, authorization_header: str | None) -> AuthUserContext:
        user_context = self.require_user(authorization_header)
        if not user_context.is_admin:
            raise AuthForbiddenError("只有管理员可以维护知识库")
        return user_context

    def _send_email_code(
        self, email: str, purpose: AuthEmailPurpose
    ) -> AuthEmailCodeWindow:
        self._ensure_email_verification_configured()
        now = datetime.now()
        with self._repository.transaction() as transaction:
            existing = transaction.find_verification_for_update(email)
            if existing is not None and existing.resend_available_at > now:
                remaining_seconds = max(
                    1, int((existing.resend_available_at - now).total_seconds())
                )
                raise AuthRateLimitError(
                    f"验证码发送过于频繁，请在 {remaining_seconds} 秒后重试"
                )

            code = f"{secrets.randbelow(1_000_000):06d}"
            verification = AuthEmailVerification(
                email=email,
                code_hash=self._hash_verification_code(email, code, purpose),
                expires_at=now + timedelta(seconds=self._email_code_expiry_seconds),
                resend_available_at=now
                + timedelta(seconds=self._email_code_cooldown_seconds),
                failed_attempts=0,
            )
            transaction.save_verification(verification)
            self._mail_sender.send_verification_code(
                email=email,
                code=code,
                purpose=purpose,
                valid_minutes=max(1, self._email_code_expiry_seconds // 60),
            )
        return self._code_window()

    def _verify_code(
        self,
        transaction: AuthRepositoryTransaction,
        *,
        email: str,
        verification_code: str,
        purpose: AuthEmailPurpose,
        action_label: str,
    ) -> AuthValidationError | None:
        now = datetime.now()
        verification = transaction.find_verification_for_update(email)
        if verification is None:
            return AuthValidationError(f"请先获取{action_label}验证码")
        if verification.failed_attempts >= self._email_code_max_failed_attempts:
            transaction.delete_verification(email)
            return AuthValidationError("验证码错误次数过多，请重新获取")
        if verification.expires_at <= now:
            transaction.delete_verification(email)
            return AuthValidationError("验证码已过期，请重新获取")

        actual_hash = self._hash_verification_code(
            email,
            str(verification_code or "").strip(),
            purpose,
        )
        if hmac.compare_digest(actual_hash, str(verification.code_hash or "")):
            return None

        next_failed_attempts = verification.failed_attempts + 1
        if next_failed_attempts >= self._email_code_max_failed_attempts:
            transaction.delete_verification(email)
            return AuthValidationError("验证码错误次数过多，请重新获取")
        transaction.increment_verification_failed_attempts(email)
        remaining_attempts = self._email_code_max_failed_attempts - next_failed_attempts
        return AuthValidationError(
            f"邮箱验证码不正确，还可尝试 {remaining_attempts} 次"
        )

    def _ensure_email_verification_configured(self) -> None:
        self._mail_sender.ensure_configured()
        self._ensure_email_code_secret_configured()

    def _ensure_email_code_secret_configured(self) -> None:
        if not self._email_code_secret_configured:
            raise AuthServiceUnavailableError(
                "邮箱验证码安全配置缺失，请先设置 APP_AUTH_EMAIL_CODE_SECRET"
            )

    def _hash_verification_code(
        self,
        email: str,
        code: str,
        purpose: AuthEmailPurpose,
    ) -> str:
        digest = hmac.new(
            self._email_code_secret,
            f"{purpose.value}:{email}:{code}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return digest

    def _create_session(self, account: AuthAccount) -> AuthSession:
        return AuthSession(
            access_token=self._security.create_access_token(account),
            account=account,
        )

    def _code_window(self) -> AuthEmailCodeWindow:
        return AuthEmailCodeWindow(
            cooldown_seconds=self._email_code_cooldown_seconds,
            expires_in_seconds=self._email_code_expiry_seconds,
        )

    @staticmethod
    def _extract_bearer_token(authorization_header: str | None) -> str:
        raw_header = str(authorization_header or "").strip()
        if len(raw_header) <= len(_TOKEN_TYPE) or not raw_header.lower().startswith(
            _TOKEN_TYPE.lower()
        ):
            raise AuthUnauthorizedError("请先登录后再使用 AI 能力")
        token = raw_header[len(_TOKEN_TYPE) :].strip()
        if not token:
            raise AuthUnauthorizedError("请先登录后再使用 AI 能力")
        return token

    @staticmethod
    def _normalize_username(username: str) -> str:
        return str(username or "").strip().lower()

    @staticmethod
    def _normalize_role(role: str) -> str:
        return "admin" if str(role or "").strip().lower() == "admin" else "user"

    @staticmethod
    def _validate_email(email: str) -> None:
        if not email:
            raise AuthValidationError("邮箱不能为空")
        if len(email) > 254 or _EMAIL_PATTERN.fullmatch(email) is None:
            raise AuthValidationError("请输入正确的邮箱地址")

    @staticmethod
    def _invalid_token() -> AuthUnauthorizedError:
        return AuthUnauthorizedError("登录凭据无效，请重新登录")
