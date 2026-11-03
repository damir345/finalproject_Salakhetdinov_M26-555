from datetime import datetime

from valutatrade_hub.core.utils import generate_salt, hash_password


class User:
    """Пользователь системы."""

    def __init__(
        self,
        user_id: int,
        username: str,
        password: str | None = None,
        hashed_password: str | None = None,
        salt: str | None = None,
        registration_date: datetime | None = None,
    ) -> None:
        self._user_id = user_id
        self._salt = salt if salt is not None else generate_salt()
        self._username = ""
        self.username = username

        if hashed_password is not None:
            self._hashed_password = hashed_password
        elif password is not None:
            self.password = password  # сеттер проверит длину и захеширует
        else:
            raise ValueError("Нужно передать password или hashed_password.")

        self._registration_date = registration_date or datetime.now()

    # --- user_id ---

    @property
    def user_id(self) -> int:
        return self._user_id

    # --- username ---

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        if not value or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым.")
        self._username = value.strip()

    # --- password (только запись: открытый пароль не хранится) ---

    @property
    def password(self) -> str:
        raise AttributeError("Пароль не хранится в открытом виде.")

    @password.setter
    def password(self, new_password: str) -> None:
        self._validate_password_length(new_password)
        self._hashed_password = hash_password(new_password, self._salt)

    # --- hashed_password ---

    @property
    def hashed_password(self) -> str:
        return self._hashed_password

    # --- salt ---

    @property
    def salt(self) -> str:
        return self._salt

    # --- registration_date ---

    @property
    def registration_date(self) -> datetime:
        return self._registration_date

    # --- Методы из задания ---

    def get_user_info(self) -> dict:
        """Возвращает информацию о пользователе без пароля."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    def verify_password(self, password: str) -> bool:
        """Проверяет, совпадает ли введённый пароль с сохранённым хешем."""
        return hash_password(password, self._salt) == self._hashed_password

    def change_password(self, new_password: str) -> None:
        """Меняет пароль пользователя с проверкой длины и хешированием."""
        self._validate_password_length(new_password)
        self._hashed_password = hash_password(new_password, self._salt)

    # --- Внутренние проверки ---

    @staticmethod
    def _validate_password_length(password: str) -> None:
        if len(password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов.")

    # --- Сериализация ---

    def to_dict(self) -> dict:
        """Словарь для сохранения в users.json (формат из задания)."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Восстанавливает пользователя из словаря users.json."""
        try:
            return cls(
                user_id=data["user_id"],
                username=data["username"],
                hashed_password=data["hashed_password"],
                salt=data["salt"],
                registration_date=datetime.fromisoformat(data["registration_date"]),
            )
        except KeyError as exc:
            raise ValueError(f"В данных пользователя нет поля {exc}") from exc
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Некорректные данные пользователя: {exc}") from exc
