"""Иерархия валют: Currency (ABC), FiatCurrency, CryptoCurrency, реестр."""

from abc import ABC, abstractmethod

from valutatrade_hub.core.exceptions import CurrencyNotFoundError


class Currency(ABC):
    """Абстрактный базовый класс валюты."""

    def __init__(self, name: str, code: str) -> None:
        if not name or not name.strip():
            raise ValueError("Имя валюты не может быть пустым.")
        normalized = code.strip().upper()
        if not (2 <= len(normalized) <= 5) or " " in normalized:
            raise ValueError(
                f"Код валюты должен быть 2–5 символов без пробелов: {code!r}"
            )
        self.name = name.strip()
        self.code = normalized

    @abstractmethod
    def get_display_info(self) -> str:
        """Строковое представление для UI/логов."""
        raise NotImplementedError


class FiatCurrency(Currency):
    """Фиатная валюта."""

    def __init__(self, name: str, code: str, issuing_country: str) -> None:
        super().__init__(name, code)
        if not issuing_country or not issuing_country.strip():
            raise ValueError("Страна/зона эмиссии не может быть пустой.")
        self.issuing_country = issuing_country.strip()

    def get_display_info(self) -> str:
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    """Криптовалюта."""

    def __init__(
        self,
        name: str,
        code: str,
        algorithm: str,
        market_cap: float,
    ) -> None:
        super().__init__(name, code)
        if not algorithm or not algorithm.strip():
            raise ValueError("Алгоритм не может быть пустым.")
        if market_cap < 0:
            raise ValueError("Капитализация не может быть отрицательной.")
        self.algorithm = algorithm.strip()
        self.market_cap = float(market_cap)

    def get_display_info(self) -> str:
        mcap = f"{self.market_cap:.2e}".replace("e+", "e")
        return (
            f"[CRYPTO] {self.code} — {self.name} (Algo: {self.algorithm}, MCAP: {mcap})"
        )


# Реестр валют (можно расширять)
_CURRENCY_REGISTRY: dict[str, Currency] = {
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
    "EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "GBP": FiatCurrency("Pound Sterling", "GBP", "United Kingdom"),
    "RUB": FiatCurrency("Russian Ruble", "RUB", "Russia"),
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
    "ETH": CryptoCurrency("Ethereum", "ETH", "Ethash", 4.0e11),
}


def get_currency(code: str) -> Currency:
    """Возвращает валюту по коду. Бросает CurrencyNotFoundError, если нет."""
    normalized = code.strip().upper()
    if not normalized:
        raise CurrencyNotFoundError(code)
    try:
        return _CURRENCY_REGISTRY[normalized]
    except KeyError as exc:
        raise CurrencyNotFoundError(normalized) from exc


def list_currencies() -> list[Currency]:
    """Возвращает список всех валют в реестре (для CLI)."""
    return list(_CURRENCY_REGISTRY.values())
