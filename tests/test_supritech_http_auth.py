"""HTTP-level authentication and tenant boundary checks, synthetic in-memory DB only."""
import os
import unittest
from unittest.mock import patch

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from backend.app.database.session import get_db
from backend.modules.auth.dependencies import get_current_user
from backend.modules.auth.security import create_access_token
from backend.modules.partners.access import require_partner_company_access
from tests.test_supritech_access_sqlite import SupritechSqliteAuthorization

TEST_SECRET = "synthetic-http-auth-tests-only-not-a-production-secret-2026"


class SupritechHttpAuthorization(SupritechSqliteAuthorization):
    def setUp(self):
        super().setUp()
        self.secret = patch.dict(os.environ, {"JWT_SECRET": TEST_SECRET})
        self.secret.start()
        app = FastAPI()

        def local_db():
            yield self.db

        app.dependency_overrides[get_db] = local_db

        @app.get("/test/companies/{company_id}")
        def read_company(company_id: int, user=Depends(get_current_user), db=Depends(get_db)):
            company = require_partner_company_access(db, user, company_id)
            return {"company_id": company.id}

        @app.post("/test/companies/{company_id}")
        def write_company(company_id: int, user=Depends(get_current_user), db=Depends(get_db)):
            company = require_partner_company_access(db, user, company_id, write=True)
            return {"company_id": company.id}

        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.secret.stop()
        super().tearDown()

    def token(self, user_id, *, company_id=None, session_version=None):
        user = self.actor(user_id)
        return create_access_token(
            str(user.id),
            user.company_id if company_id is None else company_id,
            user.session_version if session_version is None else session_version,
        )

    def test_http_without_session_is_401(self):
        self.assertEqual(self.client.get("/test/companies/10").status_code, 401)

    def test_http_partner_can_read_own_company(self):
        response = self.client.get("/test/companies/10", headers={"Authorization": "Bearer " + self.token(1)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["company_id"], 10)

    def test_http_cross_tenant_access_denied(self):
        response = self.client.get("/test/companies/20", headers={"Authorization": "Bearer " + self.token(1)})
        self.assertEqual(response.status_code, 403)

    def test_http_viewer_write_denied(self):
        response = self.client.post("/test/companies/10", headers={"Authorization": "Bearer " + self.token(2)})
        self.assertEqual(response.status_code, 403)

    def test_http_cookie_write_requires_csrf_header(self):
        token = self.token(1)
        response = self.client.post("/test/companies/10", cookies={"printflow_session": token})
        self.assertEqual(response.status_code, 403)
        approved = self.client.post("/test/companies/10", cookies={"printflow_session": token},
                                    headers={"X-CSRF-Protection": "1"})
        self.assertEqual(approved.status_code, 200)

    def test_http_wrong_company_claim_is_401(self):
        response = self.client.get("/test/companies/10",
                                   headers={"Authorization": "Bearer " + self.token(1, company_id=20)})
        self.assertEqual(response.status_code, 401)

    def test_http_revoked_session_is_401(self):
        response = self.client.get("/test/companies/10",
                                   headers={"Authorization": "Bearer " + self.token(1, session_version=99)})
        self.assertEqual(response.status_code, 401)

    def test_http_inactive_user_is_401(self):
        self.actor(1).active = False
        self.db.flush()
        response = self.client.get("/test/companies/10", headers={"Authorization": "Bearer " + self.token(1)})
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
