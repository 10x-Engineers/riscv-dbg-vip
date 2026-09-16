# Generated coverage vs the hand-written file

What `emit_sv.py` produces from `coverage_model.yaml` + `bindings/cva6.yaml`,
compared against `src/pydebug/sv/fcov/covergroups.sv`.

Regenerate with:

```bash
python3 ~/.claude/skills/functional-coverage/scripts/emit_sv.py \
    testplans/generated/coverage_model.yaml \
    --bindings testplans/generated/bindings/cva6.yaml \
    --out testplans/generated/cov_cva6_generated.sv
```

---

## The binding layer

The model is architectural: its `expression` fields are names from the
specification (`stepped_instruction_class`, `hart_state`), not signals. That is
what keeps it reusable and its holes meaningful — and it is why the first
generated file was 2200 lines that could never compile.

`bindings/cva6.yaml` supplies the missing half: what each coverpoint actually
samples on this testbench. A second DUT gets a second file, not edits to the
model.

**35 of 70 modelled coverpoints are bindable today.** The other 35 are not an
error — they are behaviours this testbench cannot observe yet, and the emitter
lists them in the output rather than emitting something that will not build.
That list is the distance between what the spec asks for and what we can see.

---

## Headline: the two are different decompositions, not two views of one thing

Only **two covergroups share a name**: `cg_debug_entry` and `cg_step_external`.
Both are ones I wrote by hand *from* the model, so they match by construction.

| | Count |
|---|---:|
| Generated covergroups (bindable) | 14 |
| Implemented covergroups | 19 |
| Shared names | **2** |

- **12 generated-only** — modelled, bindable, never written. Real coverage the
  testbench does not collect: `cg_run_control`, `cg_reset`, `cg_hart_selection`,
  `cg_abstract_command`, `cg_debug_mode`, `cg_system_bus_access`, and more.
- **17 implemented-only** — the pre-existing set. It covers the same *ground*
  but is **register-centric**: `cg_dmstatus_read` alone has 26 coverpoints, one
  per field, plus six all/any crosses.

The model is **behaviour-centric**: one covergroup per thing the DM does, one
coverpoint per condition that changes it.

Neither framing is wrong, but they are not addable, and that is exactly why the
"overall coverage" figure was unanswerable earlier. `cg_dmstatus_read.cp_allhalted`
+ `cp_anyhalted` + `x_halted` and `cg_run_control.cp_hart_transition` measure the
same DUT behaviour in two shapes.

It also explains why the register-centric set scores higher (73.66% against
52.61%): **a field that toggled is easier to hit than a behaviour that was
exercised, and proves less.** Eight of its fourteen covergroups sit at 100%.

## Drift, even where one was written from the other

`cg_step_external` exists in both and has already diverged:

| | |
|---|---|
| Model only | `cp_haltreq_during_step`, `cp_step_transition`, `x_class_x_privilege` |
| Implementation only | `cp_consecutive`, `cp_stepie_irq`, `x_class_x_consecutive`, `x_class_x_prv`, `x_class_x_stepie` |

I placed two of the model's coverpoints in `cg_hart_mode` instead, and added
three crosses the model does not have. Nobody did anything wrong; two artifacts
maintained by hand drift within days. That is the argument for generation.

## What the generated file still needs

It is not yet compilable as a drop-in. 11 of the 24 identifiers the bindings
reference do not exist in the host class:

```
cmderr_state            cur_hart_state          dtmcs_rdata
counters_advanced       time_advanced           last_tdata1
dret_executed_in_debug  progbuf_words_written   hart_mode
stopcount               stoptime
```

These are **derived state the sampling process must maintain** — a latched
`tdata1`, a counter of consecutive steps, a flag for whether `mcycle` advanced
across a halt. The binding layer names the expression; something still has to
compute it.

That is the next piece of work, and it is bounded: eleven pieces of state, most
of them a register and an assignment in the monitor that already exists.

## Decision: the implemented file stands

**`src/pydebug/sv/fcov/covergroups.sv` is the coverage of record.** It is what
`debug_pkg.sv` includes, what the regression collects, and the number to quote.
The generated file is **not** adopted and is not in any build — nothing globs
`testplans/generated/`, so it compiles nowhere by construction rather than by
convention.

That is a deliberate call, not a deferral. The implemented set works today,
against a real DUT, with its holes already characterised in
[`coverage_analysis.md`](coverage_analysis.md). Swapping it for a generated file
that still needs eleven pieces of derived state would trade working coverage for
a cleaner provenance story, and buy nothing measurable this cycle.

### What the generated artifacts are still for

They stay in the tree as the **architectural reference**, and they keep earning
their place:

- `coverage_model.yaml` remains the spec-traceable model — every bin cites its
  clause. That is what makes a hole in it mean "the spec asks for this and we do
  not do it" rather than "nobody wrote a coverpoint".
- The 12 generated-only covergroups are a **standing gap list** against the
  implemented file, not dead output.
- `bindings/cva6.yaml` records what 35 of those map to on this testbench, so
  picking this up later starts from a map rather than from scratch.

### What this costs, stated plainly

The drift documented above continues. `cg_step_external` diverged within days
even with one written from the other, and nothing here stops that — the model
and the implementation are now two hand-maintained artifacts that will keep
separating. Treat the model as a checklist to review against, not as something
that stays automatically true.

And the two numbers still do not add. The implemented file's figure is the one
to report; the model's 52.61% measures a different decomposition of the same DUT
and belongs in a sentence of its own, never summed with the other.

### If this is picked up again

The order is unchanged and the work is bounded: add the eleven derived-state
members to the coverage class, bind or explicitly mark the remaining 35
coverpoints, then generate and keep only the sampling process by hand.
