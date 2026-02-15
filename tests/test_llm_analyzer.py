from app.engine.batch import process_pair
from app.engine.differ import compute_diff
from app.engine.rules import flag_diff
from app.llm.analyzer import analyze_pair, generate_summary, should_analyze
from app.llm.mock import MockLLMClient
from app.models.policy import RenewalPair


def test_should_analyze_with_notes(home_pair: RenewalPair):
    diff = compute_diff(home_pair)
    assert should_analyze(diff, home_pair) is True


def test_should_analyze_no_triggers():
    from app.models.policy import PolicySnapshot

    prior = PolicySnapshot(
        policy_number="CLEAN-001",
        policy_type="auto",
        carrier="X",
        effective_date="2024-01-01",
        expiration_date="2025-01-01",
        premium=1000,
    )
    renewal = prior.model_copy(deep=True)
    renewal.premium = 1050
    pair = RenewalPair(prior=prior, renewal=renewal)
    diff = compute_diff(pair)
    assert should_analyze(diff, pair) is False


def test_analyze_pair_notes(home_pair: RenewalPair):
    client = MockLLMClient()
    diff = compute_diff(home_pair)
    diff = flag_diff(diff, home_pair)
    insights = analyze_pair(client, diff, home_pair)
    assert len(insights) >= 1
    assert any(i.analysis_type == "risk_signal_extractor" for i in insights)
    assert any("risk_signal_extractor" in call[1] for call in client.calls)


def test_analyze_pair_endorsement_desc(auto_pair: RenewalPair):
    diff = compute_diff(auto_pair)
    diff = flag_diff(diff, auto_pair)
    has_endorsement_desc = any(
        c.field.startswith("endorsement_description_") for c in diff.changes
    )
    if has_endorsement_desc:
        client = MockLLMClient()
        insights = analyze_pair(client, diff, auto_pair)
        assert any(i.analysis_type == "endorsement_comparison" for i in insights)


def test_process_pair_with_mock_llm(home_pair: RenewalPair):
    client = MockLLMClient()
    result = process_pair(home_pair, llm_client=client)
    assert result.policy_number == "HOME-2024-001"
    assert len(result.llm_insights) > 0
    assert len(client.calls) > 0


def test_process_pair_without_llm_no_insights(home_pair: RenewalPair):
    result = process_pair(home_pair, llm_client=None)
    assert len(result.llm_insights) == 0


def test_generate_summary_with_mock(home_pair: RenewalPair):
    client = MockLLMClient()
    result = process_pair(home_pair, llm_client=None)
    result.pair = home_pair
    summary = generate_summary(client, result)
    assert summary is not None
    assert len(summary) > 0
    assert any("review_summary" in call[1] for call in client.calls)


def test_generate_summary_llm_error(home_pair: RenewalPair):
    class ErrorClient:
        def complete(self, prompt: str, trace_name: str) -> dict:
            return {"error": "API unavailable"}

    result = process_pair(home_pair, llm_client=None)
    result.pair = home_pair
    summary = generate_summary(ErrorClient(), result)
    assert summary is None


def test_generate_summary_no_pair(home_pair: RenewalPair):
    result = process_pair(home_pair, llm_client=None)
    result.pair = None
    client = MockLLMClient()
    summary = generate_summary(client, result)
    assert summary is None


def test_process_pair_with_llm_generates_natural_summary(home_pair: RenewalPair):
    client = MockLLMClient()
    result = process_pair(home_pair, llm_client=client)
    assert "Risk:" not in result.summary
    assert "Flags:" not in result.summary
