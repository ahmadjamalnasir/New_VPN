from datetime import datetime
from typing import Optional
import ipaddress

from pydantic import BaseModel, EmailStr, field_validator


class UserBase(BaseModel):
    email: EmailStr
    tier: Optional[str] = "free"
    role: Optional[str] = "user"
    subscription_expires_at: Optional[datetime] = None


class UserCreate(UserBase):
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class UserLogin(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None


class TokenData(BaseModel):
    email: Optional[str] = None


class TokenRefresh(BaseModel):
    refresh_token: str


class ServerBase(BaseModel):
    name: str
    location: str
    ip_address: str
    vpn_subnet: str
    port: int = 51820
    public_key: str
    is_premium: bool = False


class ServerCreate(ServerBase):
    @field_validator("vpn_subnet")
    def validate_subnet(cls, v: str):
        try:
            ipaddress.ip_network(v)
        except ValueError as exc:
            raise ValueError("Must be a valid CIDR notation (e.g. 10.8.0.0/24)") from exc
        return v


class ServerResponse(ServerBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True


class VPNConfigResponse(BaseModel):
    config: str
    private_key: Optional[str] = None
    public_key: str
    server_ip: str
    initial_issuance: bool = False


class VPNKeyRevoke(BaseModel):
    reason: Optional[str] = None


class VPNKeyResponse(BaseModel):
    id: int
    user_id: Optional[int]
    server_id: int
    public_key: str
    assigned_ip: str
    is_revoked: bool
    revoked_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True
