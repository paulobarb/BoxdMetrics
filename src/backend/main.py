import os
import logging

from mangum import Mangum
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import REGISTRY, push_to_gateway
from prometheus_client.exposition import basic_auth_handler
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.routes import router as upload_router
from core.security import limiter

logger = logging.getLogger(__name__)

app = FastAPI(
    title="BoxdMetrics API",
    docs_url=None if os.getenv("ENVIRONMENT") == "production" else "/docs",
    redoc_url=None if os.getenv("ENVIRONMENT") == "production" else "/redoc"
)

# CORS configuration based on environment
is_aws = os.environ.get('LAMBDA_TASK_ROOT')
is_local_dev = os.environ.get('ENVIRONMENT') == 'development'

if is_local_dev or not is_aws:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3001", "http://localhost:3000", "http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:5500", "http://localhost:8080"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

instrumentator = Instrumentator().instrument(app)

def grafana_auth_handler(url, method, timeout, headers, data):
    username = os.getenv("GRAFANA_USER_ID")
    password = os.getenv("GRAFANA_TOKEN")
    return basic_auth_handler(url, method, timeout, headers, data, username, password)

# Send the metrics to Grafana Cloud before the Lambda function dies
@app.middleware("http")
async def push_metrics_after_request(request: Request, call_next):
    response = await call_next(request)

    push_url = os.getenv("GRAFANA_PUSH_URL")
    
    if is_aws and os.getenv("ENVIRONMENT") == "production" and push_url:
        try:
            push_to_gateway(
                push_url,
                job="boxdmetrics-api",
                registry=REGISTRY,
                handler=grafana_auth_handler
            )
        except Exception as e:
            logger.error(f"Grafana Push Failed: {e}")
            
    return response

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(upload_router, prefix="/api")

handler = Mangum(app)