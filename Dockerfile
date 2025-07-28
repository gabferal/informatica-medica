FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements-production.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements-production.txt

# Copiar código
COPY . .

# Crear directorio de uploads
RUN mkdir -p static/uploads/assignments static/uploads/materials

# Exponer puerto
EXPOSE 8080

# Comando de inicio
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "app:app"]