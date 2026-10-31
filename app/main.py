from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import Base, engine
from .routers import assets, auth, coach, money

settings = get_settings()
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FinCoach",
    description="Educational personal finance for beginners in India. Not a regulated adviser.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_origin,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(money.router)
app.include_router(assets.router)
app.include_router(coach.router)


@app.get("/api/health")
def health():
    return {"ok": True, "product": "FinCoach", "role": "educational"}
