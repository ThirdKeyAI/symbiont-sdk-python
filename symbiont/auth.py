"""Authentication and authorization management for the Symbiont SDK."""

import hashlib
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

import jwt
from pydantic import BaseModel

from .config import AuthConfig


class AuthMethod(str, Enum):
    """Authentication method enumeration."""
    API_KEY = "api_key"
    JWT = "jwt"
    OAUTH2 = "oauth2"
    BASIC = "basic"


class TokenType(str, Enum):
    """Token type enumeration."""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"


class Permission(str, Enum):
    """Permission enumeration."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    EXECUTE = "execute"


class Role(BaseModel):
    """Role definition with permissions."""
    name: str
    permissions: Set[Permission]
    description: Optional[str] = None
    expires_at: Optional[datetime] = None


class AuthToken(BaseModel):
    """Authentication token model."""
    token: str
    token_type: TokenType
    expires_at: datetime
    issued_at: datetime
    user_id: str
    roles: List[str] = []
    permissions: Set[Permission] = set()
    metadata: Dict[str, Any] = {}


class AuthUser(BaseModel):
    """Authenticated user model."""
    user_id: str
    username: Optional[str] = None
    email: Optional[str] = None
    roles: List[str] = []
    permissions: Set[Permission] = set()
    is_active: bool = True
    last_login: Optional[datetime] = None
    metadata: Dict[str, Any] = {}


class AuthProvider(ABC):
    """Abstract base class for authentication providers."""

    @abstractmethod
    def authenticate(self, credentials: Dict[str, Any]) -> Optional[AuthUser]:
        """Authenticate user with provided credentials.

        Args:
            credentials: Authentication credentials

        Returns:
            AuthUser if authentication successful, None otherwise
        """
        pass

    @abstractmethod
    def validate_token(self, token: str) -> Optional[AuthUser]:
        """Validate authentication token.

        Args:
            token: Token to validate

        Returns:
            AuthUser if token is valid, None otherwise
        """
        pass


class JWTHandler:
    """JWT token handler for encoding and decoding tokens."""

    def __init__(self, config: AuthConfig):
        """Initialize JWT handler.

        Args:
            config: Authentication configuration
        """
        self.config = config
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate JWT configuration."""
        if not self.config.jwt_secret_key:
            raise ValueError("JWT secret key is required")
        if not self.config.jwt_algorithm:
            raise ValueError("JWT algorithm is required")

    def generate_token(self,
                      user_id: str,
                      roles: List[str] = None,
                      permissions: Set[Permission] = None,
                      token_type: TokenType = TokenType.ACCESS,
                      expires_in: Optional[int] = None) -> AuthToken:
        """Generate a JWT token.

        Args:
            user_id: User identifier
            roles: User roles
            permissions: User permissions
            token_type: Type of token to generate
            expires_in: Token expiration time in seconds

        Returns:
            AuthToken: Generated token
        """
        roles = roles or []
        permissions = permissions or set()

        # Determine expiration time
        if expires_in is None:
            if token_type == TokenType.REFRESH:
                expires_in = self.config.jwt_refresh_expiration_seconds
            else:
                expires_in = self.config.jwt_expiration_seconds

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=expires_in)

        # Create payload
        payload = {
            'sub': user_id,
            'iat': int(now.timestamp()),
            'exp': int(expires_at.timestamp()),
            'iss': self.config.token_issuer,
            'aud': self.config.token_audience,
            'type': token_type.value,
            'roles': roles,
            'permissions': [p.value for p in permissions] if permissions else []
        }

        # Generate token
        token = jwt.encode(
            payload,
            self.config.jwt_secret_key,
            algorithm=self.config.jwt_algorithm
        )

        return AuthToken(
            token=token,
            token_type=token_type,
            expires_at=expires_at,
            issued_at=now,
            user_id=user_id,
            roles=roles,
            permissions=permissions
        )

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode and validate a JWT token.

        Args:
            token: JWT token to decode

        Returns:
            Token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self.config.jwt_secret_key,
                algorithms=[self.config.jwt_algorithm],
                issuer=self.config.token_issuer,
                audience=self.config.token_audience
            )
            return payload
        except jwt.InvalidTokenError:
            return None

    def refresh_token(self, refresh_token: str) -> Optional[AuthToken]:
        """Refresh an access token using a refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New access token if refresh successful, None otherwise
        """
        if not self.config.enable_refresh_tokens:
            return None

        payload = self.decode_token(refresh_token)
        if not payload or payload.get('type') != TokenType.REFRESH.value:
            return None

        # Generate new access token
        permissions = {Permission(p) for p in payload.get('permissions', [])}
        return self.generate_token(
            user_id=payload['sub'],
            roles=payload.get('roles', []),
            permissions=permissions,
            token_type=TokenType.ACCESS
        )


