"""Singleton DatabaseManager — абстракция над JSON-хранилищем."""

import json
from pathlib import Path
from typing import Any

from valutatrade_hub.infra.settings import SettingsLoader


class DatabaseManager:
    """
    Singleton: единая точка доступа к JSON-файлам.

    Реализация через __new__: для одного класса проще и читабельнее
    метакласса; гарантирует ровно один экземпляр.
    """

    _instance: "DatabaseManager | None" = None
    _initialized: bool = False

    def __new__(cls) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        settings = SettingsLoader()
        self._users_file: Path = settings.get("users_file")
        self._portfolios_file: Path = settings.get("portfolios_file")
        self._rates_file: Path = settings.get("rates_file")

    # --- низкоуровневые операции ---

    def _ensure_file(self, path: Path, default: Any) -> None:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(default, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    def _read(self, path: Path, default: Any) -> Any:
        self._ensure_file(path, default)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Файл {path.name} повреждён: {exc}") from exc

    def _write(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    # --- users ---

    def load_users(self) -> list[dict]:
        return self._read(self._users_file, default=[])

    def save_users(self, users: list[dict]) -> None:
        self._write(self._users_file, users)

    # --- portfolios ---

    def load_portfolios(self) -> list[dict]:
        return self._read(self._portfolios_file, default=[])

    def save_portfolios(self, portfolios: list[dict]) -> None:
        self._write(self._portfolios_file, portfolios)

    # --- rates ---

    def load_rates(self) -> dict:
        return self._read(self._rates_file, default={})

    def save_rates(self, rates: dict) -> None:
        self._write(self._rates_file, rates)
