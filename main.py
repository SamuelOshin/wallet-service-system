"""
FastAPI application entry point.

Initializes the FastAPI app, registers routes, and configures exception handlers.
"""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.core.config import get_settings
from app.api.routes import api_keys, auth, wallet
from app.api.utils.exception_handlers import (
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)

from contextlib import asynccontextmanager
from app.api.core.database import engine
from app.api.models import Base
import logging

# Clear cached settings to ensure fresh load from .env
try:
    get_settings.cache_clear()
except AttributeError:
    pass

settings = get_settings()

logger = logging.getLogger(__name__)


def _mask_value(value: str, prefix: int = 8, suffix: int = 6) -> str:
    if not value:
        return "<empty>"
    if len(value) <= prefix + suffix:
        return value
    return f"{value[:prefix]}...{value[-suffix:]}"


# Only raise error for actual placeholder strings
if settings.GOOGLE_CLIENT_ID and (
    settings.GOOGLE_CLIENT_ID == "your-google-client-id.apps.googleusercontent.com"
    or settings.GOOGLE_CLIENT_ID == "your-client-id.apps.googleusercontent.com"
    or settings.GOOGLE_CLIENT_ID.startswith("your-")
):
    logger.warning(
        "Detected placeholder Google client id. Make sure GOOGLE_CLIENT_ID is set in your environment or .env file."
    )
    if settings.DEBUG:
        raise RuntimeError(
            "GOOGLE_CLIENT_ID is a placeholder. Set your real client ID in environment or .env before starting the app."
        )

logger.info(
    "Google OAuth: client_id=%s redirect_uri=%s",
    _mask_value(settings.GOOGLE_CLIENT_ID),
    settings.GOOGLE_REDIRECT_URI,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables synchronously
    Base.metadata.create_all(engine)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Wallet Service with Paystack, JWT & API Keys",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(api_keys.router, prefix=settings.API_V1_PREFIX)
app.include_router(wallet.router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    """
    Root endpoint for health check.

    Returns:
        dict: Basic API information.

    """
    return {
        "message": "Wallet Service API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring.

    Returns:
        dict: Service health status.
    """
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.APP_PORT,
        reload=settings.DEBUG,
    )
