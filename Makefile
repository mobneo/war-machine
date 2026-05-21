.PHONY: run install

run:
	poetry run python -m bot.main

install:
	poetry install
