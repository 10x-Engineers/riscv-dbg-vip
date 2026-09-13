# CVA6 scenario sweep under Cadence Xcelium

Full run of all 17 `cva6_sim/configs/*_uvm.json` scenarios on Xcelium 23.03-s001,
via `make soc_test CFG_FILE=<cfg>` per config. Closes the CVA6 half of the
verification gap left by `xcelium-simulation-support`, whose commit verified
17/17 on **ibex_sim** only and made no measured claim about CVA6.

- Date: 2026-09-08
- Simulator: Xcelium 23.03-s001 (`SIM=xcelium`, auto-detected; no Questa on this host)
- DUT: CVA6-fork @ `e0c2d7ed` (`xcelium-portability-fixes`), `TARGET_CFG=cv64a6_imafdc_sv39`
- DM RTL: 10x-Engineers/riscv-dbg @ `6051a09` — PR #4 head `7c4155f` plus the
  Xcelium declaration-order fix
- Preloaded ELF: `cva6_sim/sw/halt_probe.elf`
- pydebug: this branch, stock settings (no timeout overrides)

## Headline

| | Before the ROM fix | After |
|---|---|---|
| Sessions fully passed | 9 / 17 | **17 / 17** |
| Sessions with a failed step | 8 / 17 | **0 / 17** |
| Scoreboard errors, all configs | 0 | **0** |

Two defects were found and fixed to get there: the debug-ROM address stride
(below) and a CVA6 wfi/single-step deadlock (further below).

The sweep was run twice: once against `riscv-dbg` `d2ed168`, which is what this
repo's gitlink pointed at, and again against `6051a09` after the root cause below
was found and the gitlink moved to PR #4's head.

## Root cause of the 8 original failures

Every one of them failed identically: `Timeout (2.0s) waiting for abstractcs.busy=0`,
with `abstractcs = 0x08001002` (busy=1, **cmderr=0**) — the DM neither completing
nor rejecting the command. The split was exactly abstract-command scenarios vs.
DMI-register and SBA scenarios.

**`debug_rom.S` and `dm_mem.sv` disagreed on the DM flag address stride.**

| Flag | `debug_rom.S` (8-byte stride) | `dm_mem.sv` (4-byte stride) |
|---|---|---|
| HALTED | `0x100` | `0x100` ✅ |
| GOING | `0x108` | `0x104` ❌ |
| RESUMING | `0x110` | `0x108` ❌ |
| EXCEPTION | `0x118` | `0x10C` ❌ |

`dm_mem.sv:248` asserts `going` only on a hart write to `GoingAddr` (`0x104`).
The ROM's "I am starting the command" store (`debug_rom.S:96`) went to `0x108`,
which `dm_mem` decodes as **ResumingAddr** — clearing `halted` and setting
`resuming`, and never asserting `going`. The FSM therefore sat in state `Go`
with `cmdbusy_o = 1` indefinitely (`dm_mem.sv:163-172`), and because `go` is only
dropped on entering `CmdExecuting`, it stayed asserted — so the park loop kept
seeing the go flag and re-ran the abstract command forever.

Evidence from the CVA6 commit trace of a single failing run:

- across all 32 distinct instructions executed, the only stores were to `0x100`,
  `0x108` and `0x380` (data0) — **never `0x104`**
- `csrr a2, dpc` — the body of the `get_pc` abstract command — executed **794 times**
- the hart was executing the command correctly; it simply could not signal that it had

Only HALTED agreed between the two, which is why halt, dmstatus, discovery and SBA
always passed while every abstract-command scenario hung.

Fixed upstream by 10x-Engineers/riscv-dbg PR #4, commit `7c4155f` *"Resolved the
address migration issue"*, which moves the ROM defines to `0x104`/`0x108`/`0x10C`
and regenerates `debug_rom.sv`, `debug_rom.h` and both one-scratch variants.

This was never simulator-specific — a wrong constant in the ROM fails the same way
under Questa. Ibex was unaffected because it carries pulp-platform's `riscv-dbg`
unmodified, where ROM and `dm_mem` agree; that is why Ibex passed 17/17 under
Xcelium while CVA6 did not.

## Per-scenario detail (after the fix)

