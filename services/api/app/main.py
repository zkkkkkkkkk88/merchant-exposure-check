from fastapi import FastAPI

from app.merchants.router import router as merchants_router

app = FastAPI(title="Merchant Exposure API")
app.include_router(merchants_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
