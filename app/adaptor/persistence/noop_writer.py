from datetime import datetime

from app.domain.models.review import ReviewResult


class NoopResultWriter:
    def save_rule_result(self, job_id: str, result: ReviewResult) -> None:
        pass

    def save_llm_result(self, job_id: str, result: ReviewResult) -> None:
        pass

    def update_broker_contacted(self, policy_number: str, value: bool) -> None:
        pass

    def update_quote_generated(self, policy_number: str, value: bool) -> None:
        pass

    def update_quotes(self, policy_number: str, quotes: list[dict]) -> None:
        pass

    def update_reviewed_at(self, policy_number: str, value: datetime) -> None:
        pass

    def load_latest_results(self) -> list[dict]:
        return []

    def load_latest_llm_results(self) -> list[dict]:
        return []

    def save_comparison_result(self, job_id: str, result: dict) -> None:
        pass

    def load_latest_comparison(self) -> dict | None:
        return None
