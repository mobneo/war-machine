.PHONY: run install docker-build docker-up docker-down docker-logs

run:
	poetry run python -m bot.main

install:
	poetry install

docker-start:
	docker compose up -d --build

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-rebuild:
	docker compose build --no-cache && docker-compose up -d

docker-clean:
	docker compose down -v
