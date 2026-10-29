"""Exercise the actual /auth router against synthetic SQLite, never the production app."""
import os
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.database.session import get_db
from backend.modules.auth.router import router as auth_router, _login_attempts
from backend.modules.auth.security import hash_password
from tests.test_supritech_access_sqlite import SupritechSqliteAuthorization


class SupritechRealLoginRouter(SupritechSqliteAuthorization):
    def setUp(self):
        super().setUp()
        self.environment = patch.dict(os.environ, {
            "JWT_SECRET": "synthetic-real-login-tests-not-production-2026",
            "ENVIRONMENT": "testing",
            "TALVOA_ALLOW_PUBLIC_REGISTRATION": "false",
        })
        self.environment.start()
        _login_attempts.clear()
        self.actor(1).username = "supritech"
        self.actor(1).password_hash = hash_password("synthetic-pass-2026")
        self.db.commit()
        app = FastAPI()
        app.include_router(auth_router, prefix="/api/v1")

        def isolated_db():
            yield self.db

        app.dependency_overrides[get_db] = isolated_db
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        _login_attempts.clear()
        self.environment.stop()
        super().tearDown()

    def login(self, identity="supritech", password="synthetic-pass-2026"):
        return self.client.post("/api/v1/auth/login", json={"email": identity, "password": password})

    def test_login_by_partner_username_sets_http_only_cookie(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user_name"], "Partner admin")
        self.assertIn("httponly", response.headers["set-cookie"].lower())
        self.assertEqual(self.client.get("/api/v1/auth/me").status_code, 200)

    def test_login_by_email_is_supported(self):
        self.assertEqual(self.login("partner@example.invalid").status_code, 200)

    def test_wrong_password_returns_401(self):
        self.assertEqual(self.login(password="invalid-password").status_code, 401)

    def test_unknown_account_returns_401(self):
        self.assertEqual(self.login(identity="unknown-user").status_code, 401)

    def test_inactive_user_cannot_login(self):
        self.actor(1).active = False
        self.db.commit()
        self.assertEqual(self.login().status_code, 403)

    def test_registration_is_disabled_by_default(self):
        response = self.client.post("/api/v1/auth/register", json={
            "user_name": "Synthetic User",
            "email": "new@example.invalid",
            "password": "synthetic-pass-2026",
            "company_name": "Synthetic Tenant",
        })
        self.assertEqual(response.status_code, 403)

    def test_logout_revokes_session(self):
        self.assertEqual(self.login().status_code, 200)
        self.assertEqual(self.client.get("/api/v1/auth/me").status_code, 200)
        response = self.client.post("/api/v1/auth/logout", headers={"X-CSRF-Protection": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/v1/auth/me").status_code, 401)


if __name__ == "__main__":
    unittest.main()
