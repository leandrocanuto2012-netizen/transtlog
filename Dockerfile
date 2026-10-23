# ============================================================
# Dockerfile para deploy no Render (ou qualquer plataforma com container)
# Uso no Render: New + > Web Service > selecione "Docker" no Runtime
# ============================================================
FROM python:3.11-slim

# Evita arquivos .pyc e buffer de log
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instala dependências do sistema necessárias para psycopg2 (PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação
COPY . .

# Inicializa banco (cria tabelas se não existem) e inicia o servidor
# O Render injeta $PORT e $DATABASE_URL automaticamente
CMD sh -c "python init_db.py && gunicorn app:app --bind 0.0.0.0:${PORT:-8000} --workers 3 --timeout 120"
