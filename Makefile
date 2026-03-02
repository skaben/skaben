.DEFAULT_GOAL := help

ACCENT := $(shell tput setaf 13)
RESET := $(shell tput sgr0)

IMAGE_NAME := skaben-api
IMAGE_TAG := latest
IMAGE := $(IMAGE_NAME):$(IMAGE_TAG)

DOCKERFILE := docker/Dockerfile
CONTEXT := .

API_SERVICE := api
WORKERS := scheduler worker_internal worker_send worker_save worker_mqtt

PYTHON_VERSION ?= 3.12
VENV_DIR := .venv

### -----------------------------
### Docker
### -----------------------------

.PHONY: image-build
image-build: ## Build base image without cache
	@docker build --no-cache -t $(IMAGE) -f $(DOCKERFILE) $(CONTEXT)

.PHONY: image-remove
image-remove: ## Remove local server image
	@docker rmi $(IMAGE) 2>/dev/null || true

.PHONY: build
build: image-build ## Build image + compose services
	@docker-compose down --remove-orphans
	@docker volume rm skaben_node_modules 2>/dev/null || true
	@docker-compose build --no-cache

.PHONY: start
start: stop ## Start all services
	@mkdir -p logs/nginx tmp
	@docker-compose up --force-recreate --remove-orphans -d
	@docker-compose ps

.PHONY: stop
stop: ## Stop all services
	@docker-compose down --remove-orphans

.PHONY: restart
restart.%: ## Restart service [restart.[service]]
	@docker-compose up --force-recreate --remove-orphans -d $*

.PHONY: restart-workers
restart-workers: ## Restart workers
	@docker-compose up --force-recreate --remove-orphans -d $(WORKERS)

.PHONY: sh
sh.%: ## Open shell in service
	@docker-compose exec $* sh

.PHONY: migrate
migrate:
	@docker-compose exec $(API_SERVICE) python manage.py migrate

.PHONY: migrations
migrations:
	@docker-compose exec $(API_SERVICE) python manage.py makemigrations

.PHONY: superuser
superuser:
	@docker-compose exec $(API_SERVICE) python manage.py createsuperuser

.PHONY: logs-backend
logs-backend:
	@docker-compose logs -f $(WORKERS) api

.PHONY: info
info:
	@docker-compose ps -a

### -----------------------------
### Data Management
### -----------------------------

.PHONY: load_initial
load_initial:  ## Load initial data from json into DB 
	@docker-compose exec ${API_SERVICE} python manage.py loaddata skaben_data.json

.PHONY: dump_initial
dump_initial:  ## Save current DB data into json (alert, core, peripheral_devices)
	@docker-compose exec ${API_SERVICE} python manage.py dumpdata alert core peripheral_devices --indent 4 > skaben_data.json

### -----------------------------
### UV / Python Environment
### -----------------------------

.PHONY: uv-install
uv-install: ## Install uv globally (user install)
	@curl -LsSf https://astral.sh/uv/install.sh | sh

.PHONY: venv
venv: ## Create virtualenv with specified Python version (PYTHON_VERSION=3.11)
	@uv venv --python $(PYTHON_VERSION) --clear $(VENV_DIR)

.PHONY: venv-remove
venv-remove: ## Remove virtualenv
	@rm -rf $(VENV_DIR)

.PHONY: install
install: ## Install project dependencies into venv (from lock)
	@uv sync

.PHONY: install-dev
install-dev: ## Install including dev dependencies
	@uv sync --extra dev

.PHONY: lock
lock: ## Generate or update uv.lock
	@uv lock

.PHONY: update
update: ## Update all dependencies and refresh lock
	@uv lock --upgrade

### -----------------------------
### Help
### -----------------------------

.PHONY: help
help:
	@echo "\nCommands:\n"
	@grep -E '^[a-zA-Z.%_-]+:.*?## .*$$' $(firstword $(MAKEFILE_LIST)) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(ACCENT)%-25s$(RESET) %s\n", $$1, $$2}'
	@echo ""