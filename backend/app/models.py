from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    tier = Column(String, default="free")
    role = Column(String, default="user")
    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    vpn_keys = relationship("VPNKey", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user")

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    location = Column(String)
    ip_address = Column(String)
    vpn_subnet = Column(String)
    port = Column(Integer, default=51820)
    public_key = Column(String)
    is_active = Column(Boolean, default=True)
    is_premium = Column(Boolean, default=False)

    vpn_keys = relationship("VPNKey", back_populates="server")


class VPNKey(Base):
    __tablename__ = "vpn_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    server_id = Column(Integer, ForeignKey("servers.id"))
    private_key = Column(String, nullable=True)
    public_key = Column(String)
    assigned_ip = Column(String)
    is_revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="vpn_keys")
    server = relationship("Server", back_populates="vpn_keys")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="refresh_tokens")
