from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import User
from ..schemas import (GoogleLoginRequest, LoginRequest, RegisterRequest,
                       TokenResponse, UserResponse)
from ..security import create_token, get_current_user, hash_password, verify_password
from ..services import google_auth

router = APIRouter(prefix="/auth", tags=["auth"])


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


@router.post("/google", response_model=TokenResponse)
def google_login(body: GoogleLoginRequest, db: Session = Depends(get_db)):
    """Вход по id_token от Google (приложение получает его через expo-auth-session).

    Сервер проверяет подпись и audience у Google (tokeninfo), затем ищет
    пользователя по email или создаёт нового.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise _oauth_not_configured()
    try:
        claims = google_auth.verify_id_token(body.id_token, audience=settings.GOOGLE_CLIENT_ID)
    except google_auth.GoogleAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "BAD_GOOGLE_TOKEN", "message": str(e)},
        )
    email = claims["email"].strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            password_hash="oauth:google:" + claims.get("sub", ""),
            name=(claims.get("name") or email.split("@")[0])[:100],
        )
        db.add(user)
        db.commit()
    return TokenResponse(token=create_token(user.id), user=UserResponse.model_validate(user))


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
