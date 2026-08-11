from fastapi import FastAPI

app = FastAPI(title="Merchant Exposure API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
