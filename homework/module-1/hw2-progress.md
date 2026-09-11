# HW2 progress note (local working note, not a submission file)

Style: interactive tutorial (handout walkthrough prompt). Started 2026-09-11.

## Current status
Part A done (offline span check passed). Next: Part B.

## Deliverables checklist
- [x] Part A: `record_tool_result` and `_set_permission_denied_attributes` in `observability/instrument.py`
- [ ] Part B: `create_session` in `server/app.py`; `uv run pytest --runxfail -vv tests/test_hw_holes.py -k "create_session_binds"` passes
- [ ] Part C: `post_message` in `server/app.py` with the `cartwheel.session_message` root span and its attributes
- [ ] Part D: `tests/test_observability.py` with two auth tests; `-k hw2` holes test, own tests, and full suite pass
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

## Prompt versions (Part F)
- current: (pending)
- earlier: (pending)

## Next step
Part B: implement `create_session` in `server/app.py`, then `uv sync` and the focused test.
