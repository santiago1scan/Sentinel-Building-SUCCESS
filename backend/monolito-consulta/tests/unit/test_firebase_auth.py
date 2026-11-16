"""Verificación de ID tokens de Firebase: firma, audiencia, emisor, vigencia y lista de correos.

No hay red: las llaves de Google se reemplazan por un par RSA generado en la prueba.
"""
import base64
import hashlib
import hmac
import json
import logging
import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.firebase_auth import FirebaseVerifier, parse_allowed_emails

PROJECT = "sentinel-test"
ISSUER = f"https://securetoken.google.com/{PROJECT}"


def new_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


SIGNING_KEY = new_key()


class FakeJwks:
    """Reemplaza a PyJWKClient: entrega siempre la llave pública del par de prueba."""

    def __init__(self, public_key=SIGNING_KEY.public_key(), error: Exception | None = None):
        self.public_key = public_key
        self.error = error

    def get_signing_key_from_jwt(self, token):
        if self.error:
            raise self.error
        return SimpleNamespace(key=self.public_key)


def make_token(key=SIGNING_KEY, **overrides) -> str:
    now = int(time.time())
    claims = {
        "iss": ISSUER, "aud": PROJECT, "sub": "uid-123", "iat": now, "exp": now + 3600,
        "auth_time": now, "email": "admin@example.com", "email_verified": True,
    }
    claims.update(overrides)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "test-kid"})


def verifier(**kwargs) -> FirebaseVerifier:
    return FirebaseVerifier(PROJECT, jwks_client=kwargs.pop("jwks", FakeJwks()), **kwargs)


def test_valid_token_returns_the_user():
    user = verifier().verify(make_token())

    assert user.uid == "uid-123"
    assert user.email == "admin@example.com"
    assert user.email_verified is True


def test_expired_token_is_rejected():
    token = make_token(iat=int(time.time()) - 7200, exp=int(time.time()) - 3600)

    with pytest.raises(UnauthorizedError):
        verifier().verify(token)


def test_token_for_another_firebase_project_is_rejected():
    with pytest.raises(UnauthorizedError):
        verifier().verify(make_token(aud="otro-proyecto", iss="https://securetoken.google.com/otro-proyecto"))


def test_token_with_wrong_issuer_is_rejected():
    with pytest.raises(UnauthorizedError):
        verifier().verify(make_token(iss="https://evil.example.com/" + PROJECT))


def test_token_signed_with_another_key_is_rejected():
    with pytest.raises(UnauthorizedError):
        verifier().verify(make_token(key=new_key()))


def test_token_without_subject_is_rejected():
    with pytest.raises(UnauthorizedError):
        verifier().verify(make_token(sub=None))


def test_token_without_expiration_is_rejected():
    with pytest.raises(UnauthorizedError):
        verifier().verify(make_token(exp=None))


def test_unsigned_token_is_rejected():
    forged = jwt.encode({"iss": ISSUER, "aud": PROJECT, "sub": "x", "exp": int(time.time()) + 60},
                        key=None, algorithm="none")

    with pytest.raises(UnauthorizedError):
        verifier().verify(forged)


def test_hs256_token_signed_with_the_public_key_is_rejected():
    """Ataque de confusión de algoritmo: solo se acepta RS256, aunque el HMAC use la llave pública."""
    public_pem = SIGNING_KEY.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    now = int(time.time())

    def b64(data: dict) -> bytes:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=")

    signing_input = b64({"alg": "HS256", "typ": "JWT", "kid": "test-kid"}) + b"." + b64(
        {"iss": ISSUER, "aud": PROJECT, "sub": "x", "iat": now, "exp": now + 60})
    signature = base64.urlsafe_b64encode(hmac.new(public_pem, signing_input, hashlib.sha256).digest()).rstrip(b"=")
    forged = (signing_input + b"." + signature).decode()

    with pytest.raises(UnauthorizedError):
        verifier().verify(forged)


def test_garbage_is_rejected():
    with pytest.raises(UnauthorizedError):
        verifier().verify("esto-no-es-un-jwt")


def test_unknown_key_id_is_rejected_as_unauthorized():
    jwks = FakeJwks(error=jwt.PyJWKClientError("Unable to find a signing key that matches kid"))

    with pytest.raises(UnauthorizedError):
        verifier(jwks=jwks).verify(make_token())


def test_failure_to_download_google_keys_is_not_reported_as_a_bad_token():
    jwks = FakeJwks(error=jwt.PyJWKClientConnectionError("sin red"))

    with pytest.raises(jwt.PyJWKClientConnectionError):
        verifier(jwks=jwks).verify(make_token())


def test_any_authenticated_user_is_accepted_without_an_allowlist():
    assert verifier().verify(make_token(email="cualquiera@example.com")).uid == "uid-123"


def test_user_in_the_allowlist_is_accepted_ignoring_case():
    allowed = parse_allowed_emails("Admin@Example.com, otro@example.com")

    assert verifier(allowed_emails=allowed).verify(make_token(email="ADMIN@example.com")).uid == "uid-123"


def test_authenticated_user_outside_the_allowlist_is_forbidden():
    allowed = parse_allowed_emails("admin@example.com")

    with pytest.raises(ForbiddenError):
        verifier(allowed_emails=allowed).verify(make_token(email="intruso@example.com"))


def test_token_without_email_is_forbidden_when_an_allowlist_exists():
    allowed = parse_allowed_emails("admin@example.com")

    with pytest.raises(ForbiddenError):
        verifier(allowed_emails=allowed).verify(make_token(email=None))


def test_parse_allowed_emails_ignores_blanks():
    assert parse_allowed_emails(None) == frozenset()
    assert parse_allowed_emails(" , ") == frozenset()
    assert parse_allowed_emails("a@x.com,,B@x.com ") == frozenset({"a@x.com", "b@x.com"})


def test_rejection_is_logged_without_the_token(caplog):
    token = make_token(key=new_key())

    with caplog.at_level(logging.WARNING, logger="app.core.firebase_auth"):
        with pytest.raises(UnauthorizedError):
            verifier().verify(token)

    assert "rechazado" in caplog.text
    assert token not in caplog.text
