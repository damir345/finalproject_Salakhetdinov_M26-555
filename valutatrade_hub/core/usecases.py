"""Бизнес-логика: регистрация, логин, портфель, buy/sell."""

from valutatrade_hub.core.exceptions import InsufficientFundsError
from valutatrade_hub.core.models import Portfolio, User, Wallet
from valutatrade_hub.core.utils import (
    PORTFOLIOS_FILE,
    USERS_FILE,
    get_rate,
    read_json,
    write_json,
)
from valutatrade_hub.infra.settings import SettingsLoader


def _base_currency() -> str:
    """Базовая валюта из настроек (по умолчанию USD)."""
    return SettingsLoader().get("default_base_currency", "USD")


# --- Пользователи ---


def _load_users() -> list[dict]:
    return read_json(USERS_FILE, default=[])


def _save_users(users: list[dict]) -> None:
    write_json(USERS_FILE, users)


def register(username: str, password: str) -> User:
    """Регистрирует нового пользователя и сохраняет в users.json."""
    users = _load_users()
    if any(u["username"] == username for u in users):
        raise ValueError(f"Имя пользователя {username!r} уже занято.")

    next_id = max((u["user_id"] for u in users), default=0) + 1
    user = User(user_id=next_id, username=username, password=password)
    users.append(user.to_dict())
    _save_users(users)

    # Пустой портфель (без кошельков)
    portfolio = Portfolio(user=user)
    portfolios = _load_portfolios()
    portfolios.append(portfolio.to_dict())
    _save_portfolios(portfolios)

    return user


def login(username: str, password: str) -> User:
    """Проверяет логин/пароль и возвращает User."""
    users = _load_users()
    for data in users:
        if data["username"] == username:
            user = User.from_dict(data)
            if user.verify_password(password):
                return user
            raise ValueError("Неверный пароль")
    raise ValueError(f"Пользователь {username!r} не найден")


# --- Портфели ---


def _load_portfolios() -> list[dict]:
    return read_json(PORTFOLIOS_FILE, default=[])


def _save_portfolios(portfolios: list[dict]) -> None:
    write_json(PORTFOLIOS_FILE, portfolios)


def get_portfolio(user: User) -> Portfolio:
    """Возвращает портфель пользователя, создавая его при необходимости."""
    portfolios = _load_portfolios()
    for data in portfolios:
        if data["user_id"] == user.user_id:
            return Portfolio.from_dict(data, user=user)

    portfolio = Portfolio(user=user)
    portfolio.add_currency(_base_currency())
    portfolios.append(portfolio.to_dict())
    _save_portfolios(portfolios)
    return portfolio


def save_portfolio(portfolio: Portfolio) -> None:
    """Сохраняет портфель (обновляет запись по user_id)."""
    portfolios = _load_portfolios()
    data = portfolio.to_dict()
    for i, existing in enumerate(portfolios):
        if existing["user_id"] == portfolio.user_id:
            portfolios[i] = data
            break
    else:
        portfolios.append(data)
    _save_portfolios(portfolios)


# --- Курсы ---


def get_rate_info(from_currency: str, to_currency: str | None = None) -> dict:
    """Обёртка над utils.get_rate (для CLI)."""
    frm = from_currency.strip().upper()
    to = (to_currency or _base_currency()).strip().upper()
    try:
        return get_rate(frm, to)
    except ValueError as exc:
        raise ValueError(
            f"Курс {frm}→{to} недоступен. Повторите попытку позже."
        ) from exc


# --- Buy / Sell ---


def buy(user: User, currency_code: str, amount: float) -> dict:
    """
    Покупает amount единиц currency_code за USD.

    Возвращает словарь с деталями операции, включая old_balance/new_balance.
    """
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")
    code = currency_code.strip().upper()
    if not code:
        raise ValueError("Код валюты не может быть пустым")
    if code == "USD":
        raise ValueError("Нельзя покупать USD за USD")

    base = _base_currency()
    portfolio = get_portfolio(user)
    try:
        rate_info = get_rate(code, base)
    except ValueError as exc:
        raise ValueError(f"Не удалось получить курс для {code}→{base}") from exc

    rate = rate_info["rate"]
    cost = amount * rate

    base_wallet = portfolio.add_currency(base)
    if base_wallet.balance < cost:
        raise InsufficientFundsError(base_wallet.balance, cost, base)

    target = portfolio.add_currency(code)
    old_balance = target.balance
    base_wallet.withdraw(cost)
    target.deposit(amount)
    save_portfolio(portfolio)

    return {
        "operation": "buy",
        "currency_code": code,
        "amount": amount,
        "rate": rate,
        "cost_usd": cost,
        "old_balance": old_balance,
        "new_balance": target.balance,
    }


def sell(user: User, currency_code: str, amount: float) -> dict:
    """
    Продаёт amount единиц currency_code за USD.

    Возвращает словарь с деталями операции, включая old_balance/new_balance.
    """
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")
    code = currency_code.strip().upper()
    if not code:
        raise ValueError("Код валюты не может быть пустым")
    if code == "USD":
        raise ValueError("Нельзя продавать USD за USD")

    base = _base_currency()
    portfolio = get_portfolio(user)
    if code not in portfolio.wallets:
        raise ValueError(
            f"У вас нет кошелька {code!r}. "
            f"Добавьте валюту: она создаётся автоматически при первой покупке."
        )

    try:
        rate_info = get_rate(code, base)
    except ValueError as exc:
        raise ValueError(f"Не удалось получить курс для {code}→{base}") from exc

    rate = rate_info["rate"]
    proceeds = amount * rate

    target = portfolio.get_wallet(code)
    old_balance = target.balance
    base_wallet = portfolio.add_currency(base)
    target.withdraw(amount)
    base_wallet.deposit(proceeds)
    save_portfolio(portfolio)

    return {
        "operation": "sell",
        "currency_code": code,
        "amount": amount,
        "rate": rate,
        "proceeds_usd": proceeds,
        "old_balance": old_balance,
        "new_balance": target.balance,
    }


def get_wallet_value_in(wallet: Wallet, base_currency: str) -> float:
    """Стоимость одного кошелька в base_currency по текущим курсам."""
    base = base_currency.strip().upper()
    if base == wallet.currency_code:
        return wallet.balance
    info = get_rate(wallet.currency_code, base)
    return wallet.balance * info["rate"]
