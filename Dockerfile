# Stage 1: build the React app into static files.
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python API + Tesseract, serving the built frontend.
FROM python:3.12-slim

# Tesseract engine with the three OCR languages of the app (fra, eng, ara).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-fra \
        tesseract-ocr-eng \
        tesseract-ocr-ara \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY --from=frontend /frontend/dist frontend/dist

# Do not run as root.
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
