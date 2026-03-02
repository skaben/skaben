from django.core.management.base import BaseCommand
from core.scheduler.service import get_service


class Command(BaseCommand):
    """Django command to start the scheduler for RabbitMQ"""

    help = "Starts the scheduler for recurrent service."

    def handle(self, *args: str, **options: str) -> None:
        """
        Handles the execution of the command.

        Args:
            *args: Positional arguments passed to the command.
            **options: Keyword arguments passed to the command.
        """
        try:
            self.stdout.write(self.style.SUCCESS("Scheduler starting..."))
            service = get_service()
            service.start()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("Scheduler stopped manually. Exiting..."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Scheduler encountered an error: {e}"))
