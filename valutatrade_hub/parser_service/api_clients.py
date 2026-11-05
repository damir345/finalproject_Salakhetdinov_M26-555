"""Клиенты внешних API: CoinGecko (крипто) и ExchangeRate-API (фиат)."""

from abc import ABC, abstractmethod

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig


class BaseApiClient(ABC):
    """Базовый клиент: единый интерфейс fetch_rates() -> dict[str, float]."""

    def __init__(self, config: ParserConfig) -> None:
        self.config = config

    @abstractmethod
    def fetch_rates(self) -> dict[str, float]:
        """Возвращает {PAIR: rate}, например {"BTC_USD": 59337.21}."""
        raise NotImplementedError


class CoinGeckoClient(BaseApiClient):
    """Клиент CoinGecko: криптовалюты к USD."""

    def fetch_rates(self) -> dict[str, float]:
        ids = ",".join(
            self.config.CRYPTO_ID_MAP[c] for c in self.config.CRYPTO_CURRENCIES
        )
        params = {
            "ids": ids,
            "vs_currencies": self.config.BASE_CURRENCY.lower(),
        }
        try:
            response = requests.get(
                self.config.COINGECKO_URL,
                params=params,
                timeout=self.config.REQUEST_TIMEOUT,
            )
        except requests.exceptions.RequestException as exc:
            raise ApiRequestError(f"CoinGecko: {exc}") from exc

        if response.status_code != 200:
            raise ApiRequestError(f"CoinGecko: HTTP {response.status_code}")

        try:
            data = response.json()
        except ValueError as exc:
            raise ApiRequestError(f"CoinGecko: некорректный JSON: {exc}") from exc

        result: dict[str, float] = {}
        base = self.config.BASE_CURRENCY
        for code in self.config.CRYPTO_CURRENCIES:
            coin_id = self.config.CRYPTO_ID_MAP[code]
            if coin_id not in data:
                continue
            rate = data[coin_id].get(base.lower())
            if rate is None:
                continue
            result[f"{code}_{base}"] = float(rate)
        return result


class ExchangeRateApiClient(BaseApiClient):
    """Клиент ExchangeRate-API: фиатные валюты к базовой."""

    def fetch_rates(self) -> dict[str, float]:
        if not self.config.EXCHANGERATE_API_KEY:
            raise ApiRequestError("ExchangeRate-API: не задан EXCHANGERATE_API_KEY")
        url = (
            f"{self.config.EXCHANGERATE_API_URL}/"
            f"{self.config.EXCHANGERATE_API_KEY}/latest/"
            f"{self.config.BASE_CURRENCY}"
        )
        try:
            response = requests.get(url, timeout=self.config.REQUEST_TIMEOUT)
        except requests.exceptions.RequestException as exc:
            raise ApiRequestError(f"ExchangeRate-API: {exc}") from exc

        if response.status_code != 200:
            raise ApiRequestError(f"ExchangeRate-API: HTTP {response.status_code}")

        try:
            data = response.json()
        except ValueError as exc:
            raise ApiRequestError(
                f"ExchangeRate-API: некорректный JSON: {exc}"
            ) from exc

        if data.get("result") != "success":
            raise ApiRequestError(
                f"ExchangeRate-API: {data.get('error-type', 'unknown error')}"
            )

        rates = data.get("rates", {})
        base = self.config.BASE_CURRENCY
        result: dict[str, float] = {}
        for code in self.config.FIAT_CURRENCIES:
            if code not in rates:
                continue
            # ExchangeRate-API отдаёт BASE – CODE, а нам нужен CODE – BASE
            # (1 EUR = X USD). Поэтому берём обратное значение.
            result[f"{code}_{base}"] = 1.0 / float(rates[code])
        return result
