FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libdbus-1-dev \
    libglib2.0-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Install the package in editable mode
RUN pip install -e .

# Create config directory
RUN mkdir -p /root/.fuzzyterminal

# Set entrypoint
ENTRYPOINT ["fuzzy"]
