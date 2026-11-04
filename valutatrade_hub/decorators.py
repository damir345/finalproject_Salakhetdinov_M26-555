"""Декораторы проекта."""

import functools
import logging
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def log_action(
    action: str,
    *,
    verbose: bool = False,
) -> Callable[[F], F]:
    """
    Логирует доменную операцию (BUY/SELL/REGISTER/LOGIN).

    Параметры:
        action: "BUY" | "SELL" | "REGISTER" | "LOGIN"
        verbose: добавлять контекст «было → стало» (old_balance/new_balance)

    Декоратор не глотает исключения: фиксирует их в лог и пробрасывает.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = logging.getLogger(func.__module__)
            extra_base: dict[str, Any] = {"action": action}

            # Пытаемся вытащить user/username из аргументов
            user = kwargs.get("user")
            if user is None and args:
                first = args[0]
                if hasattr(first, "user_id") and hasattr(first, "username"):
                    user = first
            if user is not None:
                extra_base["user"] = getattr(user, "username", None)
                extra_base["user_id"] = getattr(user, "user_id", None)
            elif "username" in kwargs:
                extra_base["user"] = kwargs["username"]
            elif args and isinstance(args[0], str):
                extra_base["user"] = args[0]

            extra_base["currency"] = None
            extra_base["amount"] = None
            if len(args) >= 3:
                extra_base["currency"] = args[1]
                extra_base["amount"] = args[2]
            if kwargs.get("currency_code") is not None:
                extra_base["currency"] = kwargs["currency_code"]
            if kwargs.get("amount") is not None:
                extra_base["amount"] = kwargs["amount"]

            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                extra = dict(extra_base)
                extra["result"] = "ERROR"
                extra["error_type"] = type(exc).__name__
                extra["error_message"] = str(exc)
                logger.error("%s %s", action, extra, extra=extra)
                raise

            extra = dict(extra_base)
            extra["result"] = "OK"
            if isinstance(result, dict):
                extra["rate"] = result.get("rate")
                extra["base"] = result.get("base")
                if verbose:
                    extra["old_balance"] = result.get("old_balance")
                    extra["new_balance"] = result.get("new_balance")
            logger.info("%s %s", action, extra, extra=extra)
            return result

        return wrapper  # type: ignore[return-value]

    return decorator
