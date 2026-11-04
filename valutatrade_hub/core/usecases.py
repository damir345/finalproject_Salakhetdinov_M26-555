"""Бизнес-логика: регистрация, логин, портфель, buy/sell."""

from valutatrade_hub.core.models import Portfolio, User, Wallet
from valutatrade_hub.core.utils import (
    PORTFOLIOS_FILE,
    USERS_FILE,
    get_rate,
    read_json,
    write_json,
)

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
    portfolio.add_currency("USD")
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


def get_rate_info(from_currency: str, to_currency: str = "USD") -> dict:
    """Обёртка над utils.get_rate (для CLI)."""
    return get_rate(from_currency, to_currency)


# --- Buy / Sell ---


def buy(user: User, currency_code: str, amount: float) -> dict:
    if amount <= 0:
        raise ValueError("Сумма должна быть положительным числом.")
    code = currency_code.strip().upper()
    if code == "USD":
        raise ValueError("Нельзя покупать USD за USD.")

    portfolio = get_portfolio(user)
    rate_info = get_rate(code, "USD")
    rate = rate_info["rate"]
    cost = amount * rate

    usd_wallet = portfolio.add_currency("USD")
    if usd_wallet.balance < cost:
        raise ValueError(
            f"Недостаточно USD: нужно {cost:.2f}, на балансе {usd_wallet.balance:.2f}."
        )

    target = portfolio.add_currency(code)
    usd_wallet.withdraw(cost)
    target.deposit(amount)
    save_portfolio(portfolio)

    return {
        "operation": "buy",
        "currency_code": code,
        "amount": amount,
        "rate": rate,
        "cost_usd": cost,
    }


def sell(user: User, currency_code: str, amount: float) -> dict:
    if amount <= 0:
        raise ValueError("Сумма должна быть положительным числом.")
    code = currency_code.strip().upper()
    if code == "USD":
        raise ValueError("Нельзя продавать USD за USD.")

    portfolio = get_portfolio(user)
    rate_info = get_rate(code, "USD")
    rate = rate_info["rate"]
    proceeds = amount * rate

    target = portfolio.get_wallet(code)
    if target.balance < amount:
        raise ValueError(
            f"Недостаточно {code}: нужно {amount}, на балансе {target.balance}."
        )

    usd_wallet = portfolio.add_currency("USD")
    target.withdraw(amount)
    usd_wallet.deposit(proceeds)
    save_portfolio(portfolio)

    return {
        "operation": "sell",
        "currency_code": code,
        "amount": amount,
        "rate": rate,
        "proceeds_usd": proceeds,
    }


def get_wallet_value_in(wallet: Wallet, base_currency: str) -> float:
    """Стоимость одного кошелька в base_currency по текущим курсам."""
    base = base_currency.strip().upper()
    if base == wallet.currency_code:
        return wallet.balance
    info = get_rate(wallet.currency_code, base)
    return wallet.balance * info["rate"]
