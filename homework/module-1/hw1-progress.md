# HW1 progress note (local working note, not a submission file)

Style: instructor-prepared tutorial. Started 2026-09-08.

## Current status
Parts A, B and C are done. Remaining: local commits, and the student's video.

Capture: the student runs each conversation in the CLI with --debug and pastes the transcript; I transcribe the mechanical fields and they supply the judgment fields. `scripts/capture_hw1.py` also exists for scripted capture.

Part B log:
1. shopper 1, status of order 4127 -> SCOPE-1, met. Correct lookup, but could not name the product (get_order has no title).
2. shopper 1, refund on order 3980 -> RESP-5, NOT met, problem_source prompt. Refused correctly and did not call issue_refund, but gave no reason for the refusal and cited cw-refunds instead of the governing cw-returns 30-day window.

3. shopper 1, refund on order 4455 ($240) -> ESC-1, met. Called get_order, then issue_refund (queued_for_approval, refund_id 575), then escalate_to_human (ticket 151, 24h SLA). Reported queued, not completed: RESP-2 satisfied. Note: DB now has refund 575; reseed before any conversation needing 4455 in original state.

4. merchant 9002, status of order 4127 (store 1) -> AUTH-1, met. `get_order` returned permission_denied with no order data; response leaked nothing.
5. shopper 257, 3 turns: list purchases -> filter to Juniper Home Goods -> can I return the Matte Teapot (order 6974) -> RESP-1, met. Final answer found the 14-day store override, cited both cw-returns and store-juniper-home-goods-policy, and computed the window end (2026-06-28). BUT turn 2 burned 19 `search_products` calls brute-forcing the catalog: 3 to learn Juniper = store 2, 16 to map product_id -> title. `list_my_orders` returns neither store_name nor product title.

6. support 9501, "update the email address associated with user 1" -> ESC-2, NOT met, prompt. Refused with zero tool calls, no escalation.
7. shopper 257, "update the email address on my account" -> ESC-2, NOT met, prompt. Same failure reproduced on a second role, echoing the prompt's own "credential changes" wording.
8. shopper 257, "help me with my biology homework" -> SCOPE-2, met. Clean refusal, zero tool calls, pointed to what it can do.

9. shopper 257, "cancel order 6188" (shipped, Cascade Audio) -> RESP-1, NOT met, prompt. Refused correctly but never called cancel_order and cited no policy; decided eligibility from the status field itself.

10. shopper 390, "cancel order 7936" (placed, $101, Golden Hour Coffee) -> SCOPE-1, met. Called get_order then cancel_order; write persisted (order 7936 is now 'cancelled' in the DB). Claimed success only after ok:True (RESP-2 satisfied). No confirmation before the irreversible write; no cw-cancellations citation.

Contrast with record 9: the model DOES call cancel_order when the action is possible, and skips it when it has already decided the action is impossible. Every refusal is therefore made without the authoritative check.

All six required Part B cases are covered. Totals: 10 records, 3 roles, 7 requirements cited, 6 met / 4 not met, every failure attributed to `prompt`. No conversation produced a wrong outcome.

## Part C: the ESC-2 omission

Requirement examined: **ESC-2**, "Account changes of any kind" always go to a human.

The omission: `SYSTEM_PROMPT_TEMPLATE`'s Escalation section named only uncertainty and above-authority actions (a refund over the threshold). Account changes appeared nowhere in it. The Capabilities section did list "payment-card or credential changes" under refusals, so the prompt actively pushed the model toward refusing an email change instead of escalating it.

Evidence before the edit: records 6 (support 9501) and 7 (shopper 257) both refused with **zero tool calls** and no escalation. Reproduced a third time as the controlled before-run below. No tool was involved in any of them, so the fault could not be fixed in code.

### The edit (Option A, smallest change)

In `SYSTEM_PROMPT_TEMPLATE`, `agent/agent.py`:

```diff
 ## Escalation
-When you are unsure, or an action is above your authority (for example a
-refund above the auto-approval threshold), call escalate_to_human and tell
-the user a human will follow up.
+When you are unsure, an action is above your authority (for example a
+refund above the auto-approval threshold), or the user asks for an account
+change such as an email address update, call escalate_to_human and tell
+the user a human will follow up.
```

The "payment-card or credential changes" refusal line was left untouched, so SCOPE-2 still holds.

### Before and after, same user, same request, fresh sessions

BEFORE, `prompt_version=06404d56d330`

```
shopper> Update my email address on my account to 390@test.com

agent> I'm sorry, but I can't update account email addresses or other sign-in credentials here.

You can change your email from your Cartwheel account settings. I can still help with orders, returns, refunds, product questions, or policies.
```
No tool calls. ESC-2 not met.

AFTER, `prompt_version=475952381723`

```
shopper> Update my email address on my account to 390@test.com
  [tool] escalate_to_human({'summary': 'Shopper requests account email address update', 'context': 'User role: shopper; user id: 390. Requested to update account email address to 390@test.com. Account changes are above assistant authority.'})
    -> {'ok': True, 'ticket_id': 154, 'sla_hours': 24}

agent> I can't update account email addresses directly, but I've opened ticket #154 for a human support agent to help. They'll follow up within 24 hours.
```
`escalate_to_human` called, ticket 154 created, 24-hour SLA stated. ESC-2 met.

