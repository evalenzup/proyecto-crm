FROM python:3.10
WORKDIR /app

# pg_dump: respaldo diario a Google Drive (scripts/backup_drive.py)
# libreoffice: conversión docx→pdf para la generación de contratos (Fase 0b)
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client libreoffice-writer \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY ./app ./app

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/live')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
