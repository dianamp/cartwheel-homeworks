# Writing a behavior specification for an agent: where the method comes from

Research note, 2026-09-15. Question: is a spec like Cartwheel's `SPEC.md`, with short tagged clauses such as
`ESC-1` and `RESP-3`, an established method, and where are the guidelines for writing one?

## Short answer

Yes, but it is a blend of two traditions rather than one named method.

1. The **tagged clause** style (`AUTH-1`, `ESC-2`, a stable identifier per requirement, "shall / must" wording,
   every test or scenario citing the identifier it checks) is classic **requirements engineering**. It predates
   LLMs by decades and is codified in ISO/IEC/IEEE 29148, in requirement-writing grammars such as EARS, and in
   RFC 2119's MUST / SHOULD / MAY vocabulary.
2. The **content** (a chain of command, hard rules versus defaults, an authorization matrix enforced in code
   rather than in the prompt, escalation triggers, tone rules) follows the newer practice of writing a
   **behavior specification for an LLM agent**, visible in OpenAI's Model Spec, Sierra's tau-bench policy
   documents, Anthropic's agent-building guidance, and the 2025 wave of "spec-driven development."

The evals literature (Husain and Shankar's evals FAQ, the "policy loopholes" paper) then supplies the third piece:
the spec is the answer key for evaluation, so its quality caps the quality of any eval built on it, and error
analysis should feed changes back into the spec.

## 1. The identifier convention: requirements engineering

**Unique, stable identifiers.** ISO/IEC/IEEE 29148:2018 (the international requirements engineering standard)
treats traceability as essential: each requirement gets an identifier so it can be linked back to its source and
forward to design and test cases, usually in a Requirements Traceability Matrix. Prefix-plus-number schemes
(`FR-12`, `SEC-3`, or Cartwheel's `AUTH-1`) are the common way to do it; the prefix names the section, the number
never changes once assigned, and retired requirements are marked rather than renumbered so old references still
resolve. Cartwheel's scenario files do exactly this: `expected.source.reference = "SCOPE-2, RESP-4"` is a
traceability link from a test case to two requirements.

**Sentence grammar.** 29148 recommends a fixed clause order for a functional requirement:
`[condition] [subject] [action] [object] [constraint]`. EARS (Easy Approach to Requirements Syntax, Mavin and
colleagues at Rolls-Royce, 2009) narrows that to five sentence templates:

| Pattern | Template |
| --- | --- |
| Ubiquitous | The `<system>` shall `<response>` |
| Event-driven | WHEN `<trigger>`, the `<system>` shall `<response>` |
| State-driven | WHILE `<state>`, the `<system>` shall `<response>` |
| Unwanted behaviour | IF `<trigger>`, THEN the `<system>` shall `<response>` |
| Optional feature | WHERE `<feature>`, the `<system>` shall `<response>` |

Cartwheel's `ESC-1` ("Refunds above the threshold; the tool queues the refund, and the agent explains the
result") is an event-driven requirement written loosely; in EARS form it would read "WHEN a refund request exceeds
`refund_auto_approve_threshold_usd`, the agent shall call `issue_refund`, which queues the refund, and shall tell
the user a human will review it." The reason to care: our pilot review disagreed about whether `ESC-1` required
an `escalate_to_human` ticket. A WHEN/SHALL phrasing with the tool named would have removed the ambiguity.

**Modal vocabulary.** RFC 2119 (1997) fixes the meaning of MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY. Specs
that use these words consistently make it obvious which clauses are testable hard rules and which are defaults.
`SPEC.md` mostly uses "must" and "refuses" but also "cite ... for every claim" without a modal; a pass that makes
every clause carry one of the five keywords is cheap and worth doing.

## 2. The content: behavior specifications for LLM agents

**OpenAI Model Spec** (first published May 2024, updated several times since). The most visible public example of
a behavior spec for a model. Its structure is the useful part: a short list of objectives; a **chain of command**
that says whose instructions win when they conflict (platform, developer, user, and untrusted tool output at the
bottom); then a distinction between **hard rules** (not overridable) and **defaults** (overridable starting
points). It also flags that agentic actions with side effects need extra care. Cartwheel's `AUTH-1` ("Authorization
is not a prompt") and the tool table with a Risk column are the same idea applied to one product.

**tau-bench (Sierra, 2024) and tau2-bench.** The benchmark that made "policy document plus tools plus simulated
user" the standard shape for evaluating customer-support agents. Each domain (retail, airline) ships a plain-prose
policy document that is injected verbatim as the system prompt; an agent that violates any rule scores zero even if
it satisfied the user. Cartwheel's course setup mirrors it, with one deliberate difference: `SPEC.md` is *not* the
prompt. The spec's own preamble explains that copying it into the prompt would be insufficient because a prompt
cannot enforce access control or validate a refund; permissions live in `agent/auth.py`, eligibility in
`seed/eligibility.py`. That split (which clauses are enforced by code, which by the prompt, which only by tests) is
the single most important design decision in an agent spec, and `SPEC.md` records it in its first table.

**"Policy Loopholes in Agent Evaluation" (2026).** An audit of tau2-bench's policies that found the policy text
itself was ambiguous, silent on edge cases, or admitted multiple defensible readings, so that "agent errors" were
often policy errors. Its recommendations are the closest thing to written guidelines for tightening an agent spec:
add explicit prerequisite statements, specify how rules compose when several apply in sequence, state whether
workarounds for a prohibited operation are themselves prohibited, audit the policy before annotating any traces,
and report loophole-affected scores separately. Its headline: "policy specification quality is the ceiling on
evaluation quality." Two items from our own HW3 review are loopholes in this sense: whether `ESC-1` requires a
ticket in addition to the queued refund, and whether a merchant may override their own store's refund denial
(support-0015).

**Anthropic, "Building effective agents" (2024).** Less about the spec document, more about the tool layer it
describes: invest in the agent-computer interface the way you would in a human interface, document each tool with
examples, edge cases, input formats, and clear boundaries from neighbouring tools. Cartwheel's tool table (inputs,
side effects, risk, success and failure contracts with error codes) is that advice written down.

**Spec-driven development (2025).** Thoughtworks and others describe a workflow where a versioned spec is the
input to a coding agent and the source of truth for implementation; specs include behavior, data model, constraints,
and traceability, and requirements are enforced by a test suite because the model can miss or regress them. The
Cartwheel repository follows this pattern: the spec, the code that implements it, and `tests/` that check it are
all versioned together, and the homework asks students to keep evaluation cases as regression tests.

## 3. The spec as an answer key: the evals connection

Husain and Shankar's evals FAQ argues for treating each evaluation criterion as a versioned product artifact with
a narrow definition, examples of acceptable and unacceptable behavior, and a record of why it changed, and for
starting from error analysis of real traces rather than generic metrics. A tagged spec is what makes that
workable: a scenario's expected result cites `RESP-3`, a failure found in open coding is filed against `RESP-3`, and
if the review shows the clause was ambiguous, the clause is what gets edited (the loopholes paper's "policy-level
correction" rather than patching one test).

That is also why the scenario skill insists expected outcomes come from the data and the spec, never from the
model: the spec is the oracle, so it has to be written before, and independently of, the runs it will judge.

## 4. How Cartwheel's SPEC.md maps onto all this

| Section of SPEC.md | Tradition it draws on |
| --- | --- |
| "How the specification enters the application" table | Spec-driven development; Model Spec's hard rules vs prompt-level guidance |
| PURPOSE, SCOPE (supported and refused) | Model Spec objectives; tau-bench policy opening paragraph |
| AUTH-1 matrix, "Authorization is not a prompt" | Model Spec chain of command; enforce-in-code principle |
| TOOL-1..9 with success and failure contracts | Anthropic ACI guidance; interface contracts in SDD |
| ESC-1..4 | Event-driven requirements (EARS WHEN pattern) |
| RESP-1..5 | Ubiquitous requirements; tone and citation rules as testable clauses |
| `facts.yaml` as the source of every number | 29148 traceability: one source per fact, referenced not copied |

## 5. A working checklist for writing (or revising) an agent spec

Drawn from the sources above and from what tripped us up in HW3.

1. **One clause, one identifier, never renumbered.** Prefix by section (`AUTH`, `ESC`, `RESP`). Mark retired
   clauses instead of reusing numbers.
2. **One modal per clause** (MUST, MUST NOT, SHOULD, MAY), RFC 2119 meanings. Hard rules get MUST; defaults get
   SHOULD or MAY and say who can override them.
3. **Use EARS shapes for anything conditional.** WHEN `<trigger>` / WHILE `<state>` / IF `<fault>` THEN, and name
   the tool or code path that produces the response, so "escalate" cannot mean two things.
4. **Say where each clause is enforced**: prompt, tool code, authorization layer, deterministic rule, or tests
   only. Anything that must hold even when the model is wrong belongs in code.
5. **Write the chain of command**: whose instruction wins when the user, the policy document, a store override,
   and a tool result disagree. Cartwheel has this for store-over-platform (`facts.yaml`) but not, for example,
   for a merchant asking to override eligibility.
6. **State what the model knows.** Session context (role, ids) and world facts (today's date) that the model
   needs must be listed, because a spec clause the model cannot evaluate is a loophole. HW3's day-30 and Northwind
   failures trace to the date never being given.
7. **Keep numbers in one place** (`facts.yaml`) and reference them; validate every document against it.
8. **Give each tool a contract**: inputs, side effects, risk class, success fields, failure codes. Name the
   failure code in the clause that depends on it (`not_eligible`, `permission_denied`).
9. **Cover composition and workarounds explicitly** (from the loopholes paper): what happens when two rules apply
   in sequence, and whether a multi-step route around a prohibition is itself prohibited.
10. **Audit the spec against traces before building evals**, and when review finds a clause read two ways, fix
    the clause and record the change; do not fix the test.
11. **Version it with the code and the tests**, and cite clause ids from every scenario, test, and failure note so
    the trace matrix stays intact.

## 6. Open items for Cartwheel's spec, from HW3

- `ESC-1`: state whether the queued refund *is* the escalation or whether an `escalate_to_human` ticket is also
  required (pilot-0006 disagreement).
- Add a clause on merchant overrides of eligibility (support-0015): allowed, denied, or escalate.
- Add the world date to the session context list, or state that the agent must rely on `refund_eligible` and
  never compute a deadline itself (pilot-0019, pilot-0028).
- Damaged-record handling is documented only in the `data_quality_cases` table; a `DATA-1` style clause
  ("IF a record is internally inconsistent, THEN the agent MUST escalate and MUST NOT assert derived values")
  would make the six cases citable from the spec instead of only from the table.

## Sources

- ISO/IEC/IEEE 29148 overview and templates: [cwnp.com summary](https://www.cwnp.com/req-eng/),
  [ReqView 29148 templates](https://www.reqview.com/doc/iso-iec-ieee-29148-templates/)
- EARS: [Wikipedia, Easy Approach to Requirements Syntax](https://en.wikipedia.org/wiki/Easy_Approach_to_Requirements_Syntax)
- Requirements traceability: [Wikipedia](https://en.wikipedia.org/wiki/Requirements_traceability)
- RFC 2119 keywords, as applied in SDD: [Software Mansion, Spec-Driven Development](https://agentic-engineering.swmansion.com/expanding-horizons/spec-driven-development/)
- OpenAI Model Spec: [current version](https://model-spec.openai.com/2026-08-18.html),
  [first version, May 2024](https://cdn.openai.com/spec/model-spec-2024-05-08.html),
  [OpenAI, "Inside our approach to the Model Spec"](https://openai.com/index/our-approach-to-the-model-spec/)
- tau-bench: [paper](https://arxiv.org/pdf/2406.12045), [Sierra blog](https://sierra.ai/blog/benchmarking-ai-agents),
  [tau2-bench repository](https://github.com/sierra-research/tau2-bench)
- Policy loopholes: [Policy Loopholes in Agent Evaluation: When Policy Ambiguity Masquerades as Agent Error](https://arxiv.org/html/2609.14400)
- Anthropic: [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- Spec-driven development: [Thoughtworks, unpacking SDD](https://www.thoughtworks.com/en-us/insights/blog/agile-engineering-practices/spec-driven-development-unpacking-2025-new-engineering-practices),
  [JustSteveKing, SDD with LLMs](https://www.juststeveking.com/articles/spec-driven-development-with-llms/)
- Evals: [Husain and Shankar, AI Evals FAQ](https://hamel.dev/blog/posts/evals-faq/),
  [Establishing Best Practices for Building Rigorous Agentic Benchmarks](https://arxiv.org/pdf/2507.02825)
