FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Copia los 4 paquetes Python en modo editable (`06_M4_api.md` Dockerfile).
# El build espera ser invocado desde la raíz del repo: `docker build -f api/Dockerfile .`
COPY core/ core/
COPY engine/ engine/
COPY analytics/ analytics/
COPY api/ api/

RUN pip install --upgrade pip \
 && pip install -e ./core -e ./engine -e ./analytics -e ./api

# El volumen montado por docker-compose en `data/` provee la SQLite pre-poblada.
VOLUME ["/app/data"]

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
