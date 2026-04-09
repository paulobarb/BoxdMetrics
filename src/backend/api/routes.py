import os

from fastapi import APIRouter, File, HTTPException, Request, Security, UploadFile
import pandas as pd
import logging

from core.security import verify_api_key, limiter
from services import etl_letterboxd

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload")
@limiter.limit("3/minute")
def upload_files(
    request: Request,
    files: list[UploadFile] = File(...),
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
            file_size_mb = file_size / (1024 * 1024)
            suggestion = " Try splitting into smaller CSV files." if file_size > 10 * 1024 * 1024 else ""
            raise HTTPException(
                status_code=400,
                detail=f"File '{uploaded_file.filename}' is {file_size_mb:.1f}MB. Maximum allowed is 2MB.{suggestion}"
            )

        try:
            if uploaded_file.filename == "watched.csv":
                watched_df = pd.read_csv(uploaded_file.file)
            elif uploaded_file.filename == "ratings.csv":
                ratings_df = pd.read_csv(uploaded_file.file)
            elif uploaded_file.filename == "diary.csv":
                diary_df = pd.read_csv(uploaded_file.file)
        except Exception as e:
            logger.error(f"File reading error: {e}")
            error_type = type(e).__name__
            raise HTTPException(
                status_code=400,
                detail=f"Error reading '{uploaded_file.filename}': {error_type}. "
                       f"Please ensure it's a valid CSV file with the correct format."
            )

    if watched_df is not None and ratings_df is not None and diary_df is not None:
        try:
            topCnt, topDec, oldestYear, newestYear = etl_letterboxd.process_watched(watched_df)
            avgRating = etl_letterboxd.process_ratings(ratings_df)
            topDay = etl_letterboxd.process_diary(diary_df)
            
            return {
                "totalMovies": len(watched_df),
                "topDecade": topDec,
                "topCount": topCnt,
                "avgRating": avgRating,
                "topDay": topDay,
                "oldestYear": oldestYear,
            "newestYear": newestYear
            }
        except Exception as e:
            logger.error(f"Processing error: {e}")
            raise HTTPException(status_code=500, detail="Data processing failed.")

    missing = []
    if watched_df is None:
        missing.append("watched.csv")
    if ratings_df is None:
        missing.append("ratings.csv")
    if diary_df is None:
        missing.append("diary.csv")

    raise HTTPException(
        status_code=400,
        detail=f"Missing required files: {', '.join(missing)}. Please upload all 3 CSV files."
    )