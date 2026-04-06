import os
import logging
import pandas as pd
import urllib.request
import asyncio
from typing import List
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from prometheus_fastapi_instrumentator import Instrumentator

import etl

# --- CONFIGURATION ---
logger = logging.getLogger(__name__)
DUCKDNS_URL = os.getenv("DUCKDNS_API_URL", "https://www.duckdns.org/update")
API_KEY = os.getenv("API_SECRET_KEY")

# LIFESPAN ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("ENVIRONMENT") == "production":
        token = os.getenv("DUCKDNS_TOKEN")
        domain = os.getenv("DUCKDNS_DOMAIN")
        
        if token and domain:
            try:
                url = f"{DUCKDNS_URL}?domains={domain}&token={token}&ip="

                loop = asyncio.get_event_loop()
                def fetch_url():
                    with urllib.request.urlopen(url) as response:
                        return response.read().decode('utf-8')
                
                result = await loop.run_in_executor(None, fetch_url)

                if "OK" in result:
                    logger.info(f"DuckDNS updated for {domain}")
                else:
                    logger.error(f"DuckDNS error: {result}")
            except Exception as e:
                logger.error(f"Failed to update DuckDNS: {e}")
    yield

app = FastAPI(title="BoxdMetrics API", lifespan=lifespan)

# --- SECURITY ---
security = HTTPBearer()

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API key not configured")
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
def upload_files(
    files: List[UploadFile] = File(...),
    authenticated: bool = Security(verify_api_key) 
):
    watched_df = None
    ratings_df = None
    diary_df = None

    for uploaded_file in files:
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