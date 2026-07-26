# Milestone 2 — Internal Subscription Testing Toolkit

This toolkit is additive developer infrastructure. It does not alter Stripe checkout, portal, webhook, pricing, or customer-profile persistence.

## Activation

The backend requires all of the following:

- `ENVIRONMENT` is not `production` or `prod`.
- `ENABLE_INTERNAL_TESTING=true`.
- A matching `X-DiMarket-Internal-Token` for administrative routes.
- A matching `X-DiMarket-QA-Token` for QA-session creation and QA authorization.

Production always responds with `404 Not found`, even when testing flags are accidentally supplied.

The frontend panel additionally requires a Vite development build and `VITE_ENABLE_INTERNAL_TESTING=true`. Because it checks `import.meta.env.DEV`, it cannot render in a production Vite build.

## Routes

All routes are excluded from OpenAPI and mounted under `/internal/subscriptions`:

- `PUT /override` — apply Free, Pro, Expired, Trial, or Cancelled.
- `DELETE /override/{user_id}` — clear a developer override.
- `POST /simulate` — simulate new subscription, renewal, cancellation, expiration, failed payment, trial expiration, downgrade, or upgrade.
- `POST /qa/session` — create a synthetic `qa:<session>` identity without changing a customer account.
- `POST /reset` — remove local overrides, simulations, clocks, and test metadata in one operation.
- `POST /stripe-test-clock` — create a Stripe Test Clock when explicitly enabled with an `sk_test_` key.
- `POST /stripe-test-clock/advance` — advance an existing test clock.

## Storage and reset

Temporary state is stored in `INTERNAL_TESTING_STATE_PATH` (default `/tmp/dimarket_subscription_testing.json`) using atomic file replacement. It contains no Stripe secrets and no production customer mutation. Resetting all state replaces the file with an empty baseline.

## QA authentication

QA authentication uses `Authorization: QA <session_id>` plus `X-DiMarket-QA-Token`. It is a separate authentication scheme from customer Bearer tokens. Synthetic QA users bypass Supabase profile repair and subscription-usage writes.

## Stripe Test Clocks

Test Clock operations are disabled unless `ENABLE_STRIPE_TEST_CLOCKS=true`, the Stripe key starts with `sk_test_`, and the installed Stripe SDK exposes Test Clocks. Unavailable environments receive a controlled `503`; production Stripe behavior is untouched.
