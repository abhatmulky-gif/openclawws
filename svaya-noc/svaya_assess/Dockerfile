FROM python:3.11-slim

WORKDIR /app

# Install dependencies first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY . .

# Create writable data directory for SQLite
RUN mkdir -p /data && chmod 777 /data
ENV ASSESS_DB_PATH=/data/leads.db

EXPOSE 8080

# Production: gunicorn with 2 sync workers (suitable for Railway free tier)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "60", "app:app"]
