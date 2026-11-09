import os
import pytest

# Force a clean, isolated SQLite DB for the test run
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_procuremind.db")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.core.database import Base, engine  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    return TestClient(app)
