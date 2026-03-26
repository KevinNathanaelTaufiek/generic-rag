import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# In-memory store: {task_id: task_dict}
_tasks: dict[str, dict] = {}


class ManageTaskRequest(BaseModel):
    action: str                          # create | update | delete | list
    task_id: Optional[str] = None
    title: Optional[str] = None
    tags: Optional[list[str]] = None     # nested array
    metadata: Optional[dict] = None      # nested object


class ManageTaskResponse(BaseModel):
    success: bool
    action: str
    task: Optional[dict] = None
    tasks: Optional[list] = None
    message: str


@router.post("/tasks/manage", response_model=ManageTaskResponse)
def manage_task(body: ManageTaskRequest):
    action = body.action.lower()

    if action == "create":
        if not body.title:
            raise HTTPException(status_code=400, detail="title is required for create")
        task_id = str(uuid.uuid4())[:8]
        task = {
            "task_id": task_id,
            "title": body.title,
            "tags": body.tags or [],
            "metadata": body.metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _tasks[task_id] = task
        return ManageTaskResponse(
            success=True,
            action="create",
            task=task,
            message=f"Task '{body.title}' created with ID {task_id}.",
        )

    if action == "update":
        if not body.task_id or body.task_id not in _tasks:
            raise HTTPException(status_code=404, detail=f"task_id '{body.task_id}' not found")
        task = _tasks[body.task_id]
        if body.title is not None:
            task["title"] = body.title
        if body.tags is not None:
            task["tags"] = body.tags
        if body.metadata is not None:
            task["metadata"] = {**task["metadata"], **body.metadata}
        task["updated_at"] = datetime.now(timezone.utc).isoformat()
        return ManageTaskResponse(
            success=True,
            action="update",
            task=task,
            message=f"Task '{body.task_id}' updated.",
        )

    if action == "delete":
        if not body.task_id or body.task_id not in _tasks:
            raise HTTPException(status_code=404, detail=f"task_id '{body.task_id}' not found")
        task = _tasks.pop(body.task_id)
        return ManageTaskResponse(
            success=True,
            action="delete",
            task=task,
            message=f"Task '{body.task_id}' deleted.",
        )

    if action == "list":
        return ManageTaskResponse(
            success=True,
            action="list",
            tasks=list(_tasks.values()),
            message=f"{len(_tasks)} task(s) found.",
        )

    raise HTTPException(status_code=400, detail=f"Unknown action '{action}'. Use: create | update | delete | list")


@router.get("/tasks")
def list_tasks():
    """Read-only endpoint polled by the standalone UI."""
    return {"tasks": list(_tasks.values())}
