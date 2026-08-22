# author: jf
from pydantic import BaseModel, ConfigDict, Field


class AuthLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=254)
    keyId: str = Field(min_length=1, max_length=128)
    encryptedKey: str = Field(min_length=1, max_length=1024)
    iv: str = Field(min_length=1, max_length=64)
    encryptedPassword: str = Field(min_length=1, max_length=4096)
    issuedAt: int = Field(gt=0)
    requestId: str = Field(min_length=1, max_length=64)


class AuthLoginKeyResponse(BaseModel):
    algorithm: str
    keyId: str
    publicKey: str


class AuthRegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8)
    displayName: str = Field(min_length=1, max_length=64)


class AuthUserResponse(BaseModel):
    id: str
    username: str
    displayName: str
    role: str
    permissions: list[str]


class AuthLoginResponse(BaseModel):
    accessToken: str
    user: AuthUserResponse
