FROM python:3.9

WORKDIR /app

# Copiar dependencias y optimizar instalación
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY app /app

# Exponer el puerto de la aplicación
EXPOSE 8000

# Definir el comando de arranque
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

