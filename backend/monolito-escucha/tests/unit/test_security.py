"""Unit tests for the node token hashing helper."""
import re

from app.core.security import hash_token


def test_hash_is_sha256_hex_digest():
    digest = hash_token("abc")

    assert re.fullmatch(r"[0-9a-f]{64}", digest)
    # Known SHA-256 test vector, so the algorithm cannot drift silently.
    assert digest == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_hash_is_deterministic_for_the_same_token():
    assert hash_token("node-token") == hash_token("node-token")


def test_different_tokens_produce_different_hashes():
    assert hash_token("token-a") != hash_token("token-b")


def test_hash_does_not_contain_the_plain_token():
    token = "super-secret-node-token"

    assert token not in hash_token(token)
