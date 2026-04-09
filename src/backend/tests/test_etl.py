import pandas as pd
import pytest
from fastapi import HTTPException
from backend.services.etl_letterboxd import process_watched, process_ratings, process_diary


# Test process_watched function.

def test_process_watched_valid():
    years = [1990, 1990, 1990, 2000, 2000]
    df = pd.DataFrame({'Year': years})
    
    result = process_watched(df)
    assert result == (3, 1990, 1990, 2000)

def test_process_watched_empty():
    empty_df = pd.DataFrame(columns=['Year'])
    result = process_watched(empty_df)
    assert result == (0, 0, 0, 0)

def test_process_watched_missing_columns():
    df = pd.DataFrame()

    with pytest.raises(HTTPException) as e:
        process_watched(df)
    assert e.value.status_code == 400

def test_process_watched_wrong_columns():
    df = pd.DataFrame({'Title': ['Movie 1', 'Movie 2']})
    with pytest.raises(HTTPException) as e:
        process_watched(df)
    assert e.value.status_code == 400

# -----------------------------
# Test process_ratings function
# -----------------------------

def test_process_ratings_valid():
    ratings= [4.5, 4.0, 4.5]
    df = pd.DataFrame({'Rating': ratings})
    
    result = process_ratings(df)
    assert result == 4.33

def test_process_ratings_empty():
    empty_df = pd.DataFrame(columns=['Rating'])
    result = process_ratings(empty_df)
    assert result == 0.0


def test_process_ratings_missing_columns():
    df = pd.DataFrame()

    with pytest.raises(HTTPException) as e:
        process_ratings(df)
    assert e.value.status_code == 400

def test_process_ratings_wrong_columns():
    df = pd.DataFrame({'Title': ['Movie 1', 'Movie 2']})
    with pytest.raises(HTTPException) as e:
        process_ratings(df)
    assert e.value.status_code == 400

# ----------------------------
# Test process_diary function
# ----------------------------

def test_process_diary_valid():
    watched_date = ['2024-05-30', '2024-06-11', '2024-06-30', '2024-05-26']
    df = pd.DataFrame({'Watched Date': watched_date})
    
    result = process_diary(df)
    assert result == "Sunday"

def test_process_diary_empty():
    empty_df = pd.DataFrame(columns=['Watched Date'])
    result = process_diary(empty_df)
    assert result == "Unknown"


def test_process_diary_missing_columns():
    df = pd.DataFrame()

    with pytest.raises(HTTPException) as e:
        process_diary(df)
    assert e.value.status_code == 400

def test_process_diary_wrong_columns():
    df = pd.DataFrame({'Title': ['Movie 1', 'Movie 2']})
    with pytest.raises(HTTPException) as e:
        process_diary(df)
    assert e.value.status_code == 400
# ----------------------------
# Integration Test for Full ETL Pipeline
# ----------------------------

def test_full_etl_pipeline():
    """Integration test covering all three ETL functions together"""
    # Create realistic Letterboxd dataframes
    watched_df = pd.DataFrame({
        'Year': [1994, 1994, 1999, 2008, 2010, 2019]
    })
    
    ratings_df = pd.DataFrame({
        'Rating': [5.0, 4.5, 4.5, 4.0, 5.0, 3.5]
    })
    
    diary_df = pd.DataFrame({
        'Watched Date': [
            '2024-01-15',  # Monday
            '2024-01-20',  # Saturday
            '2024-01-27',  # Saturday
            '2024-02-03'   # Saturday
        ]
    })
    
    # Execute ETL pipeline
    top_cnt, top_dec, oldest, newest = process_watched(watched_df)
    avg_rating = process_ratings(ratings_df)
    top_day = process_diary(diary_df)
    
    # Verify results
    assert top_cnt == 3  # Two movies from 1990s
    assert top_dec == 1990  # 1990s is top decade
    assert oldest == 1994
    assert newest == 2019
    assert avg_rating == 4.42  # Rounded to 2 decimals
    assert top_day == "Saturday"