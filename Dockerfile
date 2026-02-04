# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (needed for geospatial libraries like shapely/geopandas if not pre-built wheels)
# sometimes 'gdal-bin', 'libgdal-dev', 'g++' are needed depending on the wheel availability
# For now, we'll assume binary wheels are available for standard linux, clean up if needed.
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 8000
EXPOSE 8000

# Define environment variable
ENV MODULE_NAME=src.backend.api.main
ENV VARIABLE_NAME=app
ENV PORT=8000

# Run uvicorn when the container launches
CMD ["uvicorn", "src.backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
