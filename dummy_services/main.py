from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from routes import notify, tasks, random_number

app = FastAPI(title="Dummy Microservices", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(notify.router)
app.include_router(tasks.router)
app.include_router(random_number.router)

# Serve Task Manager UI
_static = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=_static), name="static")


@app.get("/ui")
def ui():
    return FileResponse(_static / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}
