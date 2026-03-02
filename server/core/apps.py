from core.transport.config import get_mq_config
from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "core"
    verbose_name = "00: Базовые настройки системы"

    def ready(self):
        """Do something on app start"""
        get_mq_config()
