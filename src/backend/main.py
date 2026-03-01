import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import etl

import logging
logger = logging.getLogger(__name__)

app = FastAPI(title="BoxdMetrics API")

@app.post("/upload/")
def upload_files(files: List[UploadFile] = File(...)):
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
