"""Tests for the webhook verification module."""

import hashlib
import hmac
import time

import jwt
import pytest

from symbiont.exceptions import WebhookVerificationError
from symbiont.webhooks import (
    HmacVerifier,
    JwtVerifier,
    WebhookProvider,
)

SECRET = b"test-secret-key"
BODY = b'{"event": "push"}'


def _hmac_sig(secret: bytes, body: bytes) -> str:
    return hmac.new(secret, body, hashlib.sha256).hexdigest()


class TestHmacVerifier:
    """Tests for HmacVerifier."""

    def test_valid_hmac(self):
        """Valid HMAC signature passes verification."""
        sig = _hmac_sig(SECRET, BODY)
        verifier = HmacVerifier(secret=SECRET, header_name="X-Signature")
        verifier.verify({"X-Signature": sig}, BODY)

    def test_hmac_with_prefix(self):
        """HMAC with prefix (e.g. sha256=) is stripped correctly."""
        sig = _hmac_sig(SECRET, BODY)
        verifier = HmacVerifier(
            secret=SECRET, header_name="X-Hub-Signature-256", prefix="sha256="
        )
        verifier.verify({"X-Hub-Signature-256": f"sha256={sig}"}, BODY)

    def test_invalid_signature(self):
        """Wrong signature raises WebhookVerificationError."""
        verifier = HmacVerifier(secret=SECRET, header_name="X-Signature")
        with pytest.raises(WebhookVerificationError, match="mismatch"):
            verifier.verify({"X-Signature": "bad"}, BODY)

    def test_missing_header(self):
        """Missing header raises WebhookVerificationError."""
        verifier = HmacVerifier(secret=SECRET, header_name="X-Signature")
        with pytest.raises(WebhookVerificationError, match="Missing"):
            verifier.verify({}, BODY)

    def test_case_insensitive_header(self):
        """Header lookup is case-insensitive."""
        sig = _hmac_sig(SECRET, BODY)
        verifier = HmacVerifier(secret=SECRET, header_name="X-Signature")
        verifier.verify({"x-signature": sig}, BODY)


class TestJwtVerifier:
    """Tests for JwtVerifier."""

    def test_valid_jwt(self):
        """Valid JWT passes verification."""
        token = jwt.encode(
            {"sub": "test", "exp": time.time() + 3600},
            SECRET,
            algorithm="HS256",
        )
        verifier = JwtVerifier(secret=SECRET, header_name="Authorization")
        verifier.verify({"Authorization": f"Bearer {token}"}, BODY)

    def test_expired_jwt(self):
        """Expired JWT raises WebhookVerificationError."""
        token = jwt.encode(
            {"sub": "test", "exp": time.time() - 3600},
            SECRET,
            algorithm="HS256",
        )
        verifier = JwtVerifier(secret=SECRET, header_name="Authorization")
        with pytest.raises(WebhookVerificationError, match="expired"):
            verifier.verify({"Authorization": f"Bearer {token}"}, BODY)


class TestWebhookProvider:
    """Tests for WebhookProvider factory."""

    def test_github_preset(self):
        """GitHub provider creates a verifier with the right header and prefix."""
        sig = _hmac_sig(SECRET, BODY)
        verifier = WebhookProvider.GITHUB.verifier(SECRET)
        verifier.verify({"X-Hub-Signature-256": f"sha256={sig}"}, BODY)
