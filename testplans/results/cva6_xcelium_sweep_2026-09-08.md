# CVA6 scenario sweep under Cadence Xcelium

Full run of all 17 `cva6_sim/configs/*_uvm.json` scenarios on Xcelium 23.03-s001,
via `make soc_test CFG_FILE=<cfg>` per config. Closes the CVA6 half of the
verification gap left by `xcelium-simulation-support`, whose commit verified
17/17 on **ibex_sim** only and made no measured claim about CVA6.

- Date: 2026-09-08
- Simulator: Xcelium 23.03-s001 (`SIM=xcelium`, auto-detected; no Questa on this host)
- DUT: CVA6-fork @ `0175c9e2` (`xcelium-portability-fixes`), `TARGET_CFG=cv64a6_imafdc_sv39`
- DM RTL: 10x-Engineers/riscv-dbg @ `6051a09` — PR #4 head `7c4155f` plus the
  Xcelium declaration-order fix
- Preloaded ELF: `cva6_sim/sw/halt_probe.elf`
- pydebug: this branch, stock settings (no timeout overrides)

## Headline

| | Before the ROM fix | After |
|---|---|---|
| Sessions fully passed | 9 / 17 | **16 / 17** |
| Sessions with a failed step | 8 / 17 | **1 / 17** |
| Scoreboard errors, all configs | 0 | **0** |

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
| single_step | **2/3** | Checked=1474 Errors=0 | Mismatches=0 | 2/3 |
| sw_breakpoint_progbuf | 3/3 | Checked=38 Errors=0 | Mismatches=0 | 1/3 |
| trigger | 13/13 | Checked=117 Errors=0 | Mismatches=0 | 13/13 |

## The one remaining failure

`single_step_uvm` no longer times out. It now fails with **`Abstract command error
cmderr=4`** (`CmdErrorHaltResume` — the hart was not halted when the command was
issued). This is a different defect from the ROM stride, in the area of the hart's
autonomous re-halt after a step, and is **not investigated here**. Note the scoreboard
still reports `Checked=1474 Errors=0`, so the DMI traffic itself is consistent.

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
