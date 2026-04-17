FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc libpq-dev netcat-openbsd && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

# CMD [ "sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000" ]

CMD ["sh", "/app/entrypoint.sh"]