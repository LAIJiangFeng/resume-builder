# author: jf


class AuthError(RuntimeError):
    """认证链路可预期的业务异常。"""


class AuthValidationError(AuthError):
    pass


class AuthUnauthorizedError(AuthError):
    pass


class AuthForbiddenError(AuthError):
    pass


class AuthConflictError(AuthError):
    pass


class AuthRateLimitError(AuthError):
    pass


class AuthServiceUnavailableError(AuthError):
    pass


class AuthStorageError(AuthError):
    pass


class AuthUserAlreadyExistsError(AuthConflictError):
    pass


class AuthVerificationWriteConflictError(AuthRateLimitError):
    pass
