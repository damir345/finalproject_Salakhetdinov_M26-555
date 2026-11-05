# ValutaTrade Hub

Консольное приложение для симуляции торговли валютами: регистрация пользователей,
виртуальные кошельки, покупка/продажа валют по курсам, просмотр портфеля.
Включает **Core Service** (CLI, пользователи, портфели) и **Parser Service**
(сбор курсов из внешних API, история, кеш).

---

## Демо

Посмотреть полный сценарий работы приложения (регистрация, вход, просмотр портфеля, 
покупка/продажа, получение курсов, обновление курсов через Parser Service и обработка ошибок) 
можно по ссылке:

https://asciinema.org/a/03vr1UwkcHCEYDQL
---

## Содержание

- [Возможности](#возможности)
- [Стек](#стек)
- [Установка](#установка)
- [Запуск](#запуск)
- [Команды CLI](#команды-cli)
- [Пример сессии](#пример-сессии)
- [Архитектура](#архитектура)
- [Структура проекта](#структура-проекта)
- [Форматы JSON](#форматы-json)
- [Parser Service](#parser-service)
- [Разработка и сборка](#разработка-и-сборка)

---

## Возможности

- Регистрация и вход с хешированием пароля (sha256 + соль).
- Портфель с кошельками по валютам (USD, EUR, GBP, RUB, BTC, ETH, SOL).
- Покупка/продажа валюты за базовую (по умолчанию USD).
- Просмотр портфеля с конвертацией в базовую валюту.
- Получение курса валюты с кешем (`data/rates.json`, TTL 5 минут) и обратным курсом.
- **Parser Service**: сбор курсов из CoinGecko (крипто) и ExchangeRate-API (фиат),
  история замеров, кеш для Core, планировщик.
- **Иерархия валют**: `Currency` (ABC) → `FiatCurrency`, `CryptoCurrency`,
  реестр `get_currency(code)`.
- **JSON-логирование** операций с ротацией (`logs/actions.log`).
- **Пользовательские исключения** и понятные сообщения об ошибках.
- **Singleton-инфраструктура**: `SettingsLoader`, `DatabaseManager`.

---

## Стек

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) — управление зависимостями и сборка
- `requests` — HTTP-запросы к CoinGecko и ExchangeRate-API
- `prettytable` — таблицы в CLI
- `ruff` — линтер и форматтер (dev)
- Стандартная библиотека: `json`, `hashlib`, `secrets`, `shlex`, `logging`, `abc`,
  `dataclasses`, `logging.handlers`

---

## Установка

```bash
git clone https://github.com/damir345/finalproject_Salakhetdinov_M26-555.git
cd finalproject_Salakhetdinov_M26-555
uv sync
```

## Запуск

```bash
uv run finalproject-salakhetdinov-m26-555
```
или
```bash
uv run python -m valutatrade_hub
```
При первом запуске создаются пустые data/users.json, data/portfolios.json,
data/rates.json (если их нет) и каталог logs/.

## Команды CLI

Все аргументы — в формате `--flag value`.

| Команда | Аргументы | Описание |
|---|---|---|
| `register` | `--username <str>`, `--password <str>` | Регистрация. Пароль ≥ 4 символов, username уникален |
| `login` | `--username <str>`, `--password <str>` | Вход. Устанавливает текущую сессию |
| `show-portfolio` | `[--base <code>]` | Портфель и стоимость в базовой валюте (по умолчанию `USD`) |
| `buy` | `--currency <code>`, `--amount <float>` | Купить валюту за базовую |
| `sell` | `--currency <code>`, `--amount <float>` | Продать валюту за базовую |
| `get-rate` | `--from <code>`, `--to <code>` | Курс и обратный курс |
| `help` | — | Справка по командам |
| `exit` / `quit` | — | Выход |

`buy`/`sell`/`show-portfolio` требуют активной сессии (`login`).
`register`/`login`/`get-rate` — доступны без входа.

## Пример сессии

```text
> register --username alice --password 1234
Пользователь 'alice' зарегистрирован (id=1). Войдите: login --username alice --password ****

> login --username alice --password 1234
Вы вошли как 'alice'

> buy --currency BTC --amount 0.05
Покупка выполнена: 0.0500 BTC по курсу 59337.21 USD/BTC
Изменения в портфеле:
- BTC: было 0.0000 → стало 0.0500
Оценочная стоимость покупки: 2966.86 USD

> sell --currency BTC --amount 0.01
Продажа выполнена: 0.0100 BTC по курсу 59337.21 USD/BTC
Изменения в портфеле:
- BTC: было 0.0500 → стало 0.0400
Оценочная выручка: 593.37 USD

> show-portfolio
Портфель пользователя 'alice' (база: USD):
- BTC: 0.0400  → 2373.49 USD
- USD: 2626.51  → 2626.51 USD
---------------------------------
ИТОГО: 5000.00 USD

> get-rate --from USD --to BTC
Курс USD→BTC: 0.00001685 (обновлено: 2025-10-09 12:05:22)
Обратный курс BTC→USD: 59337.21

> buy --currency XYZ --amount 1
Ошибка: Неизвестная валюта 'XYZ'
Поддерживаемые коды: USD, EUR, GBP, RUB, BTC, ETH

> sell --currency BTC --amount 100
Ошибка: Недостаточно средств: доступно 0.0400 BTC, требуется 100.0000 BTC

> exit
До свидания!
```

## Структура проекта

```text
finalproject_Salakhetdinov_M26-555/
├── data/                       # runtime-данные (в .gitignore)
│   ├── users.json
│   ├── portfolios.json
│   └── rates.json
├── logs/                       # логи (в .gitignore)
│   └── actions.log
├── valutatrade_hub/
│   ├── __init__.py
│   ├── logging_config.py       # JSON-логи, ротация
│   ├── decorators.py           # @log_action
│   ├── core/
│   │   ├── currencies.py       # Currency, FiatCurrency, CryptoCurrency
│   │   ├── exceptions.py       # ValutaTradeError и наследники
│   │   ├── models.py           # User, Wallet, Portfolio
│   │   ├── usecases.py         # register, login, buy, sell, get_rate_info
│   │   └── utils.py            # хеширование, JSON, get_rate
│   ├── infra/
│   │   ├── __init__.py
│   │   ├── settings.py         # SettingsLoader (Singleton)
│   │   └── database.py         # DatabaseManager (Singleton)
│   └── cli/
│       ├── __init__.py
│       └── interface.py        # Session, _parse_flags, команды, run()
├── main.py                     # точка входа
├── pyproject.toml
├── uv.lock
├── README.md
└── .gitignore
```

## Форматы JSON

### `data/users.json`

```json
[
  {
    "user_id": 1,
    "username": "alice",
    "hashed_password": "3e2a19...",
    "salt": "x5T9!",
    "registration_date": "2025-10-09T12:00:00"
  }
]
```

### `data/portfolios.json`

```json
[
  {
    "user_id": 1,
    "wallets": {
      "USD": {"balance": 1500.0},
      "BTC": {"balance": 0.05}
    }
  }
]
```

### `data/rates.json` — кеш Core Service

```json
{
  "pairs": {
    "EUR_USD": {"rate": 1.08, "updated_at": "2025-10-09T12:00:00+00:00", "source": "ParserService"},
    "BTC_USD": {"rate": 59337.21, "updated_at": "2025-10-09T12:00:00+00:00", "source": "ParserService"}
  },
  "last_refresh": "2025-10-09T12:00:01+00:00"
}
```
get_rate поддерживает оба формата (плоский и pairs), но Parser Service пишет pairs.

### `data/exchange_rates.json` — история Parser Service

```json
[
  {
    "id": "BTC_USD_2025-10-10T12:00:00Z",
    "from_currency": "BTC",
    "to_currency": "USD",
    "rate": 59337.21,
    "timestamp": "2025-10-10T12:00:00Z",
    "source": "CoinGecko",
    "meta": {"status_code": 200, "raw_id": "bitcoin"}
  }
]
```

- `id = <FROM>_<TO>_<ISO-UTC timestamp>` — уникальный идентификатор замера.
- Запись добавляется только после успешного ответа API.

## Parser Service

Отдельный микросервис для сбора курсов из внешних API. Пишет в
`data/rates.json` (кеш для Core) и `data/exchange_rates.json` (история).

### Источники

| Источник | Что | Ключ |
|---|---|---|
| CoinGecko | Криптовалюты (BTC, ETH, SOL) к USD | не требуется |
| ExchangeRate-API | Фиатные валюты (EUR, GBP, RUB) к USD | `EXCHANGERATE_API_KEY` (env) |

### Команды

| Команда | Аргументы | Описание |
|---|---|---|
| `update-rates` | `[--source coingecko\|exchangerate]` | Обновить курсы из API |
| `show-rates` | `[--currency CODE] [--top N] [--base CODE]` | Показать из кеша |

`update-rates` при ошибке одного источника продолжает работу с другим.
Результат: `Update successful. Total rates updated: N.`

### Переменные окружения

```bash
export EXCHANGERATE_API_KEY=ваш_ключ
```

- Без ключа ExchangeRate-API вернёт ApiRequestError, CoinGecko продолжит работать.

## Разработка и сборка

```bash
uv run ruff check .          # линтер
uv run ruff check . --fix    # автоисправление
uv run ruff format .         # форматирование
uv run ruff format --check . # проверка форматирования
uv build                     # сборка пакета (dist/*.whl, dist/*.tar.gz)
```