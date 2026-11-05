"""CLI: единственная точка входа для пользовательских команд."""

import shlex

from valutatrade_hub.core import usecases
from valutatrade_hub.core.currencies import list_currencies
from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    InsufficientFundsError,
)
from valutatrade_hub.core.models import User
from valutatrade_hub.core.utils import STUB_RATES_USD
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import ParserStorage
from valutatrade_hub.parser_service.updater import RatesUpdater


def _parse_flags(args: list[str], required: set[str]) -> dict[str, str]:
    """
    Парсит аргументы вида --flag value.

    Возвращает словарь {flag: value} без ведущих '--'.
    Бросает ValueError, если:
      - аргумент не начинается с '--';
      - у флага нет значения;
      - отсутствует обязательный флаг.
    """
    flags: dict[str, str] = {}
    i = 0
    while i < len(args):
        token = args[i]
        if not token.startswith("--"):
            raise ValueError(f"Ожидался флаг вида --name, получено: {token!r}")
        name = token[2:]
        if not name:
            raise ValueError("Пустое имя флага.")
        if i + 1 >= len(args):
            raise ValueError(f"У флага --{name} нет значения.")
        flags[name] = args[i + 1]
        i += 2

    missing = required - flags.keys()
    if missing:
        names = ", ".join(f"--{m}" for m in sorted(missing))
        raise ValueError(f"Не хватает обязательных флагов: {names}")
    return flags


HELP = """Доступные команды:
  register <username> <password>     — регистрация
  login <username> <password>        — вход
  show-portfolio                     — портфель и балансы
  buy <currency> <amount>            — купить валюту за USD
  sell <currency> <amount>           — продать валюту за USD
  get-rate <from> [to]               — курс (по умолчанию к USD)
  update-rates [--source coingecko|exchangerate]  — обновить курсы из API
  show-rates [--currency CODE] [--top N] [--base CODE] — курсы из кеша
  help                               — эта справка
  exit                               — выход
"""


class Session:
    """Состояние текущей сессии CLI."""

    def __init__(self) -> None:
        self.user: User | None = None


def _require_login(session: Session) -> User:
    if session.user is None:
        raise ValueError("Сначала выполните login")
    return session.user


def _cmd_register(session: Session, args: list[str]) -> None:
    flags = _parse_flags(args, required={"username", "password"})
    user = usecases.register(flags["username"], flags["password"])
    print(
        f"Пользователь {user.username!r} зарегистрирован (id={user.user_id}). "
        f"Войдите: login --username {user.username} --password ****"
    )


def _cmd_login(session: Session, args: list[str]) -> None:
    flags = _parse_flags(args, required={"username", "password"})
    user = usecases.login(flags["username"], flags["password"])
    session.user = user
    print(f"Вы вошли как {user.username!r}")


CRYPTO_CODES = {"BTC", "ETH"}


def _fmt_amount(value: float, code: str = "") -> str:
    """2 знака для фиата, 4 — для криптовалюты."""
    if code in CRYPTO_CODES:
        return f"{value:.4f}"
    return f"{value:.2f}"


def _cmd_show_portfolio(session: Session, args: list[str]) -> None:
    user = _require_login(session)
    flags = _parse_flags(args, required=set())
    base = flags.get("base", "USD").strip().upper()

    if base not in STUB_RATES_USD:
        raise ValueError(f"Неизвестная базовая валюта {base!r}")

    portfolio = usecases.get_portfolio(user)
    wallets = portfolio.wallets

    if not wallets:
        print(f"Портфель пользователя {user.username!r} пуст.")
        return

    print(f"Портфель пользователя {user.username!r} (база: {base}):")
    total = 0.0
    for code, wallet in sorted(wallets.items()):
        value = usecases.get_wallet_value_in(wallet, base)
        total += value
        print(f"- {code}: {_fmt_amount(wallet.balance, code)}  → {value:.2f} {base}")
    print("-" * 33)
    print(f"ИТОГО: {total:.2f} {base}")


def _cmd_buy(session: Session, args: list[str]) -> None:
    user = _require_login(session)
    flags = _parse_flags(args, required={"currency", "amount"})
    code = flags["currency"]
    try:
        amount = float(flags["amount"])
    except ValueError:
        raise ValueError(f"'amount' должен быть числом: {flags['amount']!r}") from None

    result = usecases.buy(user.user_id, code, amount)

    print(
        f"Покупка выполнена: {result['amount']:.4f} "
        f"{result['currency_code']} по курсу {result['rate']:.2f} "
        f"USD/{result['currency_code']}"
    )
    print("Изменения в портфеле:")
    print(
        f"- {result['currency_code']}: было {result['old_balance']:.4f} "
        f"→ стало {result['new_balance']:.4f}"
    )
    print(f"Оценочная стоимость покупки: {result['cost_usd']:.2f} USD")


