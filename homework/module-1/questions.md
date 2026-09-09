# HW1 questions

Questions that came up while working through Homework 1. Personal tracking
document, not a submission file.

## 1. How do I choose one `requirement` when several apply?

Conversation 1 (shopper 1, "What's the status of order 4127?") arguably
touches SCOPE-1 (order status lookups are supported), AUTH-1 (a shopper may
view their own orders), and RESP-3 (do not invent values). The record has
room for only one identifier, or `null`.

Resolved. Working rule: pick the requirement this conversation could
actually have violated, not every requirement it touches. A conversation
touches many requirements but only tests the ones with a real failure mode
present.

Applied to conversation 1: AUTH-1 could not have failed, because shopper 1
owns order 4127 and there is no denial path to get wrong. SCOPE-1 could have
failed, by refusing a supported request or answering from memory without a
tool call. Recorded as SCOPE-1. AUTH-1 gets its real test in the merchant
9002 / order 4127 conversation.

## 2. Should SPEC.md say how order status is presented?

Nothing in SPEC.md or `SYSTEM_PROMPT_TEMPLATE` says which order fields to
include in a reply, how to format dates or currency, whether to repeat
information, or how to structure the output. The model invents a format each
time, and it happens to be a reasonable one.

Observed in conversation 1: the tool returned `total_usd: 84.0`,
`ordered_at: '2026-06-14'`, `refund_eligible: true`, plus `store_id`,
`product_id`, and `quantity`. The model rendered `$84.00`, "June 14, 2026",
"Yes", dropped the three id/quantity fields, and invented a summary line plus
a bullet list. RESP-5 covers tone ("direct and respectful language") but not
content selection or structure.

Question: should the spec add a response-content requirement for order
lookups, or is presentation deliberately left to the model?

Status: open. Candidate for the Part C prompt investigation.

## 3. The agent cannot name the product in an order

My stated expectation for conversation 1 included "what the item was". The
agent did not say. `get_order` returns `product_id: 1` and no title, so the
agent never had the product name available. The raw database row says
"Heavy-Duty Vase".

This is not a model failure. The information was never in the tool result.

Status: open. Strong candidate for the additional tool required by Part A.

## 4. Part C candidate: the prompt never asks for the reason behind a refusal

SPEC.md RESP-5 requires language "that explains the relevant decision".
`SYSTEM_PROMPT_TEMPLATE` says to cite a policy id for policy claims and to
"decline out-of-scope requests in one or two sentences", but it never says to
state the reason an eligible-looking action was refused, or to cite the
policy that governs that reason.

Observed in conversation 2 (shopper 1, refund on order 3980): the agent
refused correctly and cited cw-refunds, but cw-refunds covers refund method
and the $100 threshold. The rule that actually decided the case is the
30-day return window in cw-returns, which the agent never fetched. The
shopper is told "not currently refund-eligible" with no reason and no date.

Assessed as met_requirement: false, problem_source: prompt. The tools
returned everything needed; the model chose not to look up the governing
policy.

Status: open. This is the leading candidate for the Part C prompt revision,
pending a second conversation that confirms the same behavior.

## 5. Citation behavior is inconsistent between conversations

