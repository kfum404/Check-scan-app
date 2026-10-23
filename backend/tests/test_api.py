from datetime import datetime, timedelta, timezone

from app.db import SessionLocal
from app.models import Receipt, ReceiptItem, User

SAMPLE_TEXT = """ООО "Евроопт"
23.10.2026 14:32
1. ХЛЕБ РЖАНОЙ              2.45
2. МОЛОКО 3.2%             3.10
ИТОГО:                      5.55
"""


def _seed_confirmed_receipt(user_id: int, days_ago: int = 1) -> int:
    db = SessionLocal()
    try:
        r = Receipt(
            user_id=user_id,
            shop_name="Евроопт",
            date=datetime.now(timezone.utc) - timedelta(days=days_ago),
            total_amount=5.55,
            currency="BYN",
            category="Продукты",
            status="confirmed",
        )
        db.add(r)
        db.flush()
        db.add(ReceiptItem(receipt_id=r.id, item_name="ХЛЕБ РЖАНОЙ", price=2.45))
        db.add(ReceiptItem(receipt_id=r.id, item_name="МОЛОКО 3.2%", price=3.10))
        db.commit()
        return r.id
    finally:
        db.close()


def _user_id(headers) -> int:
    import jwt
    token = headers["Authorization"].split()[1]
    return int(jwt.decode(token, "test-secret", algorithms=["HS256"])["sub"])


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_register_and_login(client):
    r = client.post("/auth/register", json={
        "email": "a@example.com", "password": "secret123",
    })
    assert r.status_code == 201
    r = client.post("/auth/login", json={"email": "a@example.com", "password": "secret123"})
    assert r.status_code == 200
    assert r.json()["token"]


def test_scan_flow(client, auth_headers, monkeypatch):
    """Полный сценарий: фото → OCR-черновик → ручная правка → подтверждение."""
    from app.routers import receipts as receipts_router

    monkeypatch.setattr(
        receipts_router.ocr, "image_to_text_auto",
        lambda *a, **kw: (SAMPLE_TEXT, 70.0, 0, "thresh"),
    )
    r = client.post(
        "/receipts/scan",
        files={"file": ("check.jpg", b"\xff\xd8\xff fake-jpeg", "image/jpeg")},
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    receipt = r.json()["receipt"]
    assert receipt["status"] == "draft"
    assert receipt["shop_name"] == 'ООО "Евроопт"'
    assert float(receipt["total_amount"]) == 5.55
    assert len(receipt["items"]) == 2

    rid = receipt["id"]
    r = client.patch(f"/receipts/{rid}", json={
        "shop_name": "Евроопт",
        "date": receipt["date"],
        "total_amount": 5.55,
        "category": "Продукты",
    }, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "confirmed"


def test_history_and_detail(client, auth_headers):
    rid = _seed_confirmed_receipt(_user_id(auth_headers))
    r = client.get("/receipts?page=1&size=10", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["total"] == 1

    r = client.get(f"/receipts/{rid}", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()["items"]) == 2


def test_stats_weekly(client, auth_headers):
    _seed_confirmed_receipt(_user_id(auth_headers), days_ago=0)
    r = client.get("/stats/weekly", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert sum(e["amount"] for e in body["by_day"]) > 0
    assert body["by_category"][0]["label"] == "Продукты"


def test_summary(client, auth_headers):
    _seed_confirmed_receipt(_user_id(auth_headers))
    r = client.get("/receipts/summary/home", headers=auth_headers)
    assert r.status_code == 200
    assert float(r.json()["month_spent"]) > 0
    assert len(r.json()["receipts"]) == 1


def test_user_patch(client, auth_headers):
    r = client.patch("/users/me", json={"notifications_enabled": False}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["notifications_enabled"] is False


def test_unauthorized(client):
    assert client.get("/receipts").status_code in (401, 403)


def test_stats_home_and_summary(client, auth_headers):
    _seed_confirmed_receipt(_user_id(auth_headers), days_ago=0)
    r = client.get("/stats/home", headers=auth_headers)
    assert r.status_code == 200
    assert float(r.json()["today_spent"]) > 0
    assert float(r.json()["month_limit"]) == 5000

    r = client.get("/stats/summary?period=week", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["count"] == 1
    assert len(r.json()["by_day"]) == 7


def test_delete_receipt(client, auth_headers):
    rid = _seed_confirmed_receipt(_user_id(auth_headers))
    r = client.delete(f"/receipts/{rid}", headers=auth_headers)
    assert r.status_code == 204
    assert client.get(f"/receipts/{rid}", headers=auth_headers).status_code == 404
