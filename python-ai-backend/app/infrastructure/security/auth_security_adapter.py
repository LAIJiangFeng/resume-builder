# author: jf
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import threading
import time
from datetime import datetime, timezone
from uuid import UUID

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.application.dto.auth_dto import (
    AuthEncryptedLoginCommand,
    AuthLoginKey,
    AuthTokenClaims,
)
from app.application.ports.auth_security_port import AuthSecurityPort
from app.domain.exceptions.auth_exceptions import (
    AuthRateLimitError,
    AuthUnauthorizedError,
    AuthValidationError,
)
from app.domain.models.auth import AuthAccount

_LOGIN_ENCRYPTION_ALGORITHM = "RSA-OAEP-256+A256GCM"
_LOGIN_REQUEST_TTL_MILLIS = 120_000
_LOGIN_MAX_FUTURE_SKEW_MILLIS = 30_000
_LOGIN_REPLAY_ENTRY_TTL_MILLIS = (
    _LOGIN_REQUEST_TTL_MILLIS + _LOGIN_MAX_FUTURE_SKEW_MILLIS
)
_LOGIN_REPLAY_CACHE_MAX_ENTRIES = 10_000
_LOGIN_AES_KEY_LENGTH = 32
_LOGIN_GCM_IV_LENGTH = 12
_BASE64URL_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


