import os
import secrets
from fastapi import HTTPException, Request, Header
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.config import API_KEY

is_aws = os.environ.get('LAMBDA_TASK_ROOT')

# --- RATE LIMITER ---
def get_real_ip(request: Request):
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"

if is_aws:
    limiter = Limiter(key_func=get_real_ip)
else:
    # In Docker, use the service name 'redis' instead of 'localhost'
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    limiter = Limiter(key_func=get_remote_address, storage_uri=redis_url)

# --- API KEY AUTH ---
async def verify_api_key(x_api_key: str | None = Header(None)):
    if not API_KEY:
        raise HTTPException(status_code=503, detail="API key not configured")
    if not x_api_key or not secrets.compare_digest(x_api_key.encode(), API_KEY.encode()):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True
