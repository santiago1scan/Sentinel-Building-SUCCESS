"""Node token helpers. Must hash exactly like monolito-consulta (app/core/security.py)."""
import hashlib


def hash_token(token: str) -> str:
    """Return the SHA-256 hex digest used to look up a node by its token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
