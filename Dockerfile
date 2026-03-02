# Use a lightweight Python image
FROM python:3.11-slim

# Set environment variables to ensure Python output is logged
# immediately and doesn't create .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies if needed (none for basic FastAPI)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc

# Copy only requirements first to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create a non-privileged user for security
# This prevents the app from running as 'root' inside the container
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# DigitalOcean App Platform defaults to 8080
EXPOSE 8080

# The CMD needs to point to the 'app' object inside 'src/main.py'
# We use --host 0.0.0.0 to allow external traffic
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]