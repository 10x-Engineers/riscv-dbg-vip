# CVA6 scenario sweep under Cadence Xcelium

Full run of all 17 `cva6_sim/configs/*_uvm.json` scenarios on Xcelium 23.03-s001,
via `make soc_test CFG_FILE=<cfg>` per config. Closes the CVA6 half of the
verification gap left by `xcelium-simulation-support`: that branch's commit
verified 17/17 on **ibex_sim** only, and made no measured claim about CVA6.

- Date: 2026-09-08
- Simulator: Xcelium 23.03-s001 (`SIM=xcelium`, auto-detected; no Questa on this host)
- DUT: CVA6-fork @ `106e85f2` (`xcelium-portability-fixes`), `TARGET_CFG=cv64a6_imafdc_sv39`
- DM RTL: 10x-Engineers/riscv-dbg @ `40fa2a0`
- Preloaded ELF: `cva6_sim/sw/halt_probe.elf`
- pydebug: this branch, stock settings (no timeout overrides)

## Headline

| | |
|---|---|
| Sessions fully passed | **9 / 17** |
| Sessions with a failed step | **8 / 17** |
| Distinct root causes among the 8 | **1** |
| `UVM_ERROR` (excluding the known #130) | **0** |
| Scoreboard errors, all 17 configs | **0** |

Every failure is the same one: `Timeout (2.0s) waiting for abstractcs.busy=0`.
The split is exactly **abstract-command scenarios vs. everything else** — DMI
register access and System Bus Access are clean across the board.

## Per-scenario detail

| Scenario | Session | Scoreboard | Model check | Note |
|---|---|---|---|---|
| discovery | 2/2 | Checked=7 Errors=0 | Checked=3 Mismatches=0 | |
| dm_activation | 3/3 | Checked=18 Errors=0 | Checked=7 Mismatches=0 | |
| external_trigger | 3/3 | Checked=13 Errors=0 | Checked=4 Mismatches=0 | |
| halt_on_reset | 6/6 | Checked=23 Errors=0 | Checked=7 Mismatches=0 | |
| hart_selection | 4/4 | Checked=15 Errors=0 | Checked=4 **Mismatches=1** | known #130, see below |
| read_dmstatus | 1/1 | Checked=2 Errors=0 | Checked=1 Mismatches=0 | |
| report_halt_status | 4/4 | Checked=11 Errors=0 | Checked=4 Mismatches=0 | |
| sba | 4/4 | Checked=20 Errors=0 | Checked=6 Mismatches=0 | |
| trigger | 13/13 | Checked=643 Errors=0 | Checked=296 Mismatches=0 | |
| csr_access | 2/4 | Checked=61 Errors=0 | Checked=27 Mismatches=0 | abstractcs.busy |
| gpr_write | 2/4 | Checked=45 Errors=0 | Checked=19 Mismatches=0 | abstractcs.busy |
| halt | 3/4 | Checked=42 Errors=0 | Checked=19 Mismatches=0 | abstractcs.busy |
| program_buffer | 5/6 | Checked=72 Errors=0 | Checked=32 Mismatches=0 | abstractcs.busy |
| reset_ctrl | 10/11 | Checked=553 Errors=0 | Checked=263 Mismatches=0 | abstractcs.busy |
| run_control | 5/9 | Checked=1239 Errors=0 | Checked=611 Mismatches=0 | abstractcs.busy |
| single_step | 2/3 | Checked=60 Errors=0 | Checked=28 Mismatches=0 | abstractcs.busy |
| sw_breakpoint_progbuf | 1/3 | Checked=45 Errors=0 | Checked=20 Mismatches=0 | abstractcs.busy |

## The abstract-command hang

First failing step in every case is the first abstract command the scenario
issues. For `halt_uvm.json` that is step 4, `get_pc()`:

```
WRITE command  (addr=0x17) data=0x002207b1     @ t=11666000
READ  abstractcs (addr=0x16) data=0x08001002 (busy=1 cmderr=0)   ... forever
```

`0x08001002` decodes as `busy=1`, `cmderr=0`, `datacount=2`, `progbufsize=8`.
The hart is confirmed halted first — `dmstatus=0x00800383`, `allhalted=1` — and
`cmderr` never sets, so the DM neither completes nor rejects the command.

**This is not the 2-second client timeout being too tight.** Re-running with
`RISCVDebug.DEFAULT_TIMEOUT` raised from 2.0 s to 60 s (diagnostic only, reverted)
left `abstractcs` at `0x08001002` across **1.45 s of simulated time** after the
command write at 11.7 ms. The command is stuck, not slow. Raising the timeout is
therefore not a fix, and the timeout value is not implicated.

Scope of the defect, from the evidence available here:

- **Not a pydebug/client issue.** The same client, unchanged, passes all 17 on
  ibex_sim under the same Xcelium.
- **Not caused by the Xcelium portability fixes.** Those are a streaming-concat
  rewrite in `axi_riscv_amos.sv`, an assignment-pattern spelling change in
  `cva6_tlb.sv`, and a declaration move in `dm_csrs.sv` — all three
  behaviour-preserving, and none on the abstract-command path.
- **Questa comparison not possible on this host** (no `vsim` installed). The
  2026-08-27 Milestone-5 cross-check recorded CVA6 17/17 sessions passing under
  Questa, so this is either a tool divergence or a change since that run. Not
  diagnosed further here.

Known and already recorded: `999cdce2`'s own commit message states that abstract-command
scenarios still hang under Xcelium and that it does not address them. This sweep
quantifies that open issue — 8 of 17 scenarios, one root cause — rather than
reporting a new one.

## #130 reproduction

`hart_selection_uvm.json` produces exactly one `MODEL_MISMATCH`:

```
DMI addr=0x11 (dmstatus): RTL returned 0x0000cc82, dm_ref_model expected 0x0000c082
```

Bits 10/11 (`anyrunning`/`allrunning`) for a nonexistent hart selection. This is
byte-identical to what the Questa Milestone-5 cross-check recorded on both DUTs,
and to what the Xcelium ibex_sim run recorded. Issue **#130**, still open, RTL-side
fix, out of scope here. Xcelium reproduces Questa's verdict including this divergence.
