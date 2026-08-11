from app.scans.adapters.base import (
    AdapterResultNotFoundError,
    SearchRequest,
    SearchResponse,
)


class ManualSearchAdapter:
    name = "manual"

    def __init__(self, results: dict[str, SearchResponse]) -> None:
        self._results = results.copy()

    async def search(self, request: SearchRequest) -> SearchResponse:
        try:
            return self._results[request.query]
        except KeyError as error:
            raise AdapterResultNotFoundError(
                f"No manual result supplied for correlation {request.correlation_id}"
            ) from error
