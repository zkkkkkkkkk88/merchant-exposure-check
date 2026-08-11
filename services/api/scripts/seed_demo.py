from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.merchants.models import Merchant
from app.merchants.schemas import MerchantCreate, MerchantSourceCreate
from app.merchants.service import MerchantService
from app.queries.generator import TemplateQueryGenerator
from app.queries.models import QuerySet
from app.queries.schemas import QueryUpdate
from app.queries.service import QueryLibraryService
from app.scans.models import ScanRun
from app.scans.schemas import (
    ManualCitationCreate,
    ManualResultCreate,
    ManualResultsCreate,
)
from app.scans.service import ScanService


@dataclass(frozen=True)
class SeedResult:
    merchant_id: UUID
    query_set_id: UUID
    scan_run_id: UUID


def seed_demo(session: Session) -> SeedResult:
    merchant = session.scalar(
        select(Merchant).where(Merchant.normalized_name == "o'eat gastronomy")
    )
    if merchant is None:
        merchant = MerchantService.create(
            session,
            MerchantCreate(
                name="O'eat Gastronomy",
                branch_name="杭州万象城店",
                city="杭州",
                industry="餐饮",
                sources=[
                    MerchantSourceCreate(
                        kind="meituan",
                        url="https://pmtmeishi.meituan.com/dp/prefer/list/1510759369",
                        is_verified=True,
                    )
                ],
            ),
        )

    query_set = session.scalar(
        select(QuerySet)
        .where(QuerySet.merchant_id == merchant.id)
        .order_by(QuerySet.version.asc())
        .limit(1)
    )
    if query_set is None:
        query_set = QueryLibraryService.generate(
            session,
            merchant.id,
            count=30,
            generator=TemplateQueryGenerator(),
        )
        for query in query_set.queries:
            QueryLibraryService.update_query(
                session,
                query.id,
                QueryUpdate(review_status="approved", is_enabled=True),
            )
    scan_run = session.scalar(
        select(ScanRun)
        .where(
            ScanRun.merchant_id == merchant.id,
            ScanRun.query_set_id == query_set.id,
        )
        .order_by(ScanRun.created_at.asc())
        .limit(1)
    )
    if scan_run is None:
        scan_run = ScanService.create_run(session, merchant.id, query_set.id, "manual")
        results = []
        for index, query in enumerate(query_set.queries):
            mentioned = index < 12
            results.append(
                ManualResultCreate(
                    query_id=query.id,
                    raw_text=(
                        f"1. O'eat Gastronomy：与“{query.text}”相关的公开推荐。"
                        if mentioned
                        else "本次公开回答推荐了其他商家。"
                    ),
                    citations=(
                        [
                            ManualCitationCreate(
                                url=(
                                    "https://pmtmeishi.meituan.com/dp/prefer/"
                                    "list/1510759369"
                                ),
                                title="O'eat Gastronomy 公开门店页",
                            )
                        ]
                        if mentioned
                        else []
                    ),
                )
            )
        ScanService.add_manual_results(
            session,
            scan_run.id,
            ManualResultsCreate(results=results),
        )
    return SeedResult(
        merchant_id=merchant.id,
        query_set_id=query_set.id,
        scan_run_id=scan_run.id,
    )


def main() -> None:
    with SessionLocal() as session:
        result = seed_demo(session)
        print(f"Seeded merchant={result.merchant_id} query_set={result.query_set_id}")


if __name__ == "__main__":
    main()
