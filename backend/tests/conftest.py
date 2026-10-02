import os
from dotenv import load_dotenv

load_dotenv()

os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL")

import pytest
from app import app
from database import Base, engine


@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)
    with app.test_client() as c:
        yield c
    Base.metadata.drop_all(bind=engine)