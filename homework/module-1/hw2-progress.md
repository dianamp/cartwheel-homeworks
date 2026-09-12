# HW2 progress note (local working note, not a submission file)

Style: interactive tutorial (handout walkthrough prompt). Started 2026-09-11.

## Current status
Parts A to F done; hw2-traces.json complete. Remaining: commit hw2-traces.json, student's video.

## Deliverables checklist
- [x] Part A: `record_tool_result` and `_set_permission_denied_attributes` in `observability/instrument.py`
- [x] Part B: `create_session` in `server/app.py`; `uv run pytest --runxfail -vv tests/test_hw_holes.py -k "create_session_binds"` passes
- [x] Part C: `post_message` in `server/app.py` with the `cartwheel.session_message` root span and its attributes
- [x] Part D: `tests/test_observability.py` 2 passed; `-k hw2` 1 passed under `--runxfail`; full suite 135 passed, 12 skipped, 21 xfailed, 9 xpassed (offline)
- [x] Part E: Langfuse up (Docker fixed: credential helper symlink + upstream quay.io image), server up, 8 traces recorded (shopper 1, merchant 9002); root and tool span attributes confirmed via API
- [x] Part F: merchant 9002, "What is going on with order 4127?": current 1c43d7b67056 (trace 110f3d2109ac116768657c8cb4bcfb63) vs earlier HW1 wording 0811eb545d28 (trace 5fafca5968eb7970cb9486a5b17db0a0); prompt restored
- [x] `homework/module-1/hw2-traces.json`: shopper 1 / order 3980 (8974f3ca0d5aba217a5e50394061f84d) and merchant 9002 / order 7713 (0b2055b4ab4f178d3aaa0fa4b286be65)
- [~] Commit: instrument.py, app.py, test_observability.py, agent/tools.py, tests/conftest.py committed and pushed; hw2-traces.json still to commit
- [ ] Video, <= 5 minutes, continuous (PENDING, student records it)

## Evidence so far
- HW1 complete: all five tools implemented in `agent/tools.py`, 10 records in `hw1-session.jsonl`, prompt revised (ESC-2 escalation edit). The pre-revision prompt in `hw1-progress.md` is the "earlier version" available for Part F.
- `data/cartwheel.db` and `data/policies/` present.
- `.env` present with (names only) a model key, `CARTWHEEL_MODEL`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`, `TRACELOOP_TRACE_CONTENT`, `CARTWHEEL_DEV_SECRET`.
- Docker 28 with Compose v2 installed.
- HW2 placeholders untouched: `create_session`, `post_message` (server/app.py); `record_tool_result`, `_set_permission_denied_attributes` (observability/instrument.py).

## HW1 regression fixed during Part D (2026-09-12)
- Upstream merge added `db.list_order_search_candidates` and `test_hw1_find_order_roles_and_old_matches`; the HW1 `find_order` still searched only the 20 newest orders and returned extra keys. Rewrote the scope/output in `agent/tools.py` and raised `FIND_ORDER_MIN_SCORE` to 80 (max-over-token-pairs scoring let one weak pair match once the whole history was searched). `-k hw1` 8 passed; tool/auth/eligibility 24 passed; one live CLI spot check OK. `agent/tools.py` now needs committing with the HW2 files.

## Test isolation fix during Part D (2026-09-12)
- `litellm/__init__.py` calls `load_dotenv()` on import, leaking `.env`'s `LANGFUSE_*` into the pytest process after the first LiteLLM-routed CLI test; `test_m2_run_judge_persists_store_predictions_for_prevalence` then tried a live Langfuse. Added an autouse fixture `_offline_langfuse` in `tests/conftest.py` that removes the three variables per test. `tests/conftest.py` also needs committing.

## Part E findings
- Langfuse consumes `gen_ai.input.messages`/`gen_ai.output.messages` into the span's Input/Output fields; they do not appear under metadata attributes. Trace-level input/output populated (checked via `lf.api.trace.get`).
- Trace tree: trace row + root span (same name, not a duplicate) > Agent Workflow > cartwheel-support.agent > openai.response, list_my_orders, openai.response. Responses API spans carry `gen_ai.response.model`, no `gen_ai.request.model`.
- `cartwheel.store_id` now recorded as a string (upstream change); server restart needed before merchant requests.
- Session id is not on any span (not required); optional `session.id` root attribute would enable Langfuse Sessions grouping.

## Prompt versions (Part F)
- current: 1c43d7b67056
- earlier: 0811eb545d28 (HW1 pre-ESC-2 Escalation wording)

## Next step
Commit `homework/module-1/hw2-traces.json`, then the student records the video (plan in `hw2-notes.md`). Handout checks last run 2026-09-12: hw2 hole 1 passed, test_observability 2 passed, full suite 136 passed / 13 skipped / 21 xfailed / 9 xpassed, all offline. Live model calls this session: the Part E/F requests and one CLI find_order spot check.
