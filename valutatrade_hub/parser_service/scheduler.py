"""Планировщик периодического обновления курсов."""

import logging
import time

from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import ParserStorage
from valutatrade_hub.parser_service.updater import RatesUpdater

logger = logging.getLogger(__name__)


def run_scheduler(interval_seconds: int = 300) -> None:
    """
    Бесконечный цикл: обновляет курсы каждые interval_seconds.

    Прерывается по Ctrl+C.
    """
    config = ParserConfig()
    storage = ParserStorage(config)
    updater = RatesUpdater(config, storage)
    logger.info("Scheduler started, interval=%ds", interval_seconds)
    try:
        while True:
            try:
                result = updater.run_update()
                logger.info(
                    "Scheduled update: updated=%d, errors=%d",
                    result["updated"],
                    len(result["errors"]),
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Scheduler update failed: %s", exc)
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
