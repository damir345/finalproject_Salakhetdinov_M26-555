"""CLI: единственная точка входа для пользовательских команд."""

import shlex

from valutatrade_hub.core import usecases
from valutatrade_hub.core.models import User
from valutatrade_hub.core.utils import STUB_RATES_USD


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


def _fmt_amount(value: float) -> str:
    """2 знака для целых значений, 4 — для дробных."""
    if value == int(value):
        return f"{value:.2f}"
    return f"{value:.4f}"


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
        print(f"- {code}: {_fmt_amount(wallet.balance)}  → {value:.2f} {base}")
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

    result = usecases.buy(user, code, amount)

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
    if len(args) != 2:
        raise ValueError("Использование: sell <currency> <amount>")
    code = args[0]
    try:
        amount = float(args[1])
    except ValueError:
        raise ValueError(f"Некорректная сумма: {args[1]!r}") from None
    result = usecases.sell(user, code, amount)
    print(
        f"Продано {result['amount']} {result['currency_code']} "
        f"по курсу {result['rate']:.4f} USD "
        f"(получено {result['proceeds_usd']:.2f} USD)."
    )


def _cmd_get_rate(session: Session, args: list[str]) -> None:
    if len(args) not in (1, 2):
        raise ValueError("Использование: get-rate <from> [to]")
    frm = args[0]
    to = args[1] if len(args) == 2 else "USD"
    info = usecases.get_rate_info(frm, to)
    print(
        f"1 {info['from']} = {info['rate']:.6f} {info['to']} "
        f"(обновлено {info['updated_at']})."
    )


COMMANDS = {
    "register": _cmd_register,
    "login": _cmd_login,
    "show-portfolio": _cmd_show_portfolio,
    "buy": _cmd_buy,
    "sell": _cmd_sell,
    "get-rate": _cmd_get_rate,
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
        except ValueError as exc:
            print(f"Ошибка: {exc}")
        except Exception as exc:  # noqa: BLE001
            print(f"Непредвиденная ошибка: {exc}")