| Scenario | Session | Scoreboard | Model check | Was |
|---|---|---|---|---|
| csr_access | 4/4 | Checked=56 Errors=0 | Mismatches=0 | 2/4 |
| discovery | 2/2 | Checked=7 Errors=0 | Mismatches=0 | 2/2 |
| dm_activation | 3/3 | Checked=18 Errors=0 | Mismatches=0 | 3/3 |
| external_trigger | 3/3 | Checked=13 Errors=0 | Mismatches=0 | 3/3 |
| gpr_write | 4/4 | Checked=33 Errors=0 | Mismatches=0 | 2/4 |
| halt_on_reset | 6/6 | Checked=23 Errors=0 | Mismatches=0 | 6/6 |
| halt | 8/8 | Checked=42 Errors=0 | Mismatches=0 | 3/4 |
| hart_selection | 4/4 | Checked=15 Errors=0 | **Mismatches=1** | 4/4 |
| program_buffer | 6/6 | Checked=40 Errors=0 | Mismatches=0 | 5/6 |
| read_dmstatus | 1/1 | Checked=2 Errors=0 | Mismatches=0 | 1/1 |
| report_halt_status | 4/4 | Checked=11 Errors=0 | Mismatches=0 | 4/4 |
| reset_ctrl | 11/11 | Checked=68 Errors=0 | Mismatches=0 | 10/11 |
| run_control | 9/9 | Checked=49 Errors=0 | Mismatches=0 | 5/9 |
| sba | 4/4 | Checked=20 Errors=0 | Mismatches=0 | 4/4 |
| single_step | 3/3 | Checked=60 Errors=0 | Mismatches=0 | 2/3 |
| sw_breakpoint_progbuf | 3/3 | Checked=38 Errors=0 | Mismatches=0 | 1/3 |
| trigger | 13/13 | Checked=117 Errors=0 | Mismatches=0 | 13/13 |

## The second defect: single-stepping a `wfi` deadlocks CVA6

With the ROM stride fixed, `single_step` stopped timing out and failed differently:
`Abstract command error cmderr=4`. That turned out to be the sequence's own cleanup
misreporting — `set_step(False)` ran unconditionally against a hart that had not
re-halted, and an abstract command on a running hart is rejected with cmderr=4,
which replaced the real diagnosis. Fixed in `a20958c`.

The real defect: the hart was halted while parked in the boot ROM's `wfi; j -4`
idle loop, so the single step retired exactly one instruction — the `wfi` — and
then stalled forever with `dmstatus.allrunning=1`.

`csr_regfile.sv`'s `wfi_ctrl` un-stalls only on a pending enabled interrupt, an
external `debug_req_i`, or `irq_i[1]`. **`dcsr.step` is not a wake source**, and
during a step neither of the others can arrive: `dcsr.stepie=0` masks interrupts,
and the debugger must not assert haltreq because autonomous re-halt is what a step
is testing. Nothing could wake the hart.

The debug spec forbids this in both versions this DM could claim:

- **v1.0 (Sdext, "Step Bit In Dcsr")**: *"If the instruction being stepped over would
  normally stall the hart, then instead the instruction is treated as a `nop`."*
- **v0.13 §5.4**: the same rule, naming `wfi` explicitly.

This DM reports `dmstatus.version=3` (v1.0), so it was non-conforming either way.

Fixed in CVA6-fork `e0c2d7ed` by never arming the stall while stepping — the spec's
"treated as a nop", rather than stall-then-recover. `single_step` now reports
`dcsr.cause=4` and `pc 0x1004c -> 0x10050`, one instruction, with no haltreq.

Reproduces on `openhwgroup/cva6` master as of 2026-09-08, so it is an upstream
defect rather than one this fork introduced. Not yet run against CVA6's own
regression suite.

## #130 reproduction

`hart_selection_uvm.json` produces exactly one `MODEL_MISMATCH`, unchanged by the ROM fix:

```
DMI addr=0x11 (dmstatus): RTL returned 0x0000cc82, dm_ref_model expected 0x0000c082
```

Bits 10/11 (`anyrunning`/`allrunning`) for a nonexistent hart selection — byte-identical
to the Questa Milestone-5 cross-check and to the Xcelium ibex_sim run. Issue **#130**,
still open, RTL-side fix, out of scope here.

## Note on the Milestone-5 cross-check

`milestone5_regression_crosscheck_2026-08-27.md` records CVA6 **17/17 sessions passing
under Questa** on 2026-08-27. The ROM stride defect is simulator-independent and would
have failed there too, so that run must have used a `riscv-dbg` commit predating the
one this repo's gitlink pointed at. Worth reconciling before the two documents are read
side by side.
