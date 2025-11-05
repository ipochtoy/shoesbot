FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Collect static files
RUN python shoessite/manage.py collectstatic --noinput || true

# Expose port
EXPOSE 8000

# Start command
CMD python shoessite/manage.py migrate && \
    cd shoessite && \
    gunicorn shoessite.wsgi:application --bind 0.0.0.0:$PORT

