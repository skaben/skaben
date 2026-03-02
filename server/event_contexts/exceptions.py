class StopContextError(Exception):
    """Контекст обработки сообщения остановлен с ошибкой."""

    def __init__(self, error: str, *args, **kwargs):
        super().__init__(self, args, kwargs)
        self.error = error
