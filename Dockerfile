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

# Copy start script
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Collect static files
RUN python shoessite/manage.py collectstatic --noinput || true

# Expose port
EXPOSE 8000

# Simple CMD
CMD ["/start.sh"]

