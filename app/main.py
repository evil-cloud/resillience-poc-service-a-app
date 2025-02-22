import os
import logging
import requests
import pybreaker
import redis
from fastapi import FastAPI
from config import SERVICE_B_URL, SERVICE_C_URL, REDIS_HOST, REDIS_PORT
from logging_config import setup_logging
from prometheus_client import Counter
from prometheus_fastapi_instrumentator import Instrumentator

# Configurar logging
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

@app.get("/api/v1/consul")
async def call_service_b():
    try:
        logger.info("Verificando si la respuesta está en caché...")
        cached_response = redis_client.get("service_b_response")
        if cached_response:
            logger.info("✅ Usando respuesta cacheada de Redis.")
            cache_hits.inc()
            return {"message": f"Respuesta cacheada de B: {cached_response}"}

        logger.info("🚀 Llamando a Service B...")
        response = circuit_breaker.call(requests.get, SERVICE_B_URL, timeout=2)

        if response.status_code >= 500:
            raise pybreaker.CircuitBreakerError(f"Service B devolvió {response.status_code}")

        try:
            redis_client.setex("service_b_response", CACHE_TTL, response.text)
            logger.info(f"💾 Respuesta de B almacenada en caché ({CACHE_TTL}s).")
        except Exception as e:
            logger.error(f"⚠️ Error guardando en Redis: {str(e)}")

        return {"message": f"Respuesta de B: {response.text}"}

    except (requests.exceptions.RequestException, pybreaker.CircuitBreakerError) as e:
        logger.warning(f"⚡ Circuit Breaker activado: {str(e)}. Redirigiendo a Service C.")
        circuit_breaker_activations.inc()

        try:
            response = requests.get(SERVICE_C_URL, timeout=2)
            return {"message": f"B falló, respuesta de C: {response.text}"}
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error crítico: Service C también falló: {str(e)}")
            return {"error": "Ambos servicios B y C fallaron"}

    except Exception as e:
        logger.error(f"🔥 Error inesperado en Service A: {str(e)}")
        return {"error": "Fallo inesperado en Service A"}

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "A"}

