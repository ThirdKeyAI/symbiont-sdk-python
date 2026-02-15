"""Webhook signature verification for the Symbiont SDK.

Provides HMAC and JWT based webhook verification, ported from
the Rust runtime's webhook_verify module.
"""

import hashlib
import hmac
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Optional

import jwt

from .exceptions import WebhookVerificationError


class SignatureVerifier(ABC):
    """Abstract base class for webhook signature verifiers."""

    @abstractmethod
    def verify(self, headers: Dict[str, str], body: bytes) -> None:
        """Verify the webhook signature.

        Args:
            headers: HTTP request headers.
            body: Raw request body bytes.

        Raises:
            WebhookVerificationError: If verification fails.
        """


class HmacVerifier(SignatureVerifier):
    """HMAC-SHA256 webhook signature verifier."""

    def __init__(
        self,
        secret: bytes,
        header_name: str,
        prefix: Optional[str] = None,
    ) -> None:
        self._secret = secret
        self._header_name = header_name.lower()
        self._prefix = prefix

    def _find_header(self, headers: Dict[str, str]) -> str:
        """Case-insensitive header lookup."""
        for key, value in headers.items():
            if key.lower() == self._header_name:
                return value
        raise WebhookVerificationError(
            f"Missing signature header: {self._header_name}",
            header_name=self._header_name,
        )

    def verify(self, headers: Dict[str, str], body: bytes) -> None:
        sig_value = self._find_header(headers)

        # Strip prefix if configured
        if self._prefix and sig_value.startswith(self._prefix):
            sig_value = sig_value[len(self._prefix):]

        # Compute expected HMAC
        expected = hmac.new(self._secret, body, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(expected, sig_value):
            raise WebhookVerificationError(
                "HMAC signature mismatch",
                header_name=self._header_name,
            )


class JwtVerifier(SignatureVerifier):
    """JWT-based webhook signature verifier."""

    def __init__(
        self,
        secret: bytes,
        header_name: str,
        required_issuer: Optional[str] = None,
    ) -> None:
        self._secret = secret
        self._header_name = header_name.lower()
        self._required_issuer = required_issuer

    def _find_header(self, headers: Dict[str, str]) -> str:
        for key, value in headers.items():
            if key.lower() == self._header_name:
                return value
        raise WebhookVerificationError(
            f"Missing JWT header: {self._header_name}",
            header_name=self._header_name,
        )

    def verify(self, headers: Dict[str, str], body: bytes) -> None:
        token = self._find_header(headers)

        # Strip Bearer prefix
        if token.startswith("Bearer "):
            token = token[7:]

        decode_options = {"algorithms": ["HS256"]}
        if self._required_issuer:
            decode_options["issuer"] = self._required_issuer

        try:
            jwt.decode(token, self._secret, **decode_options)
        except jwt.ExpiredSignatureError as exc:
            raise WebhookVerificationError(
                "JWT token has expired",
                header_name=self._header_name,
            ) from exc
        except jwt.InvalidIssuerError as exc:
            raise WebhookVerificationError(
                "JWT issuer mismatch",
                header_name=self._header_name,
            ) from exc
        except jwt.PyJWTError as exc:
            raise WebhookVerificationError(
                f"JWT verification failed: {exc}",
                header_name=self._header_name,
            ) from exc


class WebhookProvider(Enum):
    """Pre-configured webhook providers with known header names and prefixes."""

    GITHUB = ("X-Hub-Signature-256", "sha256=")
    STRIPE = ("Stripe-Signature", None)
    SLACK = ("X-Slack-Signature", "v0=")
    CUSTOM = ("X-Signature", None)

    def __init__(self, header_name: str, prefix: Optional[str]) -> None:
        self._header_name = header_name
        self._prefix = prefix

    def verifier(self, secret: bytes) -> SignatureVerifier:
        """Create an HMAC verifier configured for this provider.

        Args:
            secret: The shared secret for HMAC verification.

        Returns:
            A configured HmacVerifier instance.
        """
        return HmacVerifier(
            secret=secret,
            header_name=self._header_name,
            prefix=self._prefix,
        )
