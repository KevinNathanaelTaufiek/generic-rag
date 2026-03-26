import random
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class RandomNumberRequest(BaseModel):
    min: int = 1
    max: int = 100


class RandomNumberResponse(BaseModel):
    number: int
    min: int
    max: int


@router.post("/random-number", response_model=RandomNumberResponse)
def get_random_number(body: RandomNumberRequest):
    number = random.randint(body.min, body.max)
    return RandomNumberResponse(number=number, min=body.min, max=body.max)
