FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
# Railway injects PORT at runtime; default to 8000 locally.
CMD uvicorn src.backend.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
