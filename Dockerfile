# Use official Python runtime as a parent image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed for audio libraries sometimes, but keep it minimal for now)
# apt-get update && apt-get install -y ...

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python packages
# --no-cache-dir to keep image small
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
# This includes server/, config/ and data/ (knowledge base)
COPY . .

# Expose the port the app runs on
EXPOSE 8765

# Set environment variables
# PYTHONUNBUFFERED=1 ensures output is flushed immediately
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0

# Run the application
CMD ["python", "main.py"]
