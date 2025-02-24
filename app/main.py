import os
import logging
import json
import requests
import pybreaker
import redis
import threading
import time
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from config import SERVICE_B_URL, SERVICE_C_URL, REDIS_HOST, REDIS_PORT
from logging_config import setup_logging
from prometheus_client import Counter
from prometheus_fastapi_instrumentator import Instrumentator

# Configurar logging en formato JSON
logger = setup_logging()

def log_json(level, component, message, status_code=None):
    log_entry = {
        "level": level,
        "time": datetime.now(timezone.utc).isoformat(),
        "component": component,
        "message": message
    }
    if status_code is not None:
        log_entry["status_code"] = status_code
    print(json.dumps(log_entry))

# Configurar Redis
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# Configurar Circuit Breaker
circuit_breaker = pybreaker.CircuitBreaker(fail_max=3, reset_timeout=10)

# Métricas Prometheus
circuit_breaker_activations = Counter("circuit_breaker_activations", "Veces que el Circuit Breaker se activó")
cache_hits = Counter("redis_cache_hits", "Veces que se usó la caché en Redis")

# Configurar FastAPI
app = FastAPI()

# Instrumentar Prometheus
Instrumentator().instrument(app).expose(app)

# Configuración del tiempo de caché en Redis
CACHE_TTL = 20  # Segundos

# Configuración del tiempo de verificación de Redis (N segundos)
REDIS_CHECK_INTERVAL = 10  # Segundos

def check_redis_connection():
    while True:
        try:
            if redis_client.ping():
                log_json("info", "redis", "Connection established successfully.")
            else:
                log_json("critical", "redis", "CRITICAL ERROR: Unable to establish connection to Redis.")
                os._exit(1)
        except redis.exceptions.ConnectionError as e:
            log_json("critical", "redis", f"CRITICAL ERROR: Connection failed: {str(e)}")
            os._exit(1)
        time.sleep(REDIS_CHECK_INTERVAL)

threading.Thread(target=check_redis_connection, daemon=True).start()

@app.get("/api/v1/consul")
async def call_service_b():
    try:
        log_json("info", "cache", "Checking if response is cached...")
        cached_response = redis_client.get("service_b_response")
        if cached_response:
            log_json("info", "cache", f"Cached response retrieved: {cached_response}", 200)
            cache_hits.inc()
            return {"message": f"Cached response from B: {cached_response}"}

        log_json("info", "service", "Requesting Service B...")
        response = circuit_breaker.call(requests.get, SERVICE_B_URL, timeout=2)

        if response.status_code >= 500:
            raise pybreaker.CircuitBreakerError(f"Service B returned {response.status_code}")

        try:
            redis_client.setex("service_b_response", CACHE_TTL, response.text)
            log_json("info", "cache", f"Response from B cached for {CACHE_TTL} seconds.", 200)
        except Exception as e:
            log_json("error", "cache", f"Error storing response in Redis: {str(e)}", 500)

        return {"message": f"Response from B: {response.text}"}

    except (requests.exceptions.RequestException, pybreaker.CircuitBreakerError) as e:
        log_json("warning", "circuit_breaker", f"Activated: {str(e)}. Redirecting to Service C.", 503)
        circuit_breaker_activations.inc()

        try:
            response = requests.get(SERVICE_C_URL, timeout=2)
            return {"message": f"B failed, response from C: {response.text}"}
        except requests.exceptions.RequestException as e:
            log_json("error", "service", f"CRITICAL ERROR: Service C also failed: {str(e)}", 503)
            raise HTTPException(status_code=503, detail="Both services B and C failed")

    except Exception as e:
        log_json("error", "service-a", f"Unexpected failure in Service A: {str(e)}", 500)
        raise HTTPException(status_code=500, detail="Unexpected failure in Service A")

@app.get("/health")
async def health_check():
    log_json("info", "service-a", "Health check endpoint called.", 200)
    return {"status": "ok", "service": "A"}

