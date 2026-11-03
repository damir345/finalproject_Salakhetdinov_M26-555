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


class Wallet:
    """Кошелёк пользователя для одной конкретной валюты."""

    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        if not currency_code or not currency_code.strip():
            raise ValueError("Код валюты не может быть пустым.")
        self._currency_code = currency_code.strip().upper()
        self._balance = 0.0
        self.balance = balance  # сеттер проверит тип и неотрицательность

    # --- currency_code (только чтение) ---

    @property
    def currency_code(self) -> str:
        return self._currency_code

    # --- balance (геттер + сеттер с проверками) ---

    @property
    def balance(self) -> float:
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("Баланс должен быть числом.")
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным.")
        self._balance = float(value)

    # --- Методы из задания ---

    def deposit(self, amount: float) -> None:
        """Пополняет баланс на amount (положительное число)."""
        self._validate_amount(amount)
        self.balance = self._balance + amount

    def withdraw(self, amount: float) -> None:
        """Снимает amount, если баланс позволяет."""
        self._validate_amount(amount)
        if amount > self._balance:
            raise ValueError(
                f"Недостаточно средств: баланс {self._balance}, запрошено {amount}."
            )
        self.balance = self._balance - amount

    def get_balance_info(self) -> dict:
        """Возвращает информацию о текущем балансе."""
        return {
            "currency_code": self._currency_code,
            "balance": self._balance,
        }

    # --- Внутренние проверки ---

    @staticmethod
    def _validate_amount(amount: float) -> None:
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise TypeError("Сумма должна быть числом.")
        if amount <= 0:
            raise ValueError("Сумма должна быть положительным числом.")

    # --- Сериализация ---

    def to_dict(self) -> dict:
        """Словарь для хранения в портфеле (формат из задания)."""
        return {
            "currency_code": self._currency_code,
            "balance": self._balance,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Wallet":
        """Восстанавливает кошелёк из словаря."""
        try:
            return cls(
                currency_code=data["currency_code"],
                balance=data["balance"],
            )
        except KeyError as exc:
            raise ValueError(f"В данных кошелька нет поля {exc}") from exc
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Некорректные данные кошелька: {exc}") from exc


# Фиктивные курсы относительно USD (1 единица валюты = X USD).
EXCHANGE_RATES: dict[str, float] = {
    "USD": 1.0,
    "EUR": 1.08,
    "GBP": 1.27,
    "BTC": 60000.0,
    "ETH": 3000.0,
}


class Portfolio:
    """Набор кошельков одного пользователя."""

    def __init__(
        self,
        user: User,
        wallets: dict[str, Wallet] | None = None,
    ) -> None:
        self._user = user
        self._wallets: dict[str, Wallet] = {}
        if wallets:
            for code, wallet in wallets.items():
                if code != wallet.currency_code:
                    raise ValueError(
                        f"Ключ {code!r} не совпадает с кодом кошелька "
                        f"{wallet.currency_code!r}."
                    )
                self._wallets[code] = wallet

    # --- user (только чтение) ---

    @property
    def user(self) -> User:
        return self._user

    @property
    def user_id(self) -> int:
        return self._user.user_id

    # --- wallets (только чтение, копия словаря) ---

    @property
    def wallets(self) -> dict[str, Wallet]:
        return dict(self._wallets)

    # --- Методы из задания ---

    def add_currency(self, currency_code: str) -> Wallet:
        """
        Добавляет кошелёк в портфель и возвращает его.

        Если кошелёк с таким кодом уже есть — возвращает существующий
        (идемпотентно, без создания дубликата).
        """
        code = currency_code.strip().upper()
        if not code:
            raise ValueError("Код валюты не может быть пустым.")
        if code in self._wallets:
            return self._wallets[code]
        wallet = Wallet(code)
        self._wallets[code] = wallet
        return wallet

    def get_wallet(self, currency_code: str) -> Wallet:
        """Возвращает кошелёк по коду валюты."""
        code = currency_code.strip().upper()
        if code not in self._wallets:
            raise KeyError(f"В портфеле нет кошелька {code!r}.")
        return self._wallets[code]

    def get_total_value(self, base_currency: str = "USD") -> float:
        """
        Возвращает общую стоимость всех кошельков в base_currency.

        Курсы берутся из EXCHANGE_RATES (относительно USD).
        Если курса нет — ValueError.
        """
        base = base_currency.strip().upper()
        if base not in EXCHANGE_RATES:
            raise ValueError(f"Нет курса для базовой валюты {base!r}.")

        base_rate = EXCHANGE_RATES[base]
        total = 0.0
        for code, wallet in self._wallets.items():
            if code not in EXCHANGE_RATES:
                raise ValueError(f"Нет курса для валюты {code!r}.")
            total += wallet.balance * EXCHANGE_RATES[code] / base_rate
        return total

    # --- Сериализация ---

    def to_dict(self) -> dict:
        """Словарь для portfolios.json (формат из задания)."""
        return {
            "user_id": self._user.user_id,
            "wallets": {
                code: {"balance": wallet.balance}
                for code, wallet in self._wallets.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict, user: User) -> "Portfolio":
        """
        Восстанавливает портфель из словаря.

        Нужен объект User, потому что портфель ссылается на пользователя.
        """
        try:
            wallets_data = data["wallets"]
            wallets = {
                code: Wallet(code, payload["balance"])
                for code, payload in wallets_data.items()
            }
            return cls(user=user, wallets=wallets)
        except KeyError as exc:
            raise ValueError(f"В данных портфеля нет поля {exc}") from exc
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Некорректные данные портфеля: {exc}") from exc
