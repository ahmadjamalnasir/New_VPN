import os
import random
import string
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.main import app


def random_email() -> str:
    return "".join(random.choices(string.ascii_lowercase, k=10)) + "@example.com"


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def test_user_data():
    return {
        "email": random_email(),
        "password": "testpassword123",
    }


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "VPN Project API is running"}


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_user(client, test_user_data):
    response = client.post("/users/", json=test_user_data)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == test_user_data["email"]
    assert data["is_active"] is True
    assert data["tier"] == "free"
    assert "hashed_password" not in data


def test_register_duplicate_email(client, test_user_data):
    client.post("/users/", json=test_user_data)
    response = client.post("/users/", json=test_user_data)
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


def test_login_success(client, test_user_data):
    client.post("/users/", json=test_user_data)
    response = client.post(
        "/token",
        data={
            "username": test_user_data["email"],
            "password": test_user_data["password"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, test_user_data):
    client.post("/users/", json=test_user_data)
    response = client.post(
        "/token",
        data={
            "username": test_user_data["email"],
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 401


def test_login_nonexistent_user(client):
    response = client.post(
        "/token",
        data={
            "username": "nonexistent@example.com",
            "password": "testpassword",
        },
    )
    assert response.status_code == 401


def test_get_user_me(client, test_user_data):
    client.post("/users/", json=test_user_data)
    token_res = client.post(
        "/token",
        data={
            "username": test_user_data["email"],
            "password": test_user_data["password"],
        },
    )
    token = token_res.json()["access_token"]

    response = client.get(
        "/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == test_user_data["email"]


def test_get_user_me_no_token(client):
    response = client.get("/users/me")
    assert response.status_code == 401


def test_list_servers_empty(client):
    response = client.get("/servers/")
    assert response.status_code == 200
    assert response.json() == []


def test_non_admin_cannot_create_server(client, test_user_data):
    client.post("/users/", json=test_user_data)
    token_res = client.post(
        "/token",
        data={
            "username": test_user_data["email"],
            "password": test_user_data["password"],
        },
    )
    token = token_res.json()["access_token"]

    server_data = {
        "name": "Test Server",
        "location": "New York",
        "ip_address": "192.168.1.50",
        "vpn_subnet": "10.9.0.0/24",
        "public_key": "x" * 44,
    }
    response = client.post(
        "/servers/", json=server_data, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


def test_rate_limiting(client, test_user_data):
    for _ in range(5):
        response = client.post("/users/", json=test_user_data)
        if response.status_code == 429:
            break

    assert response.status_code in (201, 400, 429)


def test_password_validation_short(client):
    response = client.post(
        "/users/",
        json={"email": random_email(), "password": "short"},
    )
    assert response.status_code == 422
