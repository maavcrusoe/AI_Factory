"""Cifrado de tokens de proyecto (Fernet). Nunca se guarda ni se registra el token en claro."""

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from app.config import get_settings


class TokenCryptoError(Exception):
    pass


def _fernet() -> MultiFernet:
    """TOKEN_ENCRYPTION_KEY admite varias claves separadas por coma: la primera cifra, todas descifran.
    Así se rota sin perder tokens (ver docs/runbooks/rotacion-tokens.md)."""
    raw = get_settings().token_encryption_key
    keys = [k.strip() for k in (raw or "").split(",") if k.strip()]
    if not keys:
        raise TokenCryptoError("TOKEN_ENCRYPTION_KEY no configurada: no se guardan tokens")
    try:
        return MultiFernet([Fernet(k.encode()) for k in keys])
    except ValueError as exc:
        raise TokenCryptoError("TOKEN_ENCRYPTION_KEY no es una clave Fernet válida") from exc


def encrypt_token(token: str) -> str:
    return _fernet().encrypt(token.encode()).decode()


def decrypt_token(stored: str) -> str:
    try:
        return _fernet().decrypt(stored.encode()).decode()
    except InvalidToken as exc:
        raise TokenCryptoError("token no descifrable: revisa TOKEN_ENCRYPTION_KEY") from exc


def rotate_ciphertext(stored: str) -> str:
    """Re-cifra con la clave primaria. Falla si ninguna clave configurada lo descifra."""
    try:
        return _fernet().rotate(stored.encode()).decode()
    except InvalidToken as exc:
        raise TokenCryptoError("token no descifrable con ninguna clave configurada") from exc
