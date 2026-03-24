from fastapi import APIRouter
from app.api.v1 import audit, chat, knowledge, users

router = APIRouter()
router.include_router(knowledge.router)
router.include_router(chat.router)
router.include_router(audit.router)
router.include_router(users.router)
