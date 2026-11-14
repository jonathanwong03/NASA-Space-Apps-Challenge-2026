# Build context: ./backend (so the shared "common" package can be copied in)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY requirements-common.txt /app/requirements-common.txt
COPY catalog_service/requirements.txt /app/catalog_service/requirements.txt
RUN pip install -r /app/catalog_service/requirements.txt

COPY common /app/common
COPY catalog_service /app/catalog_service

RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s --retries=12   CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=4).status == 200 else 1)"
CMD ["uvicorn", "catalog_service.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
