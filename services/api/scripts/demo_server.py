import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./demo-e2e.db")

import uvicorn

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from scripts.seed_demo import seed_demo


def main() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        seed_demo(session)
    uvicorn.run(app, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
