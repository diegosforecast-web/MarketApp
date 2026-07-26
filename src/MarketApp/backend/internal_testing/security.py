from __future__ import annotations

import hmac

from fastapi import Header, HTTPException

from internal_testing.environment import load_internal_testing_settings


def _secure_match(provided: str | None, expected: str | None) -> bool:
    return bool(provided and expected and hmac.compare_digest(provided, expected))


def require_internal_admin(
    x_dimarket_internal_token: str | None = Header(default=None),
) -> str:
    settings = load_internal_testing_settings()
    if settings.is_production or not settings.enabled:
        raise HTTPException(status_code=404, detail="Not found.")
    if not _secure_match(x_dimarket_internal_token, settings.admin_token):
        raise HTTPException(status_code=403, detail="Internal administrator authorization is required.")
    return "internal-admin"


def require_qa_token(
    x_dimarket_qa_token: str | None = Header(default=None),
) -> str:
    settings = load_internal_testing_settings()
    if settings.is_production or not settings.enabled:
        raise HTTPException(status_code=404, detail="Not found.")
    if not _secure_match(x_dimarket_qa_token, settings.qa_token):
        raise HTTPException(status_code=403, detail="QA authorization is required.")
    return "qa"
