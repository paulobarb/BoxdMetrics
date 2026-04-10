import os

#DUCKDNS_URL = os.getenv("DUCKDNS_API_URL", "https://www.duckdns.org/update")
API_KEY = os.getenv("API_SECRET_KEY", "dev_secret_123")
ENV = os.getenv("ENVIRONMENT", "development")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")