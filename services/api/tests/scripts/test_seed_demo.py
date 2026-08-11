from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.merchants.models import Merchant
from app.queries.models import Query
from scripts.seed_demo import seed_demo


def test_seed_demo_is_idempotent(db_session: Session) -> None:
    first = seed_demo(db_session)
    second = seed_demo(db_session)

    assert first.merchant_id == second.merchant_id
    assert first.query_set_id == second.query_set_id
    assert first.scan_run_id == second.scan_run_id
    assert db_session.scalar(
        select(func.count(Merchant.id)).where(
            Merchant.normalized_name == "o'eat gastronomy"
        )
    ) == 1
    assert db_session.scalar(
        select(func.count(Query.id)).where(Query.query_set_id == first.query_set_id)
    ) == 30
    assert db_session.scalar(
        select(func.count(Query.id)).where(
            Query.query_set_id == first.query_set_id,
            Query.review_status == "approved",
            Query.is_enabled.is_(True),
        )
    ) == 30