class AuthSecurityAdapter(AuthSecurityPort):
    def __init__(self, *, token_secret: str, token_ttl_seconds: int) -> None:
        safe_secret = (
            str(token_secret or "").strip() or "resume-builder-local-demo-auth-secret"
        )
        self._token_secret = safe_secret.encode("utf-8")
        self._token_ttl_seconds = max(300, int(token_ttl_seconds))
        self._private_key = rsa.generate_private_key(
            public_exponent=65_537, key_size=2_048
        )
        encoded_public_key = self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        self._key_id = self._base64url_encode(
            hashlib.sha256(encoded_public_key).digest()[:18]
        )
        self._public_key = base64.b64encode(encoded_public_key).decode("ascii")
        self._consumed_request_ids: dict[str, int] = {}
        self._consumed_request_ids_lock = threading.Lock()

    def get_login_key(self) -> AuthLoginKey:
        # RSA 私钥只保留在当前进程，服务重启后自动轮换。
        return AuthLoginKey(
            algorithm=_LOGIN_ENCRYPTION_ALGORITHM,
            key_id=self._key_id,
            public_key=self._public_key,
        )

    def decrypt_login_password(self, command: AuthEncryptedLoginCommand) -> str:
        normalized_username = self._normalize_username(command.username)
        self._validate_login_metadata(command, normalized_username)
        self._consume_request_id(command.request_id, command.issued_at)

        try:
            encrypted_key = self._strict_base64url_decode(command.encrypted_key)
            iv = self._strict_base64url_decode(command.iv)
            encrypted_password = self._strict_base64url_decode(
                command.encrypted_password
            )
            if len(iv) != _LOGIN_GCM_IV_LENGTH or len(encrypted_password) < 16:
                raise ValueError("登录密文字段长度无效")

            aes_key = self._private_key.decrypt(
                encrypted_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )
            if len(aes_key) != _LOGIN_AES_KEY_LENGTH:
                raise ValueError("登录会话密钥长度无效")

            additional_data = self._build_login_additional_data(
                normalized_username, command
            )
            decrypted_password = AESGCM(aes_key).decrypt(
                iv, encrypted_password, additional_data
            )
            return decrypted_password.decode("utf-8")
        except Exception as exc:
            # 所有密文错误统一收敛，避免向调用方暴露具体解密失败环节。
            raise AuthValidationError("登录加密请求无效，请重新提交") from exc

    def hash_password(self, raw_password: str) -> str:
        return hashlib.sha256(str(raw_password or "").encode("utf-8")).hexdigest()

    def verify_password(self, raw_password: str, stored_password_hash: str) -> bool:
        expected_hash = self.hash_password(raw_password)
        safe_stored_hash = str(stored_password_hash or "").strip().lower()
        return hmac.compare_digest(expected_hash, safe_stored_hash)

    def create_access_token(self, account: AuthAccount) -> str:
        issued_at = self._now_seconds()
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": account.id,
            "username": self._normalize_username(account.username),
            "displayName": account.display_name,
            "role": self._normalize_role(account.role),
            "permissions": list(account.permissions),
            "pwdv": self.create_password_version(account.password_hash),
            "iat": issued_at,
            "exp": issued_at + self._token_ttl_seconds,
        }
        signing_input = f"{self._encode_json(header)}.{self._encode_json(payload)}"
        return f"{signing_input}.{self._sign(signing_input)}"

    def decode_access_token(self, token: str) -> AuthTokenClaims:
        parts = str(token or "").split(".")
        if len(parts) != 3:
            raise self._invalid_token()

        signing_input = f"{parts[0]}.{parts[1]}"
        if not hmac.compare_digest(self._sign(signing_input), parts[2]):
            raise self._invalid_token()

        try:
            payload = json.loads(
                self._strict_base64url_decode(parts[1]).decode("utf-8")
            )
            if not isinstance(payload, dict):
                raise ValueError("登录令牌载荷无效")
            expires_at = int(payload.get("exp") or 0)
        except (TypeError, ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise self._invalid_token() from exc

        if expires_at <= self._now_seconds():
            raise AuthUnauthorizedError("登录已过期，请重新登录")

        user_id = str(payload.get("sub") or "").strip()
        username = self._normalize_username(str(payload.get("username") or ""))
        password_version = str(payload.get("pwdv") or "").strip()
        if not user_id or not username or not password_version:
            raise self._invalid_token()
        return AuthTokenClaims(
            user_id=user_id,
            username=username,
            password_version=password_version,
        )

    def create_password_version(self, password_hash: str) -> str:
        safe_password_hash = str(password_hash or "").strip().lower()
        return self._sign(f"password-version:{safe_password_hash}")

    def _validate_login_metadata(
        self,
        command: AuthEncryptedLoginCommand,
        normalized_username: str,
    ) -> None:
        if not normalized_username or not secrets.compare_digest(
            self._key_id, str(command.key_id or "")
        ):
            raise AuthValidationError("登录加密请求无效，请重新提交")

        now_millis = time.time_ns() // 1_000_000
        if command.issued_at < now_millis - _LOGIN_REQUEST_TTL_MILLIS:
            raise AuthValidationError("登录加密请求无效，请重新提交")
        if command.issued_at > now_millis + _LOGIN_MAX_FUTURE_SKEW_MILLIS:
            raise AuthValidationError("登录加密请求无效，请重新提交")

        try:
            parsed_request_id = UUID(str(command.request_id or ""))
        except ValueError as exc:
            raise AuthValidationError("登录加密请求无效，请重新提交") from exc
        if str(parsed_request_id) != str(command.request_id).lower():
            raise AuthValidationError("登录加密请求无效，请重新提交")

    def _consume_request_id(self, request_id: str, issued_at: int) -> None:
        now_millis = time.time_ns() // 1_000_000
        with self._consumed_request_ids_lock:
            expired_ids = [
                cached_request_id
                for cached_request_id, expires_at in self._consumed_request_ids.items()
                if expires_at < now_millis
            ]
            for cached_request_id in expired_ids:
                self._consumed_request_ids.pop(cached_request_id, None)

            if len(self._consumed_request_ids) >= _LOGIN_REPLAY_CACHE_MAX_ENTRIES:
                raise AuthRateLimitError("安全登录请求过多，请稍后重试")
            if request_id in self._consumed_request_ids:
                raise AuthValidationError("登录加密请求无效，请重新提交")
            self._consumed_request_ids[request_id] = (
                max(now_millis, issued_at) + _LOGIN_REPLAY_ENTRY_TTL_MILLIS
            )

    def _build_login_additional_data(
        self,
        normalized_username: str,
        command: AuthEncryptedLoginCommand,
    ) -> bytes:
        return (
            f"{normalized_username}\n{self._key_id}\n{command.issued_at}\n{command.request_id}"
        ).encode("utf-8")

    def _encode_json(self, payload: dict[str, object]) -> str:
        raw_json = json.dumps(
            payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        )
        return self._base64url_encode(raw_json.encode("utf-8"))

    def _sign(self, signing_input: str) -> str:
        digest = hmac.new(
            self._token_secret, signing_input.encode("utf-8"), hashlib.sha256
        ).digest()
        return self._base64url_encode(digest)

    def _strict_base64url_decode(self, raw_value: str) -> bytes:
        safe_value = str(raw_value or "").strip()
        if not safe_value or _BASE64URL_PATTERN.fullmatch(safe_value) is None:
            raise ValueError("字段不是有效的 Base64URL")
        padded_value = safe_value + "=" * (-len(safe_value) % 4)
        return base64.b64decode(
            padded_value.encode("ascii"), altchars=b"-_", validate=True
        )

    @staticmethod
    def _base64url_encode(raw_bytes: bytes) -> str:
        return base64.urlsafe_b64encode(raw_bytes).decode("ascii").rstrip("=")

    @staticmethod
    def _normalize_username(username: str) -> str:
        return str(username or "").strip().lower()

    @staticmethod
    def _normalize_role(role: str) -> str:
        return "admin" if str(role or "").strip().lower() == "admin" else "user"

    @staticmethod
    def _now_seconds() -> int:
        return int(datetime.now(timezone.utc).timestamp())

    @staticmethod
    def _invalid_token() -> AuthUnauthorizedError:
        return AuthUnauthorizedError("登录凭据无效，请重新登录")
