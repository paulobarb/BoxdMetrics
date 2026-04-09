from fastapi import HTTPException, Request, Security, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from slowapi import Limiter

from core.config import API_KEY

# --- RATE LIMITER ---
def get_real_ip(request: Request):
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"

limiter = Limiter(key_func=get_real_ip)


# --- API KEY AUTH ---
async def verify_api_key(x_api_key: str = Header(...)):
    """Verify API key from X-API-Key header.

    Using custom header instead of Authorization Bearer because
    AWS Lambda Function URLs with auth_type=NONE reject requests
    with Authorization headers (treated as AWS SigV4).
    """
    if not API_KEY:
        raise HTTPException(status_code=503, detail="API key not configured")
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True
