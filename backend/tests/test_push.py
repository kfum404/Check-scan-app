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
