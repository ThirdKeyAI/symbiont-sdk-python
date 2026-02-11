"""AgentPin integration for client-side credential verification and discovery.

Wraps the ``agentpin`` PyPI package directly — AgentPin is a client-side
cryptographic verification layer, not a Symbiont Runtime HTTP endpoint.

Typical usage::

    from symbiont import Client
    client = Client()

    # Generate keys
    private_key, public_key = client.agentpin.generate_key_pair()

    # Issue a credential
    jwt = client.agentpin.issue_credential(
        private_key_pem=private_key,
        kid=client.agentpin.generate_key_id(public_key),
        issuer="example.com",
        agent_id="agent-1",
        capabilities=["read:data", "write:data"],
    )

    # Verify online (fetches discovery document)
    result = client.agentpin.verify_credential(jwt)
"""

from typing import Any, Dict, List, Optional, Tuple

from agentpin import (
    Capability,
    KeyPinStore,
    VerificationResult,
    VerifierConfig,
    build_discovery_document,
    create_trust_bundle,
    fetch_discovery_document,
    generate_key_id,
    generate_key_pair,
    issue_credential,
    jwk_to_pem,
    load_trust_bundle,
    pem_to_jwk,
    save_trust_bundle,
    validate_discovery_document,
    verify_credential,
    verify_credential_offline,
    verify_credential_with_bundle,
)


