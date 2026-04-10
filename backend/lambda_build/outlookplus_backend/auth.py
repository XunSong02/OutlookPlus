from __future__ import annotations

from dataclasses import dataclass
from fastapi import Depends, HTTPException, Header

from outlookplus_backend.config import AuthConfig, load_auth_config
from outlookplus_backend.domain import UserId


class AuthError(Exception):
    pass


class AuthTokenVerifier:
    def verify(self, authorization_header: str) -> UserId:
        """Return UserId if header contains a valid Bearer token; raise AuthError otherwise."""
        raise NotImplementedError


@dataclass(frozen=True)
class DevAuthTokenVerifier(AuthTokenVerifier):
    config: AuthConfig

    def verify(self, authorization_header: str) -> UserId:
        if not authorization_header:
            raise AuthError("Missing Authorization header")
        if not authorization_header.startswith("Bearer "):
            raise AuthError("Expected Bearer token")
        token = authorization_header[len("Bearer ") :].strip()

        if token.startswith("dev:") and len(token) > 4:
            return token[4:]

        if self.config.dev_token and token == self.config.dev_token:
            if not self.config.dev_user_id:
                raise AuthError("OUTLOOKPLUS_DEV_USER_ID not set")
            return self.config.dev_user_id

        raise AuthError("Invalid token")


def get_auth_verifier(config: AuthConfig = Depends(load_auth_config)) -> AuthTokenVerifier:
    return DevAuthTokenVerifier(config=config)


def require_user_id(
    authorization: str | None = Header(default=None, alias="Authorization"),
    verifier: AuthTokenVerifier = Depends(get_auth_verifier),
    config: AuthConfig = Depends(load_auth_config),
) -> UserId:
    # Mode A: demo / no-auth.
    if (config.mode or "A").upper() == "A":
        return "demo"

    # Mode B: dev stub.
    try:
        return verifier.verify(authorization_header=authorization or "")
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
