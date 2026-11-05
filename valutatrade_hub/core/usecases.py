"""Бизнес-логика: регистрация, логин, портфель, buy/sell."""

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import InsufficientFundsError
from valutatrade_hub.core.models import Portfolio, User, Wallet
from valutatrade_hub.core.utils import get_rate
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader

_db = DatabaseManager()


def _base_currency() -> str:
    """Базовая валюта из настроек (по умолчанию USD)."""
    return SettingsLoader().get("default_base_currency", "USD")


# --- Пользователи ---


def _load_users() -> list[dict]:
    return _db.load_users()


def _save_users(users: list[dict]) -> None:
    _db.save_users(users)


def _get_user_by_id(user_id: int) -> User:
    """Загружает пользователя по user_id из users.json."""
    for data in _load_users():
        if data["user_id"] == user_id:
            return User.from_dict(data)
    raise ValueError(f"Пользователь с id={user_id} не найден")


@log_action(action="REGISTER")
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


@log_action(action="LOGIN")
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
    return _db.load_portfolios()


def _save_portfolios(portfolios: list[dict]) -> None:
    _db.save_portfolios(portfolios)


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
    get_currency(frm)  # CurrencyNotFoundError, если неизвестен
    get_currency(to)
    return get_rate(frm, to)


# --- Buy / Sell ---


@log_action(action="BUY", verbose=True)
def buy(user_id: int, currency_code: str, amount: float) -> dict:
    """
    Покупает amount единиц currency_code за базовую валюту.

    Возвращает словарь с деталями операции, включая old_balance/new_balance.
    """
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")
    code = currency_code.strip().upper()
    if not code:
        raise ValueError("Код валюты не может быть пустым")
    get_currency(code)  # CurrencyNotFoundError, если неизвестен
    base = _base_currency()
    if code == base:
        raise ValueError(f"Нельзя покупать {base} за {base}")

    user = _get_user_by_id(user_id)
    portfolio = get_portfolio(user)
    rate_info = get_rate(code, base)
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
        "user": user.username,
        "user_id": user_id,
        "currency_code": code,
        "amount": amount,
        "rate": rate,
        "base": base,
        "cost_usd": cost,
        "old_balance": old_balance,
        "new_balance": target.balance,
    }


@log_action(action="SELL", verbose=True)
def sell(user_id: int, currency_code: str, amount: float) -> dict:
    """
    Продаёт amount единиц currency_code за базовую валюту.

    Возвращает словарь с деталями операции, включая old_balance/new_balance.
    """
    if amount <= 0:
        raise ValueError("'amount' должен быть положительным числом")
    code = currency_code.strip().upper()
    if not code:
        raise ValueError("Код валюты не может быть пустым")
    get_currency(code)  # CurrencyNotFoundError, если неизвестен
    base = _base_currency()
    if code == base:
        raise ValueError(f"Нельзя продавать {base} за {base}")

    user = _get_user_by_id(user_id)
    portfolio = get_portfolio(user)
    if code not in portfolio.wallets:
        raise ValueError(
            f"У вас нет кошелька {code!r}. "
            f"Добавьте валюту: она создаётся автоматически при первой покупке."
        )

    rate_info = get_rate(code, base)
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
        "user": user.username,
        "user_id": user_id,
        "currency_code": code,
        "amount": amount,
        "rate": rate,
        "base": base,
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
