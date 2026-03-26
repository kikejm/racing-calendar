# Usa una imagen ligera de Python
FROM python:3.11-slim

# Evita que Python genere archivos .pyc y buffer de salida
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente, datos y frontend
COPY src/ ./src/
COPY data/ ./data/
COPY public/ ./public/

# Exponer el puerto (aunque la nube lo gestiona, es buena práctica)
EXPOSE 8080

# Comando de inicio: apunta a src.api:app
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8080"]