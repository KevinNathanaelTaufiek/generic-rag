from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class NotifyRequest(BaseModel):
    to: str
    message: str


class NotifyResponse(BaseModel):
    sent: bool
    to: str
    timestamp: str


@router.post("/notify", response_model=NotifyResponse)
def notify(body: NotifyRequest):
    print(f"[NOTIFY] To: {body.to} | Message: {body.message}")
    return NotifyResponse(
        sent=True,
        to=body.to,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
