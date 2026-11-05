"""Пользовательские исключения проекта."""


class ValutaTradeError(Exception):
    """Базовое исключение проекта."""


class CurrencyNotFoundError(ValutaTradeError):
    """Неизвестная валюта."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"Неизвестная валюта '{code}'")


class InsufficientFundsError(ValutaTradeError):
    """Недостаточно средств для операции."""

    def __init__(self, available: float, required: float, code: str) -> None:
        self.available = available
        self.required = required
        self.code = code
        super().__init__(
            f"Недостаточно средств: доступно {available:.4f} {code}, "
            f"требуется {required:.4f} {code}"
        )


class ApiRequestError(ValutaTradeError):
    """Сбой внешнего API (заглушка на будущее для Parser Service)."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")
