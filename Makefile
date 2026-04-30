.PHONY: help install migrations migrate createsuperuser runserver test clean docker-up docker-down docker-logs

help:
	@echo "DataGrapho - Available Commands"
	@echo "================================"
	@echo "make install          - Install dependencies"
	@echo "make migrations       - Create migrations"
	@echo "make migrate          - Apply migrations"
	@echo "make createsuperuser  - Create superuser"
	@echo "make runserver        - Run development server"
	@echo "make test             - Run tests"
	@echo "make clean            - Clean cache and pycache"
	@echo "make docker-up        - Start Docker containers"
	@echo "make docker-down      - Stop Docker containers"
	@echo "make docker-logs      - Show Docker logs"
	@echo "make format           - Format code with black"
	@echo "make lint             - Lint code with pylint"

install:
	pip install -r requirements.txt

migrations:
	python manage.py makemigrations

migrate:
	python manage.py migrate

createsuperuser:
	python manage.py createsuperuser

runserver:
	python manage.py runserver

test:
	python manage.py test

test-coverage:
	coverage run --source='.' manage.py test
	coverage report

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	find . -type d -name '.pytest_cache' -exec rm -rf {} +
	find . -type f -name '.coverage' -delete

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-build:
	docker-compose build

format:
	black --line-length 100 src/accounts/ src/catalogo_depara/ src/depara/ src/datagrapho/ tests/ manage.py

lint:
	pylint --load-plugins pylint_django src/accounts/ src/catalogo_depara/ src/depara/ src/datagrapho/ tests/

db-shell:
	python manage.py dbshell

shell:
	python manage.py shell

static:
	python manage.py collectstatic --noinput

freeze:
	pip freeze > requirements-lock.txt
