# Google OAuth (POST /auth/google по id_token) + экспорт CSV.
from app.config import settings
from app.services import google_auth

AUD = "test-client-id"


def _run_with_client_id(fn):
    old = settings.GOOGLE_CLIENT_ID
    settings.GOOGLE_CLIENT_ID = AUD
    try:
        fn()
    finally:
        settings.GOOGLE_CLIENT_ID = old


def _fake_verify(id_token, audience=None):
    assert audience == AUD
    return {"sub": "123456", "email": "OAuth.User@Example.com",
            "email_verified": "true", "name": "Олег Тестовый",
            "aud": AUD}


def _fake_verify_wrong_aud(id_token, audience=None):
    raise google_auth.GoogleAuthError("id_token выдан другому приложению (audience не совпал)")


def _fake_verify_unverified(id_token, audience=None):
    raise google_auth.GoogleAuthError("Email у аккаунта Google не подтверждён")


class TestGoogleLogin:
    def test_not_configured(self, client):
        old = settings.GOOGLE_CLIENT_ID
        settings.GOOGLE_CLIENT_ID = None
        try:
            r = client.post("/auth/google", json={"id_token": "x" * 30})
            assert r.status_code == 503
            assert r.json()["detail"]["code"] == "OAUTH_NOT_CONFIGURED"
        finally:
            settings.GOOGLE_CLIENT_ID = old

    def test_bad_token_rejected(self, client, monkeypatch):
        monkeypatch.setattr(google_auth, "verify_id_token", _fake_verify_wrong_aud)
        def run():
            r = client.post("/auth/google", json={"id_token": "x" * 30})
            assert r.status_code == 401
            assert r.json()["detail"]["code"] == "BAD_GOOGLE_TOKEN"
        _run_with_client_id(run)

    def test_unverified_email_rejected(self, client, monkeypatch):
        monkeypatch.setattr(google_auth, "verify_id_token", _fake_verify_unverified)
        def run():
            r = client.post("/auth/google", json={"id_token": "x" * 30})
            assert r.status_code == 401
            assert "token=" not in r.text
        _run_with_client_id(run)

    def test_new_user_created_and_token_works(self, client, db_session, monkeypatch):
        monkeypatch.setattr(google_auth, "verify_id_token", _fake_verify)
        def run():
            r = client.post("/auth/google", json={"id_token": "y" * 30})
            assert r.status_code == 200
            token = r.json()["token"]
            # email в нижнем регистре, имя из claims
            from app.models import User
            u = db_session.query(User).filter_by(email="oauth.user@example.com").one()
            assert u.name == "Олег Тестовый"
            assert u.password_hash == "oauth:google:123456"
            me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
            assert me.status_code == 200
            assert me.json()["email"] == "oauth.user@example.com"
        _run_with_client_id(run)

    def test_existing_user_reused_not_rewritten(self, client, db_session,
                                                monkeypatch, auth_headers):
        from app.models import User
        monkeypatch.setattr(google_auth, "verify_id_token",
                            lambda id_token, audience=None: {
                                "sub": "999", "email": "Test@Example.com",
                                "email_verified": "true", "name": "Новое Имя",
                                "aud": AUD,
                            })
        def run():
            me = client.get("/auth/me", headers=auth_headers).json()  # test@example.com
            # логинимся Google-аккаунтом с тем же email
            r = client.post("/auth/google", json={"id_token": "z" * 30})
            assert r.status_code == 200
            u = db_session.get(User, me["id"])
            assert u.name == me["name"]  # имя не перезаписали
            assert u.email == "test@example.com"
        _run_with_client_id(run)


class TestExportCsv:
    def test_export_empty(self, client, auth_headers):
        r = client.get("/receipts/export.csv", headers=auth_headers)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/csv")
        assert "Дата;Магазин;Категория" in r.text

    def test_export_with_receipts(self, client, auth_headers, db_session):
        from datetime import datetime
        from app.models import Receipt, ReceiptItem
        me = client.get("/auth/me", headers=auth_headers).json()
        rid = me["id"]
        rec = Receipt(user_id=rid, shop_name="Евроопт", category="Продукты",
                      date=datetime(2025, 4, 17, 21, 37), total_amount=5.5, status="confirmed")
        db_session.add(rec)
        db_session.flush()
        db_session.add(ReceiptItem(receipt_id=rec.id, item_name="Синабон", price=5.5))
        db_session.commit()
        r = client.get("/receipts/export.csv", headers=auth_headers)
        assert r.status_code == 200
        assert "Евроопт" in r.text
        assert "Синабон — 5.5" in r.text
        assert "5.50" in r.text

    def test_export_requires_auth(self, client):
        r = client.get("/receipts/export.csv")
        assert r.status_code == 401

    def test_draft_not_exported(self, client, auth_headers, db_session):
        from datetime import datetime
        from app.models import Receipt
        me = client.get("/auth/me", headers=auth_headers).json()
        db_session.add(Receipt(user_id=me["id"], shop_name="Черновик", category="Прочее",
                               date=datetime(2025, 4, 17, 21, 37), total_amount=100, status="draft"))
        db_session.commit()
        r = client.get("/receipts/export.csv", headers=auth_headers)
        assert "Черновик" not in r.text
