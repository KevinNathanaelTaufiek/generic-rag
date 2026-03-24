from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
def list_users():
    return {"users": settings.predefined_users}
