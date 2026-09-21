# HW4 video prep (5 minutes, one take, no slides)

Drive the review app (`localhost:8030`) and the repo. Have these open before recording: support-0176 and support-0054 in the Review view, the Taxonomy tab, `SPEC.md` at RESP-6.

## 1. One interface decision made after inspecting traces
- No trace carried `cartwheel.session_id`, so the interface groups turns by `cartwheel.scenario_id` and orders them by timestamp; you added the session id to the root span for future runs.
- Show a multi-turn conversation (support-0011) as one timeline with tool call and result paired inline, which is what the standard Langfuse view could not do.

## 2. One Workshop suggestion and your decision
- Workshop replays showed the agent guessing today's date: support-0054 called a July 12 deadline "past" while the tool said `refund_eligible: true` (the world is as of July 1, 2026). You accepted it, and it became the mode `no_reference_date` and RESP-7.
- Contrast with the one you rejected: the retrieval-caused re-fetch in 0230, which you decided still counts as `redundant_policy_lookup` because the product fix is to make search return the full policy.

## 3. Two failure modes, one supporting trace each
- `write_without_confirmation`: support-0176, shopper says "I think I need to cancel it", agent calls `cancel_order` with no confirmation turn. Point at the red write line in the labeling card.
- `verbose_reply`: support-0052 turn 3, no tool calls, 500+ tokens restating the previous two turns. Show the flagged quote in the margin.

## 4. One taxonomy revision or rejected group
- `unnecessary_escalation` and `premature_escalation` were merged into `unwarranted_escalation` because one product change (tighten ESC-3) fixes both.
- Mention the reverse case too: `first_person_framing` was split out of tone because it needs a different fix than verbosity.

## 5. One rejected search suggestion and the boundary excluding it
- support-0035 was suggested as a close negative for `verbose_reply` because the reply is 84 characters; you rejected it because it says "cancelled" twice. Boundary: repetition, not length.
- Open the Suggestions tab, Rejected table, and read your reason aloud; that is the artifact.

## 6. One relationship between a mode and SPEC.md
- `write_without_confirmation` and RESP-6: the rule did not exist before HW4, was added from 0053/0066/0134, widened after 0167/0176, then tightened to "order number or widget" after the search review.
- Show the RESP-6 paragraph in `SPEC.md` with the annotation ids inline.

## 7. New modes in the final 15
- One: `incomplete_write_outcome`, first seen in support-0097 (a queued refund reported as "submitted for approval" with no amount, order, or timing). It was later promoted to the tenth mode `incomplete_outcome_report`.
- Say the number and the decision in one breath: "one new mode in the final 15, so the taxonomy was stable and I did not draw a fifth batch."

## Scope statement (say once, near the end)
- Ten final modes (above the handout's eight, by decision), five labeled on 64 conversations, with 0192 labeled on 2 of 20 turns and batch 3 left for HW5.
