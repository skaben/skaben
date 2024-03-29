# Основной репозиторий проекта SKABEN

### запуск сборки TL;DR

1. спуллить себе
2. сказать `make fetch && make build`
3. положить `.env` в `skaben/server_core`
4. сказать `make start`
5. не забыть создать суперюзера и миграции для Джанго

### запуск сборки чуть подробнее

- фронт запускается на `127.0.0.1`
- админка на `127.0.0.1/admin`
- веб-интерфейс rabbitmq - `127.0.0.1:15672`

##### дополнительно можно поднять pgadmin:
- `cd docker_build/pgadmin && docker-compose up`
- он стартует на `127.0.0.1:5050` и требует минимальной настройки в веб-интерфейсе, чтобы подключиться к БД

Все операции со сборкой производятся через `make`, ниже приведен список команд. Запуск без аргументов показывает `help`.

### требует выхода в интернет
`fetch:` Скачать все репозитории\
`build:` Собрать без кэша\
`rebuild:` Собрать без кэша, с удалением node_modules\

### не требует выхода в интернет
`start:` Запуск всех сервисов\
`sh.%:` Открыть shell в указанном сервисе [sh.[service]]\
`exec:` Выполнение команды в указанном сервисе [service [command]]
`migrate` Применить миграции\
`migrations` Создать новую миграцию\
`superuser` Создать суперюзера в админке Django\
`stop` Остановка всех сервисов\
`restart.%:` Перезапустить сервис [restart.[service]]\
`info` Показать список сервисов

