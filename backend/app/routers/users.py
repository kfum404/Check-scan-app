from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..schemas import UserPatchRequest, UserResponse
from ..security import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/me", response_model=UserResponse)
def patch_me(
    body: UserPatchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Тумблеры профиля и тема — экран Профиль."""
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    db.commit()
    return user
