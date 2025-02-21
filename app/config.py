import os

SERVICE_B_URL = os.getenv("SERVICE_B_URL", "http://service-b:8000/")
SERVICE_C_URL = os.getenv("SERVICE_C_URL", "http://service-c:8000/")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
