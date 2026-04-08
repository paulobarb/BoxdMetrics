import os
import httpx
import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.api.routes import router as upload_router
from backend.core.config import DUCKDNS_URL
from backend.core.security import limiter

logger = logging.getLogger(__name__)

# --- LIFESPAN ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    token = os.getenv("DUCKDNS_TOKEN")
    domain = os.getenv("DUCKDNS_DOMAIN")

    if token and domain:
        try:
            url = f"{DUCKDNS_URL}?domains={domain}&token={token}&ip="

            if not url.startswith("https://"):
                logger.error(f"Insecure URL scheme: {url}")
                raise ValueError("Only HTTPS URLs allowed for DuckDNS")

            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                result = response.text.strip()

            if result == "OK":
                logger.info(f"DuckDNS updated for {domain}")
            else:
                logger.error(f"DuckDNS update failed: {result}")
        except Exception as e:
            logger.error(f"DuckDNS error: {e}")
    yield

app = FastAPI(
    title="BoxdMetrics API", 
    lifespan=lifespan,
    docs_url=None if os.getenv("ENVIRONMENT") == "production" else "/docs",
    redoc_url=None if os.getenv("ENVIRONMENT") == "production" else "/redoc"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- MIDDLEWARE & METRICS ---
Instrumentator().instrument(app).expose(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://boxd-metrics.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router, prefix="/api")