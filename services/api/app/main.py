from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.merchants.router import router as merchants_router
from app.mobile_checks.router import router as mobile_checks_router
from app.platform_audits.router import router as platform_audits_router
from app.queries.router import router as queries_router
from app.reports.router import router as reports_router
from app.scans.router import router as scans_router
from app.system.router import router as system_router

app = FastAPI(title="Merchant Exposure API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "X-Filename"],
)
app.include_router(merchants_router)
app.include_router(mobile_checks_router)
app.include_router(platform_audits_router)
app.include_router(queries_router)
app.include_router(scans_router)
app.include_router(reports_router)
app.include_router(system_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
