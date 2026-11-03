import hashlib
import secrets


def generate_salt(length: int = 8) -> str:
    """Генерирует случайную соль заданной длины."""
    return secrets.token_hex(length // 2)


def hash_password(password: str, salt: str) -> str:
    """Возвращает sha256-хеш от password + salt."""
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()