class TokenValidator:
    """Token validation and management."""

    def __init__(self, jwt_handler: JWTHandler):
        """Initialize token validator.

        Args:
            jwt_handler: JWT handler instance
        """
        self.jwt_handler = jwt_handler
        self._blacklisted_tokens: Set[str] = set()

    def validate_token(self, token: str) -> Optional[AuthUser]:
        """Validate a token and return user information.

        Args:
            token: Token to validate

        Returns:
            AuthUser if token is valid, None otherwise
        """
        if token in self._blacklisted_tokens:
            return None

        payload = self.jwt_handler.decode_token(token)
        if not payload:
            return None

        # Convert permissions back to enum
        permissions = {Permission(p) for p in payload.get('permissions', [])}

        return AuthUser(
            user_id=payload['sub'],
            roles=payload.get('roles', []),
            permissions=permissions,
            last_login=datetime.now(timezone.utc)
        )

    def blacklist_token(self, token: str) -> None:
        """Add token to blacklist.

        Args:
            token: Token to blacklist
        """
        self._blacklisted_tokens.add(token)

    def is_token_blacklisted(self, token: str) -> bool:
        """Check if token is blacklisted.

        Args:
            token: Token to check

        Returns:
            True if blacklisted, False otherwise
        """
        return token in self._blacklisted_tokens


class RoleManager:
    """Role and permission management."""

    def __init__(self):
        """Initialize role manager."""
        self._roles: Dict[str, Role] = {}
        self._setup_default_roles()

    def _setup_default_roles(self) -> None:
        """Set up default system roles."""
        default_roles = [
            Role(
                name="admin",
                permissions={Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN, Permission.EXECUTE},
                description="Full system access"
            ),
            Role(
                name="user",
                permissions={Permission.READ, Permission.WRITE, Permission.EXECUTE},
                description="Standard user access"
            ),
            Role(
                name="readonly",
                permissions={Permission.READ},
                description="Read-only access"
            )
        ]

        for role in default_roles:
            self._roles[role.name] = role

    def create_role(self, role: Role) -> None:
        """Create a new role.

        Args:
            role: Role to create
        """
        self._roles[role.name] = role

    def get_role(self, role_name: str) -> Optional[Role]:
        """Get role by name.

        Args:
            role_name: Name of the role

        Returns:
            Role if found, None otherwise
        """
        return self._roles.get(role_name)

    def get_permissions_for_roles(self, role_names: List[str]) -> Set[Permission]:
        """Get combined permissions for multiple roles.

        Args:
            role_names: List of role names

        Returns:
            Combined set of permissions
        """
        permissions = set()
        for role_name in role_names:
            role = self.get_role(role_name)
            if role:
                permissions.update(role.permissions)
        return permissions

    def has_permission(self, user_roles: List[str], required_permission: Permission) -> bool:
        """Check if user has required permission.

        Args:
            user_roles: User's roles
            required_permission: Required permission

        Returns:
            True if user has permission, False otherwise
        """
        user_permissions = self.get_permissions_for_roles(user_roles)
        return required_permission in user_permissions or Permission.ADMIN in user_permissions


