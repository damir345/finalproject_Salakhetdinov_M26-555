"""Конфигурация Parser Service: API-ключи, эндпоинты, списки валют."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass
class ParserConfig:
    """Настройки Parser Service. Ключ — из переменной окружения."""

    EXCHANGERATE_API_KEY: str = field(
        default_factory=lambda: os.getenv("EXCHANGERATE_API_KEY", "")
    )

    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    BASE_CURRENCY: str = "USD"
    FIAT_CURRENCIES: tuple[str, ...] = ("EUR", "GBP", "RUB")
    CRYPTO_CURRENCIES: tuple[str, ...] = ("BTC", "ETH", "SOL")
    CRYPTO_ID_MAP: dict[str, str] = field(
        default_factory=lambda: {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
        }
    )

    RATES_FILE_PATH: Path = field(
        default_factory=lambda: SettingsLoader().get("rates_file")
    )
    HISTORY_FILE_PATH: Path = field(
        default_factory=lambda: _project_root() / "data" / "exchange_rates.json"
    )

    REQUEST_TIMEOUT: int = 10
    SOURCE_COINGECKO: str = "CoinGecko"
    SOURCE_EXCHANGERATE: str = "ExchangeRate-API"