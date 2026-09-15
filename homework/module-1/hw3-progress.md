# HW3 progress note (local working note, not a submission file)

Style: interactive tutorial (handout walkthrough prompt). Started 2026-09-14.
Model for every run: gpt-5.5 (CARTWHEEL_MODEL in .env).

## Current status
Branch hw3 created. Preparation done. Part A approved. Starting Part B (pilot).

## Deliverables checklist
- [x] Preparation: data reset 2026-09-14 10:37; manual trace fcafd7432effb21eac4505c0bb53d901 (shopper 251, find_order) and runner smoke trace fd9f67c521984a99f7247b05583206f3 (cartwheel.scenario_id = smoke-0001) both complete. Two live calls.
- [x] Part A: dimension plan approved by the student 2026-09-14
- [x] Part B: `scenarios/pilot_scenarios.jsonl` (30 scenarios, validated, sample accepted by the student 2026-09-14)
- [x] Part B: `scenarios/pilot-results.jsonl` (student ran it; 30/30 completed on gpt-5.5)
- [x] Part B: `scenarios/pilot_review.jsonl` (13 reviewed, 6 confirmed failures; student's decisions)
- [x] Part C: `scenarios/support_scenarios.jsonl` (250 generated 2026-09-14, ~500 model calls; 65 critic rewrites; --final validation passes)
- [x] Part C: `scenarios/support_review.jsonl` (17 reviewed: 16 accept, 1 reject; both groups, all roles, all nine intents)
- [x] Part C: `scenarios/monitoring_scenarios.jsonl` (50: first five reviewed ids, then 25 challenge / 25 coverage by student's choice; all roles, all intents, 11 dq, 13 state-changing; seed 7)
- [x] Part C: `uv run python -m scenarios.validate scenarios/support_scenarios.jsonl --final` passes (after the 0026 replacement)
- [x] Part D: student reset data and ran it 21:23 to ~22:25; 250/250 completed (175 coverage, 75 challenge), no errors, no --resume needed; longest support-0192 at 157 s
- [x] Part E: `reports/smoke-output.txt` (student ran it 22:48): 61 escalations, 1.34M in / 226K out tokens, get_order 218, issue_refund 43, cancel_order 14, 10 permission denials
- [x] Part E: `traces/support_traces.json` (student ran export 22:49): 313 traces, 250 unique ids, 0 missing; checked support-0076, support-0192, support-0003 (conversation, model, tools, scenario id all present)
- [x] Commit every file in the handout's "Files to commit" list (student committed on branch hw3: 57fddd9, a788c40, bb51679, 9b9e34d)
- [x] Video recorded by the student 2026-09-15 (plan in hw3-video-prep.md; segment 3 uses support-0023 trace 57a2cc507a80b3698881978edad027b0)

## Decisions and evidence
### Pilot conversations (Part B step 2, 2026-09-14)
scratchpad/generate_messages.py: one gpt-5.5 call per scenario (sees only the gen block) plus one critic call; 4 workers.
scenarios/pilot_scenarios.jsonl written and validated (30 records, 20/10, 6 dq).
Student review decisions: (1) messages must identify the order ONE way (number, casual product, or product+store) and never
use full listing titles; regenerated all 30. (2) When a casual description matches several of the user's orders, keep the
scenario and make it two turns: agent should ask which, user's followup disambiguates; expected outcome prefixed
ask_which_order_then_. Applied to 0003, 0004, 0008, 0015 (builder detects this automatically). 0014 uses the order number.
Now 25 one-turn, 4 two-turn... see file for counts. Sample review (skill Step 6): accepted.

### Pilot plan (Part B step 1, 2026-09-14)
Built by scratchpad/build_pilot_plan.py into scratchpad/pilot_plan.json (no model calls): 20 coverage + 10 challenge,
roles 24/4/2, every intent, all eight styles, turns 26x1 3x2 1x3, one scenario per dq case, 22 distinct orders.
World today = 2026-07-01 (meta.world_asof); expected results computed as of that date. The system prompt does not tell the model the date.
Notable rows: 0019 day-30 boundary (order delivered 2026-06-01), 0027 Juniper 14d override (order 569), 0028 Northwind 45d override,
0029 other shopper's order, 0030 three-turn correction (shopper 7).

### Approved dimension plan (Part A)
Student proposed intent and user style; the rest come from SPEC.md and the data.
- role: shopper, merchant, support (AUTH-1)
- intent: order_status, return_deadline, refund, cancellation, policy_question, product_search, dispute, account_change, out_of_scope
- record_state: order placed / shipped / delivered_in_window / delivered_past_window / above_threshold / already_refunded_or_cancelled / damaged (six dq cases); product; store_policy_page; none
- applicable_policy: platform doc id (cw-returns, cw-refunds, cw-cancellations, cw-disputes, ...), store override (Saltbox 7d, Juniper 14d, Meridian 21d, Northwind 45d, Cascade and Second Stitch restocking), none
- tools_needed: none, one_lookup, several_calls
- difficulty: well_specified, ambiguous, missing_information, boundary, correction_across_turns, authorization_boundary
- user_style: the validator's eight values (student's impatient -> frustrated_impatient, elderly/confused -> confused_rambling, gen z -> terse_fragmentary or typo_heavy)
- turn_count recorded per scenario (1 + followups). No extra dimensions.
Seeded data: 500 shoppers, 20 merchants, 5 support; orders 8915 delivered (480 eligible), 74 shipped, 35 placed, 403 cancelled, 573 refunded.

## Next step
HW3 complete. Remaining housekeeping: commit the updated notes, then squash-merge hw3 into main.


## Final review (Part C step 3, 2026-09-14)
Student reviewed 17 (ids in support_review.jsonl). Rejected support-0026 (journal under $20: zero matches, answer key did not
describe a zero-result reply); replaced by a journal search with 13 real listings, same id, message regenerated (2 calls).
Student notes: product search is in scope (SCOPE-1, TOOL-3); spec may need to say whether merchants can override refund policy (0015).
Student added a 20-turn scenario (support-0192) to test long conversations. Flagged but unchanged: 0044 and 0147 say 'delivered' then ask status.

## Final plan (Part C step 1, 2026-09-14)
scratchpad/build_final_plan.py -> scratchpad/final_plan.json: 250 = 175 coverage + 75 challenge (30 dq: 5 per case, 45 other:
7 stricter store overrides, 5 Northwind looser override, 2 day-30, 3 day-31, $99.75 / $100.25 / 2x partial refund of exactly $100,
8 authorization boundaries, 4 corrections, 5 missing-information, 2 already refunded, 1 cancelled, 2 three-turn pressuring, 2 restocking-fee stores).
Roles 180/44/26; every intent; 211 one-turn, 34 two-turn, 5 three-turn; 169 distinct orders; 227 objective, 23 judgment.
Ambiguity detection from the pilot applied automatically (18 ambiguous). Ids support-0001..0250, shuffled so groups interleave.
Note: no eligible order totals exactly $100, so the exact-threshold boundary is a $100 partial refund on a larger order.

## Pilot run and review (Part B steps 4 and 5, 2026-09-14)
Student ran the pilot: scenarios/pilot-results.jsonl, 30/30 completed on gpt-5.5 (11:44).
Pilot changed data: refunds 575 (order 117), 576 (89, queued), 577 (529), 578 (1825); orders 105 and 180 cancelled; tickets 151-156.
Student reviewed 13 results; decisions and evidence live in scenarios/pilot_review.jsonl (13 records, 12 valid).
Confirmed failures (6): 0006 (no human-review ticket on above-threshold refund; note: ESC-1 may treat the queued refund as
the escalation, student to confirm), 0019 (day-30 boundary: agent said the deadline had passed and escalated), 0020 (verbose,
and called a 42-day-old order outside the 60-day dispute window), 0028 (computed 2026-07-12 then treated it as past),
0022 (flagged reversed dates but did not escalate), 0023 (missed the store mismatch, did not escalate).
Invalid scenario: 0024 (Heavy-Duty Vase title is shared by products 1, 2, 16, 19 at Blue Heron and 76, 78 at Juniper; revise reason).
Root cause noted for HW4, not fixed here: the system prompt never tells the model the world date (2026-07-01).
Pre-screen of the 19 unreviewed results: 0003, 0004, 0005 borderline (listed both instead of asking; unnecessary ticket; verbose); the rest matched.
Verbosity observations recorded on 0004, 0020, 0021, 0027 for open coding in HW4.

## Pilot scenario review notes
 I reviewed a bunch of scenarios, here are my notes: pilot-0006 - valid, failure, evidence: was not escalated for human review ESC-1
  pilot-0019  - valid, failure, evidence: result did not match expected
  pilot-0020 - valid, failure, evidence: response was WAY too verbose RESP-5
  pilot-0021 - valid, not a failure, but the response is too verbose.
  pilot-0030 - valid, not failure
  pilot-0029 - valid, not failure
  pilot-0028- valid, failure, evidence: should be refund eligible but the response was confused because it thinks 2026-07-12 is before today, scenario maybe needs to be revised to know today's date correctly (today in cartwheel world)
  pilot-0027 - valid, not failure, but the response was a bit too verbose, so this will be a good one to code later. Offering too much extra support and asking about if the order was damaged, seems like fishing for a lie
  pilot-0025, valid, not failure, would be good to handle missing data with some kind of escalation, in open coding
  pilot-0026, valid, not failure
  pilot-0024, not valid, not failure, there are more than 2 products with that name, so the evidence is not complete. Should update the scenario to say exactly which products have that same name, or mention that more than 1 product has that name.
  Turn them into the formatted jsonl files scenarios/pilot_review.jsonl

## 250 Scenaario review
Save each decision in scenarios/support_review.jsonl with scenario_id, decision, reason, and change. Use accept, revise, or reject for the decision. Apply every revision and replace every rejected scenario.
Table has columns
scenario_id, decision, reason, change
support-0026, reject,  The agent lists real matches with prices and invents nothing - but there are none, agent should list zero results and suggest the user go to the cartwheel app to search for items. Also, this is underspecified - do we help find products in this agent or is this out of scope.
support-0054, accept, okay to reuse a pilot order,
support-0015, accept, nice test of whether merchants should be able to override their own refund policies, no change but potentially need to update spec
support-0192, accept, huge number of turns
support-0187, accept
support-0185, accept
support-0193, accept
support-0194, accept
support-0198, accept
support-0100, accept
support-0250, accept

