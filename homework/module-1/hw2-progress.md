# HW2 progress note (local working note, not a submission file)

Style: interactive tutorial (handout walkthrough prompt). Started 2026-09-11.

## Current status
Parts A, B, C done (B focused test passed per student). Next: Part D.

## Deliverables checklist
- [x] Part A: `record_tool_result` and `_set_permission_denied_attributes` in `observability/instrument.py`
- [x] Part B: `create_session` in `server/app.py`; `uv run pytest --runxfail -vv tests/test_hw_holes.py -k "create_session_binds"` passes
- [x] Part C: `post_message` in `server/app.py` with the `cartwheel.session_message` root span and its attributes
- [~] Part D: `tests/test_observability.py` written, 2 passed; `-k hw2` xpassed. Full suite: 1 remaining failure (`test_m2_run_judge_persists_store_predictions_for_prevalence`, Langfuse connection refused), being bisected
- [ ] Part E: Langfuse up in Docker, server up, at least five traced requests from `hw1-session.jsonl`, root and tool spans inspected
- [ ] Part F: same request under two prompt versions, two different `cartwheel.prompt_version` hashes recorded
- [ ] `hw2-traces.json` with exactly two trace records
- [ ] Commit `observability/instrument.py`, `server/app.py`, `tests/test_observability.py`, `hw2-traces.json`
- [ ] Video, <= 5 minutes, continuous (PENDING, student records it)

## Evidence so far
- HW1 complete: all five tools implemented in `agent/tools.py`, 10 records in `hw1-session.jsonl`, prompt revised (ESC-2 escalation edit). The pre-revision prompt in `hw1-progress.md` is the "earlier version" available for Part F.
- `data/cartwheel.db` and `data/policies/` present.
- `.env` present with (names only) a model key, `CARTWHEEL_MODEL`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`, `TRACELOOP_TRACE_CONTENT`, `CARTWHEEL_DEV_SECRET`.
- Docker 28 with Compose v2 installed.
- HW2 placeholders untouched: `create_session`, `post_message` (server/app.py); `record_tool_result`, `_set_permission_denied_attributes` (observability/instrument.py).

## HW1 regression fixed during Part D (2026-09-12)
- Upstream merge added `db.list_order_search_candidates` and `test_hw1_find_order_roles_and_old_matches`; the HW1 `find_order` still searched only the 20 newest orders and returned extra keys. Rewrote the scope/output in `agent/tools.py` and raised `FIND_ORDER_MIN_SCORE` to 80 (max-over-token-pairs scoring let one weak pair match once the whole history was searched). `-k hw1` 8 passed; tool/auth/eligibility 24 passed; one live CLI spot check OK. `agent/tools.py` now needs committing with the HW2 files.

## Prompt versions (Part F)
- current: (pending)
- earlier: (pending)

## Next step
Part D: bisect which earlier test leaks `LANGFUSE_*` into the process so the m2 judge test goes live; then full suite green.
