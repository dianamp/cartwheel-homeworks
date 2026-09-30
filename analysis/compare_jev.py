"""Compare a Jev (TypeSafe) judge with the gpt-4o-mini verbose_reply judges.

Run from the repository root with ``JEV_API_KEY`` in ``.env``:

    uv run python -m analysis.compare_jev plan              # offline: request sizes, no API calls
    uv run --env-file .env python -m analysis.compare_jev dev
    uv run python -m analysis.compare_jev freeze any_rule 0.5
    uv run --env-file .env python -m analysis.compare_jev test
    uv run --env-file .env python -m analysis.compare_jev swap gpt-5-mini   # frozen v0 prompt, other model
    uv run --env-file .env python -m analysis.compare_jev langfuse          # log cached Jev answers
    uv run --env-file .env python -m analysis.compare_jev versions v1       # v0 vs another question version

``--version v1`` points ``dev``, ``test``, ``plan``, and ``langfuse`` at
``verbose_reply-jev-v1.json`` and its own cache. The default is v0.

Jev returns a yes probability for each Noul question in
``analysis/prompts/verbose_reply-jev-v0.json`` and no critique. A decision rule
turns those probabilities into Pass/Fail:

- ``any_rule``: Fail when any rule question (repetition, unneeded mechanics,
  unsolicited offer) is above the threshold.
- ``holistic``: Fail when the single ``verbose`` question is above the threshold.

``dev`` runs the train and dev splits and reports every rule and threshold
next to gpt-4o-mini v0 to v4 on the current labels. Pick one rule and threshold
from dev, ``freeze`` it, and only then run ``test``, the same way the
gpt-4o-mini judge was frozen before its test run. The judge sees the same
``hw5_trace_inputs.json`` records; labels stay out of the request.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from analysis.helpers.tools import _wilson_interval

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "analysis" / "state"
REPORT = ROOT / "analysis" / "report"
MODE = "verbose_reply"
VERSION = "v0"
QUESTIONS_FILE = ROOT / "analysis" / "prompts" / f"{MODE}-jev-{VERSION}.json"
CACHE_FILE = STATE / "judges" / f"{MODE}-jev-{VERSION}.json"
ENDPOINT = "https://api.typesafe.ai/v1/systemone"
OPENAI_JUDGES = [f"{MODE}-v{i}" for i in range(5)]
THRESHOLDS = (0.3, 0.4, 0.5, 0.6, 0.7)


def use_version(version: str) -> None:
    """Point the module at one question version and its answer cache."""
    global VERSION, QUESTIONS_FILE, CACHE_FILE
    VERSION = version
    QUESTIONS_FILE = ROOT / "analysis" / "prompts" / f"{MODE}-jev-{version}.json"
    CACHE_FILE = STATE / "judges" / f"{MODE}-jev-{version}.json"


def _spec() -> dict[str, Any]:
    return json.loads(QUESTIONS_FILE.read_text())


def _labels() -> dict[str, int]:
    """HW5 labels, 1 = Pass, 0 = Fail."""
    path = STATE / "hw5_labels" / f"{MODE}.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return {r["trace_id"]: int(r["label"]) for r in rows}


def _splits() -> dict[str, list[str]]:
    return json.loads((STATE / "splits.json").read_text())[MODE]


def build_state(record: dict[str, Any]) -> dict[str, Any]:
    """Split a saved input record into the named fields the questions refer to."""
    messages = record["trace"]
    final = messages[-1]
    request = messages[-2]
    assert final["role"] == "assistant" and request["role"] == "user", record["trace_id"]
    return {
        "earlier_conversation": [{"role": m["role"], "text": m["text"]} for m in messages[:-2]],
        "user_request": request["text"],
        "final_reply": final["text"],
    }


def _load_cache() -> dict[str, Any]:
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text())
    spec = _spec()
    return {
        "judge_id": f"{MODE}-jev-{VERSION}",
        "model": spec["model"],
        "questions_file": str(QUESTIONS_FILE.relative_to(ROOT)),
        "questions_hash": _hash(spec["questions"]),
        "status": "draft",
        "decision": None,
        "answers": {},
    }


def _hash(obj: Any) -> str:
    import hashlib

    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:12]


def _save_cache(cache: dict[str, Any]) -> None:
    CACHE_FILE.write_text(json.dumps(cache, indent=2) + "\n")


def _ask(client: httpx.Client, spec: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    body = {"model": spec["model"], "state": state, "questions": spec["questions"]}
    for attempt in range(6):
        response = client.post(ENDPOINT, json=body)
        if response.status_code == 429 or response.status_code >= 500:
            wait = float(response.headers.get("retry-after") or 2 ** attempt)
            time.sleep(min(wait, 30))
            continue
        response.raise_for_status()
        return response.json()
    response.raise_for_status()
    raise RuntimeError("Jev request kept failing")


def run_jev(trace_ids: list[str]) -> dict[str, Any]:
    """Ask Jev about each trace once; answers are cached by trace id."""
    spec = _spec()
    cache = _load_cache()
    if cache["questions_hash"] != _hash(spec["questions"]):
        raise RuntimeError(
            f"{QUESTIONS_FILE.name} changed after answers were cached; "
            "save the new questions as a new version instead."
        )
    records = {r["trace_id"]: r for r in json.loads((STATE / "hw5_trace_inputs.json").read_text())}
    todo = [t for t in trace_ids if t not in cache["answers"]]
    key = os.environ.get("JEV_API_KEY") or os.environ.get("TYPESAFE_API_KEY")
    if todo and not key:
        raise RuntimeError("JEV_API_KEY is not set; add it to .env and run with --env-file .env")
    with httpx.Client(headers={"Authorization": f"Bearer {key}"}, timeout=60) as client:
        for n, trace_id in enumerate(todo, 1):
            result = _ask(client, spec, build_state(records[trace_id]))
            cache["answers"][trace_id] = {
                "model": result.get("model"),
                "nouls": {q: a["noul"] for q, a in result["answers"].items()},
                "usage": result.get("usage"),
            }
            _save_cache(cache)
            print(f"  {n}/{len(todo)} {trace_id} {cache['answers'][trace_id]['nouls']}")
    return cache


def jev_fail(nouls: dict[str, float], rule: str, threshold: float) -> bool:
    spec = _spec()
    if rule == "any_rule":
        return max(nouls[q] for q in spec["rule_questions"]) > threshold
    if rule == "holistic":
        return nouls[spec["holistic_question"]] > threshold
    raise ValueError(rule)


def metrics(preds: dict[str, int], trace_ids: list[str]) -> dict[str, Any]:
    """TPR/TNR with Pass (1) as the positive class, Wilson 95% intervals."""
    labels = _labels()
    tp = sum(labels[t] == 1 and preds[t] == 1 for t in trace_ids)
    fn = sum(labels[t] == 1 and preds[t] == 0 for t in trace_ids)
    tn = sum(labels[t] == 0 and preds[t] == 0 for t in trace_ids)
    fp = sum(labels[t] == 0 and preds[t] == 1 for t in trace_ids)
    tpr = tp / (tp + fn) if tp + fn else 0.0
    tnr = tn / (tn + fp) if tn + fp else 0.0
    return {
        "tpr": round(tpr, 4), "tnr": round(tnr, 4),
        "tpr_interval": _wilson_interval(tp, tp + fn),
        "tnr_interval": _wilson_interval(tn, tn + fp),
        "balanced_accuracy": round((tpr + tnr) / 2, 4),
        "agreement": round((tp + tn) / len(trace_ids), 4),
        "tp": tp, "fn": fn, "tn": tn, "fp": fp, "n": len(trace_ids),
    }


def openai_preds(judge_id: str) -> dict[str, int]:
    """Saved gpt-4o-mini verdicts, 1 = Pass (the judges use pass_positive)."""
    judge = json.loads((STATE / "judges" / f"{judge_id}.json").read_text())
    assert judge["label_convention"] == "pass_positive"
    return {t: int(v) for t, v in judge["predictions"][judge["prompt_hash"]].items()}


def jev_preds(cache: dict[str, Any], rule: str, threshold: float) -> dict[str, int]:
    return {t: 0 if jev_fail(a["nouls"], rule, threshold) else 1 for t, a in cache["answers"].items()}


def model_swap_path(model: str) -> Path:
    return STATE / "judges" / f"{MODE}-v0-{model}.json"


def run_model_swap(model: str, splits_to_run: tuple[str, ...] = ("dev", "test")) -> dict[str, Any]:
    """Run the frozen v0 prompt unchanged on another OpenAI model.

    Uses the same DocETL path as ``run_judge`` but caches into its own file,
    so the HW5 judge history and the frozen v0 record stay untouched.
    """
    from analysis.helpers import scale

    os.environ.setdefault("CARTWHEEL_JUDGE_TRACE_SOURCE", str(STATE / "hw5_trace_inputs.json"))
    frozen = json.loads((STATE / "judges" / f"{MODE}-v0.json").read_text())
    assert frozen["status"] == "frozen"
    path = model_swap_path(model)
    record = json.loads(path.read_text()) if path.exists() else {
        "base_judge": frozen["judge_id"], "base_prompt_hash": frozen["prompt_hash"],
        "model": model, "label_convention": "pass_positive",
        "predictions": {}, "critiques": {},
    }
    splits = _splits()
    ids = [t for s in splits_to_run for t in splits[s]]
    todo = [t for t in ids if t not in record["predictions"]]
    for start in range(0, len(todo), 10):
        batch = todo[start:start + 10]
        fresh = scale.classify_store(frozen["prompt_text"], model, batch)
        record["predictions"].update({t: int(p) for t, p in fresh.items()})
        record["critiques"].update(getattr(fresh, "critiques", {}) or {})
        path.write_text(json.dumps(record, indent=2) + "\n")
        print(f"  {len(record['predictions'])}/{len(ids)}")
    out: dict[str, Any] = {"model": model, "prompt": f"{MODE}-v0 (frozen)"}
    for split in splits_to_run:
        lines = [f"### {split}", "", HEADER]
        out[split] = {}
        for name, preds in (("gpt-4o-mini", openai_preds(f"{MODE}-v0")),
                            (model, record["predictions"])):
            m = metrics(preds, splits[split])
            out[split][name] = m
            lines.append(_row(f"v0 on {name}", m))
        print("\n".join(lines))
    (REPORT / f"model-swap-{MODE}-v0-{model}.json").write_text(json.dumps(out, indent=2) + "\n")
    return out


def log_to_langfuse() -> dict[str, Any]:
    """Write the cached Jev answers to Langfuse, one trace per judged trace.

    No Jev calls are made: each trace holds the saved request (state and
    questions) and answers as a generation, plus one score per question. Trace
    ids are seeded from the Cartwheel trace id, and logged ids are recorded in
    the cache, so a rerun only adds traces that are missing.
    """
    from langfuse import Langfuse

    spec = _spec()
    cache = _load_cache()
    records = {r["trace_id"]: r for r in json.loads((STATE / "hw5_trace_inputs.json").read_text())}
    split_of = {t: s for s in ("train", "dev", "test") for t in _splits()[s]}
    scenario = {json.loads(line)["trace_id"]: json.loads(line)["scenario_id"]
                for line in (STATE / "hw5_labels" / f"{MODE}.jsonl").read_text().splitlines() if line.strip()}
    logged = set(cache.setdefault("langfuse_logged", []))
    lf = Langfuse()
    urls = {}
    for trace_id, answer in cache["answers"].items():
        if trace_id in logged:
            continue
        lf_trace_id = lf.create_trace_id(seed=f"{cache['judge_id']}:{trace_id}")
        nouls = answer["nouls"]
        verdict = "Fail" if jev_fail(nouls, "any_rule", 0.5) else "Pass"
        metadata = {"cartwheel_trace_id": trace_id, "scenario_id": scenario.get(trace_id),
                    "split": split_of.get(trace_id), "questions_hash": cache["questions_hash"],
                    "verdict_any_rule_0.5": verdict}
        with lf.start_as_current_span(
            name=cache["judge_id"], trace_context={"trace_id": lf_trace_id},
            input={"state": build_state(records[trace_id])}, output={"nouls": nouls, "verdict": verdict},
            metadata=metadata,
        ) as span:
            span.update_trace(name=cache["judge_id"], tags=["jev", MODE, split_of.get(trace_id, "none")],
                              metadata=metadata)
            with span.start_as_current_observation(
                as_type="generation",
                name="jev systemone", model=answer.get("model") or spec["model"],
                input={"state": build_state(records[trace_id]), "questions": spec["questions"]},
                output=nouls,
                usage_details={"input": (answer.get("usage") or {}).get("input_tokens", 0),
                               "output": (answer.get("usage") or {}).get("output_tokens", 0)},
            ):
                pass
            for question, value in nouls.items():
                span.score_trace(name=f"jev_{question}", value=float(value), data_type="NUMERIC")
        urls[trace_id] = lf.get_trace_url(trace_id=lf_trace_id)
        logged.add(trace_id)
    lf.flush()
    cache["langfuse_logged"] = sorted(logged)
    _save_cache(cache)
    return urls


def _row(name: str, m: dict[str, Any]) -> str:
    lo_p, hi_p = m["tpr_interval"]
    lo_f, hi_f = m["tnr_interval"]
    return (f"| {name} | {m['tpr']:.3f} [{lo_p:.3f}, {hi_p:.3f}] | {m['tnr']:.3f} [{lo_f:.3f}, {hi_f:.3f}] "
            f"| {m['balanced_accuracy']:.3f} | {m['tp']} / {m['fn']} / {m['tn']} / {m['fp']} |")


HEADER = "| Judge | TPR [95% CI] | TNR [95% CI] | Balanced acc. | TP / FN / TN / FP |\n| --- | --- | --- | --- | --- |"


def plan() -> None:
    """Offline check: one state per labeled trace, request sizes in characters."""
    spec = _spec()
    records = json.loads((STATE / "hw5_trace_inputs.json").read_text())
    sizes = [len(json.dumps({"state": build_state(r), "questions": spec["questions"]})) for r in records]
    splits = _splits()
    print(json.dumps({
        "model": spec["model"],
        "questions": list(spec["questions"]),
        "traces": {s: len(splits[s]) for s in ("train", "dev", "test")},
        "request_chars_max": max(sizes),
        "request_chars_total": sum(sizes),
        "approx_input_tokens_total": sum(sizes) // 4,
    }, indent=2))


def dev() -> dict[str, Any]:
    splits = _splits()
    cache = run_jev(splits["train"] + splits["dev"])
    out: dict[str, Any] = {"split": "dev", "model": cache["model"], "jev": {}, "openai": {}}
    lines = [f"### Dev ({sum(_labels()[t] == 1 for t in splits['dev'])} Pass / "
             f"{sum(_labels()[t] == 0 for t in splits['dev'])} Fail, current labels)", "", HEADER]
    for judge_id in OPENAI_JUDGES:
        m = metrics(openai_preds(judge_id), splits["dev"])
        out["openai"][judge_id] = m
        lines.append(_row(f"gpt-4o-mini {judge_id.split('-')[-1]}", m))
    for rule in ("any_rule", "holistic"):
        for threshold in THRESHOLDS:
            name = f"{rule}@{threshold}"
            m = metrics(jev_preds(cache, rule, threshold), splits["dev"])
            out["jev"][name] = m
            lines.append(_row(f"Jev {name}", m))
    train = {f"{r}@{t}": metrics(jev_preds(cache, r, t), splits["train"])
             for r in ("any_rule", "holistic") for t in THRESHOLDS}
    out["jev_train"] = train
    REPORT.mkdir(parents=True, exist_ok=True)
    (REPORT / f"dev-{MODE}-jev-{VERSION}.json").write_text(json.dumps(out, indent=2) + "\n")
    print("\n".join(lines))
    return out


def freeze(rule: str, threshold: float) -> None:
    cache = _load_cache()
    if cache["status"] == "frozen":
        raise RuntimeError(f"already frozen with {cache['decision']}")
    cache["status"] = "frozen"
    cache["decision"] = {"rule": rule, "threshold": threshold,
                         "frozen_at": datetime.now(timezone.utc).isoformat()}
    _save_cache(cache)
    print(json.dumps(cache["decision"], indent=2))


def test() -> dict[str, Any]:
    cache = _load_cache()
    if cache["status"] != "frozen":
        raise RuntimeError("freeze a decision rule on dev before running test")
    splits = _splits()
    cache = run_jev(splits["test"])
    rule, threshold = cache["decision"]["rule"], cache["decision"]["threshold"]
    labels = _labels()
    jev = metrics(jev_preds(cache, rule, threshold), splits["test"])
    gpt = metrics(openai_preds(f"{MODE}-v0"), splits["test"])
    both_wrong = sum(
        jev_preds(cache, rule, threshold)[t] != labels[t] and openai_preds(f"{MODE}-v0")[t] != labels[t]
        for t in splits["test"]
    )
    out = {
        "split": "test", "model": cache["model"], "decision": cache["decision"],
        "class_counts": {"pass": sum(labels[t] == 1 for t in splits["test"]),
                         "fail": sum(labels[t] == 0 for t in splits["test"])},
        "jev": jev, "gpt-4o-mini v0 (frozen)": gpt, "both_wrong": both_wrong,
        "input_tokens": sum((cache["answers"][t].get("usage") or {}).get("input_tokens", 0)
                            for t in splits["test"]),
    }
    (REPORT / f"test-{MODE}-jev-{VERSION}.json").write_text(json.dumps(out, indent=2) + "\n")
    print("\n".join([HEADER, _row("gpt-4o-mini v0 (frozen)", gpt), _row(f"Jev {rule}@{threshold}", jev)]))
    print(json.dumps({k: out[k] for k in ("class_counts", "both_wrong", "input_tokens")}))
    return out


def compare_versions(other: str, base: str = "v0") -> dict[str, Any]:
    """Every rule and threshold for two question versions on dev and test.

    Runs any missing Jev answers for ``other`` on all splits first. Neither
    version is frozen here, so the test rows are descriptive, like the v0
    all-rules test report.
    """
    splits = _splits()
    caches = {}
    for version in (base, other):
        use_version(version)
        caches[version] = run_jev(splits["train"] + splits["dev"] + splits["test"])
    out: dict[str, Any] = {"base": base, "other": other,
                           "note": "All decision rules shown on dev and test; none frozen from dev first.",
                           "questions_hash": {v: c["questions_hash"] for v, c in caches.items()}}
    labels = _labels()
    for split in ("dev", "test"):
        ids = splits[split]
        lines = [f"### {split} ({sum(labels[t] == 1 for t in ids)} Pass / "
                 f"{sum(labels[t] == 0 for t in ids)} Fail)", "", HEADER,
                 _row("gpt-4o-mini v0 (frozen)", metrics(openai_preds(f"{MODE}-v0"), ids))]
        out[split] = {}
        for rule in ("any_rule", "holistic"):
            for threshold in THRESHOLDS:
                for version in (base, other):
                    use_version(version)
                    name = f"Jev {version} {rule}@{threshold}"
                    m = metrics(jev_preds(caches[version], rule, threshold), ids)
                    out[split][name] = m
                    lines.append(_row(name, m))
        print("\n".join(lines) + "\n")
    shift = {}
    for q in _spec()["questions"]:
        deltas = [caches[other]["answers"][t]["nouls"][q] - caches[base]["answers"][t]["nouls"][q]
                  for t in caches[base]["answers"]]
        shift[q] = round(sum(deltas) / len(deltas), 4)
    out["mean_yes_probability_shift"] = shift
    print("mean yes-probability shift, " + other + " minus " + base + ": " + json.dumps(shift))
    (REPORT / f"versions-{MODE}-jev-{base}-vs-{other}.json").write_text(json.dumps(out, indent=2) + "\n")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["plan", "dev", "freeze", "test", "swap", "langfuse", "versions"])
    parser.add_argument("rule", nargs="?", help="any_rule or holistic (freeze), or a model id (swap)")
    parser.add_argument("threshold", nargs="?", type=float)
    parser.add_argument("--version", default="v0", help="Jev question version (default v0)")
    args = parser.parse_args()
    use_version(args.version)
    if args.command == "versions":
        compare_versions(args.rule)
        return
    if args.command == "plan":
        plan()
    elif args.command == "dev":
        dev()
    elif args.command == "freeze":
        freeze(args.rule, args.threshold)
    elif args.command == "swap":
        run_model_swap(args.rule)
    elif args.command == "langfuse":
        urls = log_to_langfuse()
        print(f"logged {len(urls)} traces")
        for trace_id, url in list(urls.items())[:3]:
            print(f"  {trace_id} {url}")
    else:
        test()


if __name__ == "__main__":
    main()
