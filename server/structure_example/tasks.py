from celery_app import celery_app
from server_core.server.structure_example.service import ExampleMathService


@celery_app.task(name="recurrent entry processing")
def recurrent_entry_processing(x: int) -> None:
    service = ExampleMathService()
    service.process_entry(x)
