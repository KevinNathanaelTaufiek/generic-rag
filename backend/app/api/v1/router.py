from fastapi import APIRouter
from app.api.v1 import knowledge, chat

router = APIRouter()
router.include_router(knowledge.router)
router.include_router(chat.router)
