"""RatesUpdater: координация клиентов и сохранение курсов."""

import logging

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.api_clients import (
    BaseApiClient,
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import ParserStorage

logger = logging.getLogger(__name__)


class RatesUpdater:
    """Опрашивает клиентов, объединяет курсы, пишет в кеш и историю."""

    def __init__(
        self,
        config: ParserConfig,
        storage: ParserStorage,
        clients: list[BaseApiClient] | None = None,
    ) -> None:
        self.config = config
        self.storage = storage
        if clients is None:
            clients = [
                CoinGeckoClient(config),
                ExchangeRateApiClient(config),
            ]
        self.clients = clients

    def run_update(self, source: str | None = None) -> dict:
        """
        Запускает обновление.

        source: None — все клиенты; "coingecko" / "exchangerate" — только один.
        Возвращает {"updated": int, "errors": list[str], "last_refresh": str|None}.
        """
        logger.info("Starting rates update...")
        all_rates: dict[str, float] = {}
        errors: list[str] = []

        for client in self.clients:
            name = self._client_name(client)
            if source and source != name:
                continue
            logger.info("Fetching from %s...", name)
            try:
                rates = client.fetch_rates()
            except ApiRequestError as exc:
                logger.error("Failed to fetch from %s: %s", name, exc)
                errors.append(f"{name}: {exc}")
                continue

            logger.info("%s OK (%d rates)", name, len(rates))
            source_label = (
                self.config.SOURCE_COINGECKO
                if name == "coingecko"
                else self.config.SOURCE_EXCHANGERATE
            )
            all_rates.update(rates)

            entries = [
                self.storage.make_history_entry(
                    pair, rate, source_label, {"status_code": 200}
                )
                for pair, rate in rates.items()
            ]
            self.storage.append_history(entries)

        if all_rates:
            cache = self.storage.update_rates_cache(all_rates, "ParserService")
            last_refresh = cache.get("last_refresh")
        else:
            last_refresh = None

        logger.info("Update done. Rates: %d, errors: %d", len(all_rates), len(errors))
        return {
            "updated": len(all_rates),
            "errors": errors,
            "last_refresh": last_refresh,
        }

    @staticmethod
    def _client_name(client: BaseApiClient) -> str:
        if isinstance(client, CoinGeckoClient):
            return "coingecko"
        if isinstance(client, ExchangeRateApiClient):
            return "exchangerate"
        return client.__class__.__name__.lower()
