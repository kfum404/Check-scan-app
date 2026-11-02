"""Проверка id_token от Google через tokeninfo (Implicit flow).

Приложение получает id_token само (expo-auth-session через прокси auth.expo.io —
Google не принимает IP-адреса в redirect URI), сервер только проверяет подпись
и audience. Функция verify_id_token монкипатчится в тестах.
"""
import json
import urllib.parse
import urllib.request

GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


class GoogleAuthError(Exception):
    pass


def verify_id_token(id_token: str, audience: str | None = None) -> dict:
    """Проверка подписи через tokeninfo → claims {sub, email, name, ...}.

    audience — наш GOOGLE_CLIENT_ID: tokeninfo сам отвергнет токен,
    выданный другому приложению.
    """
    url = f"{GOOGLE_TOKENINFO_URL}?id_token={urllib.parse.quote(id_token)}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            claims = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise GoogleAuthError(f"id_token не прошёл проверку: HTTP {e.code}") from e
    except Exception as e:
        raise GoogleAuthError(f"id_token не прошёл проверку: {e}") from e
    if audience and claims.get("aud") != audience:
        raise GoogleAuthError("id_token выдан другому приложению (audience не совпал)")
    if claims.get("email_verified") not in ("true", True):
        raise GoogleAuthError("Email у аккаунта Google не подтверждён")
    if not claims.get("email"):
        raise GoogleAuthError("Google не вернул email")
    return claims
