"""Langfuse Experiment 실행 스크립트.

등록된 3개 Dataset에 대해 OpenAI / Anthropic 두 provider로 실험을 실행한다.
각 실험 결과는 Langfuse에 trace + generation으로 기록되어 대시보드에서 비교 가능.

Usage:
    uv run python scripts/langfuse_experiment.py
    uv run python scripts/langfuse_experiment.py --dataset risk
    uv run python scripts/langfuse_experiment.py --provider openai

Required env vars:
    OPENAI_API_KEY, ANTHROPIC_API_KEY,
    LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
"""

import argparse
import json
import os
import re
import sys
import time

from app.adaptor.llm.prompts import (
    ENDORSEMENT_COMPARISON,
    RISK_SIGNAL_EXTRACTOR,
)
from dotenv import load_dotenv
from langfuse import Evaluation, Langfuse


def _check_env():
    load_dotenv()
    required = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST")
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        print(f"Missing env vars: {', '.join(missing)}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Prompt templates (from app/llm/prompts.py)
# ---------------------------------------------------------------------------
PROMPTS = {
    "risk-signal-benchmark": RISK_SIGNAL_EXTRACTOR,
    "endorsement-benchmark": ENDORSEMENT_COMPARISON,
}

# ---------------------------------------------------------------------------
# Provider config
# ---------------------------------------------------------------------------
PROVIDERS = {
    "openai": {"model": "gpt-4o-mini", "env_key": "OPENAI_API_KEY"},
    "anthropic": {
        "model": "claude-sonnet-4-5-20250929",
        "env_key": "ANTHROPIC_API_KEY",
    },
    "anthropic-haiku": {
        "model": "claude-haiku-4-5-20251001",
        "env_key": "ANTHROPIC_API_KEY",
    },
}


def _call_openai(prompt: str, model: str) -> tuple[str, dict]:
    from openai import OpenAI

    client = OpenAI()
    start = time.time()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    latency = time.time() - start
    raw = resp.choices[0].message.content
    return raw, {
        "latency_s": round(latency, 2),
        "input_tokens": resp.usage.prompt_tokens,
        "output_tokens": resp.usage.completion_tokens,
        "total_tokens": resp.usage.total_tokens,
    }


def _call_anthropic(prompt: str, model: str) -> tuple[str, dict]:
    from anthropic import Anthropic

    client = Anthropic()
    start = time.time()
    resp = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    latency = time.time() - start
    raw = resp.content[0].text
    return raw, {
        "latency_s": round(latency, 2),
        "input_tokens": resp.usage.input_tokens,
        "output_tokens": resp.usage.output_tokens,
        "total_tokens": resp.usage.input_tokens + resp.usage.output_tokens,
    }


CALLERS = {
    "openai": _call_openai,
    "anthropic": _call_anthropic,
    "anthropic-haiku": _call_anthropic,
}

_JSON_BLOCK = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)


def _extract_json(raw: str) -> str:
    m = _JSON_BLOCK.search(raw)
    return m.group(1).strip() if m else raw.strip()


# ---------------------------------------------------------------------------
# Evaluators
# ---------------------------------------------------------------------------
def json_valid_evaluator(*, output, **kwargs):
    try:
        if isinstance(output, dict):
            score = 0.0 if "error" in output else 1.0
        else:
            json.loads(str(output))
            score = 1.0
    except (json.JSONDecodeError, TypeError):
        score = 0.0
    return Evaluation(name="json_valid", value=score)


def _calc_key_match(output, expected_output, dataset_name) -> float:
    if not isinstance(output, dict) or "error" in output:
        return 0.0

    if dataset_name == "risk-signal-benchmark":
        if "signals" in output and "signals" in expected_output:
            n_out = len(output["signals"])
            n_exp = len(expected_output["signals"])
            return 1.0 if n_out == n_exp else 0.5
        return 0.0

    if dataset_name == "endorsement-benchmark":
        keys = ["material_change", "change_type"]
        matches = sum(1 for k in keys if output.get(k) == expected_output.get(k))
        return matches / len(keys)

    return 0.0


