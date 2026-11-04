"""Пользовательские исключения проекта."""


class ValutaTradeError(Exception):
    """Базовое исключение проекта."""


class CurrencyNotFoundError(ValutaTradeError):
    """Валюта с указанным кодом не найдена."""


class InsufficientFundsError(ValutaTradeError):
    """Недостаточно средств для операции."""


class WalletNotFoundError(ValutaTradeError):
    """Кошелёк с указанной валютой не найден."""


class ValidationError(ValutaTradeError):
    """Ошибка валидации входных данных."""
