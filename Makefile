.DEFAULT_GOAL := help

#env := .env

ACCENT  := $(shell tput -Txterm setaf 2)
RESET := $(shell tput init)
API_SERVICE := api

#.EXPORT_ALL_VARIABLES:
#include ${env}
#export $(shell sed 's/=.*//' ${env})

fetch: ##  Скачать все репозитории -- требует интернета
	@git submodule init
	@git submodule update --remote
	@git submodule foreach "git checkout main"
	@git submodule foreach "git pull"

build: ##  Собрать
	@docker-compose build

build-clean: ##  Собрать без кэша, с удалением node_modules -- требует интернета
	@docker-compose down --remove-orphans
	@docker volume rm skaben_node_modules 2> /dev/null || true
	@docker-compose build --no-cache

start: ##  Запуск всех сервисов
	@mkdir -p logs/nginx tmp
	@docker-compose up --force-recreate --remove-orphans -d
	@docker-compose ps

sh.%: ##  Открыть shell в указанном сервисе [sh.[service]]
	docker-compose exec $* sh

exec: ##  Выполнение команды в указанном сервисе [service [command]]
	@docker-compose exec $$CMD

migrate: ##  Применить миграции
	@docker-compose exec ${API_SERVICE} python manage.py migrate

migrations: ##  Создать новую миграцию
	@docker-compose exec ${API_SERVICE} python manage.py makemigrations

load_initial: ##  Загрузить базовые данные
	@docker-compose exec ${API_SERVICE} python manage.py loaddata skaben_initial_data.json

dump_initial: ##  Сохранить текущее состояние БД в слепок
	@docker-compose exec ${API_SERVICE} python manage.py dumpdata alert core --indent 4 > skaben_dump.json

superuser: ##  Создать юзера
	@docker-compose exec ${API_SERVICE} python manage.py createsuperuser

stop:  ##  Остановка всех сервисов
	@docker-compose down --remove-orphans

restart.%: ##  Перезапустить сервис [restart.[service]]
	@docker-compose up --force-recreate --remove-orphans -d $*

info:  ##  Показать список сервисов
	@docker-compose ps -a

logs-backend:  ##  Показать логи воркеров и API
	@docker-compose logs -f scheduler worker_send worker_save worker_mqtt api

lint-backend:  ##  Проверка синтаксиса бэкенда
	@docker-compose run --rm api flake8 .

help:
	@echo "\nКоманды:\n"
	@grep -E '^[a-zA-Z.%_-]+:.*?## .*$$' $(firstword $(MAKEFILE_LIST)) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "%2s$(ACCENT)%-20s${RESET} %s\n", " ", $$1, $$2}'
	@echo ""
