FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy only requirements first to leverage Docker layer caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Then copy rest of the application files
COPY . .
