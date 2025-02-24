import os
import logging
import requests
import pybreaker
import redis
import threading
import time
from fastapi import FastAPI
from config import SERVICE_B_URL, SERVICE_C_URL, REDIS_HOST, REDIS_PORT
from logging_config import setup_logging
from prometheus_client import Counter
from prometheus_fastapi_instrumentator import Instrumentator

# Configurar logging con estándar profesional
logger = setup_logging()

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
    """ Verifica cada N segundos si Redis sigue conectado. Si falla, lanza un error crítico. """
    while True:
        try:
            if redis_client.ping():
                logger.info("[REDIS] Connection established successfully.")
            else:
                logger.critical("[REDIS] CRITICAL ERROR: Unable to establish connection to Redis.")
                os._exit(1)  # Termina el proceso si Redis no está disponible
        except redis.exceptions.ConnectionError as e:
            logger.critical(f"[REDIS] CRITICAL ERROR: Connection failed: {str(e)}")
            os._exit(1)  # Termina el proceso si Redis no está disponible
        time.sleep(REDIS_CHECK_INTERVAL)

# Iniciar la verificación de Redis en un hilo en segundo plano
threading.Thread(target=check_redis_connection, daemon=True).start()

@app.get("/api/v1/consul")
async def call_service_b():
    try:
        logger.info("[CACHE] Checking if response is cached...")
        cached_response = redis_client.get("service_b_response")
        if cached_response:
            logger.info(f"[CACHE] Cached response retrieved: {cached_response}")
            cache_hits.inc()
            return {"message": f"Cached response from B: {cached_response}"}

        logger.info("[SERVICE] Requesting Service B...")
        response = circuit_breaker.call(requests.get, SERVICE_B_URL, timeout=2)

        if response.status_code >= 500:
            raise pybreaker.CircuitBreakerError(f"Service B returned {response.status_code}")

        try:
            redis_client.setex("service_b_response", CACHE_TTL, response.text)
            logger.info(f"[CACHE] Response from B cached for {CACHE_TTL} seconds.")
        except Exception as e:
            logger.error(f"[CACHE] Error storing response in Redis: {str(e)}")

        return {"message": f"Response from B: {response.text}"}

    except (requests.exceptions.RequestException, pybreaker.CircuitBreakerError) as e:
        logger.warning(f"[CIRCUIT BREAKER] Activated: {str(e)}. Redirecting to Service C.")
        circuit_breaker_activations.inc()

        try:
            response = requests.get(SERVICE_C_URL, timeout=2)
            return {"message": f"B failed, response from C: {response.text}"}
        except requests.exceptions.RequestException as e:
            logger.error(f"[SERVICE] CRITICAL ERROR: Service C also failed: {str(e)}")
            return {"error": "Both services B and C failed"}

    except Exception as e:
        logger.error(f"[ERROR] Unexpected failure in Service A: {str(e)}")
        return {"error": "Unexpected failure in Service A"}

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "A"}
