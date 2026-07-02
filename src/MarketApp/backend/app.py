from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import stripe

from endpoints.compare_models import router as compare_models_router

# -----------------------------
# STRIPE CONFIG
# -----------------------------
import os
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = "whsec_LbnUDCYZZZOJOauIufJgrxiHSUPmdS6z"

# -----------------------------
# IN-MEMORY USER STORAGE (TEMP)
# -----------------------------
USER_PLANS = {}

def save_user_plan(email, plan):
    USER_PLANS[email] = plan

def get_user_plan(email):
    return USER_PLANS.get(email, "free")

# -----------------------------
# APP INIT
# -----------------------------
app = FastAPI(
    title="MarketApp Backend",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(compare_models_router, prefix="/api/v1")

# -----------------------------
# BASIC ROUTES
# -----------------------------
@app.get("/")
def root():
    return {
        "service": "MarketApp Backend",
        "status": "running"
    }

@app.get("/health")
def health():
    return {
        "status": "ok"
    }

# -----------------------------
# ✅ STRIPE WEBHOOK
# -----------------------------
@app.post("/stripe-webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, WEBHOOK_SECRET
        )
    except Exception as e:
        return {"error": str(e)}

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        # ✅ Updated Stripe format
        email = session["customer_details"]["email"]
        amount = session["amount_total"]

        # ✅ match your plans
        if amount == 999:       # $9.99
            plan = "standard"
        elif amount == 1700:    # $17
            plan = "premium"
        elif amount == 4999:    # $49.99
            plan = "gold"
        else:
            plan = "free"

        save_user_plan(email, plan)

        print(f"✅ User upgraded: {email} → {plan}")

    return {"status": "success"}

# -----------------------------
# ✅ GET USER PLAN (FOR STREAMLIT)
# -----------------------------
@app.get("/user-plan")
def user_plan(email: str):
    return {
        "email": email,
        "plan": get_user_plan(email)
    }