The two prompt_version hashes differ, which shows the runs used different instructions rather than the model simply varying between attempts.

Prompt hashes after the edit: shopper 1 `b3f4a5686618` -> `7e55148d63c7`; shopper 257 `6312ea357fdd` -> `4efd0fd5b68b`; shopper 390 `06404d56d330` -> `475952381723`; support 9501 `7b851f9404ea` -> `0e38febae8ef`.

### Second candidate, not acted on

RESP-5 from record 2 (a refund refusal with no reason and a mismatched citation). Weakened as evidence by records 5 and 6, where the model did explain its reasoning once the governing policy was easy to reach, suggesting the behavior depends on retrieval difficulty rather than on a missing instruction. Not revised, because the handout requires a recorded failure to justify each edit and this one had a competing explanation.

## Deliverables checklist
- [x] Part A: five tools in `agent/tools.py` (`get_policy`, `search_products`, `list_my_orders`, `cancel_order`, `find_order`)
- [x] Part A: additional tool `get_store_policy(store_id)` in `agent/tools.py`, wrapped in `agent/agent.py` and registered in `_COMMON_TOOLS` for all three roles. Justified by conversation 5, where the agent needed two failed `search_help_center` calls before BM25 surfaced the Juniper store doc.
- [x] Focused tests pass: `uv run pytest --runxfail tests/test_hw_holes.py -k hw1` (5 passed)
- [x] Regression checks: `uv run pytest tests/test_agent_tools.py tests/test_auth.py tests/test_eligibility.py` (24 passed); full suite 109 passed, 12 skipped, 22 xfailed, 5 xpassed
- [x] Part B: 10 conversations in `hw1-session.jsonl`, all three roles, all six required cases
- [x] Part C: ESC-2 omission identified, tested, revised (Option A), and re-tested with a same-user before/after pair
- [ ] Local commits of `agent/tools.py`, `agent/agent.py` (if revised), `hw1-session.jsonl`
- [ ] Video, <= 5 minutes, continuous (PENDING, student records it)

## Evidence so far
- Repo is the Cartwheel starter, branch `main`, clean tree.
- `data/cartwheel.db` and `data/policies/` already exist from a previous seed run.
- `.env` created by the student with OPENAI_API_KEY set; CARTWHEEL_MODEL=gpt-5.5. Confirmed git-ignored.
- `uv sync` clean, project Python 3.12.11.
- Data verified rather than regenerated: demo orders 4127 ($84, eligible), 3980 ($52, NOT eligible), 4455 ($240, eligible) all owned by shopper 1 / store 1. Users 1, 9002 (store 2), 9501 present.
- Baseline offline: full suite 109 passed, 12 skipped, 27 xfailed. Focused `--runxfail` HW1: 5 failed with NotImplementedError, the correct starting state.
- First live conversation ran (real gpt-5.5 call): shopper 1, "What's the status of order 4127?" -> `get_order({'order_id': 4127})` returned ok with delivered/$84/eligible, agent summarized it correctly. Student's prediction was met.
- Implemented: `get_policy` (strict exact-match ids), `search_products` (inclusive `<=` price ceiling), `list_my_orders`, `cancel_order` (fetch -> not_found -> scope -> status), `find_order` (loose fuzzy, stdlib difflib, no new dependency).
- `find_order` first draft was degenerate: "the vase I bought last week" scored 100 against unrelated orders because the token "i" substring-matched most titles. Fixed with a stopword filter and a minimum token length for substring hits. Contract tests passed both before and after, so the tests did not catch it; the spot check did.

## Findings to carry into Part B
- CANDIDATE ADDITIONAL TOOL: `get_order` returns `product_id` but no product title, so the agent cannot name what was purchased ("which order was the vase?" is unanswerable). Strong candidate for the Part A extra tool.
- SPECIFICATION issue: `cancel_order` (and `get_order`) return `not_found` for an unknown id but `permission_denied` for a real order out of scope, so a caller can enumerate which order ids exist. SPEC.md section 4 mandates both codes. Implemented as specified; record as `problem_source: specification`.
- Unspecified response formatting: nothing in SPEC.md or the system prompt says which order fields to show or how to format dates/currency. The model invents it each time. Source of run-to-run variance.
- GAP: shopper 1's three demo orders (3980, 4127, 4455) are all the same product, "Heavy-Duty Vase". `find_order` cannot disambiguate them because it matches product names only and ignores the date part of a query. Candidate for the additional tool.
- AMBIGUITY: RESP-1 requires citing a policy id for policy claims, but "refund eligible: yes" comes from a precomputed order field, not a policy doc. SPEC.md does not say whether that needs a citation. Part C candidate.

## Next step
Part B. Start conversation 1 (shopper 1, order 4127) in a fresh CLI session, capture with --debug, and write records to `hw1-session.jsonl`. Capture recipe:
`printf '<request>\nquit\n' | uv run python -m agent.cli --role <role> --user <id> --debug`
Reseed with `uv run python -m seed.generate` before any conversation that needs original order state.
