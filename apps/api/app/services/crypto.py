"""Cifrado de tokens de proyecto (Fernet). Nunca se guarda ni se registra el token en claro."""

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


class TokenCryptoError(Exception):
    pass


def _fernet() -> Fernet:
    key = get_settings().token_encryption_key
    if not key:
        raise TokenCryptoError("TOKEN_ENCRYPTION_KEY no configurada: no se guardan tokens")
    try:
        return Fernet(key.encode())
    except ValueError as exc:
        raise TokenCryptoError("TOKEN_ENCRYPTION_KEY no es una clave Fernet válida") from exc


def encrypt_token(token: str) -> str:
    return _fernet().encrypt(token.encode()).decode()


def decrypt_token(stored: str) -> str:
    try:
        return _fernet().decrypt(stored.encode()).decode()
    except InvalidToken as exc:
        raise TokenCryptoError("token no descifrable: revisa TOKEN_ENCRYPTION_KEY") from exc
