from __future__ import annotations

import asyncio
import pytest
import httpx
import anyio.to_thread
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.routes import jobs


class SyncASGIClient:
    def __init__(self, application):
        self.application = application

    def request(self, method, url, **kwargs):
        async def send():
            original_run_sync = anyio.to_thread.run_sync

            async def run_sync_without_worker(func, *args, **run_kwargs):
                # The managed test runtime cannot create worker threads. This
                # keeps FileResponse's test callback in-process; production
                # uses Starlette's normal AnyIO worker path.
                return func(*args)

            anyio.to_thread.run_sync = run_sync_without_worker
            transport = httpx.ASGITransport(app=self.application)
            try:
                async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                    return await client.request(method, url, **kwargs)
            finally:
                anyio.to_thread.run_sync = original_run_sync

        return asyncio.run(send())

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    async def override_get_db():
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(jobs, "SessionLocal", test_session)
    monkeypatch.setattr("app.main.GENERATED_DIR", tmp_path / "generated")
    app.state.generated_dir = tmp_path / "generated"
    app.state.generated_dir.mkdir(parents=True, exist_ok=True)
    yield SyncASGIClient(app), test_session, tmp_path / "generated"
    app.dependency_overrides.clear()


@pytest.fixture()
def payload():
    return {
        "event_name": "Python Workshop 2026",
        "event_date": "2026-10-07",
        "recipients": [
            {"name": "Mousumi Das", "email": "mousumi@example.com"},
            {"name": "Rahul Sharma", "email": "rahul@example.com"},
        ],
    }
