import os

# Override the database URL BEFORE importing app.py, because that's
# exactly when app.py (via database.py) reads DATABASE_URL and creates
# the connection. Doing this after the import would mean the app
# already connected to the production database, and the override
# would have no effect.
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL")

import pytest
from app import app
from database import Base, engine


@pytest.fixture
def client():
    # Before each test: create all tables on the Neon test branch.
    Base.metadata.create_all(bind=engine)

    # test_client() — a Flask object that can make requests to the app
    # directly in Python, without a real HTTP server or terminal.
    with app.test_client() as c:
        yield c  # the test receives this object as the `client` parameter

    # After each test: drop all tables so the next test starts with a
    # clean database, regardless of the previous test's outcome.
    Base.metadata.drop_all(bind=engine)


def register_and_get_token(client, email="driver@example.com"):
    """Helper function (not a test): registers a user and returns a
    token, since almost every test below hits protected endpoints."""
    response = client.post("/api/register", json={
        "email": email, "password": "password123", "name": "Driver"
    })
    return response.get_json()["token"]


def auth_headers(token):
    """Helper function: builds the authorization header, so we don't
    repeat this line in every single test."""
    return {"Authorization": f"Bearer {token}"}


# ---------- register / login tests ----------

def test_register_success(client):
    response = client.post("/api/register", json={
        "email": "test@example.com",
        "password": "password123",
        "name": "Test User"
    })
    assert response.status_code == 201
    assert "token" in response.get_json()


def test_register_duplicate_email(client):
    client.post("/api/register", json={
        "email": "test@example.com", "password": "password123", "name": "A"
    })
    # a second registration with the same email should hit IntegrityError -> 409
    response = client.post("/api/register", json={
        "email": "test@example.com", "password": "password123", "name": "B"
    })
    assert response.status_code == 409


def test_login_wrong_password(client):
    client.post("/api/register", json={
        "email": "test@example.com", "password": "password123", "name": "A"
    })
    response = client.post("/api/login", json={
        "email": "test@example.com", "password": "wrongpass"
    })
    assert response.status_code == 401


# ---------- cities tests ----------

def test_add_city(client):
    token = register_and_get_token(client)
    response = client.post(
        "/api/cities", json={"name": "Київ"}, headers=auth_headers(token)
    )
    assert response.status_code == 201
    assert response.get_json()["name"] == "Київ"


def test_add_duplicate_city(client):
    token = register_and_get_token(client)
    client.post("/api/cities", json={"name": "Київ"}, headers=auth_headers(token))
    # a different case ("київ") should count as the same city via city_key()
    response = client.post(
        "/api/cities", json={"name": "київ"}, headers=auth_headers(token)
    )
    assert response.status_code == 409


# ---------- trips tests ----------

def test_add_trip_unknown_city(client):
    token = register_and_get_token(client)
    response = client.post(
        "/api/trips",
        json={"work_date": "2026-09-20", "city": "Одеса"},
        headers=auth_headers(token)
    )
    assert response.status_code == 400
    # check for a substring, not the exact text — more resilient to small wording tweaks
    assert "Unknown city" in response.get_json()["error"]


def test_add_trip_success(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    client.post("/api/cities", json={"name": "Київ"}, headers=headers)

    response = client.post(
        "/api/trips",
        json={
            "work_date": "2026-09-20", "city": "київ",  # lowercase on purpose
            "distance_km": 120, "fuel_cost": 450, "income": 2400
        },
        headers=headers
    )
    assert response.status_code == 201


def test_add_trip_negative_income(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    client.post("/api/cities", json={"name": "Київ"}, headers=headers)

    response = client.post(
        "/api/trips",
        json={"work_date": "2026-09-20", "city": "Київ", "income": -100},
        headers=headers
    )
    assert response.status_code == 400


def test_add_trip_invalid_date(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    client.post("/api/cities", json={"name": "Київ"}, headers=headers)

    response = client.post(
        "/api/trips",
        json={"work_date": "20-09-2026", "city": "Київ"},  # wrong date format
        headers=headers
    )
    assert response.status_code == 400


# ---------- analytics tests ----------

def test_analytics_summary(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    client.post("/api/cities", json={"name": "Київ"}, headers=headers)

    client.post("/api/trips", json={
        "work_date": "2026-09-20", "city": "Київ",
        "distance_km": 100, "fuel_cost": 400, "income": 2000
    }, headers=headers)

    client.post("/api/trips", json={
        "work_date": "2026-09-21", "city": "Київ",
        "distance_km": 100, "fuel_cost": 400, "income": 2000
    }, headers=headers)

    response = client.get("/api/analytics", headers=headers)
    summary = response.get_json()["summary"]

    assert summary["work_days"] == 2
    assert summary["total_income"] == 4000.0
    assert summary["net_income"] == 3200.0  # 4000 - (400+400)


def test_analytics_filter_unknown_city(client):
    token = register_and_get_token(client)
    headers = auth_headers(token)
    client.post("/api/cities", json={"name": "Київ"}, headers=headers)
    client.post("/api/trips", json={
        "work_date": "2026-09-20", "city": "Київ", "income": 2000
    }, headers=headers)

    # filtering by a city that isn't in the directory should return an
    # empty result set, not all of the user's trips
    response = client.get("/api/analytics?cities=Одеса", headers=headers)
    data = response.get_json()

    assert data["summary"]["work_days"] == 0
    assert data["by_city"] == []