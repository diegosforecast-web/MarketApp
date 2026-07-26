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

# Final Integration Status

Milestone 2 was completed, reviewed, and merged into `main`.

## Integration Record

- Pull request: #2
- Feature branch: `feature/milestone-2-internal-testing`
- Final feature-branch commit:
  `642b3bca741bbc371b564427ba0dd020714cc8b1`
- Verified merge commit:
  `39b6f039087a8cd389e1a7a397ebd3dcd5242f77`
- Repository status after merge:
  - Branch: `main`
  - Synchronized with `origin/main`
  - Working tree clean

## Final Verification

Run from:

`src/MarketApp/backend`

Full backend suite:

`python -m pytest -q`

Result:

`52 passed, 14 skipped, 5 warnings`

Internal toolkit suite:

`python -m pytest -q tests/test_subscription_toolkit.py`

Result:

`7 passed`

Frontend verification:

- `npm ci` completed successfully.
- Production build completed successfully.

## Engineering Decision

Milestone 2 is approved and closed.

Milestone 3 may begin from:

`39b6f039087a8cd389e1a7a397ebd3dcd5242f77`

## Future Hardening

Add explicit automated regression coverage for the supported
`ENVIRONMENT=prod` alias.

This is a future hardening improvement and does not block Milestone 3.