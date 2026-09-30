FROM python:3.11-slim-trixie

# Refresh the OpenSSL packages shipped in the base image. Keep security updates
# floating so a newer Debian patch is picked up by future builds.
# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends --only-upgrade \
        libssl3t64 openssl openssl-provider-legacy \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/
RUN python -m pip install --no-cache-dir --requirement requirements.txt

# Copy project
COPY . /app/

# Expose port
EXPOSE 8000

# Run the production WSGI server. Database migrations are orchestrated by Compose.
CMD ["gunicorn", "datagrapho.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