# ---------------------------------------------------------------------------
# Task factory
# ---------------------------------------------------------------------------
def make_task(provider: str, dataset_name: str):
    cfg = PROVIDERS[provider]
    model = cfg["model"]
    caller = CALLERS[provider]
    prompt_template = PROMPTS[dataset_name]

    def task(*, item, **kwargs):
        prompt = prompt_template.format(**item.input)

        raw = ""
        try:
            raw, usage_info = caller(prompt, model)
            cleaned = _extract_json(raw)
            result = json.loads(cleaned)
            result["_usage"] = usage_info
        except json.JSONDecodeError:
            result = {"error": "JSON parse failed", "raw": raw}
        except Exception as e:
            result = {"error": str(e)}

        return result

    return task


def make_evaluators(dataset_name: str):
    def _key_match(*, output, expected_output, **kwargs):
        score = _calc_key_match(output, expected_output, dataset_name)
        return Evaluation(name="key_match", value=score)

    return [json_valid_evaluator, _key_match]


# ---------------------------------------------------------------------------
# Run experiment
# ---------------------------------------------------------------------------
def run_experiment(langfuse: Langfuse, dataset_name: str, provider: str):
    cfg = PROVIDERS[provider]
    if not os.getenv(cfg["env_key"]):
        print(f"  Skipping {provider} — {cfg['env_key']} not set")
        return

    run_name = f"{dataset_name}-{provider}"
    dataset = langfuse.get_dataset(dataset_name)

    print(f"\n  Running: {run_name} ({len(dataset.items)} items, model={cfg['model']})")

    result = langfuse.run_experiment(
        name=run_name,
        data=dataset.items,
        task=make_task(provider, dataset_name),
        evaluators=make_evaluators(dataset_name),
        max_concurrency=1,
        metadata={"provider": provider, "model": cfg["model"]},
    )

    for ir in result.item_results:
        policy = ir.item.metadata.get("policy", "?")
        has_error = isinstance(ir.output, dict) and "error" in ir.output
        status = "FAIL" if has_error else "OK"

        evals = {e.name: e.value for e in ir.evaluations}

        if has_error:
            err = ir.output.get("error", "unknown")
            print(f"    {policy} — {status} ({err})")
        else:
            usage = ir.output.get("_usage", {}) if isinstance(ir.output, dict) else {}
            lat = usage.get("latency_s", "?")
            tok = usage.get("total_tokens", "?")
            print(f"    {policy} — {status} | latency={lat}s, tokens={tok} | scores={evals}")

    langfuse.flush()
    print(f"  Done: {run_name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
DATASET_ALIASES = {
    "risk": "risk-signal-benchmark",
    "endorsement": "endorsement-benchmark",
}


def main():
    _check_env()

    parser = argparse.ArgumentParser(description="Run Langfuse experiments")
    parser.add_argument(
        "--dataset",
        choices=["risk", "endorsement"],
        help="Run only this dataset (default: all)",
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic", "anthropic-haiku"],
        help="Run only this provider (default: all)",
    )
    args = parser.parse_args()

    datasets = [DATASET_ALIASES[args.dataset]] if args.dataset else list(DATASET_ALIASES.values())
    providers = [args.provider] if args.provider else ["openai", "anthropic", "anthropic-haiku"]

    langfuse = Langfuse()

    print("=== Langfuse Experiment Runner ===")
    print(f"Datasets: {datasets}")
    print(f"Providers: {providers}")

    for ds in datasets:
        print(f"\nDataset: {ds}")
        for prov in providers:
            run_experiment(langfuse, ds, prov)

    print("\n=== All experiments complete ===")
    print("View results: Langfuse → Datasets → select dataset → Runs")


if __name__ == "__main__":
    main()
