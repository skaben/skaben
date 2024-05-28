.DEFAULT_GOAL := help

#env := .env

ACCENT  := $(shell tput -Txterm setaf 2)
RESET := $(shell tput init)
API_SERVICE := api
WORKERS := scheduler worker_internal worker_send worker_save worker_mqtt

#.EXPORT_ALL_VARIABLES:
#include ${env}
#export $(shell sed 's/=.*//' ${env})

.PHONY: fetch
fetch: ##  Скачать все репозитории -- требует интернета
	@git pull
	@git submodule init
	@git submodule update --remote
	@git submodule foreach "git checkout main"
	@git submodule foreach "git pull"

.PHONY: build
build: ##  Собрать
	@docker-compose build

.PHONY: build-clean
build-clean: ##  Собрать без кэша, с удалением node_modules -- требует интернета
	@docker-compose down --remove-orphans
	@docker volume rm skaben_node_modules 2> /dev/null || true
	@docker-compose build --no-cache

.PHONY: start
start: stop ##  Запуск всех сервисов
	@mkdir -p logs/nginx tmp
	@docker-compose up --force-recreate --remove-orphans -d
	@docker-compose ps

.PHONY: sh
sh.%: ##  Открыть shell в указанном сервисе [sh.[service]]
	docker-compose exec $* sh

.PHONY: exec
exec: ##  Выполнение команды в указанном сервисе [service [command]]
	@docker-compose exec $$CMD

.PHONY: migrate
migrate: ##  Применить миграции
	@docker-compose exec ${API_SERVICE} python manage.py migrate

.PHONY: migrations
migrations: ##  Создать новую миграцию
	@docker-compose exec ${API_SERVICE} python manage.py makemigrations

.PHONY: load_initial
load_initial: ##  Загрузить базовые данные
	@docker-compose exec ${API_SERVICE} python manage.py loaddata skaben_data.json

.PHONY: dump_initial
dump_initial: ##  Сохранить текущее состояние БД в слепок
	@docker-compose exec ${API_SERVICE} python manage.py dumpdata alert core --indent 4 > skaben_data.json

.PHONY: superuser
superuser: ##  Создать юзера
	@docker-compose exec ${API_SERVICE} python manage.py createsuperuser

.PHONY: stop
stop:  ##  Остановка всех сервисов
	@docker-compose down --remove-orphans

.PHONY: restart
restart.%: ##  Перезапустить сервис [restart.[service]]
	@docker-compose up --force-recreate --remove-orphans -d $*

.PHONY: restart-workers
restart-workers: ##  Перезапустить воркеров
	@docker-compose up --force-recreate --remove-orphans -d ${WORKERS}

.PHONY: info
info:  ##  Показать список сервисов
	@docker-compose ps -a

.PHONY: logs-backend
logs-backend:  ##  Показать логи воркеров и API
	@docker-compose logs -f ${WORKERS} api

.PHONY: help
help:
	@echo "\nКоманды:\n"
	@grep -E '^[a-zA-Z.%_-]+:.*?## .*$$' $(firstword $(MAKEFILE_LIST)) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "%2s$(ACCENT)%-20s${RESET} %s\n", " ", $$1, $$2}'
	@echo ""
