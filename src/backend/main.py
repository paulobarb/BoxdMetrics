import os
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List
import etl
from prometheus_fastapi_instrumentator import Instrumentator
import logging
import urllib.request
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("ENVIRONMENT") == "production":
        duck_token = os.getenv("DUCKDNS_TOKEN")
        duck_domain = os.getenv("DUCKDNS_DOMAIN")
        
        if duck_token and duck_domain:
            try:
                url = f"https://www.duckdns.org/update?domains={duck_domain}&token={duck_token}&ip="
                response = urllib.request.urlopen(url)
                result = response.read().decode('utf-8')

                if result.strip() == "OK":
                    logger.info(f"Successfully updated DuckDNS for {duck_domain}")
                else:
                    logger.error(f"DuckDNS failed: {result}")
            except Exception as e:
                logger.error(f"Failed to update DuckDNS: {e}")
    yield

app = FastAPI(title="BoxdMetrics API", lifespan=lifespan)

security = HTTPBearer()
API_KEY = os.getenv("API_SECRET_KEY")

# API Key validation dependency
async def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verify the API key from the Authorization header"""
    if not API_KEY:
          raise HTTPException(status_code=500, detail="API key not configured on server")
  
    if credentials.credentials != API_KEY:
          raise HTTPException(status_code=401, detail="Invalid API key")

    return True

Instrumentator().instrument(app).expose(app)

origins = [
    "http://localhost:5173",
    "https://boxd-metrics.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/upload/")
def upload_files(
    files: List[UploadFile] = File(...),
    authenticated: bool = Security(verify_api_key) 
):
    watched_df = None
    ratings_df = None
    diary_df = None

    for uploaded_file in files: # For each uploaded file in the list of files
        try:
            if uploaded_file.filename == "watched.csv":
                watched_df = pd.read_csv(uploaded_file.file)
            elif uploaded_file.filename == "ratings.csv":
                ratings_df = pd.read_csv(uploaded_file.file)
            elif uploaded_file.filename == "diary.csv":
                diary_df = pd.read_csv(uploaded_file.file)
        except pd.errors.EmptyDataError:
            raise HTTPException(status_code=400, detail=f"The file {uploaded_file.filename} is empty.")
        except pd.errors.ParserError:
            raise HTTPException(status_code=400, detail=f"The file {uploaded_file.filename} is corrupted or not a valid CSV.")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise HTTPException(status_code=500, detail="An internal server error occurred while reading the files.")

    if watched_df is not None and ratings_df is not None and diary_df is not None:
        try:
            topCnt, topDec, oldestYear, newestYear = etl.process_watched(watched_df)
            avgRating = etl.process_ratings(ratings_df)
            topDay = etl.process_diary(diary_df)
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Something went wrong processing your files: {e}")
            raise HTTPException(status_code=500, detail="An internal server error occurred while analyzing the data.")

        statsPayload = {
            "totalMovies": int(len(watched_df)),
            "topDecade": int(topDec),
            "topCount": int(topCnt),
            "avgRating": float(avgRating),
            "topDay": str(topDay),
            "oldestYear": int(oldestYear),
            "newestYear": int(newestYear)
        }

        return statsPayload

    raise HTTPException(status_code=400, detail="Please upload watched.csv, ratings.csv, and diary.csv")
