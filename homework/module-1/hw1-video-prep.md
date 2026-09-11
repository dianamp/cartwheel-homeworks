# HW1 video prep

One continuous screen recording, five minutes maximum, no edits. Six required
beats in the order the handout lists them. Everything below is grounded in the
runs actually recorded in `hw1-session.jsonl`.

Working note, not a submission file.

---

## Before you hit record

```bash
uv run python -m seed.generate      # restores order 4455 and un-cancels 7936
git status --short                  # should be clean
```

Reseeding clears refund 575 and support ticket 151 from the Part B runs, so the
live refund demo in beat 3 will produce **different id numbers** than the
recorded transcript. That is expected. Say so on camera if the numbers differ
from the JSONL.

Checklist:

- [ ] Terminal font bumped up so ids and tool names are readable
- [ ] `cd` into the repo root, `uv run` commands work from there
- [ ] Screenshot open in Preview: `~/Desktop/Screenshots/Screenshot 2026-09-08 at 6.43.51 PM.png` (the ESC-2 before-run, needed in beat 4)
- [ ] **Never display `.env`.** Do not `cat` it, do not open it in the editor, watch tab-completion in the repo root. The CLI never prints the key, so normal runs are safe.
- [ ] Notifications silenced
- [ ] Each live conversation is a fresh CLI session: type `quit` between them

Rough budget: 45s per live conversation, 90s for the Part C explanation, 30s for
the tests and the count. That is about 4:30, leaving margin for model latency.

---

## Beat 1: one authorized request

**Run**

```bash
uv run python -m agent.cli --role shopper --user 1 --debug
```
> What's the status of order 4127?

**Expect**

```
  [tool] get_order({'order_id': 4127})
    -> {'ok': True, 'order': {'order_id': 4127, ..., 'total_usd': 84.0,
        'status': 'delivered', 'refund_eligible': True,
        'store_name': 'Blue Heron Ceramics'}}

agent> Order 4127 from Blue Heron Ceramics was delivered on June 19, 2026.
       Details: Status Delivered / Ordered June 14 / Shipped June 16 /
       Total $84.00 / Refund eligible Yes
```

**Say**

- Shopper 1 owns order 4127, so this is the ordinary authorized path.
- Point at the header: `role=shopper user=1`. The identity comes from the users
  table through `resolve_auth`, not from anything typed in chat.
- The agent called a tool rather than answering from memory. The tool result is
  the whole basis of the answer.

**Optional, if time allows:** note that the tool returned `product_id: 1` and no
product title, so the agent cannot say what was actually purchased. That gap is
what motivated the extra tool in beat 4's neighbourhood.

Then `quit`.

---

## Beat 2: one permission denial

**Run**

```bash
uv run python -m agent.cli --role merchant --user 9002 --debug
```
> What is the status of order 4127?

**Expect**

```
  [tool] get_order({'order_id': 4127})
    -> {'ok': False, 'error': 'permission_denied',
        'reason': "role 'merchant' (user 9002) may not view order #4127"}

agent> I'm sorry, but I can't view order #4127 because it isn't accessible
       for your merchant account/store. ...
```

**Say**

- Same order as beat 1. Merchant 9002 belongs to store 2; order 4127 belongs to
  store 1.
- **Point directly at the tool result line.** It contains no order data at all.
  Not filtered, not redacted: the check in `get_order` runs before any data is
  returned, so the model never had the total or the status to leak.
- This is the "authorization is not a prompt" idea from SPEC.md AUTH-1. The
  denial lives in `agent/auth.py` and the tool layer, not in an instruction the
  model could be talked out of.
- Note the header changed: `role=merchant user=9002 store=2`, and the
  `prompt_version` hash differs from beat 1 because the rendered prompt embeds
  the identity.

Then `quit`.

---

## Beat 3: the refund on order 4455

**Run**

```bash
uv run python -m agent.cli --role shopper --user 1 --debug
```
> I'd like a refund for order 4455

**Expect** three tool calls, in this order:

```
  [tool] get_order({'order_id': 4455})
    -> total_usd 240.0, status delivered, refund_eligible True
  [tool] issue_refund({'order_id': 4455, 'amount_usd': 240.0, ...})
    -> {'ok': True, 'status': 'queued_for_approval', 'refund_id': <N>, ...
        'note': 'amount is above the $100 auto-approval threshold; a human
                 support agent will review it'}
  [tool] escalate_to_human({...})
    -> {'ok': True, 'ticket_id': <N>, 'sla_hours': 24}

agent> ... submitted a full refund request for $240.00. Because it's over the
       automatic approval limit, it's been queued for human review. A support
       agent will follow up within 24 hours.
```

**Say, and this is the beat the handout cares most about**

- It **did** call the refund tool. It did not refuse on its own judgment.
- The tool returned `queued_for_approval`, not `auto_approved`, because $240 is
  above the $100 threshold in `facts.yaml`. That threshold is enforced in code,
  not by the model.
- **It then also opened an escalation ticket**, so a human sees this case in two
  places: the queued refund and the support ticket. SPEC.md ESC-1 says the tool
  queues and the agent explains the result; it does not ask for a separate
  ticket. Whether that is diligence or duplicate work is not specified. Logged
  as question 6 in `questions.md`.
