from alert.models import AlertState
from django.conf import settings
from core.transport.events import SkabenEventContext, ContextEventLevels
from event_contexts.exceptions import StopContextError
from peripheral_behavior.models import AccessCode, SkabenUser
from peripheral_devices.models.lock import LockDevice as Lock


class LockEventContext(SkabenEventContext):
    """Контекст обработки событий от лазерных дверей.

    Создает сообщения об открытии\закрытии\блокировке.
    В maintenance-режиме работы среды (white) - позволяет добавлять неизвестные системе карточки.
    """

    @staticmethod
    def create_lock_device(mac_addr: str) -> str:
        """Создает новое устройство типа 'Лазерная дверь'."""
        if not AlertState.objects.is_management_state():
            return "Устройство не зарегистрировано и должно быть создано в режиме управления средой (white)."

        new_lock = Lock.objects.create(mac_addr=mac_addr)
        new_lock.save()
        return f"Создано новое устройство типа `Замок` с адресом {mac_addr}"

    @staticmethod
    def create_new_access_record(lock: str, access_code: str) -> str:
        if len(str(access_code)) != settings.ACCESS_CODE_CARD_LEN:
            raise StopContextError(f"Код `{access_code}` полученный из `{lock}` не является картой и его нет в базе")
        if not AlertState.objects.is_management_state():
            raise StopContextError(
                f"Первая попытка авторизации `{access_code}` в `{lock}` -> "
                "не может быть добавлен (white статус не активен)."
            )

        user, created = SkabenUser.objects.get_or_create(
            name="skaben_default", description="системный пользователь по умолчанию"
        )
        instance = AccessCode.objects.create(code=access_code, user=user)
        return f"Первая попытка авторизации {instance.code} в {lock} -> {instance.code} добавлен в БД."

    def apply(self, event_headers: dict, event_data: dict):
        """Применяет правила открытия замка ключ-картой или кодом."""
        source = event_headers.get("device_uid", "")
        access_code = event_data.get("access_code", "")

        try:
            lock = Lock.objects.get(mac_addr=source)
            access = AccessCode.objects.get(code=access_code)
            success = event_data.get("success")
            result = "доступ разрешен" if success else "доступ запрещен"
            self.add_log_event(f"{lock.id} : {result} для {access}")
        except AccessCode.DoesNotExist:
            message = self.create_new_access_record(lock=source, access_code=access_code)
            self.add_log_event(message, level=ContextEventLevels.LOG)
        except Lock.DoesNotExist:
            message = self.create_lock_device(mac_addr=source)
            self.add_log_event(message, level=ContextEventLevels.LOG)
