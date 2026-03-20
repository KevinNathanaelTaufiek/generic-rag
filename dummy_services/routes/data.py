from typing import Any, Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# In-memory store: {"resource_name": [item, ...]}
_store: dict[str, list[dict]] = {}


class DataRequest(BaseModel):
    action: Literal["create", "read", "update", "delete"]
    resource: str
    data: dict[str, Any] = {}


class DataResponse(BaseModel):
    success: bool
    action: str
    resource: str
    data: Any = None


@router.post("/data", response_model=DataResponse)
def data(body: DataRequest):
    store = _store.setdefault(body.resource, [])

    if body.action == "create":
        store.append(body.data)
        return DataResponse(success=True, action="create", resource=body.resource, data=body.data)

    if body.action == "read":
        return DataResponse(success=True, action="read", resource=body.resource, data=store)

    if body.action == "update":
        match_key = next(iter(body.data), None)
        if match_key is None:
            raise HTTPException(status_code=400, detail="data must contain at least one key to match")
        updated = False
        for item in store:
            if item.get(match_key) == body.data.get(match_key):
                item.update(body.data)
                updated = True
                break
        return DataResponse(success=updated, action="update", resource=body.resource, data=body.data)

    if body.action == "delete":
        match_key = next(iter(body.data), None)
        if match_key is None:
            raise HTTPException(status_code=400, detail="data must contain at least one key to match")
        before = len(store)
        _store[body.resource] = [i for i in store if i.get(match_key) != body.data.get(match_key)]
        deleted = before - len(_store[body.resource])
        return DataResponse(success=deleted > 0, action="delete", resource=body.resource, data={"deleted_count": deleted})

    raise HTTPException(status_code=400, detail=f"Unknown action: {body.action}")
