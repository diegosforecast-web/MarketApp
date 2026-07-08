import os

import stripe
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from endpoints.forecast import router as forecast_router


stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.getenv(
    "STRIPE_WEBHOOK_SECRET",
    "whsec_LbnUDCYZZZOJOauIufJgrxiHSUPmdS6z",
)


USER_PLANS = {}


def save_user_plan(
    email: str,
    plan: str,
) -> None:
    USER_PLANS[email] = plan


def get_user_plan(
    email: str,
) -> str:
    return USER_PLANS.get(
        email,
        "free",
    )


app = FastAPI(
    title="DiMarket Backend",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    forecast_router,
    prefix="/forecast",
    tags=["Forecast"],
)


@app.get("/")
def root():
    return {
        "service": "DiMarket Backend",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
    }


@app.post("/stripe-webhook")
async def stripe_webhook(
    request: Request,
):
    payload = await request.body()
    sig_header = request.headers.get(
        "stripe-signature"
    )

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            WEBHOOK_SECRET,
        )
    except Exception as exc:
        return {
            "error": str(exc),
        }

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        email = session["customer_details"]["email"]
        amount = session["amount_total"]

        if amount == 999:
            plan = "standard"
        elif amount == 1700:
            plan = "premium"
        elif amount == 4999:
            plan = "gold"
        else:
            plan = "free"

        save_user_plan(
            email,
            plan,
        )

        print(
            f"User upgraded: {email} -> {plan}"
        )

    return {
        "status": "success",
    }


@app.get("/user-plan")
def user_plan(
    email: str,
):
    return {
        "email": email,
        "plan": get_user_plan(email),
    }