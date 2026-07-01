from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from endpoints.compare_models import router as compare_models_router

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
