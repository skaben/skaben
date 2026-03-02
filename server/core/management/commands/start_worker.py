from core.transport.config import get_mq_config
from core.worker_queue_handlers import AskHandler, BaseHandler, ClientUpdateHandler, InternalHandler, StateUpdateHandler
from django.core.management.base import BaseCommand

config = get_mq_config()

HANDLERS = {"mqtt": AskHandler, "internal": InternalHandler, "state": StateUpdateHandler, "client": ClientUpdateHandler}

_handlers_help = f'[{"|".join(HANDLERS.keys())}]'


class Command(BaseCommand):
    """Django command to start workers for RabbitMQ"""

    help = f"python manage.py run_worker {_handlers_help}"

    def add_arguments(self, parser):
        parser.add_argument("handler", type=str, help=f"choose one from {_handlers_help}")

    @staticmethod
    def bind_handler(handler: BaseHandler) -> BaseHandler:
        """Binds handler to queue."""
        return handler(config, config.queues.get(handler.incoming_mark))

    def handle(self, *args, **options):
        config.init_exchanges_and_queues()
        handler_type = options.get("handler", "")
        handler = HANDLERS.get(handler_type)
        if not handler_type or not handler:
            raise AttributeError(f"handler with name {handler_type} not configured")
        bound = self.bind_handler(handler)
        self.stdout.write(f"worker starting with handler {bound}")
        bound.start()
