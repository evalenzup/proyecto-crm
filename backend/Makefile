.PHONY: test test-build test-watch lint

# Ejecutar suite completa de tests en Docker (Python 3.10)
test:
	docker compose -f docker-compose.test.yml run --rm test

# Forzar rebuild de la imagen antes de correr tests
test-build:
	docker compose -f docker-compose.test.yml build --no-cache
	docker compose -f docker-compose.test.yml run --rm test

# Solo correr un módulo específico. Ej: make test-module MODULE=test_notificaciones
test-module:
	docker compose -f docker-compose.test.yml run --rm test \
		python -m pytest tests/$(MODULE).py -v --tb=short

# Linter rápido
lint:
	python -m ruff check app/ tests/ || true
