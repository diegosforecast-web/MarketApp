from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import stripe

from services.supabase_service import SupabaseService


ACTIVE_SUBSCRIPTION_STATUSES = {
    "active",
    "trialing",
    "past_due",
}


class BillingService:
    def __init__(self) -> None:
        secret_key = os.getenv("STRIPE_SECRET_KEY")

        if not secret_key:
            raise RuntimeError("STRIPE_SECRET_KEY is not configured.")

        stripe.api_key = secret_key

        self.supabase = SupabaseService()
        self.frontend_url = os.getenv(
            "FRONTEND_URL",
            "http://127.0.0.1:5173",
        ).rstrip("/")

        self.price_by_plan = {
            "standard": os.getenv("STRIPE_STANDARD_PRICE_ID"),
            "premium": os.getenv("STRIPE_PREMIUM_PRICE_ID"),
            "gold": os.getenv("STRIPE_GOLD_PRICE_ID"),
        }

        self.plan_by_price = {
            price_id: plan
            for plan, price_id in self.price_by_plan.items()
            if price_id
        }

    @staticmethod
    def _value(
        obj: Any,
        key: str,
        default: Any = None,
    ) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)

        return getattr(obj, key, default)

    @staticmethod
    def _timestamp_to_iso(
        value: int | float | None,
    ) -> str | None:
        if value is None:
            return None

        return datetime.fromtimestamp(
            value,
            tz=timezone.utc,
        ).isoformat()

    def validate_configuration(self) -> None:
        missing = [
            plan
            for plan, price_id in self.price_by_plan.items()
            if not price_id
        ]

        if missing:
            raise RuntimeError(
                "Missing Stripe price IDs for: "
                + ", ".join(missing)
            )

    def create_checkout_session(
        self,
        *,
        user_id: str,
        email: str | None,
        plan: str,
    ) -> dict[str, str]:
        self.validate_configuration()

        normalized_plan = plan.strip().lower()

        if normalized_plan not in self.price_by_plan:
            raise ValueError(
                "Plan must be standard, premium, or gold."
            )

        profile = self.supabase.get_profile(user_id)

        if not profile:
            raise RuntimeError("User profile was not found.")

        # Existing subscribers should change plans through Stripe's portal,
        # which avoids accidentally creating a second subscription.
        if (
            profile.get("stripe_customer_id")
            and profile.get("stripe_subscription_id")
            and profile.get("subscription_status")
            in ACTIVE_SUBSCRIPTION_STATUSES
        ):
            portal = self.create_portal_session(user_id=user_id)
            return {
                "url": portal["url"],
                "mode": "portal",
            }

        customer_id = profile.get("stripe_customer_id")
        price_id = self.price_by_plan[normalized_plan]

        parameters: dict[str, Any] = {
            "mode": "subscription",
            "line_items": [
                {
                    "price": price_id,
                    "quantity": 1,
                }
            ],
            "success_url": (
                f"{self.frontend_url}/"
                "?billing=success"
                "&session_id={CHECKOUT_SESSION_ID}"
            ),
            "cancel_url": (
                f"{self.frontend_url}/"
                "?billing=cancelled"
            ),
            "allow_promotion_codes": True,
            "client_reference_id": user_id,
            "metadata": {
                "user_id": user_id,
                "plan": normalized_plan,
            },
            "subscription_data": {
                "metadata": {
                    "user_id": user_id,
                    "plan": normalized_plan,
                }
            },
        }

        if customer_id:
            parameters["customer"] = customer_id
        elif email:
            parameters["customer_email"] = email

        session = stripe.checkout.Session.create(
            **parameters
        )

        if not session.url:
            raise RuntimeError(
                "Stripe did not return a Checkout URL."
            )

        return {
            "url": session.url,
            "session_id": session.id,
            "mode": "checkout",
        }

    def create_portal_session(
        self,
        *,
        user_id: str,
    ) -> dict[str, str]:
        profile = self.supabase.get_profile(user_id)

        if not profile:
            raise RuntimeError("User profile was not found.")

        customer_id = profile.get("stripe_customer_id")

        if not customer_id:
            raise ValueError(
                "No Stripe billing account exists for this user yet."
            )

        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=(
                f"{self.frontend_url}/"
                "?billing=portal-return"
            ),
        )

        return {"url": session.url}

    def plan_for_price(
        self,
        price_id: str | None,
    ) -> str:
        return self.plan_by_price.get(
            price_id,
            "free",
        )

    def sync_subscription(
        self,
        subscription: Any,
        *,
        fallback_user_id: str | None = None,
        fallback_email: str | None = None,
    ) -> None:
        subscription_id = self._value(
            subscription,
            "id",
        )
        customer_id = self._value(
            subscription,
            "customer",
        )
        status = self._value(
            subscription,
            "status",
            "inactive",
        )
        metadata = self._value(
            subscription,
            "metadata",
            {},
        ) or {}

        items = self._value(
            subscription,
            "items",
        )
        item_data = self._value(
            items,
            "data",
            [],
        ) or []

        first_item = item_data[0] if item_data else None
        price = (
            self._value(first_item, "price")
            if first_item
            else None
        )
        price_id = (
            self._value(price, "id")
            if price
            else None
        )

        plan = self.plan_for_price(price_id)

        if status not in ACTIVE_SUBSCRIPTION_STATUSES:
            plan = "free"

        metadata_user_id = (
            metadata.get("user_id")
            if isinstance(metadata, dict)
            else None
        )
        user_id = metadata_user_id or fallback_user_id

        if not user_id and not fallback_email and customer_id:
            customer = stripe.Customer.retrieve(customer_id)
            fallback_email = self._value(customer, "email")

        current_period_start = self._timestamp_to_iso(
            self._value(
                subscription,
                "current_period_start",
            )
        )
        current_period_end = self._timestamp_to_iso(
            self._value(
                subscription,
                "current_period_end",
            )
        )

        if user_id:
            updated = self.supabase.update_subscription_by_user_id(
                user_id=user_id,
                plan=plan,
                subscription_status=status,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                stripe_price_id=price_id,
                current_period_start=current_period_start,
                current_period_end=current_period_end,
            )

            if updated:
                return

        if customer_id:
            updated = self.supabase.update_subscription_by_customer_id(
                stripe_customer_id=customer_id,
                plan=plan,
                subscription_status=status,
                stripe_subscription_id=subscription_id,
                stripe_price_id=price_id,
                current_period_start=current_period_start,
                current_period_end=current_period_end,
            )

            if updated:
                return

        if fallback_email:
            self.supabase.update_plan_by_email(
                email=fallback_email,
                plan=plan,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                stripe_price_id=price_id,
                subscription_status=status,
                current_period_start=current_period_start,
                current_period_end=current_period_end,
            )

    def handle_checkout_completed(
        self,
        session: Any,
    ) -> None:
        subscription_id = self._value(
            session,
            "subscription",
        )

        if not subscription_id:
            return

        metadata = self._value(
            session,
            "metadata",
            {},
        ) or {}

        user_id = (
            metadata.get("user_id")
            if isinstance(metadata, dict)
            else None
        ) or self._value(
            session,
            "client_reference_id",
        )

        customer_details = self._value(
            session,
            "customer_details",
        )
        email = (
            self._value(
                customer_details,
                "email",
            )
            if customer_details
            else None
        )

        subscription = stripe.Subscription.retrieve(
            subscription_id,
            expand=["items.data.price"],
        )

        self.sync_subscription(
            subscription,
            fallback_user_id=user_id,
            fallback_email=email,
        )

    def handle_subscription_event(
        self,
        subscription: Any,
    ) -> None:
        self.sync_subscription(subscription)

    def handle_invoice_event(
        self,
        invoice: Any,
    ) -> None:
        subscription_id = self._value(
            invoice,
            "subscription",
        )

        # Newer Stripe API versions can expose the subscription under
        # parent.subscription_details.subscription.
        if not subscription_id:
            parent = self._value(
                invoice,
                "parent",
                {},
            ) or {}
            subscription_details = self._value(
                parent,
                "subscription_details",
                {},
            ) or {}
            subscription_id = self._value(
                subscription_details,
                "subscription",
            )

        if not subscription_id:
            return

        subscription = stripe.Subscription.retrieve(
            subscription_id,
            expand=["items.data.price"],
        )

        self.sync_subscription(subscription)
