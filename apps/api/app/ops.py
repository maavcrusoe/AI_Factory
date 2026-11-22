"""Operaciones de mantenimiento, desde el contenedor: `python -m app.ops rotate-token-key`."""

import argparse
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import ProjectIntegration
from app.services.crypto import rotate_ciphertext


def rotate_integration(integration: ProjectIntegration) -> int:
    """Re-cifra los dos tokens de una integración. Devuelve cuántos valores cambió (sin commit)."""
    changed = 0
    for field in ("token_encrypted", "merge_token_encrypted"):
        stored = getattr(integration, field)
        if stored:
            setattr(integration, field, rotate_ciphertext(stored))
            changed += 1
    return changed


def rotate_token_key(db: Session) -> int:
    """Re-cifra todos los tokens de proyecto con la clave primaria. Todo o nada: un token ilegible aborta."""
    changed = sum(rotate_integration(i) for i in db.scalars(select(ProjectIntegration)).all())
    db.commit()
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.ops")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "rotate-token-key",
        help="Re-cifra los tokens de proyecto con la primera clave de TOKEN_ENCRYPTION_KEY",
    )
    args = parser.parse_args(argv)
    if args.command == "rotate-token-key":
        with SessionLocal() as db:
            print(f"Tokens re-cifrados: {rotate_token_key(db)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
