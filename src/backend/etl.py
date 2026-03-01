import pandas as pd
from fastapi import HTTPException

def validate_columns(df, required_columns, filename):
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid format in {filename}. Missing columns: {missing_cols}"
        )

def process_watched(df):
    validate_columns(df, ['Year'], 'watched.csv')
    
    df['Year'] = pd.to_numeric(df['Year'], errors='coerce')
    
    clean_df = df.dropna(subset=['Year']).copy()
    
    if clean_df.empty:
        return 0, 0, 0, 0
        
    clean_df['Decade'] = (clean_df['Year'] // 10) * 10
    decadeCounts = clean_df['Decade'].value_counts()
    
    topDecade = int(decadeCounts.idxmax())
    topCount = int(decadeCounts.max())
    oldestYear = int(clean_df['Year'].min())
    newestYear = int(clean_df['Year'].max())

    return topCount, topDecade, oldestYear, newestYear

def process_ratings(df):
    validate_columns(df, ['Rating'], 'ratings.csv')
    
    df['Rating'] = pd.to_numeric(df['Rating'], errors='coerce')
    avgRating = df['Rating'].mean()
    
    if pd.isna(avgRating):
        return 0.0
        
    return round(float(avgRating), 2)

def process_diary(df):
    validate_columns(df, ['Watched Date'], 'diary.csv')
    
    df['Watched Date'] = pd.to_datetime(df['Watched Date'], errors='coerce')
    clean_df = df.dropna(subset=['Watched Date']).copy()
    
    if clean_df.empty:
        return "Unknown"
        
    clean_df['Day'] = clean_df['Watched Date'].dt.day_name()
    topDay = str(clean_df['Day'].value_counts().idxmax())

    return topDay