"""Вспомогательные функции: хеширование, JSON-хранилище, курсы."""

import hashlib
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# --- Хеширование пароля ---


def generate_salt(length: int = 8) -> str:
    """Генерирует случайную соль заданной длины."""
    return secrets.token_hex(length // 2)


def hash_password(password: str, salt: str) -> str:
    """Возвращает sha256-хеш от password + salt."""
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()


# --- Пути к файлам данных ---

# utils.py лежит в valutatrade_hub/core/:
# parents[0] = core/, parents[1] = valutatrade_hub/, parents[2] = корень проекта
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

USERS_FILE = DATA_DIR / "users.json"
PORTFOLIOS_FILE = DATA_DIR / "portfolios.json"
RATES_FILE = DATA_DIR / "rates.json"


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


def get_rate(from_currency: str, to_currency: str = "USD") -> dict:
    """
    Возвращает курс from_currency → to_currency.

    Сначала ищет в rates.json (кеш). Если нет — берёт из STUB_RATES_USD
    и сохраняет в кеш.

    Формат ответа:
        {"from": "EUR", "to": "USD", "rate": 1.08, "updated_at": "..."}
    """
    frm = from_currency.strip().upper()
    to = to_currency.strip().upper()
    if not frm or not to:
        raise ValueError("Коды валют не могут быть пустыми.")

    key = f"{frm}_{to}"
    cache = read_json(RATES_FILE, default={})

    if key in cache and "rate" in cache[key]:
        entry = cache[key]
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
    cache[key] = {"rate": rate, "updated_at": updated_at}
    cache["source"] = "StubRates"
    cache["last_refresh"] = updated_at
    write_json(RATES_FILE, cache)

    return {"from": frm, "to": to, "rate": rate, "updated_at": updated_at}
