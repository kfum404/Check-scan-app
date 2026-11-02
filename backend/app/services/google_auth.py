"""Google OAuth: консент-ссылка, обмен кода на токены, проверка id_token.

Чистый urllib (без новых зависимостей). Функции exchange_code/verify_id_token
монкипатчатся в тестах.
"""
import json
import urllib.parse
import urllib.request

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"

SCOPES = "openid email profile"


class GoogleAuthError(Exception):
    pass


def build_consent_url(client_id: str, redirect_uri: str, state: str = "checkscan") -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"


def _post_form(url: str, data: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(data).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:200]
        raise GoogleAuthError(f"Google token endpoint: HTTP {e.code}: {detail}") from e
    except Exception as e:
        raise GoogleAuthError(f"Google token endpoint: {e}") from e


def exchange_code(client_id: str, client_secret: str, code: str, redirect_uri: str) -> dict:
    """code → {id_token, access_token, ...}"""
    return _post_form(
        GOOGLE_TOKEN_URL,
        {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
    )


def verify_id_token(id_token: str) -> dict:
    """Проверка подписи/audience через tokeninfo → claims {sub, email, name, ...}."""
    url = f"{GOOGLE_TOKENINFO_URL}?id_token={urllib.parse.quote(id_token)}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            claims = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise GoogleAuthError(f"id_token не прошёл проверку: HTTP {e.code}") from e
    except Exception as e:
        raise GoogleAuthError(f"id_token не прошёл проверку: {e}") from e
    if claims.get("email_verified") not in ("true", True):
        raise GoogleAuthError("Email у аккаунта Google не подтверждён")
    if not claims.get("email"):
        raise GoogleAuthError("Google не вернул email")
    return claims
