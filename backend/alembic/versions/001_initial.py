Initial schema creation

Revision ID: 001_initial
Revises: 
Create Date: 2026-05-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("tier", sa.String(), server_default=sa.text("'free'")),
        sa.Column("role", sa.String(), server_default=sa.text("'user'")),
        sa.Column("subscription_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_id", "users", ["id"], unique=False)

    op.create_table(
        "servers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(), unique=True, nullable=False),
        sa.Column("location", sa.String(), nullable=False),
        sa.Column("ip_address", sa.String(), nullable=False),
        sa.Column("vpn_subnet", sa.String(), nullable=False),
        sa.Column("port", sa.Integer(), server_default=sa.text("51820")),
        sa.Column("public_key", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("is_premium", sa.Boolean(), server_default=sa.text("false")),
    )
    op.create_index("ix_servers_id", "servers", ["id"], unique=False)
    op.create_index("ix_servers_name", "servers", ["name"], unique=True)

    op.create_table(
        "vpn_keys",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("server_id", sa.Integer(), nullable=False),
        sa.Column("private_key", sa.String(), nullable=True),
        sa.Column("public_key", sa.String(), nullable=False),
        sa.Column("assigned_ip", sa.String(), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["server_id"], ["servers.id"]),
    )
    op.create_index("ix_vpn_keys_id", "vpn_keys", ["id"], unique=False)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(), unique=True, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_refresh_tokens_id", "refresh_tokens", ["id"], unique=False)
    op.create_index("ix_refresh_tokens_token", "refresh_tokens", ["token"], unique=True)


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    op.drop_table("vpn_keys")
    op.drop_table("servers")
    op.drop_table("users")
