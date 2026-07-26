from __future__ import annotations

import os
from dataclasses import dataclass


PRODUCTION_NAMES = {"production", "prod"}


@dataclass(frozen=True)
class InternalTestingSettings:
    environment: str
    enabled: bool
    admin_token: str | None
    qa_token: str | None
    state_path: str

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() in PRODUCTION_NAMES


def load_internal_testing_settings() -> InternalTestingSettings:
    environment = os.getenv("ENVIRONMENT", "development")
    requested = os.getenv("ENABLE_INTERNAL_TESTING", "false").strip().lower() in {
        "1", "true", "yes", "on"
    }
    is_production = environment.strip().lower() in PRODUCTION_NAMES
    return InternalTestingSettings(
        environment=environment,
        enabled=requested and not is_production,
        admin_token=os.getenv("INTERNAL_TESTING_ADMIN_TOKEN") or None,
        qa_token=os.getenv("INTERNAL_TESTING_QA_TOKEN") or None,
        state_path=os.getenv(
            "INTERNAL_TESTING_STATE_PATH",
            "/tmp/dimarket_subscription_testing.json",
        ),
    )
