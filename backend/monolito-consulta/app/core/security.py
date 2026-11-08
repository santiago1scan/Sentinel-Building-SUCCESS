"""Node token helpers. Pure functions, no database or framework dependencies."""
import hashlib
import secrets

NODE_TOKEN_BYTES = 32


def generate_node_token() -> str:
    """Create a high-entropy, URL-safe token for a node. Shown once, never stored in plain text."""
    return secrets.token_urlsafe(NODE_TOKEN_BYTES)


def hash_token(token: str) -> str:
    """Return the SHA-256 hex digest that is stored and compared in the database."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
