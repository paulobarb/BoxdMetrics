import pandas as pd
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from typing import List

app = FastAPI(title="BoxdMetrics API")

origins = [
    "http://localhost:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/upload/")
def upload_files(files: List[UploadFile] = File(...)):
    watched_df = None
    ratings_df = None
    diary_df = None

    for uploaded_file in files: # For each uploaded file in the list of files
        if uploaded_file.filename == "watched.csv":
            watched_df = pd.read_csv(uploaded_file.file)
        elif uploaded_file.filename == "ratings.csv":
            ratings_df = pd.read_csv(uploaded_file.file)
        elif uploaded_file.filename == "diary.csv":
            diary_df = pd.read_csv(uploaded_file.file)

    if watched_df is not None and ratings_df is not None and diary_df is not None:
        topCnt, topDec = movies_decades(watched_df)
        avgRating = average_rating(ratings_df)
        topDay = day_of_the_week(diary_df)
        oldestYear, newestYear = time_machine(watched_df)
    
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
        
    return {"error": "Please upload watched.csv, ratings.csv, and diary.csv"}

# Filter movies by decades
def movies_decades(watched):
    watched['Decade'] = (watched['Year'] // 10) * 10
    
    decadeCounts = watched['Decade'].value_counts()
    topDecade = decadeCounts.idxmax()
    topCount = decadeCounts.max()

    return topCount, topDecade

# User Average Rating
def average_rating(ratings):
    avgRating = ratings['Rating'].mean()
    return round(avgRating, 2)

# Day of the week with most watched movies
def day_of_the_week(diary):
    diary['Watched Date'] = pd.to_datetime(diary['Watched Date'])
    diary['Day'] = diary['Watched Date'].dt.day_name()
    
    dayCounts = diary['Day'].value_counts()
    topDay = dayCounts.idxmax()

    return topDay

# Oldest and Newest movie year watched
def time_machine(watched):
    oldestYear = watched['Year'].min()
    newestYear = watched['Year'].max()

    return oldestYear, newestYear

