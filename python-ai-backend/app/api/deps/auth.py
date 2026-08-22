# author: jf
import base64
import hashlib
import hmac
import json
import re
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from uuid import UUID, uuid4

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import Depends, Header, HTTPException

from app.application.ports.auth_user_repository import AuthAccount, AuthUserAlreadyExistsError, AuthUserRepository
from app.bootstrap.container import build_auth_user_repository
from app.infrastructure.config.settings import get_settings


_TOKEN_TYPE = "Bearer "
_TOKEN_TTL_SECONDS_DEFAULT = 43_200
_TOKEN_SECRET_FALLBACK = "resume-builder-local-demo-auth-secret"
_MAX_USER_ID_LENGTH = 64
_REGISTER_USER_ROLE = "user"
_REGISTER_USER_PERMISSIONS = ("resume_optimize", "ai_interview")
_LOGIN_ENCRYPTION_ALGORITHM = "RSA-OAEP-256+A256GCM"
_LOGIN_REQUEST_TTL_MILLIS = 120_000
_LOGIN_MAX_FUTURE_SKEW_MILLIS = 30_000
_LOGIN_REPLAY_ENTRY_TTL_MILLIS = _LOGIN_REQUEST_TTL_MILLIS + _LOGIN_MAX_FUTURE_SKEW_MILLIS
_LOGIN_REPLAY_CACHE_MAX_ENTRIES = 10_000
_LOGIN_AES_KEY_LENGTH = 32
_LOGIN_GCM_IV_LENGTH = 12
_BASE64URL_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
_CONSUMED_LOGIN_REQUEST_IDS: dict[str, int] = {}
_CONSUMED_LOGIN_REQUEST_IDS_LOCK = threading.Lock()


@dataclass(frozen=True, slots=True)
class AuthUserContext:
    user_id: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


@dataclass(frozen=True, slots=True)
class LoginEncryptionKey:
    private_key: rsa.RSAPrivateKey
    key_id: str
    public_key: str


def get_login_encryption_key() -> tuple[str, str, str]:
    # 公钥接口只暴露 SPKI 公钥和不可逆 keyId；RSA 私钥始终留在当前后端进程内。
    login_key = _login_encryption_key()
    return _LOGIN_ENCRYPTION_ALGORITHM, login_key.key_id, login_key.public_key


