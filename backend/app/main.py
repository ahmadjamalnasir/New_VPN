import logging
import logging.config
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, users, servers, vpn, admin
from app.rate_limiter import RateLimitMiddleware
from app.config import settings
from app import logging_config

logging.config.dictConfig(logging_config.LOGGING_CONFIG)

logger = logging.getLogger(__name__)

os.makedirs("logs", exist_ok=True)

app = FastAPI(title="PrimeVPN Backend", version="1.0.0")

cors_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
allow_credentials = "*" not in cors_origins and len(cors_origins) > 0

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    RateLimitMiddleware,
    per_minute=settings.rate_limit_per_minute,
    per_hour=settings.rate_limit_per_hour,
)


@app.on_event("startup")
async def startup_event():
    logger.info("PrimeVPN Backend starting up")
    logger.info(f"Environment: {settings.environment}")
    logger.info("Use Alembic migrations to manage database schema")


@app.get("/")
async def root():
    return {"message": "VPN Project API is running"}


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(servers.router)
app.include_router(vpn.router)
app.include_router(admin.router)
