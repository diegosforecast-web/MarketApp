from __future__ import annotations

from dataclasses import dataclass
from fastapi import Header, HTTPException, status
from services.supabase_service import SupabaseService


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    email: str | None


_supabase = SupabaseService()


def get_authenticated_user(
    authorization: str | None = Header(default=None),
) -> AuthenticatedUser:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication is required.")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid authorization header.")

    try:
        result = _supabase.client.auth.get_user(token)
        user = result.user
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The session is invalid or expired.",
        ) from exc

    if user is None:
        raise HTTPException(status_code=401, detail="Unable to resolve user.")

    return AuthenticatedUser(id=str(user.id), email=getattr(user, "email", None))