def _cmd_sell(session: Session, args: list[str]) -> None:
    user = _require_login(session)
    flags = _parse_flags(args, required={"currency", "amount"})
    code = flags["currency"]
    try:
        amount = float(flags["amount"])
    except ValueError:
        raise ValueError(f"'amount' должен быть числом: {flags['amount']!r}") from None

    result = usecases.sell(user.user_id, code, amount)

    print(
        f"Продажа выполнена: {result['amount']:.4f} "
        f"{result['currency_code']} по курсу {result['rate']:.2f} "
        f"USD/{result['currency_code']}"
    )
    print("Изменения в портфеле:")
    print(
        f"- {result['currency_code']}: было {result['old_balance']:.4f} "
        f"→ стало {result['new_balance']:.4f}"
    )
    print(f"Оценочная выручка: {result['proceeds_usd']:.2f} USD")


def _cmd_get_rate(session: Session, args: list[str]) -> None:
    flags = _parse_flags(args, required={"from", "to"})
    frm = flags["from"]
    to = flags["to"]
    info = usecases.get_rate_info(frm, to)
    reverse = usecases.get_rate_info(to, frm)
    updated = info["updated_at"].replace("T", " ").replace("+00:00", "")
    print(
        f"Курс {info['from']}→{info['to']}: {info['rate']:.8f} (обновлено: {updated})"
    )
    print(f"Обратный курс {reverse['from']}→{reverse['to']}: {reverse['rate']:.2f}")


def _cmd_update_rates(session: Session, args: list[str]) -> None:
    flags = _parse_flags(args, required=set())
    source = flags.get("source")
    if source and source not in ("coingecko", "exchangerate"):
        raise ValueError("--source должен быть 'coingecko' или 'exchangerate'")
    config = ParserConfig()
    storage = ParserStorage(config)
    updater = RatesUpdater(config, storage)
    result = updater.run_update(source=source)
    if result["errors"]:
        print("Update completed with errors:")
        for err in result["errors"]:
            print(f"  - {err}")
    print(
        f"Update successful. Total rates updated: {result['updated']}. "
        f"Last refresh: {result['last_refresh']}"
    )


def _cmd_show_rates(session: Session, args: list[str]) -> None:
    flags = _parse_flags(args, required=set())
    currency = flags.get("currency")
    base = flags.get("base")
    top_raw = flags.get("top")
    top = int(top_raw) if top_raw else None

    config = ParserConfig()
    storage = ParserStorage(config)
    cache = storage.load_rates()
    pairs = cache.get("pairs", {})
    last_refresh = cache.get("last_refresh") or "—"

    if not pairs:
        raise ValueError(
            "Локальный кеш курсов пуст. Выполните 'update-rates', "
            "чтобы загрузить данные."
        )

    items = list(pairs.items())
    if currency:
        code = currency.strip().upper()
        items = [(p, v) for p, v in items if p.startswith(f"{code}_")]
        if not items:
            raise ValueError(f"Курс для {code!r} не найден в кеше.")
    if base:
        b = base.strip().upper()
        items = [(p, v) for p, v in items if p.endswith(f"_{b}")]
    if top:
        items.sort(key=lambda kv: kv[1]["rate"], reverse=True)
        items = items[:top]

    print(f"Rates from cache (updated at {last_refresh}):")
    for pair, payload in items:
        print(f"- {pair}: {payload['rate']}")


COMMANDS = {
    "register": _cmd_register,
    "login": _cmd_login,
    "show-portfolio": _cmd_show_portfolio,
    "buy": _cmd_buy,
    "sell": _cmd_sell,
    "get-rate": _cmd_get_rate,
    "update-rates": _cmd_update_rates,
    "show-rates": _cmd_show_rates,
}


def run() -> None:
    """Главный цикл CLI."""
    session = Session()
    print("ValutaTrade Hub. Введите 'help' для списка команд.")
    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nВыход.")
            break

        if not raw:
            continue

        try:
            parts = shlex.split(raw)
        except ValueError as exc:
            print(f"Ошибка разбора команды: {exc}")
            continue

        command, *args = parts
        if command in ("exit", "quit"):
            print("До свидания!")
            break
        if command == "help":
            print(HELP)
            continue

        handler = COMMANDS.get(command)
        if handler is None:
            print(f"Неизвестная команда: {command}. Введите 'help'.")
            continue

        try:
            handler(session, args)
        except InsufficientFundsError as exc:
            print(f"Ошибка: {exc}")
        except CurrencyNotFoundError as exc:
            print(f"Ошибка: {exc}")
            codes = ", ".join(c.code for c in list_currencies())
            print(f"Поддерживаемые коды: {codes}")
        except ApiRequestError as exc:
            print(f"Ошибка: {exc}")
            print("Подсказка: повторите позже или проверьте сеть.")
        except ValueError as exc:
            print(f"Ошибка: {exc}")
        except Exception as exc:  # noqa: BLE001
            print(f"Непредвиденная ошибка: {exc}")
