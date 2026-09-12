## Video

Have open before recording: terminal at repo root (server NOT needed), Langfuse with both traces bookmarked.

### 1. Auth test (30s)
- Run: `uv run pytest tests/test_observability.py -k role -v`
- Say: user 1 is a shopper in the DB; claiming merchant gets 403. Identity comes from the DB row, not the request.

### 2. Trace 1: shopper 1, refund for 3980 (60s)
- Open `8974f3ca...`, root span: `user_role=shopper`, `user_id="1"`, `prompt_version=1c43d7b67056`, input/output messages.
- Walk down: model call -> `get_order` (allowed, `permission_denied=false`, order not refund-eligible) -> model call writes the refusal.

### 3. Trace 2: merchant 9002, status of 7713 (60s)
- Open `0b2055b4...`, root span: `user_role=merchant`, `user_id="9002"`, same prompt_version.
- `get_order` span: `store_id="2"`, `permission_denied=false`, result shows the shipped order; final reply reports it.

### 4. How identity was established (30s)
- POST /sessions looked up the user in the DB, built AuthContext, signed a token with session_id, user_id, role, store_id, issued_at.
- Every message must carry that token; the tools only ever see the server-built AuthContext.

### 5. Prompt versions (30s)
- Open `110f3d21...` (1c43d7b67056) and `5fafca59...` (0811eb545d28): same merchant, same message, different hash.
- Only change was the three-line Escalation wording; the hash covers the template, not the injected user context.

### 6. Regenerate span count (30s)
- Run: `uv run python -c "from observability.instrument import load_env; load_env(); from langfuse import get_client; t=get_client().api.trace.get('0b2055b4ab4f178d3aaa0fa4b286be65'); print(len(t.observations), [o.name for o in sorted(t.observations, key=lambda o: o.start_time)])"`
- Say: 6 spans = 1 root (mine) + 2 SDK grouping + 2 model calls + 1 tool. The trace row in the UI is the container, not a span.

## Things I learned / questions

-
