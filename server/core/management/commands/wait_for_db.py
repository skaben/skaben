import time

from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError


class Command(BaseCommand):
    """Django command to pause execution until database is available"""

    def handle(self, *args, **options):
        db_conn = None
        try:
            db_conn = connections["default"]
        except OperationalError:
            self.stdout.write("Database unavailable, waiting 1 second...")
            time.sleep(1)
        if not db_conn:
            return self.handle(*args, **options)
        else:
            self.stdout.write(self.style.SUCCESS("Database is available!"))
