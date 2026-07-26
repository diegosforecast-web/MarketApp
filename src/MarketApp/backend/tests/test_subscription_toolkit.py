from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from internal_testing.security import require_internal_admin
from internal_testing.subscription_toolkit import SubscriptionTestingToolkit


class SubscriptionToolkitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tempdir.name) / "state.json")
        self.environment = patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "development",
                "ENABLE_INTERNAL_TESTING": "true",
                "INTERNAL_TESTING_ADMIN_TOKEN": "admin-secret",
                "INTERNAL_TESTING_QA_TOKEN": "qa-secret",
                "INTERNAL_TESTING_STATE_PATH": self.path,
            },
            clear=False,
        )
        self.environment.start()
        self.toolkit = SubscriptionTestingToolkit(self.path)

    def tearDown(self) -> None:
        self.environment.stop()
        self.tempdir.cleanup()

    def test_developer_override_changes_effective_state_immediately(self) -> None:
        saved = self.toolkit.set_override(user_id="user-1", state="trial", actor="admin")
        effective = self.toolkit.get_effective_snapshot("user-1")
        self.assertEqual(saved["plan"], "premium")
        self.assertEqual(effective["subscription_status"], "trialing")

    def test_simulator_supports_all_required_events(self) -> None:
        for event in (
            "new_subscription", "renewal", "cancellation", "expiration",
            "failed_payment", "trial_expiration", "downgrade", "upgrade",
        ):
            result = self.toolkit.simulate_event(
                user_id=f"user-{event}", event=event, plan="premium", actor="admin"
            )
            self.assertEqual(result["scenario"], event)

    def test_inactive_events_remove_paid_feature_access(self) -> None:
        for event in ("cancellation", "expiration", "trial_expiration"):
            result = self.toolkit.simulate_event(
                user_id=event, event=event, plan="gold", actor="admin"
            )
            self.assertEqual(result["plan"], "free")

    def test_failed_payment_preserves_paid_plan_for_existing_grace_behavior(self) -> None:
        self.toolkit.simulate_event(
            user_id="grace", event="new_subscription", plan="premium", actor="admin"
        )
        result = self.toolkit.simulate_event(
            user_id="grace", event="failed_payment", plan="premium", actor="admin"
        )
        self.assertEqual(result["plan"], "premium")
        self.assertEqual(result["subscription_status"], "past_due")

    def test_reset_removes_all_local_testing_artifacts(self) -> None:
        self.toolkit.set_override(user_id="user-1", state="pro", actor="admin")
        self.toolkit.simulate_event(
            user_id="user-2", event="upgrade", plan="gold", actor="admin"
        )
        counts = self.toolkit.reset()
        self.assertEqual(counts["overrides"], 1)
        self.assertEqual(counts["simulations"], 1)
        payload = json.loads(Path(self.path).read_text(encoding="utf-8"))
        self.assertEqual(payload["overrides"], {})
        self.assertEqual(payload["simulations"], {})

    def test_production_hard_disables_toolkit_even_if_flag_is_true(self) -> None:
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "ENABLE_INTERNAL_TESTING": "true"}):
            production_toolkit = SubscriptionTestingToolkit(self.path)
            with self.assertRaises(RuntimeError):
                production_toolkit.set_override(user_id="user", state="pro", actor="admin")
            self.assertIsNone(production_toolkit.get_effective_snapshot("user"))

    def test_production_admin_route_is_concealed(self) -> None:
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "ENABLE_INTERNAL_TESTING": "true"}):
            with self.assertRaises(HTTPException) as context:
                require_internal_admin("admin-secret")
            self.assertEqual(context.exception.status_code, 404)



if __name__ == "__main__":
    unittest.main()
