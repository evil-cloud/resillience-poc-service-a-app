# 🛠️ Etapa 1: Construcción
FROM python:3.9-slim AS builder

WORKDIR /app

# Crear usuario "app" en la etapa builder
RUN groupadd -g 3000 app && useradd -m -u 10001 -g 3000 --no-log-init app

# Copiar dependencias y optimizar instalación
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# 🏗️ Etapa 2: Imagen final
FROM python:3.9-slim

WORKDIR /app

# Crear el mismo usuario "app" en la imagen final
RUN groupadd -g 3000 app && useradd -m -u 10001 -g 3000 --no-log-init app

# Copiar dependencias desde la imagen builder
COPY --from=builder /install /usr/local

# Copiar la aplicación
COPY app /app

# Ajustar permisos al usuario "app"
RUN chown -R app:app /app

# Cambiar a usuario seguro
USER app

# Exponer el puerto
EXPOSE 8000

# Comando de arranque
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