class AgentPinClient:
    """Client-side AgentPin operations for credential verification and discovery.

    Unlike other Symbiont sub-clients, AgentPinClient does NOT make HTTP calls
    to the Symbiont Runtime. AgentPin is a client-side cryptographic verification
    layer that wraps the ``agentpin`` PyPI package directly.

    This class is typically accessed through the main ``Client`` instance::

        from symbiont import Client
        client = Client()
        result = client.agentpin.verify_credential(jwt_token)
    """

    def __init__(self, parent_client: Any) -> None:
        self._client = parent_client
        self._pin_store = KeyPinStore()

    # =========================================================================
    # Key Management
    # =========================================================================

    def generate_key_pair(self) -> Tuple[str, str]:
        """Generate an ECDSA P-256 key pair.

        Returns:
            Tuple of (private_key_pem, public_key_pem)
        """
        return generate_key_pair()

    def generate_key_id(self, public_key_pem: str) -> str:
        """Derive a key ID (SHA-256 hex) from a PEM-encoded public key.

        Args:
            public_key_pem: PEM-encoded public key

        Returns:
            Hex-encoded SHA-256 key ID
        """
        return generate_key_id(public_key_pem)

    # =========================================================================
    # Credential Issuance
    # =========================================================================

    def issue_credential(
        self,
        private_key_pem: str,
        kid: str,
        issuer: str,
        agent_id: str,
        capabilities: List[str],
        audience: Optional[str] = None,
        constraints: Optional[Dict[str, Any]] = None,
        delegation_chain: Optional[List[Any]] = None,
        ttl_secs: int = 3600,
    ) -> str:
        """Issue an ES256 JWT credential.

        Args:
            private_key_pem: PEM-encoded private key
            kid: Key ID
            issuer: Issuer domain
            agent_id: Agent identifier
            capabilities: List of capability strings (e.g. ``["read:data"]``)
            audience: Optional audience claim
            constraints: Optional constraint dict
            delegation_chain: Optional delegation chain
            ttl_secs: Time-to-live in seconds (default 3600)

        Returns:
            Compact JWT string
        """
        caps = [Capability(c) for c in capabilities]
        return issue_credential(
            private_key_pem,
            kid,
            issuer,
            agent_id,
            audience,
            caps,
            constraints,
            delegation_chain,
            ttl_secs,
        )

    # =========================================================================
    # Verification
    # =========================================================================

    def verify_credential(
        self,
        jwt: str,
        audience: Optional[str] = None,
        config: Optional[VerifierConfig] = None,
    ) -> VerificationResult:
        """Full 12-step online verification.

        Fetches the discovery document and optional revocation document
        from the issuer domain automatically.

        Args:
            jwt: Compact JWT credential string
            audience: Optional expected audience
            config: Optional verifier configuration

        Returns:
            VerificationResult with validation details
        """
        return verify_credential(jwt, self._pin_store, audience, config)

    def verify_credential_offline(
        self,
        jwt: str,
        discovery: Dict[str, Any],
        revocation: Optional[Dict[str, Any]] = None,
        pin_store: Optional[KeyPinStore] = None,
        audience: Optional[str] = None,
        config: Optional[VerifierConfig] = None,
    ) -> VerificationResult:
        """Offline verification with pre-fetched documents.

        Args:
            jwt: Compact JWT credential string
            discovery: Pre-fetched discovery document
            revocation: Optional pre-fetched revocation document
            pin_store: Optional key pin store (uses internal store if None)
            audience: Optional expected audience
            config: Optional verifier configuration

        Returns:
            VerificationResult with validation details
        """
        store = pin_store if pin_store is not None else self._pin_store
        return verify_credential_offline(
            jwt, discovery, revocation, store, audience, config
        )

    def verify_credential_with_bundle(
        self,
        jwt: str,
        bundle: Dict[str, Any],
        pin_store: Optional[KeyPinStore] = None,
        audience: Optional[str] = None,
        config: Optional[VerifierConfig] = None,
    ) -> VerificationResult:
        """Trust bundle-based verification (no network required).

        Args:
            jwt: Compact JWT credential string
            bundle: Trust bundle containing discovery and revocation documents
            pin_store: Optional key pin store (uses internal store if None)
            audience: Optional expected audience
            config: Optional verifier configuration

        Returns:
            VerificationResult with validation details
        """
        store = pin_store if pin_store is not None else self._pin_store
        return verify_credential_with_bundle(
            jwt, bundle, store, audience, config
        )

    # =========================================================================
    # Discovery
    # =========================================================================

    def fetch_discovery_document(self, domain: str) -> Dict[str, Any]:
        """Fetch a domain's ``.well-known/agent-identity.json`` discovery document.

        Args:
            domain: Domain to fetch from

        Returns:
            Discovery document as a dict
        """
        return fetch_discovery_document(domain)

    def build_discovery_document(
        self,
        entity: str,
        entity_type: str,
        public_keys: List[Dict[str, Any]],
        agents: List[Dict[str, Any]],
        max_delegation_depth: int,
    ) -> Dict[str, Any]:
        """Build a discovery document locally.

        Args:
            entity: Entity domain
            entity_type: Entity type (maker, deployer, both)
            public_keys: List of JWK public key dicts
            agents: List of agent declaration dicts
            max_delegation_depth: Maximum delegation chain depth

        Returns:
            Discovery document dict
        """
        return build_discovery_document(
            entity, entity_type, public_keys, agents, max_delegation_depth
        )

    def validate_discovery_document(
        self,
        doc: Dict[str, Any],
        expected_entity: str,
    ) -> None:
        """Validate a discovery document structure and entity match.

        Args:
            doc: Discovery document to validate
            expected_entity: Expected entity domain

        Raises:
            AgentPinError: On validation failure
        """
        validate_discovery_document(doc, expected_entity)

    # =========================================================================
    # Trust Bundles
    # =========================================================================

    def create_trust_bundle(self) -> Dict[str, Any]:
        """Create an empty trust bundle.

        Returns:
            Trust bundle dict
        """
        return create_trust_bundle()

    def load_trust_bundle(self, path: str) -> Dict[str, Any]:
        """Load a trust bundle from a JSON file.

        Args:
            path: File path to load from

        Returns:
            Trust bundle dict
        """
        return load_trust_bundle(path)

    def save_trust_bundle(self, bundle: Dict[str, Any], path: str) -> None:
        """Save a trust bundle to a JSON file.

        Args:
            bundle: Trust bundle to save
            path: File path to save to
        """
        save_trust_bundle(bundle, path)

    # =========================================================================
    # Key Pinning
    # =========================================================================

    @property
    def pin_store(self) -> KeyPinStore:
        """Access the internal TOFU key pin store."""
        return self._pin_store

    def create_pin_store(self) -> KeyPinStore:
        """Create a new TOFU key pin store.

        Returns:
            New KeyPinStore instance
        """
        return KeyPinStore()

    # =========================================================================
    # JWK Utilities
    # =========================================================================

    def pem_to_jwk(self, public_key_pem: str, kid: str) -> Dict[str, Any]:
        """Convert a PEM-encoded public key to JWK format.

        Args:
            public_key_pem: PEM-encoded public key
            kid: Key ID to include in the JWK

        Returns:
            JWK dict
        """
        return pem_to_jwk(public_key_pem, kid)

    def jwk_to_pem(self, jwk: Dict[str, Any]) -> str:
        """Convert a JWK to PEM-encoded public key.

        Args:
            jwk: JWK dict

        Returns:
            PEM-encoded public key string
        """
        return jwk_to_pem(jwk)
