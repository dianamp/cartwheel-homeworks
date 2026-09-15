# HW3 video prep (local working note, not a submission file)

One continuous screen recording, 5 minutes max.

## Intro (15 s)

- built a 250-scenario support trace dataset for Cartwheel: 175 coverage and 75 challenge
scenarios, each with an expected result grounded in the database or the policy documents, ran them on gpt-5.5,
and exported the traces.

## 1. A pilot scenario that failed: pilot-0022 (90 s)

- Open http://localhost:3000/project/cartwheel-dev/traces/3724d888be150974ec043c20af7a1182?timestamp=2026-09-14T17:41:22.033Z, then the `get_order` span output, then [scenarios/pilot_review.jsonl line 12](../../scenarios/pilot_review.jsonl#L12).
- Shipped (2026-06-25) is *after* delivered (2026-06-23); the expected outcome is that this gets flagged and escalated, but the agent gave the shopper the timeline anyway and never called `escalate_to_human`.

## 2. A final scenario revised after review: support-0026 (60 s)

- Open [scenarios/support_review.jsonl line 1](../../scenarios/support_review.jsonl#L1) (the reject), then [scenarios/support_scenarios.jsonl line 26](../../scenarios/support_scenarios.jsonl#L26) (the replacement).
- The original asked for a journal under $20 but no such journal exists (cheapest $68.50), so the answer key described a reply that could not happen; replaced under the same id with a plain journal search whose answer key is 13 real listings from the products table.

## 3. One complete final trace: support-0023 (75 s)

- Open http://localhost:3000/project/cartwheel-dev/traces/57a2cc507a80b3698881978edad027b0?observation=trace-57a2cc507a80b3698881978edad027b0&timestamp=2026-09-15T03:29:55.079Z
- Shopper 392 asks the return window on "a pencil set"; 5 orders match, but instead of confirming which one is meant, we lookup all 5 orders and all 5 store policies. Then say that the non pencil set item is not refund eligible.
-   `find_order` fuzzy-matched five orders (a socket set, two dinner plate sets, a fountain pen, and the real Classic Pencil Set 8002), the agent looked up all five plus four store policies, saw 8002 has `delivered_at: null` (damaged record `dq-order-missing-delivery-date`), then answered about the fountain pen (order 5584) as "the best match" and computed a deadline of September 25, 2025; expected was `do_not_compute_return_deadline`.

## 4. Regenerate the number of final scenario identifiers (30 s)

- Terminal: `jq '[.traces[].cartwheel_scenario_id] | unique | length' traces/support_traces.json` (file: [traces/support_traces.json](../../traces/support_traces.json))
- Prints `250`: 313 traces (one per message) covering all 250 final scenario ids, none missing.

## Numbers to have ready (all from the committed files)

- Pilot: 30 scenarios, 30/30 completed on gpt-5.5; 13 results reviewed, 12 valid, 6 confirmed failures
  (pilot-0006, 0019, 0020, 0022, 0023, 0028); 1 invalid scenario (pilot-0024, duplicate-title reason was incomplete).
- Final scenarios: 250 = 175 coverage + 75 challenge; 30 damaged-record scenarios, 5 per case; ids support-0001
  to support-0250; 17 reviewed (16 accept, 1 reject); one 20-turn scenario (support-0192).
- Monitoring set: 50 = 25 coverage + 25 challenge; first five are the first five reviewed ids.
- Final run: 250/250 completed, 175 coverage and 75 challenge, no errors, no reruns; about 60 minutes;
  longest scenario support-0192 at 157 s.
- Smoke report: 61 escalations, 10 permission denials, 1.34M input / 226K output tokens;
  tool calls get_order 218, search_help_center 150, get_policy 147, find_order 102, issue_refund 43, cancel_order 14.
- Export: 313 traces, 250 unique scenario ids, 0 missing.
- The Cartwheel world date is 2026-07-01 (`meta.world_asof`); all expected results were computed as of that date.


## Things I learned / questions

-
