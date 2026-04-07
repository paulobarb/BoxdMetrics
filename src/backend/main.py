import os
import logging
import httpx
import pandas as pd
from typing import List
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, Security, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

import etl

# --- CONFIGURATION ---
logger = logging.getLogger(__name__)
DUCKDNS_URL = os.getenv("DUCKDNS_API_URL", "https://www.duckdns.org/update")
API_KEY = os.getenv("API_SECRET_KEY")

# --- LIFESPAN ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    #if os.getenv("ENVIRONMENT") == "production":
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

# 1. Create a custom function to find the real IP
def get_real_ip(request: Request):
    # Check if the proxy passed the real IP
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Sometimes this is a comma-separated list, grab the first one
        return forwarded_for.split(",")[0].strip()
    
    # Fallback to standard network IP if running locally without proxy
    return request.client.host if request.client else "127.0.0.1"

# 2. Tell SlowAPI to use your custom function!
limiter = Limiter(key_func=get_real_ip)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- SECURITY ---
security = HTTPBearer()

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    if not API_KEY:
        raise HTTPException(status_code=503, detail="API key not configured")
    if credentials.credentials != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

# --- MIDDLEWARE & METRICS ---
Instrumentator().instrument(app).expose(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://boxd-metrics.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ROUTES ---
@app.post("/upload/")
@limiter.limit("3/minute")
def upload_files(
    request: Request,
    files: List[UploadFile] = File(...),
    authenticated: bool = Security(verify_api_key) 
):
    watched_df = None
    ratings_df = None
    diary_df = None

    for uploaded_file in files:

        uploaded_file.file.seek(0, os.SEEK_END)
        file_size = uploaded_file.file.tell()
        uploaded_file.file.seek(0)
        
        if file_size > 2 * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"File {uploaded_file.filename} is too large. Max 2MB.")

        try:
            if uploaded_file.filename == "watched.csv":
                watched_df = pd.read_csv(uploaded_file.file)
            elif uploaded_file.filename == "ratings.csv":
                ratings_df = pd.read_csv(uploaded_file.file)
            elif uploaded_file.filename == "diary.csv":
                diary_df = pd.read_csv(uploaded_file.file)
        except Exception as e:
            logger.error(f"File reading error: {e}")
            raise HTTPException(status_code=400, detail=f"Error reading {uploaded_file.filename}")

    if watched_df is not None and ratings_df is not None and diary_df is not None:
        try:
            topCnt, topDec, oldestYear, newestYear = etl.process_watched(watched_df)
            avgRating = etl.process_ratings(ratings_df)
            topDay = etl.process_diary(diary_df)
            
            return {
                "totalMovies": int(len(watched_df)),
                "topDecade": int(topDec),
                "topCount": int(topCnt),
                "avgRating": float(avgRating),
                "topDay": str(topDay),
                "oldestYear": int(oldestYear),
                "newestYear": int(newestYear)
            }
        except Exception as e:
            logger.error(f"Processing error: {e}")
            raise HTTPException(status_code=500, detail="Data processing failed.")

    raise HTTPException(status_code=400, detail="Missing required CSV files.")