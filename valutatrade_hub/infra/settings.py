"""Singleton SettingsLoader — единая конфигурация проекта."""

from pathlib import Path
from typing import Any


class SettingsLoader:
    """
    Singleton: ровно один экземпляр конфигурации в приложении.

    Реализация через __new__: для одного класса это проще и читабельнее
    метакласса; гарантирует, что при повторных вызовах SettingsLoader()
    возвращается тот же объект.
    """

    _instance: "SettingsLoader | None" = None
    _initialized: bool = False

    def __new__(cls) -> "SettingsLoader":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._config = self._load_defaults()

    def _load_defaults(self) -> dict[str, Any]:
        project_root = Path(__file__).resolve().parents[2]
        data_dir = project_root / "data"
        return {
            "data_dir": data_dir,
            "users_file": data_dir / "users.json",
            "portfolios_file": data_dir / "portfolios.json",
            "rates_file": data_dir / "rates.json",
            "rates_ttl_seconds": 300,
            "default_base_currency": "USD",
            "logs_dir": project_root / "logs",
            "log_level": "INFO",
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Возвращает параметр конфигурации по ключу."""
        return self._config.get(key, default)

    def reload(self) -> None:
        """Перезагружает конфигурацию (сбрасывает кэш)."""
        self._config = self._load_defaults()

    def as_dict(self) -> dict[str, Any]:
        """Возвращает копию всей конфигурации (для отладки)."""
        return dict(self._config)
