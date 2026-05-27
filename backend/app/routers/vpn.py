import logging
import ipaddress
from datetime import datetime, timezone
from typing import Optional
from base64 import b64encode

from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app import auth, database, models, schemas

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vpn", tags=["VPN"])


def generate_wireguard_keys() -> tuple[str, str]:
    private_key_obj = x25519.X25519PrivateKey.generate()
    public_key_obj = private_key_obj.public_key()

    private_bytes = private_key_obj.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = public_key_obj.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    return b64encode(private_bytes).decode("utf-8"), b64encode(public_bytes).decode("utf-8")


def build_config(private_key: str, assigned_ip: str, server: models.Server) -> str:
    return f"""[Interface]
PrivateKey = {private_key}
Address = {assigned_ip}
DNS = 1.1.1.1, 9.9.9.9

[Peer]
PublicKey = {server.public_key}
Endpoint = {server.ip_address}:{server.port}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
"""


def assign_ip_from_subnet(db_keys, subnet: str) -> str:
    assigned_ips = set(db_keys)
    network = ipaddress.ip_network(subnet)
    hosts = list(network.hosts())
    gateway = str(hosts[0]) if hosts else None

    for host in hosts:
        if gateway and str(host) == gateway:
            continue
        candidate = f"{host}/32"
        if candidate not in assigned_ips:
            return candidate

    raise HTTPException(status_code=500, detail="No available IPs in server subnet")


@router.post("/config/{server_id}", response_model=schemas.VPNConfigResponse)
async def generate_config(
    server_id: int,
    db: AsyncSession = Depends(database.get_db),
    current_user: Optional[models.User] = Depends(auth.get_current_user_optional),
):
    server_result = await db.execute(select(models.Server).where(models.Server.id == server_id))
    server = server_result.scalar_one_or_none()

    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    if server.is_premium and (current_user is None or current_user.tier != "premium"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This server is reserved for premium users")

    user_id = current_user.id if current_user else None
    key_result = await db.execute(
        select(models.VPNKey).where(
            models.VPNKey.user_id == user_id,
            models.VPNKey.server_id == server_id,
            models.VPNKey.is_revoked.is_(False),
        )
    )
    existing_key = key_result.scalar_one_or_none()

    if existing_key:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Private key can only be retrieved at initial issuance. Re-issue a new key if needed.",
        )

    private_key, public_key = generate_wireguard_keys()

    ips_result = await db.execute(
        select(models.VPNKey.assigned_ip).where(
            models.VPNKey.server_id == server_id,
            models.VPNKey.is_revoked.is_(False),
        )
    )

    assigned_ip = assign_ip_from_subnet(ips_result.scalars().all(), server.vpn_subnet)

    db_key = models.VPNKey(
        user_id=user_id,
        server_id=server_id,
        private_key=None,
        public_key=public_key,
        assigned_ip=assigned_ip,
    )
    db.add(db_key)
    await db.commit()

    logger.info(f"VPN config issued for user_id={user_id}, server_id={server_id}")
    return {
        "config": build_config(private_key, assigned_ip, server),
        "private_key": private_key,
        "public_key": public_key,
        "server_ip": server.ip_address,
        "initial_issuance": True,
    }


@router.post("/config/{key_id}/revoke")
async def revoke_key(
    key_id: int,
    body: schemas.VPNKeyRevoke = None,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    result = await db.execute(select(models.VPNKey).where(models.VPNKey.id == key_id))
    key = result.scalar_one_or_none()

    if not key:
        raise HTTPException(status_code=404, detail="VPN key not found")

    if not current_user.is_admin and key.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to revoke this key")

    if key.is_revoked:
        raise HTTPException(status_code=400, detail="Key is already revoked")

    key.is_revoked = True
    key.revoked_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info(f"VPN key {key_id} revoked by user_id={current_user.id}, reason={body.reason if body else 'N/A'}")
    return {"message": "VPN key revoked successfully", "key_id": key_id}


@router.post("/config/{server_id}/rotate")
async def rotate_key(
    server_id: int,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    server_result = await db.execute(select(models.Server).where(models.Server.id == server_id))
    server = server_result.scalar_one_or_none()

    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    if server.is_premium and current_user.tier != "premium":
        raise HTTPException(status_code=403, detail="Premium access required")

    old_keys_result = await db.execute(
        select(models.VPNKey).where(
            models.VPNKey.user_id == current_user.id,
            models.VPNKey.server_id == server_id,
            models.VPNKey.is_revoked.is_(False),
        )
    )
    old_key = old_keys_result.scalar_one_or_none()

    private_key, public_key = generate_wireguard_keys()

    ips_result = await db.execute(
        select(models.VPNKey.assigned_ip).where(
            models.VPNKey.server_id == server_id,
            models.VPNKey.is_revoked.is_(False),
        )
    )
    assigned_ip = assign_ip_from_subnet(ips_result.scalars().all(), server.vpn_subnet)

    if old_key:
        old_key.is_revoked = True
        old_key.revoked_at = datetime.now(timezone.utc)
        await db.commit()

    new_key = models.VPNKey(
        user_id=current_user.id,
        server_id=server_id,
        private_key=None,
        public_key=public_key,
        assigned_ip=assigned_ip,
    )
    db.add(new_key)
    await db.commit()

    logger.info(f"VPN key rotated for user_id={current_user.id}, server_id={server_id}")
    return {
        "config": build_config(private_key, assigned_ip, server),
        "private_key": private_key,
        "public_key": public_key,
        "server_ip": server.ip_address,
        "initial_issuance": False,
    }


@router.get("/keys", response_model=list[schemas.VPNKeyResponse])
async def list_user_keys(
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    result = await db.execute(
        select(models.VPNKey).where(models.VPNKey.user_id == current_user.id)
    )
    return result.scalars().all()


@router.get("/keys/{key_id}", response_model=schemas.VPNKeyResponse)
async def get_key(
    key_id: int,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    result = await db.execute(
        select(models.VPNKey).where(
            models.VPNKey.id == key_id,
            models.VPNKey.user_id == current_user.id,
        )
    )
    key = result.scalar_one_or_none()

    if not key:
        raise HTTPException(status_code=404, detail="VPN key not found")

    return key
