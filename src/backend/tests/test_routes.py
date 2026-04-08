import os
import io
from fastapi.testclient import TestClient

from backend.main import app

# Create a fake browser to hit the API
client = TestClient(app)
API_KEY = os.environ["API_SECRET_KEY"]

# -----------------
# Success tests
# -----------------

def test_upload_success():
    fake_watched = io.BytesIO(b"Year\n1999\n2001\n2008")
    fake_ratings = io.BytesIO(b"Rating\n4.5\n5.0\n3.0")
    fake_diary = io.BytesIO(b"Watched Date\n2024-05-30\n2024-06-11\n2024-06-30")
    
    files = [
        ("files", ("watched.csv", fake_watched, "text/csv")),
        ("files", ("ratings.csv", fake_ratings, "text/csv")),
        ("files", ("diary.csv", fake_diary, "text/csv"))
    ]
    
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    response = client.post("/api/upload/", headers=headers, files=files)
    
    assert response.status_code == 200
    
    data = response.json()
    assert "totalMovies" in data
    assert "avgRating" in data
    assert data["totalMovies"] == 3


# -----------------
# Test rate limiter
# -----------------

def test_rate_limiting():
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "X-Forwarded-For": "192.168.1.100"
        }

    fake_file = ("files", ("dummy.csv", b"dummy", "text/csv"))
    
    # Exhaust the limit (3 requests per minute)
    for _ in range(3):
        client.post("/api/upload/", headers=headers, files=[fake_file])
        
    response = client.post("/api/upload/", headers=headers, files=[fake_file])
    
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.text

# -------------
# Test security
# -------------

def test_upload_missing_auth_header():
    # Sending no API key should get a 401 Forbidden
    response = client.post("/api/upload/")
    assert response.status_code == 401

def test_upload_invalid_api_key():
    # Sending a fake API key should get a 401 Unauthorized
    headers = {"Authorization": "Bearer FAKE_KEY"}
    response = client.post("/api/upload/", headers=headers)
    assert response.status_code == 401

# --- VALIDATION TESTS ---

def test_upload_missing_files():
    # Sending a valid API key, but no files
    headers = {"Authorization": f"Bearer {API_KEY}"}
    response = client.post("/api/upload/", headers=headers)
    
    # FastAPI automatically throws a 422 Unprocessable Entity if required files are missing
    assert response.status_code == 422

def test_upload_file_too_large():
    # Generate a fake file exactly 2.5 MB in size
    fake_large_file = io.BytesIO(b"0" * int(2.5 * 1024 * 1024))
    
    files = [
        ("files", ("watched.csv", fake_large_file, "text/csv"))
    ]
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    response = client.post("/api/upload/", headers=headers, files=files)
    
    # Should catch this and throw a 400
    assert response.status_code == 400
    assert "Maximum allowed is 2MB" in response.json()["detail"]