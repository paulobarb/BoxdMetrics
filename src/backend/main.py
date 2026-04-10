import os
import logging

from mangum import Mangum
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
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

instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)

# Send the metrics to Grafana Cloud before the Lambda function dies
@app.middleware("http")
async def push_metrics_after_request(request: Request, call_next):
    response = await call_next(request)
    
    if is_aws and os.getenv("ENVIRONMENT") == "production":
        try:
            instrumentator.push_to_gateway(
                url=os.getenv("GRAFANA_PUSH_URL"), 
                job="boxdmetrics-api",
                auth=(os.getenv("GRAFANA_USER_ID"), os.getenv("GRAFANA_TOKEN"))
            )
        except Exception as e:
            logger.error(f"Failed to push metrics to Grafana Cloud: {e}")
            
    return response

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(upload_router, prefix="/api")

handler = Mangum(app)