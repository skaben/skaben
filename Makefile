.DEFAULT_GOAL := help

env := .env

ACCENT  := $(shell tput -Txterm setaf 2)
RESET := $(shell tput init)

.EXPORT_ALL_VARIABLES:
include ${env}
export $(shell sed 's/=.*//' ${env})

fetch: ##  Скачать все репозитории
	@git submodule init
	@git submodule update --remote
	@git submodule foreach "git checkout main"

build: ##  Собрать без кэша
	@docker-compose build --no-cache

rebuild: ##  Собрать без кэша, с удалением node_modules
	@docker-compose down front -v
	@docker-compose build --no-cache

start: ##  Запуск всех сервисов
	@mkdir -p logs/nginx tmp
	@docker-compose up --force-recreate -d
	@docker-compose ps

sh.%: ##  Открыть shell в указанном сервисе [sh.[service]]
	docker-compose exec $* sh

exec: ##  Выполнение команды в указанном сервисе [service [command]]
	@docker-compose exec $$CMD

migrate: ##  Применить миграции
	@docker-compose exec back python manage.py migrate

migrations: ##  Создать новую миграцию
	@docker-compose exec back python manage.py makemigrations

stop:  ##  Остановка всех сервисов
	@docker-compose down

restart.%: ##  Перезапустить сервис [restart.[service]]
	@docker-compose up --force-recreate -d $*

info:  ##  Показать список сервисов
	@docker-compose ps -a

help:
	@echo "\nКоманды:\n"
	@grep -E '^[a-zA-Z.%_-]+:.*?## .*$$' $(firstword $(MAKEFILE_LIST)) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "%2s$(ACCENT)%-20s${RESET} %s\n", " ", $$1, $$2}'
	@echo ""
