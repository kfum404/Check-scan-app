from app.services.push import budget_event


def test_budget_event_none_below_threshold():
    assert budget_event(5000, 100, 200) is None


def test_budget_event_warn_at_80_pct():
    # 80% от 5000 = 4000; чек перевёл итог с 3900 на 4100
    title, body = budget_event(5000, 3900, 4100)
    assert "лимиту" in title.lower()
    assert "82%" in body


def test_budget_event_exceeded():
    title, body = budget_event(5000, 4990, 5010)
    assert "исчерпан" in title.lower()


def test_budget_event_not_resent_while_above():
    # уже выше лимита — повторные чеки не должны слать уведомление
    assert budget_event(5000, 5010, 5020) is None
    assert budget_event(5000, 4100, 4200) is None


def test_patch_me_accepts_push_token(client, auth_headers):
    r = client.patch("/users/me", json={"push_token": "ExponentPushToken[test123]"},
                     headers=auth_headers)
    assert r.status_code == 200
    # повторный патч другого поля не должен стирать токен
    r2 = client.patch("/users/me", json={"notifications_enabled": True},
                      headers=auth_headers)
    assert r2.status_code == 200


def _make_user_with_receipts(db_session, total: float):
    from datetime import datetime, timezone

    from app.models import Receipt, User

    user = User(name="Пуш", email="push@test.by", password_hash="x",
                monthly_budget=100, notifications_enabled=True,
                push_token="ExponentPushToken[test]")
    db_session.add(user)
    db_session.commit()
    db_session.add(Receipt(user_id=user.id, shop_name="М", date=datetime.now(timezone.utc),
                           total_amount=total, category="Прочее", status="confirmed",
                           created_at=datetime.now(timezone.utc)))
    db_session.commit()
    return user.id


def test_check_and_notify_sends_once_per_level(db_session, monkeypatch):
    """Алерт шлётся один раз; повторный чек без нового уровня — молчит."""
    from app.services import push

    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(push, "_send_expo_push",
                        lambda token, title, body: sent.append((title, body)))

    uid = _make_user_with_receipts(db_session, total=150)  # > 100 -> уровень 2
    push.check_and_notify(uid, added_amount=150)
    assert len(sent) == 1 and "исчерпан" in sent[0][0].lower()

    # второй вызов в том же месяце — уровень уже озвучен
    push.check_and_notify(uid, added_amount=10)
    assert len(sent) == 1


def test_check_and_notify_already_over_limit_alerts(db_session, monkeypatch):
    """Лимит превышен до фикса — следующий чек всё равно шлёт алерт."""
    from app.services import push

    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(push, "_send_expo_push",
                        lambda token, title, body: sent.append((title, body)))

    uid = _make_user_with_receipts(db_session, total=999)
    push.check_and_notify(uid, added_amount=1)
    assert len(sent) == 1