class AuthManager:
    """Main authentication manager."""

    def __init__(self, config: AuthConfig):
        """Initialize authentication manager.

        Args:
            config: Authentication configuration
        """
        self.config = config
        self.jwt_handler = JWTHandler(config)
        self.token_validator = TokenValidator(self.jwt_handler)
        self.role_manager = RoleManager()
        self._auth_providers: Dict[str, AuthProvider] = {}

    def register_auth_provider(self, name: str, provider: AuthProvider) -> None:
        """Register an authentication provider.

        Args:
            name: Provider name
            provider: Authentication provider instance
        """
        self._auth_providers[name] = provider

    def authenticate_with_api_key(self, api_key: str) -> Optional[AuthUser]:
        """Authenticate using API key.

        Args:
            api_key: API key for authentication

        Returns:
            AuthUser if authentication successful, None otherwise
        """
        # Simple API key validation (in production, this would check against a database)
        if api_key:
            # Generate a simple user from API key
            user_id = hashlib.sha256(api_key.encode()).hexdigest()[:16]
            return AuthUser(
                user_id=user_id,
                roles=["user"],
                permissions=self.role_manager.get_permissions_for_roles(["user"]),
                last_login=datetime.now(timezone.utc)
            )
        return None

    def authenticate_with_jwt(self, token: str) -> Optional[AuthUser]:
        """Authenticate using JWT token.

        Args:
            token: JWT token for authentication

        Returns:
            AuthUser if authentication successful, None otherwise
        """
        return self.token_validator.validate_token(token)

    def authenticate(self, method: AuthMethod, credentials: Dict[str, Any]) -> Optional[AuthUser]:
        """Authenticate user with specified method and credentials.

        Args:
            method: Authentication method
            credentials: Authentication credentials

        Returns:
            AuthUser if authentication successful, None otherwise
        """
        if method == AuthMethod.API_KEY:
            api_key = credentials.get('api_key')
            return self.authenticate_with_api_key(api_key)
        elif method == AuthMethod.JWT:
            token = credentials.get('token')
            return self.authenticate_with_jwt(token)
        else:
            # Try registered providers
            for provider in self._auth_providers.values():
                user = provider.authenticate(credentials)
                if user:
                    return user

        return None

    def generate_tokens(self, user: AuthUser) -> Dict[str, AuthToken]:
        """Generate access and refresh tokens for a user.

        Args:
            user: Authenticated user

        Returns:
            Dictionary containing access and optionally refresh tokens
        """
        tokens = {}

        # Generate access token
        access_token = self.jwt_handler.generate_token(
            user_id=user.user_id,
            roles=user.roles,
            permissions=user.permissions,
            token_type=TokenType.ACCESS
        )
        tokens['access'] = access_token

        # Generate refresh token if enabled
        if self.config.enable_refresh_tokens:
            refresh_token = self.jwt_handler.generate_token(
                user_id=user.user_id,
                roles=user.roles,
                permissions=user.permissions,
                token_type=TokenType.REFRESH
            )
            tokens['refresh'] = refresh_token

        return tokens

    def refresh_access_token(self, refresh_token: str) -> Optional[AuthToken]:
        """Refresh access token using refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New access token if successful, None otherwise
        """
        return self.jwt_handler.refresh_token(refresh_token)

    def validate_permissions(self, user: AuthUser, action: str, resource: str = None) -> bool:
        """Validate if user has permission for a specific action.

        Args:
            user: User to check permissions for
            action: Action to validate (maps to Permission)
            resource: Optional resource identifier

        Returns:
            True if user has permission, False otherwise
        """
        try:
            permission = Permission(action.lower())
            return self.role_manager.has_permission(user.roles, permission)
        except ValueError:
            # Unknown permission, deny by default
            return False

    def logout(self, token: str) -> None:
        """Logout user by blacklisting their token.

        Args:
            token: Token to blacklist
        """
        self.token_validator.blacklist_token(token)

    def create_role(self, role: Role) -> None:
        """Create a new role.

        Args:
            role: Role to create
        """
        self.role_manager.create_role(role)

    def get_user_roles(self, user: AuthUser) -> List[str]:
        """Get user's role names.

        Args:
            user: User to get roles for

        Returns:
            List of role names
        """
        return user.roles

    def get_user_permissions(self, user: AuthUser) -> Set[Permission]:
        """Get user's effective permissions.

        Args:
            user: User to get permissions for

        Returns:
            Set of permissions
        """
        return self.role_manager.get_permissions_for_roles(user.roles)
