# Use official lightweight Python
FROM python:3.11-slim

# Install system deps (if any libs need compilation)
RUN apt-get update && apt-get install -y build-essential gcc && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application code
COPY . /app

COPY credentials.json /app/credentials.json


# Ensure the credentials file path is present (container will use /app/credentials.json if present)
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json

# Expose port Cloud Run expects
EXPOSE 8080

# Default start command (runs python-server.py)
CMD ["python3", "python-server.py"]
