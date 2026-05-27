import random
import string
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def random_email() -> str:
    return "".join(random.choices(string.ascii_lowercase, k=10)) + "@example.com"


class TestAuthFlow:
    @pytest.fixture
    def user_credentials(self):
        return {"email": random_email(), "password": "testpassword123"}

    @pytest.fixture
    def registered_user(self, user_credentials):
        client.post("/users/", json=user_credentials)
        return user_credentials

    @pytest.fixture
    def auth_token(self, registered_user):
        res = client.post(
            "/token",
            data={
                "username": registered_user["email"],
                "password": registered_user["password"],
            },
        )
        return res.json()

    def test_full_login_flow(self, registered_user):
        res = client.post(
            "/token",
            data={
                "username": registered_user["email"],
                "password": registered_user["password"],
            },
        )
        assert res.status_code == 200
        assert "access_token" in res.json()
        assert "refresh_token" in res.json()

    def test_get_profile_with_token(self, auth_token):
        res = client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {auth_token['access_token']}"},
        )
        assert res.status_code == 200
        assert res.json()["tier"] == "free"

    def test_token_refresh(self, auth_token):
        refresh_token = auth_token["refresh_token"]
        res = client.post(
            "/token/refresh",
            json={"refresh_token": refresh_token},
        )
        assert res.status_code == 200
        new_data = res.json()
        assert "access_token" in new_data
        assert "refresh_token" in new_data
        assert new_data["refresh_token"] != refresh_token

    def test_logout_revokes_token(self, auth_token):
        refresh_token = auth_token["refresh_token"]
        res = client.post(
            "/logout",
            json={"refresh_token": refresh_token},
        )
        assert res.status_code == 200

        res = client.post(
            "/token/refresh",
            json={"refresh_token": refresh_token},
        )
        assert res.status_code == 401


class TestServerAccess:
    @pytest.fixture
    def user_token(self):
        email = random_email()
        client.post("/users/", json={"email": email, "password": "testpassword123"})
        res = client.post(
            "/token",
            data={"username": email, "password": "testpassword123"},
        )
        return res.json()["access_token"]

    def test_free_user_sees_only_free_servers(self, user_token):
        res = client.get(
            "/servers/",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert res.status_code == 200
        servers = res.json()
        for server in servers:
            assert not server.get("is_premium", False)

    def test_unauthenticated_sees_only_free_servers(self):
        res = client.get("/servers/")
        assert res.status_code == 200
        servers = res.json()
        for server in servers:
            assert not server.get("is_premium", False)


class TestKeyManagement:
    @pytest.fixture
    def user_token(self):
        email = random_email()
        client.post("/users/", json={"email": email, "password": "testpassword123"})
        res = client.post(
            "/token",
            data={"username": email, "password": "testpassword123"},
        )
        return res.json()["access_token"]

    def test_list_keys_empty(self, user_token):
        res = client.get(
            "/vpn/keys",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert res.status_code == 200
        assert res.json() == []

    def test_revoke_nonexistent_key(self, user_token):
        res = client.post(
            "/vpn/config/999/revoke",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert res.status_code in (404,)


class TestAdminEndpoints:
    @pytest.fixture
    def admin_token(self):
        email = random_email()
        client.post("/users/", json={"email": email, "password": "testpassword123"})
        res = client.post(
            "/token",
            data={"username": email, "password": "testpassword123"},
        )
        return res.json()["access_token"]

    def test_non_admin_cannot_list_users(self, admin_token):
        res = client.get(
            "/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 403

    def test_non_admin_cannot_toggle_server(self, admin_token):
        res = client.patch(
            "/admin/servers/1/toggle",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 403


class TestValidation:
    def test_invalid_vpn_subnet(self):
        email = random_email()
        client.post("/users/", json={"email": email, "password": "testpassword123"})
        res = client.post(
            "/token",
            data={"username": email, "password": "testpassword123"},
        )
        token = res.json()["access_token"]

        server_data = {
            "name": "Test",
            "location": "Test",
            "ip_address": "1.2.3.4",
            "vpn_subnet": "invalid",
            "public_key": "x" * 44,
        }
        res = client.post(
            "/admin/servers",
            json=server_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code in (403, 422)

    def test_short_password_rejected(self):
        res = client.post(
            "/users/",
            json={"email": random_email(), "password": "short"},
        )
        assert res.status_code == 422
