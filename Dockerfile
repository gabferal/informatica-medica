FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero (para cache)
COPY requirements-production.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements-production.txt

# Copiar código
COPY . .

# Crear directorio de uploads
RUN mkdir -p static/uploads/assignments static/uploads/materials

# Variables de entorno
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PORT=8080

# Exponer puerto
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Comando de inicio con timeout más largo
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--timeout", "120", "--worker-class", "sync", "app:app"]