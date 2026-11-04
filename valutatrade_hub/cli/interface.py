"""CLI: единственная точка входа для пользовательских команд."""

import shlex

from prettytable import PrettyTable

from valutatrade_hub.core import usecases
from valutatrade_hub.core.models import User


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
        raise ValueError("Сначала выполните login.")
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


def _cmd_show_portfolio(session: Session, args: list[str]) -> None:
    user = _require_login(session)
    portfolio = usecases.get_portfolio(user)

    table = PrettyTable()
    table.field_names = ["Валюта", "Баланс"]
    for code, wallet in sorted(portfolio.wallets.items()):
        table.add_row([code, f"{wallet.balance:.8f}".rstrip("0").rstrip(".")])
    print(table)
    print(f"Общая стоимость (USD): {portfolio.get_total_value('USD'):.2f}")


def _cmd_buy(session: Session, args: list[str]) -> None:
    user = _require_login(session)
    if len(args) != 2:
        raise ValueError("Использование: buy <currency> <amount>")
    code = args[0]
    try:
        amount = float(args[1])
    except ValueError:
        raise ValueError(f"Некорректная сумма: {args[1]!r}") from None
    result = usecases.buy(user, code, amount)
    print(
        f"Куплено {result['amount']} {result['currency_code']} "
        f"по курсу {result['rate']:.4f} USD "
        f"(списано {result['cost_usd']:.2f} USD)."
    )


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
