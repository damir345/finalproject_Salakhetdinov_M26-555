"""Настройка логирования: JSON-формат, ротация, уровень."""

import json
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader

LOG_FORMAT_JSON = True  # зафиксировано: JSON-формат для машинной обработки
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


class JsonFormatter(logging.Formatter):
    """Форматирует запись лога как JSON-строку."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Если в record есть extra-поля (action, user и т.п.) — добавим
        for key in (
            "action",
            "user",
            "user_id",
            "currency",
            "amount",
            "rate",
            "base",
            "result",
            "error_type",
            "error_message",
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: int = logging.INFO) -> None:
    """
    Настраивает корневой логгер: файл с ротацией + консоль.

    Ротация: 1 МБ на файл, 3 архивных копии, logs/actions.log.
    Формат: JSON (зафиксировано).
    Уровень: INFO (DEBUG для отладки).
    """
    settings = SettingsLoader()
    logs_dir: Path = settings.get("logs_dir")
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "actions.log"

    root = logging.getLogger()
    if root.handlers:
        return  # уже настроено

    root.setLevel(level)

    if LOG_FORMAT_JSON:
        formatter: logging.Formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt=DATE_FORMAT,
        )

    file_handler = RotatingFileHandler(
        log_file, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.WARNING)
    root.addHandler(console_handler)