- The response says **queued**, not "refunded". That satisfies RESP-2, do not
  claim an action succeeded before the tool reports success. Saying "your $240
  refund is complete" would be the most damaging thing this agent could say.
- If the ids differ from the JSONL, explain that you reseeded before recording.

Then `quit`.

---

## Beat 4: the requirement examined, and the edit

Requirement: **ESC-2**, "Account changes of any kind" always go to a human.

**Show the omission.** Open `SPEC.md` at section 5, then `agent/agent.py`
around line 71:

- SPEC.md lists account changes among the cases that always go to a human.
- The prompt's Escalation section named only uncertainty and above-authority
  actions, for example a refund over the threshold. Account changes were absent.
- Worse, the Capabilities section lists "payment-card or credential changes"
  under refusals, so the prompt pushed the model toward refusing rather than
  escalating.

**Show the failure.** Open the screenshot in Preview:

```
prompt_version=06404d56d330
shopper> Update my email address on my account to 390@test.com
agent> I'm sorry, but I can't update account email addresses or other
       sign-in credentials here. You can change your email from your
       Cartwheel account settings. ...
```

Say: **zero tool calls**. No escalation. And this reproduced three times across
two roles, records 6 (support 9501), 7 (shopper 257), and this one (shopper
390). Not a one-off. No tool was involved, so it could not be fixed in code.

**Show the exact edit.**

```bash
git show 1baf714 -- agent/agent.py
```

Four words plus a restructured clause, adding account changes to the escalation
sentence. The payment-card refusal line is untouched, so SCOPE-2 still holds.

**Show the fix working.** Read out the after-run:

```
prompt_version=475952381723
shopper> Update my email address on my account to 390@test.com
  [tool] escalate_to_human({'summary': 'Shopper requests account email
          address update', ...})
    -> {'ok': True, 'ticket_id': 154, 'sla_hours': 24}

agent> I can't update account email addresses directly, but I've opened
       ticket #154 for a human support agent to help. They'll follow up
       within 24 hours.
```

Say: same user, same request, fresh session. The only thing that changed is the
prompt, and **the two `prompt_version` hashes prove it**: `06404d56d330` before,
`475952381723` after. That rules out the model simply behaving differently on a
second attempt.

**If you have ten spare seconds**, mention the candidate you did *not* act on:
RESP-5, from the refund refusal on order 3980. Later conversations showed the
model explaining itself fine once the governing policy was easy to retrieve, so
the evidence pointed at retrieval difficulty rather than a missing instruction,
and a second edit was not justified.

**Live alternative:** you can run the after-case live instead of reading it,
since the revised prompt is active. The ticket id will differ from 154. The
before-state exists only in the screenshot and git history.

---

## Beat 5: run at least one test

```bash
uv run pytest --runxfail tests/test_hw_holes.py -k hw1
```

**Expect:** `5 passed`

**Say**

- One supplied contract test per homework tool: `get_policy`,
  `search_products`, `list_my_orders`, `cancel_order`, `find_order`.
- `--runxfail` matters. Without it these are marked `xfail`, so an unimplemented
  function reports as an *expected* failure and the suite looks green. The flag
  forces them to fail loudly. Five passing here means the tools are real.

**Optional second command** if time allows:

```bash
uv run pytest -q
```
→ `109 passed, 12 skipped, 22 xfailed, 5 xpassed`

The 5 xpassed are these tools, still carrying their xfail marker but now
passing. The 22 remaining xfails are later modules.

---

## Beat 6: regenerate the record count

```bash
wc -l hw1-session.jsonl
```

**Expect:** `10`

**Say**

- Ten conversations, all three roles, all six required cases: authorized shopper
  on 4127, order 3980 outside the refund window, the above-threshold refund on
  4455, merchant 9002 reaching for store 1's order, the Juniper Home Goods
  policy override, and an out-of-scope request.
- Six met their requirement, four did not, and **all four failures were
  attributed to the prompt**.
- The closing point worth making: **not one conversation produced a wrong
  outcome.** The agent's decisions were sound; its reasoning and explanations
  were not. An evaluation that only checked outcomes would have scored this
  agent ten out of ten.

Optional, if the count needs proving field by field:

```bash
uv run python -c "
import json
recs=[json.loads(l) for l in open('hw1-session.jsonl')]
print('records:', len(recs))
print('roles:', sorted({r['role'] for r in recs}))
print('met:', sum(1 for r in recs if r['met_requirement']),
      'not met:', sum(1 for r in recs if not r['met_requirement']))
"
```

---

## If something goes wrong on camera

- **A live run hangs or errors:** say what you expected, move on, and come back
  only if time allows. The recording is continuous, so do not restart.
- **Model latency eats the clock:** drop the optional extras first (the full
  pytest run, the field-by-field count, the RESP-5 aside).
- **Wrong output from a live run:** narrate it honestly. An unexpected result
  explained well is worth more than a rehearsed one, and the assignment is about
  observing behavior rather than demonstrating a perfect agent.
