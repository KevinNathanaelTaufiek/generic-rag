from fastapi import FastAPI
from routes import notify, data, random_number

app = FastAPI(title="Dummy Microservices", version="1.0.0")

app.include_router(notify.router)
app.include_router(data.router)
app.include_router(random_number.router)


@app.get("/health")
def health():
    return {"status": "ok"}
