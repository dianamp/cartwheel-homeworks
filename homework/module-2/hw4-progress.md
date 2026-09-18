# HW4 progress

Working notes for `hw4.md`. Checklist follows the handout order. Decisions are short; the reasoning lives in the report files under `analysis/report/`.

## Checklist

### Preparation
- [x] Confirm Langfuse is running and holds the Module 1 traces (2026-09-18)
- [x] Skip `hw3-reference.patch` (own HW3 traces exist)
- [x] Add `cartwheel.session_id` to the root span in `server/app.py` (future runs only)

### Part A, review interface
- [ ] Review 5 to 10 traces in the standard Langfuse view, note friction
- [ ] Coding agent inspects 5 to 10 traces and proposes a visual organization
- [ ] Approve the proposal
- [ ] Build `analysis/review_app/`
- [ ] Write `analysis/report/interface_comparison.md` (retained, changed, limitation)

### Part B, review 100+ traces (open coding, then axial coding after each batch)
- [ ] Batch 1: 15 uniform + 15 cluster representatives
- [ ] Batch 2: pick one product dimension before looking at outcomes, 30 traces across its values
- [ ] Batch 3: 25 traces from depth searches for candidate modes and close negatives
- [ ] Batch 4: 15 uniform after drafting the taxonomy (stability check)
- [ ] Every reviewed trace has an open code or "no failure observed"
- [ ] `analysis/state/sample_manifest.json` records which batch each trace belongs to (no trace in two batches)

### Part C, Raindrop Workshop
- [ ] Install Workshop, run `/instrument-agent` (keep OTel and Langfuse instrumentation)
- [ ] Inspect 5 to 10 runs across roles and tools
- [ ] Write `analysis/report/workshop_notes.md` (run ids, candidate failures, one uncertain case)
- [ ] Record accept / revise / reject for every Workshop suggestion used in the taxonomy

### Part D, taxonomy
- [ ] 5 to 8 binary modes, each with: snake_case name, definition, 3+ positives, 3+ close negatives, originating annotations, boundary to nearest mode, evaluator type, requirement source (SPEC id or SPEC revision)
- [ ] Merge / split by "would one product change fix both?"
- [ ] Compare with the AgentDebug taxonomy
- [ ] Agent-assisted search for one mode; review every hit; at least one rejected suggestion saved
- [ ] Document one taxonomy revision
- [ ] Any `SPEC.md` revision, with the motivating annotation named in the review summary

### Part E, apply the taxonomy
- [ ] One present / absent judgment per (trace, mode) pair
- [ ] Write accepted judgments to Langfuse as scores
- [ ] One label file per mode under `analysis/state/labels/`
- [ ] `analysis/report/review_summary.md` (sample size and composition, sample fractions per mode, new modes in the final 15, one taxonomy revision)
- [ ] Check HW5 readiness: 30 Pass and 30 Fail per mode, or plan synthetic scenarios

### Video (mine)
- [ ] Under 5 minutes, drive the interface and repo, cover the seven points in the handout

## Decisions

- **2026-09-18, review population.** Langfuse holds 361 `cartwheel.session_message` traces; the HW3 export holds 313 (all from the 2026-09-15 final run). The extra 48 are pilot and dev runs from 09-12 and 09-14, 9 of them with no scenario id. Review population = the 313 trace ids in `traces/support_traces.json`. Langfuse remains the annotation store.
- **2026-09-18, session grouping.** No trace carries `cartwheel.session_id` (HW2 never required it). Group by `cartwheel.scenario_id`, then order turns by timestamp. The HW3 runner opens one session per scenario, so this is faithful within the final run. Added `cartwheel.session_id` to the root span in `server/app.py` so future runs carry it; existing traces are unchanged. This is the "design changed after inspecting traces" item for `interface_comparison.md`.
- **2026-09-18, when to consult SPEC.md.** Open coding stays in plain words; no SPEC lookup during the first read. SPEC ids get attached during axial coding and taxonomy construction. A behavior with no requirement behind it gets a SPEC revision before it gets a label.
