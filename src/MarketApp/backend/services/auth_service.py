from __future__ import annotations

from dataclasses import dataclass
import hmac
from fastapi import Header, HTTPException, status

from internal_testing.environment import load_internal_testing_settings
from services.supabase_service import SupabaseService


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    email: str | None


_supabase = SupabaseService()


def get_authenticated_user(
    authorization: str | None = Header(default=None),
    x_dimarket_qa_token: str | None = Header(default=None),
) -> AuthenticatedUser:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication is required.")

    scheme, _, token = authorization.partition(" ")

    # QA identities are synthetic and accepted only when the explicit
    # non-production testing toolkit is enabled. They never resolve through
    # Supabase Auth and therefore cannot mutate a customer account.
    if scheme.lower() == "qa" and token:
        settings = load_internal_testing_settings()
        if (
            settings.enabled
            and not settings.is_production
            and settings.qa_token
            and x_dimarket_qa_token
            and hmac.compare_digest(x_dimarket_qa_token, settings.qa_token)
        ):
            return AuthenticatedUser(id=f"qa:{token}", email=None)
        raise HTTPException(status_code=401, detail="QA authentication is disabled.")

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
