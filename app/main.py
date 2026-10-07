from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.database import create_tables
from app.routes import certificates, jobs

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
BASE_DIR = Path(__file__).resolve().parent.parent
GENERATED_DIR = Path(os.getenv("GENERATED_DIR", str(BASE_DIR / "generated")))


@asynccontextmanager
async def lifespan(app: FastAPI):
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    create_tables()
    app.state.generated_dir = GENERATED_DIR
    yield


app = FastAPI(title="Bulk Certificate Generator", version="1.0.0", lifespan=lifespan)
app.include_router(jobs.router)
app.include_router(certificates.router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
