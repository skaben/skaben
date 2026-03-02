import logging
import time
import json
from typing import List, Optional

from django.conf import settings

from core.helpers import get_server_timestamp
from core.redis_pool import get_redis_client
from redis.exceptions import ConnectionError, BusyLoadingError
from core.scheduler.tasks import AlertTask, PingerTask, SkabenTask, UpdateDevicesOnStartTask
from core.scheduler.types import SkabenTaskType


class SchedulerService:
    """Сервис планировщика задач."""

    running: bool
    polling_interval: int
    redis_key: str = "scheduler"
    task_dispatcher = {
        SkabenTaskType.PINGER: PingerTask,
        SkabenTaskType.ALERT: AlertTask,
    }
    tasks_initial: List[SkabenTask]

    def __init__(self, tasks: List[SkabenTask], polling_interval: int = 1):
        self.redis = get_redis_client()
        self.polling_interval = polling_interval
        self.redis.delete(self.redis_key)
        self.tasks_initial = tasks

    def start(self) -> None:
        self.running = True
        self.run()

    def stop(self) -> None:
        self.running = False

    def run(self):
        for task in self.tasks_initial:
            logging.debug("Initial run: task %s", task.name)
            timeout = task.run()
            self.put(task, timeout)

        while self.running:
            for task_name in self.task_dispatcher.keys():
                try:
                    task = self.get(task_name)
                    if not task:
                        continue
                    timeout = task.run()
                    logging.debug("Task %s next run in %s seconds", task_name, timeout)
                    if task.requeue and timeout > 0:
                        self.put(task, timeout)
                except (ConnectionError, BusyLoadingError):
                    logging.exception("Redis connection unavailable")
                    continue
            time.sleep(self.polling_interval)

    def get(self, name: str) -> Optional[SkabenTask]:
        task_data = self.redis.hget(self.redis_key, name)
        if not task_data:
            return

        task_data = json.loads(task_data.decode("utf-8"))
        if task_data.get("run_after", 0) > get_server_timestamp():
            return

        task_class = self.task_dispatcher.get(name)
        if not task_class:
            return

        return task_class(
            timeout=task_data.get("timeout", 0),
            requeue=task_data.get("requeue", 0) != 0,
        )

    def put(self, task: SkabenTask, timeout: int) -> None:
        if not task:
            logging.error("Missing task to put")
            return
        requeue = 1 if task.requeue else 0
        task_data = {
            "timeout": timeout,
            "run_after": get_server_timestamp() + timeout,
            "requeue": requeue,
        }
        self.redis.hset(self.redis_key, task.name, json.dumps(task_data))


def get_service() -> SchedulerService:
    """Создает экземпляр планировщика для регулярных задач."""
    pinger = PingerTask(timeout=settings.RESPONSE_TIMEOUT.get("ping", 10), requeue=True)
    alert_changer = AlertTask(timeout=settings.SCHEDULER_TASK_TIMEOUT, requeue=True)
    update_on_start = UpdateDevicesOnStartTask()
    service = SchedulerService(tasks=[pinger, alert_changer, update_on_start])
    return service
