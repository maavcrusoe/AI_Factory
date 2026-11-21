import base64
import hashlib
import hmac
import json
import secrets
import time

SCRYPT_PARAMS = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **SCRYPT_PARAMS)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_hex, digest_hex = stored.split("$")
    except ValueError:
        return False
    if scheme != "scrypt":
        return False
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), **SCRYPT_PARAMS)
    return hmac.compare_digest(digest, bytes.fromhex(digest_hex))


def _sign(payload: str, secret: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def create_token(email: str, secret: str, ttl_seconds: int) -> str:
    body = {"sub": email, "exp": int(time.time()) + ttl_seconds}
    payload = base64.urlsafe_b64encode(json.dumps(body).encode()).decode()
    return f"{payload}.{_sign(payload, secret)}"


def read_token(token: str, secret: str) -> str | None:
    """Devuelve el email del token o None si es inválido o ha expirado."""
    try:
        payload, signature = token.rsplit(".", 1)
        if not hmac.compare_digest(signature, _sign(payload, secret)):
            return None
        body = json.loads(base64.urlsafe_b64decode(payload))
    except (ValueError, TypeError):
        return None
    if body.get("exp", 0) < time.time():
        return None
    return body.get("sub")
