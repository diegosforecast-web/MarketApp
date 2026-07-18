from __future__ import annotations

import base64
import json
import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from services.monitoring_service import monitoring_service


logger = logging.getLogger("dimarket.requests")


def _decode_jwt_subject(
    authorization: str | None,
) -> str | None:
    """
    Read the JWT subject only for request logging.

    This does not authenticate the request. Authentication remains the
    responsibility of the existing Supabase auth dependency.
    """
    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")

    if scheme.lower() != "bearer" or not token:
        return None

    parts = token.split(".")

    if len(parts) != 3:
        return None

    try:
        payload_segment = parts[1]
        padding = "=" * (-len(payload_segment) % 4)

        payload = json.loads(
            base64.urlsafe_b64decode(
                payload_segment + padding
            ).decode("utf-8")
        )

        subject = payload.get("sub")

        return str(subject) if subject else None

    except Exception:
        return None


def _safe_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    if request.client:
        return request.client.host

    return "unknown"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next,
    ) -> Response:
        request_id = (
            request.headers.get("x-request-id")
            or str(uuid.uuid4())
        )
        started_at = time.perf_counter()

        user_id = _decode_jwt_subject(
            request.headers.get("authorization")
        )
        client_ip = _safe_client_ip(request)

        request.state.request_id = request_id
        request.state.user_id = user_id

        try:
            response = await call_next(request)

        except Exception:
            elapsed_ms = (
                time.perf_counter() - started_at
            ) * 1000

            monitoring_service.record_request(
                status_code=500,
                duration_ms=elapsed_ms,
            )

            logger.exception(
                (
                    "request_failed "
                    "request_id=%s method=%s path=%s "
                    "status=500 duration_ms=%.2f "
                    "user_id=%s client_ip=%s"
                ),
                request_id,
                request.method,
                request.url.path,
                elapsed_ms,
                user_id or "anonymous",
                client_ip,
            )

            raise

        elapsed_ms = (
            time.perf_counter() - started_at
        ) * 1000

        monitoring_service.record_request(
            status_code=response.status_code,
            duration_ms=elapsed_ms,
        )

        response.headers["X-Request-ID"] = request_id

        log_method = (
            logger.warning
            if response.status_code >= 400
            else logger.info
        )

        log_method(
            (
                "request_complete "
                "request_id=%s method=%s path=%s "
                "status=%s duration_ms=%.2f "
                "user_id=%s client_ip=%s"
            ),
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            user_id or "anonymous",
            client_ip,
        )

        return response
