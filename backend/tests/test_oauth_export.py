# Google OAuth: старт/колбэк/создание пользователя + экспорт CSV.
from app.config import settings
from app.services import google_auth


class TestGoogleStart:
    def test_start_not_configured(self, client):
        old = settings.GOOGLE_CLIENT_ID
        settings.GOOGLE_CLIENT_ID = None
        try:
            r = client.get("/auth/google/start", follow_redirects=False)
            assert r.status_code == 503
            assert r.json()["detail"]["code"] == "OAUTH_NOT_CONFIGURED"
        finally:
            settings.GOOGLE_CLIENT_ID = old

    def test_start_redirects_to_google(self, client):
        old = settings.GOOGLE_CLIENT_ID
        settings.GOOGLE_CLIENT_ID = "test-client-id"
        try:
            r = client.get("/auth/google/start", follow_redirects=False)
            assert r.status_code in (302, 307)
            loc = r.headers["location"]
            assert loc.startswith("https://accounts.google.com/o/oauth2/v2/auth")
            assert "client_id=test-client-id" in loc
            assert "redirect_uri=" in loc
        finally:
            settings.GOOGLE_CLIENT_ID = old


def _fake_exchange(*args, **kwargs):
    return {"id_token": "fake"}


def _fake_verify(id_token):
    return {"sub": "123456", "email": "OAuth.User@Example.com",
            "email_verified": "true", "name": "Олег Тестовый"}


def _fake_verify_no_email(id_token):
    raise google_auth.GoogleAuthError("Email у аккаунта Google не подтверждён")


class TestGoogleCallback:
    def test_error_from_google(self, client):
        r = client.get("/auth/google/callback?error=access_denied", follow_redirects=False)
        assert r.status_code in (302, 307)
        assert "checkscan://auth?error=access_denied" in r.headers["location"]

    def test_no_code(self, client):
        r = client.get("/auth/google/callback", follow_redirects=False)
        assert r.status_code in (302, 307)
        assert "checkscan://auth?error=" in r.headers["location"]

    def test_new_user_created_and_jwt_returned(self, client, db_session, monkeypatch):
        monkeypatch.setattr(google_auth, "exchange_code", _fake_exchange)
        monkeypatch.setattr(google_auth, "verify_id_token", _fake_verify)
        old_id, old_secret = settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET
        settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET = "id", "secret"
        try:
            r = client.get("/auth/google/callback?code=abc", follow_redirects=False)
            assert r.status_code in (302, 307)
            loc = r.headers["location"]
            assert loc.startswith("checkscan://auth?token=")
            # email сохранён в нижнем регистре, имя из claims
            from app.models import User
            u = db_session.query(User).filter_by(email="oauth.user@example.com").one()
            assert u.name == "Олег Тестовый"
            assert u.password_hash == "oauth:google:123456"
            # токен рабочий — /auth/me отвечает
            token = loc.split("token=")[1]
            me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
            assert me.status_code == 200
            assert me.json()["email"] == "oauth.user@example.com"
        finally:
            settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET = old_id, old_secret

    def test_existing_user_gets_token_without_rewrite(self, client, db_session,
                                                      monkeypatch, auth_headers):
        from app.models import User
        monkeypatch.setattr(google_auth, "exchange_code", _fake_exchange)
        monkeypatch.setattr(google_auth, "verify_id_token", _fake_verify)
        old_id, old_secret = settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET
        settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET = "id", "secret"
        try:
            me = client.get("/auth/me", headers=auth_headers)
            email = me.json()["email"]
            name_before = me.json()["name"]
            r = client.get("/auth/google/callback?code=abc", follow_redirects=False)
            loc = r.headers["location"]
            assert loc.startswith("checkscan://auth?token=")
            u = db_session.get(User, me.json()["id"])
            assert u.name == name_before  # существующего юзера не перезаписали
            assert u.email == email
        finally:
            settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET = old_id, old_secret

    def test_unverified_email_rejected(self, client, monkeypatch):
        monkeypatch.setattr(google_auth, "exchange_code", _fake_exchange)
        monkeypatch.setattr(google_auth, "verify_id_token", _fake_verify_no_email)
        old_id, old_secret = settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET
        settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET = "id", "secret"
        try:
            r = client.get("/auth/google/callback?code=abc", follow_redirects=False)
            assert "checkscan://auth?error=" in r.headers["location"]
            assert "token=" not in r.headers["location"]
        finally:
            settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET = old_id, old_secret


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
