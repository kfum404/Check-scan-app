from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import User
from ..schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from ..security import create_token, get_current_user, hash_password, verify_password
from ..services import google_auth

router = APIRouter(prefix="/auth", tags=["auth"])

# схема приложения (app.json) — колбэк редиректит сюда с готовым JWT
APP_SCHEME_CALLBACK = "checkscan://auth"


def _duplicate_email() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": "EMAIL_TAKEN", "message": "Пользователь с таким email уже есть"},
    )


def _oauth_not_configured() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={"code": "OAUTH_NOT_CONFIGURED",
                "message": "Google OAuth не настроен на сервере (GOOGLE_CLIENT_ID)"},
    )


@router.get("/google/start")
def google_start():
    """Редирект на страницу согласия Google (открывается из WebBrowser приложения)."""
    if not settings.GOOGLE_CLIENT_ID:
        raise _oauth_not_configured()
    url = google_auth.build_consent_url(settings.GOOGLE_CLIENT_ID, settings.GOOGLE_REDIRECT_URI)
    return RedirectResponse(url)


@router.get("/google/callback")
def google_callback(code: str | None = None, error: str | None = None,
                    db: Session = Depends(get_db)):
    """Google возвращает сюда ?code= → меняем на JWT → редирект в приложение."""
    def back(token: str | None, err: str | None) -> RedirectResponse:
        q = f"token={token}" if token else f"error={err}"
        return RedirectResponse(f"{APP_SCHEME_CALLBACK}?{q}")

    if error or not code:
        return back(None, error or "no_code")
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        return back(None, "oauth_not_configured")
    try:
        tokens = google_auth.exchange_code(
            settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET,
            code, settings.GOOGLE_REDIRECT_URI,
        )
        claims = google_auth.verify_id_token(tokens["id_token"])
    except google_auth.GoogleAuthError as e:
        return back(None, str(e))

    email = claims["email"].strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        # первый вход через Google → создаём аккаунт без пароля
        user = User(
            email=email,
            password_hash="oauth:google:" + claims.get("sub", ""),
            name=(claims.get("name") or email.split("@")[0])[:100],
        )
        db.add(user)
        db.commit()
    return back(create_token(user.id), None)


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == body.email)):
        raise _duplicate_email()
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        name=body.name or "Саныч",
    )
    db.add(user)
    db.commit()
    return TokenResponse(token=create_token(user.id), user=UserResponse.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "BAD_CREDENTIALS", "message": "Неверный email или пароль"},
        )
    return TokenResponse(token=create_token(user.id), user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user