The $100 auto-approval threshold was cited as (cw-refunds) in conversation 2
but stated with no citation in conversation 3 ("over the automatic approval
limit"), even though it is the same fact from the same policy. In
conversation 3 the number reached the model through the issue_refund tool's
`note` field rather than a policy doc, so RESP-1 arguably does not apply.

SPEC.md RESP-1 says to cite "every claim derived from a policy document". It
does not say what to do when the same policy fact arrives through a tool
result. Related to question 2.

Status: open. Supporting evidence for the Part C candidate in question 4.

## 6. Does queuing a refund already count as escalation?

ESC-1 says: "Refunds above the threshold; the tool queues the refund, and the
agent explains the result." It does not say the agent should also call
escalate_to_human.

In conversation 3 the agent did both: issue_refund returned
status=queued_for_approval (refund_id 575), and the agent then created
support ticket 151 describing the same refund. A human now sees the same
case in two places.

Question: is the extra ticket correct diligence or duplicate work? SPEC.md
does not say.

Status: open. Recorded as met_requirement: true, since the outcome and the
explanation to the shopper were both correct.

## 7. list_my_orders and get_order return different shapes

`get_order` returns `store_name`. `list_my_orders` returns `store_id` only.
Neither returns a product title. Nothing in SPEC.md justifies the
difference.

Consequence, observed in conversation 5: the agent made 19 `search_products`
calls to answer "which of my orders are from Juniper Home Goods". Three
calls used the store filter to learn that Juniper = store 2; the other
sixteen enumerated the store catalog by keyword until product ids 55, 57 and
69 appeared with their titles. The answer was correct. The method would fail
against a store with a large catalog, because MAX_TURNS is 12.

Status: open. Not fixed by the additional tool (option C was chosen for the
policy-lookup gap instead). An enriched order-history tool remains the
obvious second candidate if another is wanted.

## 8. Additional tool: get_store_policy(store_id)

Implemented for Part A. Returns store name, the effective return window, the
platform default, has_override, restocking_fee_opt_in, and a `policies` list
of the store's own policy docs. An empty list is a success, meaning "this
store publishes no policy of its own", which is the case for 14 of the 20
stores.

Open question: when `policies` is empty the model has a 30-day number with
no store doc to cite. It should fall back to citing cw-returns, but nothing
in the prompt tells it to. Watch for this in a live conversation.

## 9. The agent decides eligibility instead of calling the tool

Record 9 (shopper 257, "cancel order 6188"): the agent called get_order, saw
status 'shipped', and refused. It never called cancel_order, so the
authoritative not_eligible check never ran, and it cited no policy even
though cw-cancellations states the pre-shipment rule.

This is the mirror of RESP-2. RESP-2 forbids claiming success before a tool
reports success; nothing forbids claiming failure before a tool reports
failure. The outcome happened to be correct here.

Assessed as met_requirement: false, problem_source: prompt. The system
prompt already says "Prefer a tool lookup over memory" and "Cite the policy
id for every policy claim", and the model did neither, so a prompt edit may
not be sufficient on its own.

Question for the write-up: should SPEC.md add the RESP-2 mirror, requiring
the agent to let the tool decide eligibility rather than pre-empting it?

## 10. Should SPEC.md specify the format of order information?

Record 10 (shopper 390, cancel order 7936) met its requirement: the order
was cancelled and the agent said so. But the whole response was one line,
"Order 7936 has been cancelled successfully." No order details, no
confirmation of what was cancelled.

Compare record 1, where a simple status lookup produced a summary sentence
plus a six-row bullet list. Same prompt, same absence of guidance, opposite
verbosity.

Proposed spec change: for any order, show the order information in a
specified format. When an action changes an order, show the updated order
information after the change completes.

Extends question 2, which raised the same gap for status lookups. Two
records now show it from opposite directions.

## 11. Question for the group: how do you handle something that partially works?

Record 10 is the case. The requirement was met (the order was cancelled, the
agent reported it truthfully), but the response quality was poor. The record
schema has one boolean, `met_requirement`, and one `problem_source`. There is
no way to say "correct outcome, weak execution".

Options considered so far:
  - Pick the requirement narrowly enough that the judgment really is binary.
    Record 10 against SCOPE-1 is a clear pass; against a hypothetical
    response-format requirement it would be a clear fail.
  - Write more than one record for the same conversation, one per
    requirement. Nothing in the handout forbids it, but it inflates the
    conversation count.
  - Mark it met and log the quality problem separately, which is what was
    done here.

Open: what does the course recommend? This seems likely to matter more in
Module 2 and Module 3, where judges score traces against criteria.
