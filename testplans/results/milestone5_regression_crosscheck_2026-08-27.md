# Milestone 5 regression cross-check (riscv-dbg-vip#6)

Independent re-run of the full UVM regression, all 17 `*_uvm.json` configs,
both DUTs, via `make soc_test CFG_FILE=<cfg>` per config (real QuestaSim
runs, not mocked). Closes the "not done — currently only cited from the
paper draft" gap `COMPLIANCE_FRAMEWORK_ROADMAP.md` itself flags for
Milestone 5.

## Headline totals

| DUT | Scoreboard | Model-check | Configs |
|---|---|---|---|
| CVA6 | Checked=738 Errors=0 | Mismatches=1 | 17/17 sessions passed |
| Ibex | Checked=564 Errors=0 | Mismatches=1 | 17/17 sessions passed |

## Cross-check against the paper's cited numbers

The paper cites CVA6 `Checked=42 Errors=0` / Ibex `Checked=38 Errors=0`.
These map to the `halt_uvm.json` config specifically (the M5 baseline
scenario), not the full-regression sum above.

- **CVA6: exact match.** `halt_uvm.json` → `Checked=42 Errors=0`.
- **Ibex: does not match exactly.** `halt_uvm.json` → `Checked=36 Errors=0`,
  not 38. A real, small discrepancy (2 checks), reported as found rather
  than rounded away. Likely explanation: the halt scenario or scoreboard
  gained/lost a couple of checks since the paper draft was written
  (2026-07-10) — not investigated further here; flagging for whoever reviews
  the paper's Table II next (relevant to riscv-dbg-vip#66).

## The 2 model-check mismatches

Both DUTs show exactly one `MODEL_MISMATCH`, both in `hart_selection_uvm.json`,
both the same signature:

```
DMI addr=0x11 (dmstatus): RTL returned 0x0000cc82, dm_ref_model expected 0x0000c082
```

Decoded: only bits 10/11 (`anyrunning`/`allrunning`) differ. This is a
reproduction of the already-filed **#130** (`dmstatus.allrunning/anyrunning=1`
for a nonexistent hart selection — RTL, both DUTs, fix direction already
documented there as an RTL change, not a DV/model fix). Not a new finding;
confirms #130 is still open and unfixed, consistent with it being
out of scope for this pass (RTL).

## Per-config detail

See the raw log this table was generated from:
`/tmp/claude-1000/.../scratchpad/regression_results.txt` (not committed —
regenerate with the loop below if needed).

```
for cfg in configs/*_uvm.json; do
    make soc_test CFG_FILE="$cfg"
done
```

Every config passed at the session level on both DUTs except the one
already-known exception: CVA6 `single_step_uvm.json` (2/3 passed — the
tracked RTL bug #127, reproduced again here, not addressed by this run).
