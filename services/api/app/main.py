from fastapi import FastAPI

from app.merchants.router import router as merchants_router
from app.queries.router import router as queries_router
from app.reports.router import router as reports_router
from app.scans.router import router as scans_router

app = FastAPI(title="Merchant Exposure API")
app.include_router(merchants_router)
app.include_router(queries_router)
app.include_router(scans_router)
app.include_router(reports_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
