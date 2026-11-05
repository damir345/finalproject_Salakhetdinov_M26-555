"""Вспомогательные функции: хеширование, JSON-хранилище, курсы."""

import hashlib
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import CurrencyNotFoundError
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader

# --- Хеширование пароля ---


def generate_salt(length: int = 8) -> str:
    """Генерирует случайную соль заданной длины."""
    return secrets.token_hex(length // 2)


def hash_password(password: str, salt: str) -> str:
    """Возвращает sha256-хеш от password + salt."""
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()


# --- Пути к файлам данных ---

_settings = SettingsLoader()
_db = DatabaseManager()

DATA_DIR = _settings.get("data_dir")
USERS_FILE = _settings.get("users_file")
PORTFOLIOS_FILE = _settings.get("portfolios_file")
RATES_FILE = _settings.get("rates_file")


# --- Чтение и запись JSON ---


def _ensure_file(path: Path, default: Any) -> None:
    """Создаёт файл с default, если его нет."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(default, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def read_json(path: Path, default: Any) -> Any:
    """Читает JSON. Если файла нет — создаёт с default и возвращает default."""
    _ensure_file(path, default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Файл {path.name} повреждён: {exc}") from exc


def write_json(path: Path, data: Any) -> None:
    """Атомарно записывает JSON (через временный файл)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)


# --- Курсы валют ---

# Фиктивные курсы относительно USD (X USD).
STUB_RATES_USD: dict[str, float] = {
    "USD": 1.0,
    "EUR": 1.08,
    "GBP": 1.27,
    "RUB": 0.01016,
    "BTC": 59337.21,
    "ETH": 3720.00,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


CACHE_TTL_SECONDS = _settings.get("rates_ttl_seconds", 300)


def get_rate(from_currency: str, to_currency: str = "USD") -> dict:
    """
    Возвращает курс from_currency → to_currency.

    Сначала ищет в rates.json (кеш). Если запись свежая (моложе 5 минут) —
    возвращает её. Иначе пересчитывает из STUB_RATES_USD и обновляет кеш.

    Поддерживает оба формата rates.json:
      - плоский:  {"EUR_USD": {"rate": ...}}
      - с обёрткой: {"pairs": {"EUR_USD": {...}}, "last_refresh": ...}

    Формат ответа:
        {"from": "EUR", "to": "USD", "rate": 1.08, "updated_at": "..."}
    """
    frm = from_currency.strip().upper()
    to = to_currency.strip().upper()
    if not frm or not to:
        raise CurrencyNotFoundError(from_currency or to_currency)

    # Валидация через реестр валют: неизвестный код → CurrencyNotFoundError
    get_currency(frm)
    get_currency(to)

    key = f"{frm}_{to}"
    cache = _db.load_rates()
    pairs = cache.get("pairs", cache)

    if key in pairs and "rate" in pairs[key]:
        entry = pairs[key]
        try:
            updated = datetime.fromisoformat(entry["updated_at"])
        except (KeyError, ValueError):
            updated = None
        if updated is not None:
            age = (datetime.now(timezone.utc) - updated).total_seconds()
            if age <= CACHE_TTL_SECONDS:
                return {
                    "from": frm,
                    "to": to,
                    "rate": float(entry["rate"]),
                    "updated_at": entry["updated_at"],
                }

    if frm not in STUB_RATES_USD or to not in STUB_RATES_USD:
        raise ValueError(f"Нет курса для пары {frm} → {to}.")

    rate = STUB_RATES_USD[frm] / STUB_RATES_USD[to]
    updated_at = _now_iso()
    pairs = cache.get("pairs", {})
    pairs[key] = {"rate": rate, "updated_at": updated_at}
    cache["pairs"] = pairs
    cache["last_refresh"] = updated_at
    _db.save_rates(cache)

    return {"from": frm, "to": to, "rate": rate, "updated_at": updated_at}
