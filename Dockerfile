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

# Change to Django directory
WORKDIR /app/shoessite

# Run migrations and start server
CMD ["sh", "-c", "python manage.py migrate && gunicorn shoessite.wsgi:application --bind 0.0.0.0:$PORT"]

