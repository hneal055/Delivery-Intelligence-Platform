# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (needed for geospatial libraries like shapely/geopandas if not pre-built wheels)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# setuptools/wheel must be installed first on python:3.12-slim (no longer bundled)
RUN pip install --no-cache-dir setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# --- Security: run as non-root user ---
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

# Expose port 8000
EXPOSE 8000

# Define environment variable
ENV MODULE_NAME=src.backend.api.main
ENV VARIABLE_NAME=app
ENV PORT=8000

# Health check — hits the /health endpoint every 30s; 3 failures = unhealthy
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run uvicorn when the container launches
CMD ["uvicorn", "src.backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