def decrypt_login_password(
    *,
    username: str,
    key_id: str,
    encrypted_key: str,
    iv: str,
    encrypted_password: str,
    issued_at: int,
    request_id: str,
) -> str:
    # 安全登录解密流程：
    # 1) 先校验账号规范化结果、公钥标识、签发时间和 UUID，避免无效请求进入高成本解密。
    # 2) 在解密前原子消费 requestId；即使后续密文错误，同一请求也不能再次尝试。
    # 3) RSA-OAEP/SHA-256 只解出随机 AES 密钥，AES-GCM 再校验 AAD 并解出密码。
    # 4) 任一字段被篡改、请求过期、请求重放或解码失败时统一返回 400，不泄露具体失败环节。
    # 5) 成功输出仅在当前调用栈交给账号摘要校验，不写日志、不落库，也不返回给客户端。
    normalized_username = _normalize_username(username)
    login_key = _login_encryption_key()
    safe_key_id = str(key_id or "")
    safe_request_id = str(request_id or "")
    _validate_login_request_metadata(normalized_username, safe_key_id, issued_at, safe_request_id, login_key)
    _consume_login_request_id(safe_request_id, issued_at)

    try:
        raw_encrypted_key = _strict_base64url_decode(encrypted_key)
        raw_iv = _strict_base64url_decode(iv)
        raw_encrypted_password = _strict_base64url_decode(encrypted_password)
        if len(raw_iv) != _LOGIN_GCM_IV_LENGTH or len(raw_encrypted_password) < 16:
            raise ValueError("登录密文字段长度无效")

        aes_key = login_key.private_key.decrypt(
            raw_encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        if len(aes_key) != _LOGIN_AES_KEY_LENGTH:
            raise ValueError("登录会话密钥长度无效")

        additional_data = _build_login_additional_data(normalized_username, safe_key_id, issued_at, safe_request_id)
        decrypted_password = AESGCM(aes_key).decrypt(raw_iv, raw_encrypted_password, additional_data)
        return decrypted_password.decode("utf-8")
    except Exception as exc:
        # 加密库对无效 RSA 密文可能抛出后端相关异常，统一收敛为不泄露细节的客户端错误。
        raise _invalid_encrypted_login_request() from exc


def authenticate_account(username: str, password: str) -> AuthAccount:
    # 登录入口只负责校验 auth_users 表中的已存在账号，不承接注册、找回密码或账号后台。
    # 这里返回数据库账号对象，后续 token 签发流程写入用户 ID、角色和权限，避免前端自行声明身份。
    account = _find_account_by_username(username)
    if account is None or not _verify_password(password, account.password_hash):
        raise HTTPException(status_code=401, detail="账号或密码错误")
    return account


def register_account(username: str, password: str, display_name: str) -> AuthAccount:
    # 注册入口流程：
    # 1) 统一账号大小写和展示名空白字符，确保前端、Spring 后端和 Python 后端契约一致。
    # 2) 先查重再创建普通用户账号；并发重复由仓储层唯一键异常兜底。
    # 3) 默认只授予简历优化和 AI 面试权限，不授予知识库管理权限。
    # 4) 返回新账号对象给路由层签发 token，注册成功即可进入应用。
    safe_username = _normalize_username(username)
    safe_password = str(password or "")
    safe_display_name = str(display_name or "").strip()

    if not safe_username:
        raise HTTPException(status_code=400, detail="账号不能为空")
    if len(safe_username) > 64:
        raise HTTPException(status_code=400, detail="账号不能超过 64 个字符")
    if len(safe_password) < 8:
        raise HTTPException(status_code=400, detail="密码至少需要 8 位")
    if not safe_display_name:
        raise HTTPException(status_code=400, detail="姓名不能为空")
    if len(safe_display_name) > 64:
        raise HTTPException(status_code=400, detail="姓名不能超过 64 个字符")

    if _find_account_by_username(safe_username) is not None:
        raise HTTPException(status_code=409, detail="账号已存在，请直接登录")

    account = AuthAccount(
        id=f"{_REGISTER_USER_ROLE}-{uuid4()}",
        username=safe_username,
        password_hash=_hash_password(safe_password),
        display_name=safe_display_name,
        role=_REGISTER_USER_ROLE,
        permissions=_REGISTER_USER_PERMISSIONS,
    )
    return _create_account(account)


def create_access_token(account: AuthAccount) -> str:
    # token 签发流程：
    # 1) 记录账号归属、角色、权限和过期时间。
    # 2) 使用 HMAC-SHA256 对 header.payload 签名。
    # 3) 只把签名后的 token 返回给前端，后续请求不能再通过 Header 伪造角色。
    issued_at = _now_seconds()
    payload = {
        "sub": account.id,
        "username": account.username,
        "displayName": account.display_name,
        "role": account.role,
        "permissions": list(account.permissions),
        "iat": issued_at,
        "exp": issued_at + _token_ttl_seconds(),
    }
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = f"{_encode_json(header)}.{_encode_json(payload)}"
    return f"{signing_input}.{_sign(signing_input)}"


def require_auth_user_context(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> AuthUserContext:
    # 路由依赖流程：
    # 1) 只读取 Authorization: Bearer token。
    # 2) 校验签名、过期时间和数据库账号归属。
    # 3) 将可信用户 ID 和角色传给 application 层，供面试会话隔离和知识库权限判断使用。
    token = _extract_bearer_token(authorization)
    account = _verify_access_token(token)
    if len(account.id) > _MAX_USER_ID_LENGTH:
        raise HTTPException(status_code=401, detail="登录凭据无效，请重新登录")
    return AuthUserContext(user_id=account.id, role=account.role)


def require_admin_user_context(
    user_context: AuthUserContext = Depends(require_auth_user_context),
) -> AuthUserContext:
    if not user_context.is_admin:
        raise HTTPException(status_code=403, detail="只有管理员可以维护知识库")
    return user_context


def _extract_bearer_token(authorization: str | None) -> str:
    raw_header = str(authorization or "").strip()
    if not raw_header.lower().startswith(_TOKEN_TYPE.lower()):
        raise HTTPException(status_code=401, detail="请先登录后再使用 AI 能力")
    token = raw_header[len(_TOKEN_TYPE):].strip()
    if not token:
        raise HTTPException(status_code=401, detail="请先登录后再使用 AI 能力")
    return token


def _verify_access_token(token: str) -> AuthAccount:
    parts = token.split(".")
    if len(parts) != 3:
        raise _invalid_token()

    signing_input = f"{parts[0]}.{parts[1]}"
    if not hmac.compare_digest(_sign(signing_input), parts[2]):
        raise _invalid_token()

    try:
        payload = json.loads(_base64url_decode(parts[1]).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        raise _invalid_token()

    expires_at = int(payload.get("exp") or 0)
    if expires_at <= _now_seconds():
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")

    account = _find_account_by_username(str(payload.get("username") or ""))
    if account is None or account.id != str(payload.get("sub") or ""):
        raise _invalid_token()
    return account


def _encode_json(payload: dict[str, object]) -> str:
    raw_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return _base64url_encode(raw_json.encode("utf-8"))


def _sign(signing_input: str) -> str:
    digest = hmac.new(_token_secret(), signing_input.encode("utf-8"), hashlib.sha256).digest()
    return _base64url_encode(digest)


def _base64url_encode(raw_bytes: bytes) -> str:
    return base64.urlsafe_b64encode(raw_bytes).decode("ascii").rstrip("=")


def _base64url_decode(raw_value: str) -> bytes:
    padding = "=" * (-len(raw_value) % 4)
    return base64.urlsafe_b64decode((raw_value + padding).encode("ascii"))


def _strict_base64url_decode(raw_value: str) -> bytes:
    safe_value = str(raw_value or "").strip()
    if not safe_value or _BASE64URL_PATTERN.fullmatch(safe_value) is None:
        raise ValueError("登录密文字段不是有效的 Base64URL")
    padding_value = safe_value + "=" * (-len(safe_value) % 4)
    return base64.b64decode(padding_value.encode("ascii"), altchars=b"-_", validate=True)


@lru_cache(maxsize=1)
def _login_encryption_key() -> LoginEncryptionKey:
    # 密钥在进程内只生成一次；服务重启后自动轮换，前端每次登录都重新获取公钥。
    private_key = rsa.generate_private_key(public_exponent=65_537, key_size=2_048)
    encoded_public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    key_id = _base64url_encode(hashlib.sha256(encoded_public_key).digest()[:18])
    public_key = base64.b64encode(encoded_public_key).decode("ascii")
    return LoginEncryptionKey(private_key=private_key, key_id=key_id, public_key=public_key)


def _validate_login_request_metadata(
    normalized_username: str,
    key_id: str,
    issued_at: int,
    request_id: str,
    login_key: LoginEncryptionKey,
) -> None:
    if not normalized_username or not secrets.compare_digest(login_key.key_id, key_id):
        raise _invalid_encrypted_login_request()

    now_millis = time.time_ns() // 1_000_000
    if issued_at < now_millis - _LOGIN_REQUEST_TTL_MILLIS:
        raise _invalid_encrypted_login_request()
    if issued_at > now_millis + _LOGIN_MAX_FUTURE_SKEW_MILLIS:
        raise _invalid_encrypted_login_request()

    try:
        parsed_request_id = UUID(str(request_id or ""))
    except ValueError as exc:
        raise _invalid_encrypted_login_request() from exc
    if str(parsed_request_id) != str(request_id).lower():
        raise _invalid_encrypted_login_request()


def _consume_login_request_id(request_id: str, issued_at: int) -> None:
    now_millis = time.time_ns() // 1_000_000
    with _CONSUMED_LOGIN_REQUEST_IDS_LOCK:
        expired_ids = [
            cached_request_id
            for cached_request_id, expires_at in _CONSUMED_LOGIN_REQUEST_IDS.items()
            if expires_at < now_millis
        ]
        for cached_request_id in expired_ids:
            _CONSUMED_LOGIN_REQUEST_IDS.pop(cached_request_id, None)

        if len(_CONSUMED_LOGIN_REQUEST_IDS) >= _LOGIN_REPLAY_CACHE_MAX_ENTRIES:
            raise HTTPException(status_code=429, detail="安全登录请求过多，请稍后重试")
        if request_id in _CONSUMED_LOGIN_REQUEST_IDS:
            raise _invalid_encrypted_login_request()

        _CONSUMED_LOGIN_REQUEST_IDS[request_id] = (
            max(now_millis, issued_at) + _LOGIN_REPLAY_ENTRY_TTL_MILLIS
        )


def _build_login_additional_data(
    normalized_username: str,
    key_id: str,
    issued_at: int,
    request_id: str,
) -> bytes:
    return f"{normalized_username}\n{key_id}\n{issued_at}\n{request_id}".encode("utf-8")


@lru_cache(maxsize=1)
def _token_secret() -> bytes:
    settings = get_settings()
    configured_secret = settings.auth_token_secret.strip()
    return (configured_secret or _TOKEN_SECRET_FALLBACK).encode("utf-8")


def _token_ttl_seconds() -> int:
    settings = get_settings()
    return max(300, settings.auth_token_ttl_seconds or _TOKEN_TTL_SECONDS_DEFAULT)


def _now_seconds() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _normalize_username(username: str) -> str:
    return str(username or "").strip().lower()


def _verify_password(raw_password: str, stored_password_hash: str) -> bool:
    expected_hash = _hash_password(str(raw_password or ""))
    return hmac.compare_digest(expected_hash, str(stored_password_hash or "").strip().lower())


def _hash_password(raw_password: str) -> str:
    return hashlib.sha256(str(raw_password or "").encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def _auth_user_repository() -> AuthUserRepository:
    return build_auth_user_repository()


def _find_account_by_username(username: str) -> AuthAccount | None:
    try:
        return _auth_user_repository().find_by_username(_normalize_username(username))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=f"登录用户表不可用：{exc}") from exc


def _create_account(account: AuthAccount) -> AuthAccount:
    try:
        return _auth_user_repository().create_user(account)
    except AuthUserAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail="账号已存在，请直接登录") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=f"注册用户表不可用：{exc}") from exc


def _invalid_token() -> HTTPException:
    return HTTPException(status_code=401, detail="登录凭据无效，请重新登录")


def _invalid_encrypted_login_request() -> HTTPException:
    return HTTPException(status_code=400, detail="登录加密请求无效，请重新提交")
