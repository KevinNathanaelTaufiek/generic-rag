from fastapi import FastAPI
from routes import search, notify, data

app = FastAPI(title="Dummy Microservices", version="1.0.0")

app.include_router(search.router)
app.include_router(notify.router)
app.include_router(data.router)


@app.get("/health")
def health():
    return {"status": "ok"}
