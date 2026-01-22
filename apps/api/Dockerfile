FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
# netcat for waiting for DB
RUN apt-get update && apt-get install -y --no-install-recommends \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Command is overridden in docker-compose for worker vs api
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
