"""Хранилище Parser Service: история (exchange_rates.json) и кеш (rates.json)."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from valutatrade_hub.parser_service.config import ParserConfig


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _atomic_write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


class ParserStorage:
    """Чтение/запись истории и кеша курсов."""

    def __init__(self, config: ParserConfig) -> None:
        self.config = config
        self.history_path = Path(config.HISTORY_FILE_PATH)
        self.rates_path = Path(config.RATES_FILE_PATH)

    # --- история ---

    def load_history(self) -> list[dict]:
        if not self.history_path.exists():
            return []
        try:
            data = json.loads(self.history_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        return data if isinstance(data, list) else []

    def append_history(self, entries: list[dict]) -> None:
        history = self.load_history()
        history.extend(entries)
        _atomic_write(self.history_path, history)

    @staticmethod
    def make_history_entry(
        pair: str, rate: float, source: str, meta: dict | None = None
    ) -> dict:
        frm, to = pair.split("_", 1)
        timestamp = _now_iso()
        entry = {
            "id": f"{frm}_{to}_{timestamp}",
            "from_currency": frm,
            "to_currency": to,
            "rate": rate,
            "timestamp": timestamp,
            "source": source,
        }
        if meta:
            entry["meta"] = meta
        return entry

    # --- кеш ---

    def load_rates(self) -> dict:
        if not self.rates_path.exists():
            return {"pairs": {}, "last_refresh": None}
        try:
            data = json.loads(self.rates_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"pairs": {}, "last_refresh": None}
        if "pairs" not in data:
            data = {"pairs": data, "last_refresh": None}
        return data

    def update_rates_cache(self, new_pairs: dict[str, float], source: str) -> dict:
        cache = self.load_rates()
        pairs: dict[str, dict] = cache.get("pairs", {})
        now = _now_iso()
        updated = 0
        for pair, rate in new_pairs.items():
            existing = pairs.get(pair)
            if existing and existing.get("updated_at", "") >= now:
                # Существующая запись не старее новой — не перезаписываем
                continue
            pairs[pair] = {"rate": rate, "updated_at": now, "source": source}
            updated += 1
        cache["pairs"] = pairs
        cache["last_refresh"] = now
        _atomic_write(self.rates_path, cache)
        return cache
