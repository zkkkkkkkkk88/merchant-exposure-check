from app.db.session import make_engine


def test_make_engine_uses_supplied_database_url() -> None:
    engine = make_engine("sqlite+pysqlite:///:memory:")

    assert str(engine.url) == "sqlite+pysqlite:///:memory:"
