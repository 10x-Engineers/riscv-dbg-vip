# RISC-V Debug Module — Verification Test Plan

Target specification: **RISC-V Debug Specification v1.0 (ratified)** —
<https://docs.riscv.org/reference/debug/v1.0/index.html>

DUT: CVA6 (`cv64a6_imafdc_sv39`) with the 10x-Engineers `riscv-dbg` fork as its
Debug Module, reporting `dmstatus.version=3` (v1.0).

---

## How to read this plan

Three levels, closed in order. There is no point debugging a halt sequence when
the DM's reset values were never checked.

| Level | Question it answers |
|---|---|
| **1. Reset** | Does every reset put the DM in the state the spec defines? |
| **2. Register access permissions** | Does each register honour its access type, from every interface that can reach it? |
| **3. Functional** | Does the DM perform the operations the spec intends? |

### Row format

A heading names the **feature under test** — that is the only general
description. Every row beneath it is one concrete, executable item:

| Type | What the row states |
|---|---|
| **Stimulate** | The exact sequence to drive. Registers, values, order. |
| **Check** | The exact condition to verify. Named fields, expected values. |
| **Cover** | The exact bins to close. Enumerated, not described. |

If a row cannot name a specific action, condition or bin, it does not belong in
the plan.

| Column | Meaning |
|---|---|
| **Pri** | P0 blocks tapeout · P1 compliance · P2 robustness · P3 optional |
| **Status** | `Not started` · `Pass` · `Fail` · `Blocked` · `N/A` |
| **Remarks** | Result, exception, and the issue it was filed as |

`Reference` anchors resolve under `https://docs.riscv.org/reference/debug/v1.0/`.

### Status

Run-control, abstract-command, program-buffer and single-step rows carry real
results from CVA6. Everything else is specified but not run — stated per row.

---

# 1. Reset Testing (unit level)

## 1.1 Debug Module reset via `dmactive`

Reference: `debug_module.html#dmcontrol` · `#reset`

| ID | Type | Action / Check / Cover | Pri | Status | Remarks |
|---|---|---|---|---|---|
| RST-001-S | Stimulate | Write `dmcontrol.dmactive=0`, wait, then write `dmactive=1` | P0 | Pass | `dm_activation_uvm` |
| RST-001-C | Check | While `dmactive=0`: every DM register other than `dmcontrol` reads its reset value | P0 | Pass | |
| RST-001-C2 | Check | `dmcontrol.dmactive` reads back 1 only after the DM has left reset | P0 | Pass | |
| RST-002-C | Check | With `dmactive=0`, `dtmcs` still reads its normal value and DMI still responds | P0 | Not started | The DTM must survive DM reset or the debugger loses its connection |
| RST-003-S | Stimulate | With `dmactive=0`, write `dmcontrol.haltreq=1` | P1 | Not started | |
| RST-003-C | Check | Hart does not halt; `dmstatus.allhalted` stays 0 | P1 | Not started | |
| RST-004-C | Check | Harts accessible to the DM are also reset when the DM is reset | P1 | Not started | Explicit spec requirement, easily missed |
| RST-005-V | Cover | `dmactive` transitions: `0→1`, `1→0`, `1→1`, `0→0` | P2 | Not started | |

## 1.2 Platform and hart reset

Reference: `debug_module.html#dmcontrol` · `#reset`

| ID | Type | Action / Check / Cover | Pri | Status | Remarks |
|---|---|---|---|---|---|
| RST-010-S | Stimulate | Write `dmcontrol.ndmreset=1`, hold, then write `0` | P0 | Pass | `reset_ctrl_uvm` |
| RST-010-C | Check | `dmstatus.ndmresetpending=1` while asserted | P0 | Pass | |
| RST-010-C2 | Check | DM and DTM registers keep their values across the reset; hart state does not | P0 | Pass | |
| RST-011-S | Stimulate | Write `dmcontrol.hartreset=1` for the selected hart, then `0` | P1 | Not started | |
| RST-011-C | Check | Selected hart resets; `dmstatus.anyhavereset=1` | P1 | Not started | |
| RST-011-C2 | Check | Non-selected harts' `havereset` bits unchanged | P1 | N/A | Single-hart DUT |
| RST-012-V | Cover | Reset source = {`ndmreset`, `hartreset`, external, power-on} | P1 | Not started | |
| RST-013-V | Cover | Hart state at reset = {running, halted, in Debug Mode, stalled in `wfi`} | P1 | Not started | |

## 1.3 DTM reset and DMI error recovery

Reference: `dtm.html#dtmcs` · `#dmi`

| ID | Type | Action / Check / Cover | Pri | Status | Remarks |
|---|---|---|---|---|---|
| RST-020-S | Stimulate | Provoke `dmi.op=2` (sticky error), then write `dtmcs.dmireset=1` | P1 | Not started | |
| RST-020-C | Check | `dtmcs.dmistat` returns to 0; DM register values are unchanged | P1 | Not started | Error recovery must not reset the DM |
| RST-021-S | Stimulate | Write `dtmcs.dmihardreset=1` mid-transaction | P2 | Not started | |
| RST-021-C | Check | DTM returns to idle; a subsequent DMI read succeeds | P2 | Not started | |
| RST-022-C | Check | After JTAG TAP reset, IDCODE reads the expected value | P1 | Pass | `discovery_uvm` |

## 1.4 Reset values, per register

Every row checks the **complete** register, not only the fields of interest — a
wrong reset value in an unused field surfaces later as an unexplained mismatch.

| ID | Type | Action / Check / Cover | Pri | Status | Remarks |
|---|---|---|---|---|---|
| RST-030-C | Check | `dmcontrol` == reset value, all fields, `dmactive=0` | P0 | Not started | |
| RST-031-C | Check | `dmstatus` == reset value: `version=3`, `impebreak`, `hasresethaltreq`, `authenticated=1` | P0 | Pass | Observed `0x00800c83`; `hasresethaltreq=0` |
| RST-032-C | Check | `hartinfo` == reset value: `nscratch`, `dataaccess`, `datasize`, `dataaddr` | P1 | Not started | `nscratch=2` — the DM owns `dscratch0/1` |
| RST-033-C | Check | `abstractcs` == reset value: `progbufsize=8`, `datacount=2`, `busy=0`, `cmderr=0` | P0 | Not started | |
| RST-034-C | Check | `command` reads `0` (WARZ) | P1 | Not started | WARZ governs read-back, not storage |
| RST-035-C | Check | `abstractauto` == 0 | P2 | Not started | |
| RST-036-C | Check | `data0..1` == reset value | P1 | Not started | |
| RST-037-C | Check | `progbuf0..7` == reset value | P1 | Not started | |
| RST-038-C | Check | `sbcs` == reset value: `sbversion=1`, supported `sbaccess*`, `sbbusy=0`, `sberror=0` | P0 | **Fail** | Model expects `0x20140808`, RTL holds `0x20160808`. `sbaccess` hardwired at `dm_csrs.sv:618` — 10x PR #4 regression, absent in pulp upstream |
| RST-039-C | Check | `sbaddress0..3`, `sbdata0..3` == reset value | P1 | Not started | |
| RST-040-C | Check | `haltsum0..3` == 0 with no hart halted | P2 | Not started | |
| RST-041-C | Check | `dmcs2` == reset value | P2 | Pass | `external_trigger_uvm` |
| RST-042-C | Check | `nextdm` == 0; `confstrptr0..3` == reset value | P2 | Not started | |
| RST-043-C | Check | `dtmcs` == reset value: `version`, `abits`, `idle`, `dmistat=0` | P0 | Not started | |
| RST-044-C | Check | After first halt: `dcsr.debugver=4`, `dcsr.cause` valid, `dpc` == halt PC | P0 | Not started | Read via abstract command |

## 1.5 Reset during an operation

The interesting failures are resets that land mid-transaction.

| ID | Type | Action / Check / Cover | Pri | Status | Remarks |
|---|---|---|---|---|---|
| RST-050-S | Stimulate | Start an abstract command; assert `ndmreset` while `abstractcs.busy=1` | P1 | Not started | Classic hang source |
| RST-050-C | Check | After reset release, `abstractcs.busy=0` and a new command completes normally | P1 | Not started | |
| RST-051-S | Stimulate | Start an SBA transfer; assert `ndmreset` while `sbcs.sbbusy=1` | P2 | Blocked | Blocked by RST-038 |
| RST-051-C | Check | `sbbusy` clears; a subsequent SBA access succeeds | P2 | Blocked | |
| RST-052-S | Stimulate | Assert reset between a DMI request and its response | P2 | Not started | |
| RST-052-C | Check | DTM returns to idle; no stuck busy | P2 | Not started | |
| RST-053-S | Stimulate | Assert `ndmreset`, write `dmcontrol.haltreq=1` while held, release reset | P1 | Pass | The portable substitute for halt-on-reset when `hasresethaltreq=0` |
| RST-053-C | Check | Hart is not reported halted during reset; enters Debug Mode on release | P1 | Pass | |
| RST-054-C | Check | While `ndmreset` asserted, DMI accesses other than `dmcontrol` do not hang the DM | P2 | Not started | Spec says UNSPECIFIED — check for absence of hang, assert no value |
| RST-055-S | Stimulate | Ten back-to-back `ndmreset` assert/deassert pairs with no settling time | P2 | Not started | |
| RST-055-C | Check | DM reaches a consistent state; `dmstatus` readable after the last one | P2 | Not started | |

## 1.6 `havereset` tracking

Reference: `debug_module.html#dmstatus` · `#dmcontrol`

| ID | Type | Action / Check / Cover | Pri | Status | Remarks |
|---|---|---|---|---|---|
| RST-060-C | Check | After any reset: `dmstatus.anyhavereset=1` and `allhavereset=1` | P1 | Pass | `reset_ctrl_uvm` |
| RST-061-C | Check | `havereset` remains set across unrelated DM reads and writes | P1 | Pass | Stickiness |
| RST-062-S | Stimulate | Write `dmcontrol.ackhavereset=1` for the selected hart | P0 | Pass | |
| RST-062-C | Check | `anyhavereset` and `allhavereset` clear to 0 | P0 | Pass | |
| RST-063-C | Check | Record whether `havereset` survives `dmactive=0` | P2 | Not started | Implementation-defined — document, do not assert |
| RST-064-V | Cover | `havereset` × `ackhavereset` = {set-no-ack, set-then-ack, ack-when-clear} | P1 | Pass | |

---

# 2. Register access permissions (unit level)

Two questions, and most plans ask only the first.

1. Does each field honour its access type — `R`, `R/W`, `WARL`, `WARZ`, `W1`,
   `R/W1C`, hardwired?
2. Does it honour it **from each interface that can reach it**? The same storage
   can be writable from one side and read-only from another.

## 2.1 Access-type conformance over DMI

Reference: `debug_module.html`

| ID | Type | Action / Check / Cover | Pri | Status | Remarks |
|---|---|---|---|---|---|
| RAP-001-S | Stimulate | For every `R` field in every DM register: write its complement | P0 | Not started | |
| RAP-001-C | Check | Field reads back its original value | P0 | Not started | |
| RAP-002-S | Stimulate | For every `R/W` field: walking-ones then walking-zeros | P0 | Not started | |
| RAP-002-C | Check | Each pattern reads back exactly | P0 | Not started | |
| RAP-003-S | Stimulate | For every `WARL` field: write each illegal value | P0 | Not started | |
| RAP-003-C | Check | Read-back is a legal value, and the **same** legal value on every repeat | P0 | Not started | WARL allows any legal value but it must be deterministic |
| RAP-004-S | Stimulate | Write `0xFFFF_FFFF` to `command` (WARZ) | P1 | Not started | |
| RAP-004-C | Check | `command` reads `0`; the command still executes | P1 | Not started | WARZ governs read-back only — do not infer the write was discarded |
| RAP-005-S | Stimulate | Write 1 then 0 to each `W1` field: `ackhavereset`, `setresethaltreq`, `clrresethaltreq` | P1 | Not started | |
| RAP-005-C | Check | Writing 1 acts, writing 0 does nothing, read returns 0 | P1 | Not started | |
| RAP-006-S | Stimulate | Set `abstractcs.cmderr` via a failing command, then write 1s to it | P1 | Not started | |
| RAP-006-C | Check | `cmderr` clears only on a write of 1s, not on a write of 0s | P1 | Not started | |
| RAP-007-C | Check | Hardwired fields read their fixed value regardless of what is written | P1 | **Fail** | `sbcs.sbaccess` — see RST-038 |
| RAP-008-C | Check | Every reserved bit in every DM register reads 0 | P1 | Not started | |
| RAP-009-S | Stimulate | Read and write every unimplemented DMI address in range | P1 | Not started | |
| RAP-009-C | Check | Reads return 0, writes are ignored, no error is raised, no hang | P1 | Not started | |
| RAP-010-V | Cover | Access type = {R, R/W, WARL, WARZ, W1, R/W1C, hardwired, reserved} | P1 | Not started | Every type exercised at least once |

## 2.2 Same register, different interface

The section most plans omit. Each row names **which interface** performs the
access and what the permission is *from there*.

| ID | Type | Action / Check / Cover | Reference | Pri | Status | Remarks |
|---|---|---|---|---|---|---|
| RAP-020-S | Stimulate | Hart in Debug Mode writes `dcsr` with a CSR instruction in the program buffer | `Sdext.html#csr-dcsr` | P0 | Pass | |
| RAP-020-C | Check | Debugger reading `dcsr` via Access Register sees the hart's write | `Sdext.html#csr-dcsr` | P0 | Pass | |
| RAP-021-S | Stimulate | Debugger issues Access Register write to `dcsr` while the hart is **running** | `Sdext.html#csr-dcsr` | P1 | Not started | |
| RAP-021-C | Check | Command fails with `cmderr=4`; `dcsr` is not modified | `Sdext.html#csr-dcsr` | P1 | Not started | Spec forbids changing some `dcsr` bits while running |
| RAP-022-C | Check | Hart reads `dcsr` or `dpc` in M-mode → illegal-instruction trap | `Sdext.html#csr-dcsr` | P0 | Not started | Debug CSRs are invisible outside Debug Mode |
| RAP-023-S | Stimulate | Debugger writes `0xDEADBEEF` to `dscratch0`, then executes any program-buffer command | `Sdext.html#csr-dscratch0` | P1 | **Fail** | |
| RAP-023-C | Check | With `hartinfo.nscratch=2`, `dscratch0/1` are DM scratch — the debugger's value is **not** expected to survive | `debug_module.html#hartinfo` | P1 | **Fail** | `TC-DCSR-003` asserts preservation. The **testplan expectation is wrong**, not the RTL — re-specify, do not file |
| RAP-024-S | Stimulate | Debugger writes `progbuf0..7` over DMI; hart executes them | `debug_module.html#program-buffer` | P1 | Not started | |
| RAP-024-C | Check | Hart cannot write `progbuf` — a store to that address does not alter the buffer | `debug_module.html#program-buffer` | P1 | Not started | |
| RAP-025-S | Stimulate | Debugger writes `data0`; then runs an Access Register read of a GPR | `debug_module.html#data0` | P1 | Pass | `gpr_write_uvm` |
| RAP-025-C | Check | `data0` now holds the GPR value — the abstract command overwrote the debugger's value | `debug_module.html#data0` | P1 | Pass | |
| RAP-026-C | Check | Where `hartinfo.dataaccess=1`, the hart reading `dataaddr` sees the same value as DMI reading `data0` | `debug_module.html#hartinfo` | P2 | Not started | Two views of one storage |
| RAP-027-S | Stimulate | Read physical address A by SBA; read the same A by a program-buffer load | `debug_module.html#sbcs` | P1 | Blocked | Blocked by RST-038 |
| RAP-027-C | Check | Values agree, or differ only where the hart's MMU/PMP explains it | `debug_module.html#sbcs` | P1 | Blocked | |
| RAP-028-S | Stimulate | Configure PMP to deny the hart access to A; read A by SBA | `debug_module.html#sbcs` | P1 | Blocked | |
| RAP-028-C | Check | SBA read succeeds — it bypasses hart privilege and translation | `debug_module.html#sbcs` | P1 | Blocked | |
| RAP-029-C | Check | Hart cannot reach DM registers as memory, except the Debug ROM and the `data` window | `debug_module.html` | P2 | Not started | |
| RAP-030-S | Stimulate | Hart stores to a Debug ROM address | `debug_module.html` | P2 | Not started | |
| RAP-030-C | Check | ROM contents unchanged; the park loop still functions | `debug_module.html` | P2 | Not started | |
| RAP-031-V | Cover | Interface = {DMI, hart CSR, hart load/store, SBA, program buffer} × register class | P1 | Not started | |

## 2.3 Access gated by DM state

| ID | Type | Action / Check / Cover | Reference | Pri | Status | Remarks |
|---|---|---|---|---|---|---|
| RAP-040-C | Check | With `dmactive=0`, only `dmcontrol` is meaningful | `debug_module.html#dmcontrol` | P0 | Pass | `dm_activation_uvm` |
| RAP-041-C | Check | `dmstatus.version` is readable before activation and before authentication | `debug_module.html#dmstatus` | P0 | Pass | The only reliable version discriminator |
| RAP-042-S | Stimulate | Write `command` while `abstractcs.busy=1` | `debug_module.html#abstractcs` | P0 | Not started | |
| RAP-042-C | Check | `cmderr=1` (busy); the in-flight command completes unaffected | `debug_module.html#abstractcs` | P0 | Not started | |
| RAP-043-S | Stimulate | Write `sbaddress0` while `sbcs.sbbusy=1` | `debug_module.html#sbcs` | P1 | Blocked | |
| RAP-043-C | Check | `sbcs.sbbusyerror=1`; the in-flight transfer is unaffected | `debug_module.html#sbcs` | P1 | Blocked | |
| RAP-044-C | Check | With `authenticated=0`, only `dmstatus`, `dmcontrol` and `authdata` are accessible | `debug_module.html#authdata` | P3 | N/A | Authentication not implemented — recorded, not silently skipped |
| RAP-045-V | Cover | Gating state = {`dmactive=0`, `ndmreset=1`, `busy=1`, `sbbusy=1`, `authenticated=0`} | P1 | Not started | |

---

# 3. Functional verification

Each feature states its **intent** — what the spec is trying to achieve — and
the **debugger workflow** that achieves it. Workflows come from the spec's own
Appendix A (`debugger_implementation.html`); where a row derives from OpenOCD
instead, it says so and asserts only that the DM tolerates the sequence.
Debugger behaviour is evidence of convention, never of requirement.

## 3.1 Debug Module activation

**Intent.** Bring the DM out of reset and confirm it is genuinely alive — which
means reading something other than the one register that reads correctly even
when nothing else works.

**Workflow.** `dmactive=1` → poll read-back → read `dmstatus` → read registers
beyond `version`.

| ID | Type | Action / Check / Cover | Reference | Pri | Status | Remarks |
|---|---|---|---|---|---|---|
| ACT-001-S | Stimulate | Write `dmcontrol.dmactive=1`; poll `dmcontrol` until it reads back 1 | `debug_module.html#dmcontrol` | P0 | Pass | `dm_activation_uvm` (3/3) |
| ACT-001-C | Check | `dmcontrol.dmactive` reads 1 within the polling budget | `debug_module.html#dmcontrol` | P0 | Pass | |
| ACT-002-S | Stimulate | After activation, read `hartinfo`, `abstractcs` and `haltsum0` | `debug_module.html#dmstatus` | P0 | Pass | |
| ACT-002-C | Check | `abstractcs.progbufsize=8`, `datacount=2`, `hartinfo.nscratch=2` — values consistent with the DUT, not all-zero and not all-ones | `debug_module.html#abstractcs` | P0 | Pass | **The real activation check.** `dmstatus.version` reads correctly even on a dead DM, so checking it proves nothing |
| ACT-003-S | Stimulate | Write `dmactive=0`, then `dmactive=1` again | `debug_module.html#dmcontrol` | P0 | Pass | |
| ACT-003-C | Check | All DM registers are back at reset values after the cycle | `debug_module.html#dmcontrol` | P0 | Pass | |
| ACT-004-S | Stimulate | Write `dmactive=1` when it is already 1 | `debug_module.html#dmcontrol` | P2 | Not started | |
| ACT-004-C | Check | No register changes value; no hart state changes | `debug_module.html#dmcontrol` | P2 | Not started | |

## 3.2 Discovery and version detection

**Intent.** Determine what the hardware is without assuming anything, and
without disturbing a running hart.

| ID | Type | Action / Check / Cover | Reference | Pri | Status | Remarks |
|---|---|---|---|---|---|---|
| DIS-001-C | Check | `dmstatus.version == 3` (v1.0) | `debug_module.html#dmstatus` | P0 | Pass | `discovery_uvm` (2/2) |
| DIS-002-S | Stimulate | Run the spec's version-detection sequence: read `dmcontrol`, preserve bits, write, poll, read `dmstatus.version` | `debug_module.html#version-detection` | P0 | Not started | The spec prescribes an exact procedure |
| DIS-002-C | Check | Sequence completes and reports 3; no hart state changed | `debug_module.html#version-detection` | P0 | Not started | |
| DIS-003-S | Stimulate | Write all-ones to `dmcontrol.hartsel`, read back | `debug_module.html#dmcontrol` | P1 | Not started | Standard width probe |
| DIS-003-C | Check | Read-back width equals the implemented `hartsel` width | `debug_module.html#dmcontrol` | P1 | Not started | |
| DIS-004-S | Stimulate | Issue DMI accesses with fewer idle cycles than `dtmcs.idle` | `dtm.html#dtmcs` | P1 | Not started | |
| DIS-004-C | Check | DM either completes or returns busy — never corrupts data | `dtm.html#dmi` | P1 | Not started | Under-reported `idle` causes intermittent failures on fast debuggers |
| DIS-005-S | Stimulate | Access `progbuf[progbufsize]` and `data[datacount]` — one past the declared count | `debug_module.html#abstractcs` | P1 | Not started | |
| DIS-005-C | Check | Out-of-range accesses read 0 and are ignored | `debug_module.html#abstractcs` | P1 | Not started | |
| DIS-006-S | Stimulate | Run full discovery while the hart is running | `debug_module.html` | P1 | Not started | |
| DIS-006-C | Check | Hart is still running afterwards; `dmstatus.allrunning=1` throughout | `debug_module.html#dmstatus` | P1 | Not started | Debuggers discover before halting |
| DIS-007-C | Check | `nextdm == 0` when this is the only DM | `debug_module.html#nextdm` | P2 | Not started | |

## 3.3 Hart selection and availability

**Intent.** Address the right hart, and report truthfully about harts that do
not exist or cannot respond.

| ID | Type | Action / Check / Cover | Reference | Pri | Status | Remarks |
|---|---|---|---|---|---|---|
| HS-001-S | Stimulate | Write `dmcontrol.hartsel=0` (a hart that exists) | `debug_module.html#dmcontrol` | P0 | **Fail** | `hart_selection_uvm` aborts: RTL `0x0080cc83` vs model `0x0080c083` |
| HS-001-C | Check | `dmstatus` reports that hart's state; `anynonexistent=0` | `debug_module.html#dmstatus` | P0 | **Fail** | |
| HS-002-S | Stimulate | Write `dmcontrol.hartsel` to an index with no hart | `debug_module.html#dmcontrol` | P1 | **Fail** | |
| HS-002-C | Check | `anynonexistent=1`, `allnonexistent=1` | `debug_module.html#dmstatus` | P1 | Not started | |
| HS-002-C2 | Check | `allrunning=0` and `anyrunning=0` — a hart that does not exist is not running | `debug_module.html#dmstatus` | P1 | **Fail** | RTL reports `allrunning=1`/`anyrunning=1`. Spec violation, reproduces on **both** DUTs — issue #130 |
| HS-003-C | Check | `hartsel` is unchanged by halt, resume and abstract commands | `debug_module.html#dmcontrol` | P1 | Not started | |
| HS-004-S | Stimulate | Hold a hart in reset, then read `dmstatus` | `debug_module.html#dmstatus` | P1 | Not started | |
| HS-004-C | Check | `anyunavail`/`allunavail` reflect the unavailable hart | `debug_module.html#dmstatus` | P1 | Not started | |
| HS-005-V | Cover | Hart state reported = {running, halted, unavailable, nonexistent, in reset} | P1 | Not started | |
| HS-006-V | Cover | `hartsel` = {0, max implemented, first nonexistent, all-ones} | P1 | Not started | |

## 3.4 Halt

**Intent.** Stop a hart wherever it is — including where it is not executing
instructions — and learn why it stopped.

**Workflow** (Appendix A `#halting`). `haltreq=1` → poll `dmstatus.allhalted` →
clear `haltreq` → read `dcsr.cause`.

| ID | Type | Action / Check / Cover | Reference | Pri | Status | Remarks |
|---|---|---|---|---|---|---|
| HALT-001-S | Stimulate | With the hart running, write `dmcontrol.haltreq=1`; poll `dmstatus`; clear `haltreq` | `debug_module.html#dmcontrol` | P0 | Pass | `halt_uvm`, `run_control_uvm` |
| HALT-001-C | Check | `dmstatus.allhalted=1` and `anyhalted=1`; `allrunning=0` | `debug_module.html#dmstatus` | P0 | Pass | |
| HALT-001-C2 | Check | `dcsr.cause == 3` (haltreq) | `Sdext.html#csr-dcsr` | P0 | Pass | |
| HALT-001-C3 | Check | `dpc` == the address of the instruction that would have executed next | `Sdext.html#csr-dpc` | P0 | Pass | |
| HALT-002-S | Stimulate | With the hart already halted, write `haltreq=1` again | `debug_module.html#dmcontrol` | P1 | Pass | |
| HALT-002-C | Check | No state change; `dcsr.cause` unchanged; no error | `debug_module.html#dmcontrol` | P1 | Pass | |
| HALT-003-S | Stimulate | Let the hart reach a `wfi` with no interrupt pending; assert `haltreq` | `Sdext.html#4-1-3-wait-for-interrupt-instruction` | P0 | Not started | **Different RTL path from SSTEP-004** — `debug_req_i`, not `dcsr.step` |
| HALT-003-C | Check | Hart leaves the stalled state, completes the `wfi`, enters Debug Mode; `dcsr.cause=3` | `Sdext.html#4-1-3-wait-for-interrupt-instruction` | P0 | Not started | |
| HALT-004-S | Stimulate | Assert `haltreq` in the cycle the hart takes a trap | `Sdext.html#debugmode` | P1 | Not started | |
| HALT-004-C | Check | `dpc` is coherent — either the faulting PC or the handler entry, not a mixture | `Sdext.html#csr-dpc` | P1 | Not started | |
| HALT-005-S | Stimulate | Assert `haltreq` with an interrupt pending and enabled | `Sdext.html#debugmode` | P1 | Not started | |
| HALT-005-C | Check | Hart halts; the interrupt remains pending and is taken after resume | `Sdext.html#debugmode` | P1 | Not started | |
| HALT-006-C | Check | `haltsum0` bit for the halted hart is set | `debug_module.html#haltsum0` | P2 | Pass | `report_halt_status_uvm` (4/4) |
| HALT-007-A | Assertion | Hart halts within the spec's one-second bound after `haltreq` | `debug_module.html#dmcontrol` | P2 | Not started | Cycle-domain property — SVA, not a directed test |
| HALT-008-V | Cover | Privilege at halt = {M, S, U} — `dcsr.prv` records each | `Sdext.html#csr-dcsr` | P1 | Not started | |
| HALT-009-V | Cover | Hart activity at halt = {ordinary insn, `wfi`, taking a trap, in a tight loop, executing a load/store} | P1 | Not started | |
| HALT-010-S | Stimulate | Select multiple harts and assert `haltreq` | `debug_module.html#dmstatus` | P1 | N/A | Single-hart DUT — `allhalted` vs `anyhalted` cannot be distinguished |

## 3.5 Resume

**Intent.** Continue from where the hart stopped, with the debugger able to
confirm the resume actually happened.

**Workflow.** `resumereq=1` → poll `dmstatus.allresumeack` → confirm
`allrunning`.

| ID | Type | Action / Check / Cover | Reference | Pri | Status | Remarks |
|---|---|---|---|---|---|---|
| RES-001-S | Stimulate | With the hart halted, write `dmcontrol.resumereq=1` | `debug_module.html#dmcontrol` | P0 | Pass | `run_control_uvm` (9/9) |
| RES-001-C | Check | `dmstatus.allrunning=1`, `allhalted=0` | `debug_module.html#dmstatus` | P0 | Pass | |
| RES-001-C2 | Check | `allresumeack=1` and `anyresumeack=1` | `debug_module.html#dmstatus` | P0 | Pass | |
| RES-002-S | Stimulate | With the hart **running**, write `resumereq=1` | `debug_module.html#dmcontrol` | P1 | Pass | |
| RES-002-C | Check | Hart keeps running, but `allresumeack`/`anyresumeack` are **cleared** | `debug_module.html#dmstatus` | P1 | Pass | The §3.5 asymmetry: the request is ignored, the ack is not |
| RES-003-S | Stimulate | Write `dmcontrol` with `haltreq=1` and `resumereq=1` in the same access | `debug_module.html#dmcontrol` | P1 | Pass | |
| RES-003-C | Check | `haltreq` wins; the hart halts; `resumereq` has no effect | `debug_module.html#dmcontrol` | P1 | Pass | |
| RES-004-S | Stimulate | While halted, write `dpc` to a different valid address, then resume | `Sdext.html#csr-dpc` | P0 | Not started | How a debugger implements "jump to" |
| RES-004-C | Check | Execution continues from the written `dpc`, not the original halt PC | `Sdext.html#csr-dpc` | P0 | Not started | |
| RES-005-S | Stimulate | Record all GPRs and CSRs while halted; resume; re-halt; read them again | `Sdext.html#debugmode` | P0 | Not started | |
| RES-005-C | Check | Every register the debugger did not write is unchanged | `Sdext.html#debugmode` | P0 | Not started | Abstract commands and the program buffer must not corrupt hart state |
| RES-006-S | Stimulate | Assert `ndmreset`; write `resumereq=1` while reset is held | `debug_module.html#dmcontrol` | P2 | Pass | |
| RES-006-C | Check | No halt/run transition occurs | `debug_module.html#dmstatus` | P2 | Pass | |
| RES-007-V | Cover | `haltreq` × `resumereq` = {`1,0`}, {`0,1`}, {`1,1`}, {`0,0`} | P1 | Pass | |
| RES-008-V | Cover | `resumereq` × prior state = {halted, running, in reset} | P1 | Pass | |

## 3.6 Abstract commands

**Intent.** Read and write hart state without the hart executing anything the
debugger supplied — the minimum capability for a hart with no working memory.

**Workflow** (Appendix A `#accessing-registers`). Write `data0..` if writing →
write `command` → poll `abstractcs.busy` → read `cmderr` → read `data0..`.

| ID | Type | Action / Check / Cover | Reference | Pri | Status | Remarks |
|---|---|---|---|---|---|---|
| AC-001-S | Stimulate | Access Register, `regno=0x1008` (`x8`), `write=0`, `aarsize=3` | `debug_module.html#access-register` | P0 | Pass | `gpr_write_uvm` (4/4) |
| AC-001-C | Check | `abstractcs.busy` clears, `cmderr=0`, `data0` holds the GPR value | `debug_module.html#abstractcs` | P0 | Pass | |
| AC-002-S | Stimulate | Write `data0=0xA5A5_A5A5`; Access Register with `write=1` to a GPR; read it back | `debug_module.html#access-register` | P0 | Pass | |
| AC-002-C | Check | Read-back equals the written value | `debug_module.html#access-register` | P0 | Pass | |
| AC-003-S | Stimulate | Access Register on `regno=0x1000` (`x0`) with `write=1` | `debug_module.html#access-register` | P1 | Not started | |
| AC-003-C | Check | `x0` still reads 0 | `debug_module.html#access-register` | P1 | Not started | |
| AC-004-S | Stimulate | Access Register on a CSR `regno` (e.g. `0x07b0` for `dcsr`) | `debug_module.html#access-register` | P0 | Pass | `csr_access_uvm` 3/4 |
| AC-004-C | Check | `cmderr=0`; `data0` holds the CSR value | `debug_module.html#access-register` | P0 | Pass | |
| AC-005-S | Stimulate | Access Register with `aarsize` the DUT does not support | `debug_module.html#access-register` | P1 | Not started | |
| AC-005-C | Check | `cmderr=2` (not supported); no hart state changes | `debug_module.html#abstractcs` | P1 | Not started | |
| AC-006-S | Stimulate | Access Register with an unimplemented `regno` | `debug_module.html#access-register` | P1 | Not started | |
| AC-006-C | Check | `cmderr` is 2 or 3; the DM remains usable | `debug_module.html#abstractcs` | P1 | Not started | |
| AC-007-S | Stimulate | Issue any abstract command while the hart is **running** | `debug_module.html#abstractcs` | P0 | Pass | |
| AC-007-C | Check | `cmderr=4` (halt/resume) | `debug_module.html#abstractcs` | P0 | Pass | Observed while root-causing SSTEP-004 |
| AC-008-S | Stimulate | Provoke `cmderr!=0`, then issue a **valid** command without clearing it | `debug_module.html#abstractcs` | P0 | Not started | |
| AC-008-C | Check | `cmderr` retains its original value — it is sticky, and the valid command does not clear it | `debug_module.html#abstractcs` | P0 | Not started | A debugger that forgets this misattributes the next failure |
| AC-009-S | Stimulate | Write 1s to `cmderr`, then issue a valid command | `debug_module.html#abstractcs` | P0 | Not started | |
| AC-009-C | Check | `cmderr=0` and the command completes normally | `debug_module.html#abstractcs` | P0 | Not started | |
| AC-010-S | Stimulate | Access Register with `postexec=1` and a program buffer loaded | `debug_module.html#access-register` | P1 | Pass | `program_buffer_uvm` (6/6) |
| AC-010-C | Check | Register transfer happens **and** the program buffer executes | `debug_module.html#access-register` | P1 | Pass | |
| AC-011-S | Stimulate | Access Register with `transfer=0`, `postexec=1` | `debug_module.html#access-register` | P2 | Not started | |
| AC-011-C | Check | No register transfer; program buffer still runs | `debug_module.html#access-register` | P2 | Not started | |
| AC-012-S | Stimulate | Access Register with `aarpostincrement=1`, twice | `debug_module.html#access-register` | P2 | Not started | |
| AC-012-C | Check | `command.regno` has advanced by one between the two | `debug_module.html#access-register` | P2 | Not started | |
| AC-013-S | Stimulate | Issue `cmdtype=1` (Quick Access) and `cmdtype=2` (Access Memory) | `debug_module.html#abstractcs` | P1 | Not started | Both absent on this DUT |
| AC-013-C | Check | `cmderr=2` (not supported); DM remains usable | `debug_module.html#abstractcs` | P1 | Not started | |
| AC-014-S | Stimulate | Set `abstractauto`, then read `data0` | `debug_module.html#abstractauto` | P2 | Not started | |
| AC-014-C | Check | The command re-executes automatically on the `data0` access | `debug_module.html#abstractauto` | P2 | Not started | |
| AC-015-C | Check | After any abstract command, GPRs/CSRs other than the target are unchanged | `debug_module.html#abstract-commands` | P0 | Not started | Except `dscratch0/1` — see RAP-023 |
| AC-016-V | Cover | `cmderr` = {0 none, 1 busy, 2 not supported, 3 exception, 4 halt/resume, 5 bus, 7 other} | `debug_module.html#abstractcs` | P1 | Not started | |
| AC-017-V | Cover | `regno` class = {GPR, FPR, CSR, unimplemented}; `aarsize` = {32, 64, unsupported} | P1 | Not started | |

## 3.7 Program Buffer

**Intent.** Execute arbitrary instructions on a halted hart, for everything
abstract commands cannot express.

| ID | Type | Action / Check / Cover | Reference | Pri | Status | Remarks |
|---|---|---|---|---|---|---|
| PB-001-S | Stimulate | Write `addi x8,x8,1` then `ebreak` into `progbuf`; run with `postexec=1` | `debug_module.html#program-buffer` | P0 | Pass | `program_buffer_uvm` (6/6) |
| PB-001-C | Check | `x8` incremented by 1; `cmderr=0`; hart still in Debug Mode | `debug_module.html#program-buffer` | P0 | Pass | |
| PB-002-S | Stimulate | Use the program buffer to load from a known memory address into a GPR | `debug_module.html#program-buffer` | P0 | Not started | |
| PB-002-C | Check | GPR holds the memory contents, honouring the hart's MMU and PMP | `debug_module.html#program-buffer` | P0 | Not started | Contrast with SBA — RAP-027 |
| PB-003-S | Stimulate | Fill all 8 `progbuf` words | `debug_module.html#abstractcs` | P1 | Not started | |
| PB-003-C | Check | All 8 execute in order | `debug_module.html#program-buffer` | P1 | Not started | |
| PB-004-C | Check | With `dmstatus.impebreak=1`, a buffer with no explicit `ebreak` still returns to Debug Mode | `debug_module.html#dmstatus` | P1 | Pass | `impebreak=1` on this DUT |
| PB-005-S | Stimulate | Place an instruction that faults (e.g. load from an unmapped address) in the buffer | `debug_module.html#program-buffer` | P0 | Pass | `sw_breakpoint_progbuf_uvm` (3/3) |
| PB-005-C | Check | `cmderr=3` (exception); hart stays in Debug Mode and accepts the next command | `debug_module.html#abstractcs` | P0 | Pass | |
| PB-006-S | Stimulate | Place an illegal instruction encoding in the buffer | `debug_module.html#program-buffer` | P1 | Not started | |
| PB-006-C | Check | `cmderr=3`; DM recovers | `debug_module.html#abstractcs` | P1 | Not started | |
| PB-007-S | Stimulate | Place a jump targeting an address outside the program buffer | `debug_module.html#program-buffer` | P2 | Not started | |
| PB-007-C | Check | Record the behaviour — the spec permits treating it as an illegal instruction | `debug_module.html#program-buffer` | P2 | Not started | Document what this DUT does; do not assert one option |
| PB-008-S | Stimulate | Execute the buffer twice without rewriting it | `debug_module.html#program-buffer` | P2 | Not started | |
| PB-008-C | Check | Second execution behaves identically; buffer contents persisted | `debug_module.html#program-buffer` | P2 | Not started | |
| PB-009-C | Check | Program buffer executes at the privilege recorded in `dcsr.prv` | `Sdext.html#debugmode` | P1 | Not started | |
| PB-010-V | Cover | Buffer outcome = {normal `ebreak` return, implicit `ebreak`, exception, illegal instruction, control transfer out} | P1 | Not started | |

## 3.8 System Bus Access

**Intent.** Reach memory with no working CPU — independent of the hart, its MMU
and its PMP.

> **Blocked.** `sbcs.sbaccess` is hardwired on this DUT (RST-038), so every row
> below aborts before its verdict. Specified, not skipped.

| ID | Type | Action / Check / Cover | Reference | Pri | Status | Remarks |
|---|---|---|---|---|---|---|
| SBA-001-S | Stimulate | Set `sbaccess=2` (32-bit), write `sbaddress0=A`, read `sbdata0` | `debug_module.html#sbcs` | P0 | Blocked | Blocked by RST-038 |
| SBA-001-C | Check | `sbdata0` holds the contents of A; `sberror=0` | `debug_module.html#sbcs` | P0 | Blocked | |
| SBA-002-S | Stimulate | Write `sbaddress0=A`, write `sbdata0=V`, then read A back | `debug_module.html#sbcs` | P0 | Blocked | |
| SBA-002-C | Check | A holds V | `debug_module.html#sbcs` | P0 | Blocked | |
| SBA-003-S | Stimulate | Set `sbreadonaddr=1`, write `sbaddress0` | `debug_module.html#sbcs` | P1 | Blocked | |
| SBA-003-C | Check | A read is triggered by the address write alone | `debug_module.html#sbcs` | P1 | Blocked | |
| SBA-004-S | Stimulate | Set `sbreadondata=1`, read `sbdata0` repeatedly | `debug_module.html#sbcs` | P1 | Blocked | |
| SBA-004-C | Check | Each read triggers the next bus read | `debug_module.html#sbcs` | P1 | Blocked | |
| SBA-005-S | Stimulate | Set `sbautoincrement=1`, perform four reads | `debug_module.html#sbcs` | P1 | Blocked | |
| SBA-005-C | Check | `sbaddress0` advances by the access size each time | `debug_module.html#sbcs` | P1 | Blocked | Block transfers depend on this |
| SBA-006-S | Stimulate | Set `sbaccess` to an unsupported size | `debug_module.html#sbcs` | P1 | Blocked | |
| SBA-006-C | Check | `sberror=4` (unsupported size) | `debug_module.html#sbcs` | P1 | Blocked | |
| SBA-007-S | Stimulate | Write a misaligned `sbaddress0` for the selected size | `debug_module.html#sbcs` | P1 | Blocked | |
| SBA-007-C | Check | `sberror=3` (alignment) | `debug_module.html#sbcs` | P1 | Blocked | |
| SBA-008-S | Stimulate | Target an unmapped physical address | `debug_module.html#sbcs` | P1 | Blocked | |
| SBA-008-C | Check | `sberror=2` (bus error) | `debug_module.html#sbcs` | P1 | Blocked | |
| SBA-009-C | Check | `sberror` is sticky and clears only on a write of 1s | `debug_module.html#sbcs` | P1 | Blocked | |
| SBA-010-S | Stimulate | Perform SBA reads while the hart is running | `debug_module.html#sbcs` | P1 | Blocked | The main reason SBA exists |
| SBA-010-C | Check | Hart continues undisturbed; `dmstatus.allrunning=1` throughout | `debug_module.html#sbcs` | P1 | Blocked | |
| SBA-011-V | Cover | `sbaccess` = {8, 16, 32, 64, 128, unsupported}; `sberror` = {0,1,2,3,4,7} | P1 | Blocked | |

## 3.9 Single-step — external, via `dcsr.step`

**Intent.** Execute exactly one instruction and return to Debug Mode unaided,
**including instructions that would otherwise never complete**.

**Workflow** (Appendix A `#single-step`). The hart is halted first — that
halt uses `haltreq` and is a precondition, not part of the test:

1. `haltreq=1` → poll `allhalted` → **`haltreq=0`** (the clear matters, see below)
2. Access Register write `dcsr.step=1`
3. `resumereq=1` → hart executes `dret`, retires exactly one instruction
4. Hart re-enters Debug Mode **on its own**
5. Read `dcsr.cause`, expect 4

The property under test is step 4: the hart re-halts with `haltreq` deasserted
throughout steps 3–4. Leaving `haltreq` set would re-halt the hart for the
original request and the test would pass having proved nothing — which is why
the `haltreq=0` write in step 1 is load-bearing, and why `SSTEP-001-C` checks
it explicitly rather than assuming it.

> The published v1.0 HTML renders this paragraph with an empty cross-reference
> (*"the debugger just sets in before letting the hart run"*). Cite
> `Sdext.html#stepbit` for the normative text.

| ID | Type | Action / Check / Cover | Reference | Pri | Status | Remarks |
|---|---|---|---|---|---|---|
| SSTEP-001-S | Stimulate | Halt the hart (`haltreq=1`, poll `allhalted`, then `haltreq=0`); Access Register write `dcsr.step=1`; write `resumereq=1` | `Sdext.html#stepbit` | P0 | Pass | `single_step_uvm` (9/9) |
| SSTEP-001-C0 | Check | `dmcontrol.haltreq` reads 0 before `resumereq` is written, and stays 0 until the hart re-halts | `debug_module.html#dmcontrol` | P0 | Not started | **Guards the whole test.** With `haltreq` still set the hart re-halts for the original request and the step proves nothing |
| SSTEP-001-C | Check | After `resumereq`, `dmstatus.allhalted` returns to 1 with `haltreq=0` throughout — the hart re-entered Debug Mode on its own | `debug_module.html#dmstatus` | P0 | Pass | |
| SSTEP-001-C2 | Check | `dcsr.cause == 4` (step) | `Sdext.html#csr-dcsr` | P0 | Pass | Not 3 — a 3 means the hart never stepped |
| SSTEP-001-C3 | Check | `dpc` advanced by exactly the stepped instruction's length | `Sdext.html#csr-dpc` | P0 | Pass | |
| SSTEP-002-S | Stimulate | Step a 2-byte compressed instruction | `Sdext.html#stepbit` | P1 | Pass | |
| SSTEP-002-C | Check | `dpc` advanced by 2 | `Sdext.html#csr-dpc` | P1 | Pass | |
| SSTEP-003-S | Stimulate | Step a taken branch | `Sdext.html#stepbit` | P1 | Not started | |
| SSTEP-003-C | Check | `dpc` == branch target, not the sequential next address | `Sdext.html#csr-dpc` | P1 | Not started | |
| SSTEP-004-S | Stimulate | Step until `dpc` == address of a `wfi` with no interrupt pending; set `dcsr.step=1`; `resumereq` | `Sdext.html#stepbit` | P0 | Pass | |
| SSTEP-004-C | Check | After `resumereq`, `dmstatus.allhalted` returns to 1 with `haltreq=0` throughout | `debug_module.html#dmstatus` | P0 | Pass | **Found a real CVA6 defect.** Without the fix: `dmstatus=0x00830c83`, `allrunning=1` on three successive reads — the hart never returned |
| SSTEP-004-C2 | Check | `dcsr.cause == 4`; `dpc` advanced by 4 (the `wfi`'s own length) | `Sdext.html#csr-dcsr` | P0 | Pass | `wfi_ctrl` armed the stall without checking `dcsr.step`. Filed `openhwgroup/cva6#3549` (dup of #3497, PR #3525). Fixed by gating on `!dcsr_q.step` |
| SSTEP-005-S | Stimulate | Step `wrs.sto` / `wrs.nto` | `Sdext.html#stepbit` | P3 | N/A | Zawrs absent — would decode illegal and test the trap handler instead |
| SSTEP-006-S | Stimulate | Set `dcsr.stepie=0`, raise an enabled interrupt, then step one instruction | `Sdext.html#csr-dcsr` | P1 | Pass | `stepie=0` is our sequences' default |
| SSTEP-006-C | Check | No interrupt is taken during the step; `dcsr.cause=4`; `mepc` unchanged | `Sdext.html#csr-dcsr` | P1 | Not started | |
| SSTEP-007-S | Stimulate | Set `dcsr.stepie=1`, raise an enabled interrupt, then step | `Sdext.html#csr-dcsr` | P1 | Not started | |
| SSTEP-007-C | Check | The interrupt is taken; `dpc` == trap handler entry | `Sdext.html#csr-dcsr` | P1 | Not started | |
| SSTEP-008-S | Stimulate | Step an instruction that traps (e.g. a load from an unmapped address) | `Sdext.html#stepbit` | P1 | Not started | |
| SSTEP-008-C | Check | Debug Mode is re-entered with `dpc` == the handler's first instruction | `Sdext.html#stepbit` | P1 | Not started | Related upstream issue #3429 |
| SSTEP-009-S | Stimulate | Step an `ecall`, an `mret`, and an `sret` | `Sdext.html#stepbit` | P1 | Not started | |
| SSTEP-009-C | Check | `dcsr.prv` reflects the privilege **after** the transition | `Sdext.html#csr-dcsr` | P1 | Not started | |
| SSTEP-010-S | Stimulate | Set a trigger at the PC about to be stepped, then step | `Sdtrig.html` | P2 | Not started | OpenOCD removes the breakpoint first (`riscv.c:4201`) — check the DM tolerates both orders |
| SSTEP-010-C | Check | Exactly one of {step, trigger} reports; `dcsr.cause` is unambiguous | `Sdext.html#csr-dcsr` | P2 | Not started | |
| SSTEP-011-S | Stimulate | Enable a watchpoint, then step, then read the trigger registers back | `Sdtrig.html` | P2 | Not started | OpenOCD disables watchpoints around a step (`riscv.c:4213`) — workflow-derived, not required |
| SSTEP-011-C | Check | Trigger registers are restored to their pre-step values | `Sdtrig.html` | P2 | Not started | |
| SSTEP-012-S | Stimulate | Write `dcsr.step=0`, then `resumereq` | `Sdext.html#csr-dcsr` | P0 | Pass | |
| SSTEP-012-C | Check | Hart runs freely; no autonomous re-halt | `debug_module.html#dmstatus` | P0 | Pass | |
| SSTEP-013-S | Stimulate | Step 14 consecutive instructions | `Sdext.html#stepbit` | P1 | Pass | Observed clean |
| SSTEP-013-C | Check | `dpc` advances monotonically; `dcsr.cause=4` every time; no drift | `Sdext.html#csr-dpc` | P1 | Pass | |
| SSTEP-014-V | Cover | Stepped instruction class = {ordinary, compressed, taken branch, not-taken branch, `wfi`, trapping, privilege-changing, load, store} | P1 | Not started | |
| SSTEP-015-V | Cover | `stepie` × interrupt-pending = {0,0}, {0,1}, {1,0}, {1,1} | P1 | Not started | |
| SSTEP-016-V | Cover | Privilege at step = {M, S, U} | P1 | Not started | |

## 3.10 Single-step — native, via the `icount` trigger

**Intent.** Let an M-mode OS or debug stub single-step a less-privileged program
with no access to `dcsr`. **This is a different mechanism from §3.9 with
different guarantees**, and the plan must not conflate them.

The spec is explicit about the limitations, and two of them invert §3.9's
behaviour:

> Interrupts will fire as usual. Debuggers that want to disable interrupts while
> stepping must disable them by changing `mstatus`, and specially handle
> instructions that read `mstatus`.
> **`wfi` instructions are not treated specially and might take a very long time
> to complete.**

| | external step (§3.9) | native step (§3.10) |
|---|---|---|
| Mechanism | `dcsr.step` | `icount` trigger, `count=1` |
| Interrupt masking | `dcsr.stepie` | none — debugger must edit `mstatus` |
| `wfi` | treated as a `nop` | **not** special; may stall indefinitely |

| ID | Type | Action / Check / Cover | Reference | Pri | Status | Remarks |
|---|---|---|---|---|---|---|
| NSTEP-001-S | Stimulate | From M-mode, set `icount` with `count=1`, `action=0`, `m=0`; `mret` to U-mode | `Sdext.html#stepicount` | P2 | Not started | |
| NSTEP-001-C | Check | Exactly one U-mode instruction retires before the trap back to M-mode | `Sdext.html#stepicount` | P2 | Not started | |
| NSTEP-002-S | Stimulate | Repeat NSTEP-001 with an enabled interrupt pending | `Sdext.html#stepicount` | P2 | Not started | |
| NSTEP-002-C | Check | The interrupt fires — `icount` provides **no** masking, unlike `dcsr.stepie` | `Sdext.html#stepicount` | P2 | Not started | Inverts SSTEP-006 |
| NSTEP-003-S | Stimulate | Clear `mstatus.MIE` before stepping, then step | `Sdext.html#stepicount` | P2 | Not started | The spec's prescribed workaround |
| NSTEP-003-C | Check | No interrupt is taken during the step | `Sdext.html#stepicount` | P2 | Not started | |
| NSTEP-004-S | Stimulate | Step an instruction that reads `mstatus` while the debugger has modified it | `Sdext.html#stepicount` | P2 | Not started | |
| NSTEP-004-C | Check | Record whether the program observes the debugger's `mstatus` value | `Sdext.html#stepicount` | P2 | Not started | The spec says such instructions need special handling — this row quantifies the exposure |
| NSTEP-005-S | Stimulate | Step a `wfi` using `icount` with no interrupt pending | `Sdext.html#stepicount` | P2 | Not started | |
| NSTEP-005-C | Check | The `wfi` is **not** treated as a `nop`; the hart may stall until an interrupt arrives | `Sdext.html#stepicount` | P2 | Not started | **Opposite of SSTEP-004.** Confirm the stall is real rather than assuming §3.9's rule applies |
| NSTEP-006-C | Check | Stepping in the same privilege mode as the debug stub behaves per §`nativestep` | `debugger_implementation.html#nativestep` | P3 | Not started | Appendix A flags this case as more complicated |
| NSTEP-007-V | Cover | `icount` step from = {U-mode with M-mode stub, same privilege as stub} | P2 | Not started | |

## 3.11 Debug Mode entry and exit

| ID | Type | Action / Check / Cover | Reference | Pri | Status | Remarks |
|---|---|---|---|---|---|---|
| DM-001-S | Stimulate | Enable `dcsr.ebreakm=1`; execute `ebreak` in M-mode | `Sdext.html#csr-dcsr` | P0 | Pass | `sw_breakpoint_progbuf_uvm` |
| DM-001-C | Check | Debug Mode entered; `dcsr.cause=1` (ebreak) | `Sdext.html#csr-dcsr` | P0 | Pass | |
| DM-002-S | Stimulate | Set `dcsr.ebreakm=0`; execute `ebreak` in M-mode | `Sdext.html#csr-dcsr` | P0 | Not started | |
| DM-002-C | Check | Ordinary breakpoint trap, **not** Debug Mode; `mcause=3` | `Sdext.html#csr-dcsr` | P0 | Not started | The mirror of DM-001 — catches a stuck-enabled bit |
| DM-003-S | Stimulate | Execute `dret` from Debug Mode | `Sdext.html#dret` | P0 | Pass | Observed in trace |
| DM-003-C | Check | Hart returns to `dpc` at privilege `dcsr.prv` | `Sdext.html#dret` | P0 | Pass | |
| DM-004-S | Stimulate | Execute `dret` in M-mode outside Debug Mode | `Sdext.html#dret` | P1 | Not started | |
| DM-004-C | Check | Illegal-instruction trap | `Sdext.html#dret` | P1 | Not started | |
| DM-005-C | Check | Interrupts do not fire while the hart is in Debug Mode | `Sdext.html#debugmode` | P0 | Not started | |
| DM-006-S | Stimulate | Set `dcsr.stopcount=1`, enter Debug Mode, read `mcycle` before and after a delay | `Sdext.html#csr-dcsr` | P2 | Not started | |
| DM-006-C | Check | `mcycle` does not advance while halted | `Sdext.html#csr-dcsr` | P2 | Not started | |
| DM-007-S | Stimulate | Set `dcsr.stoptime=1`, enter Debug Mode, read `time` before and after | `Sdext.html#csr-dcsr` | P2 | Not started | |
| DM-007-C | Check | `time` does not advance while halted | `Sdext.html#csr-dcsr` | P2 | Not started | |
| DM-008-C | Check | The hart parks in the Debug ROM loop and stays responsive indefinitely | `debug_module.html` | P0 | Pass | A stride bug here hung every abstract command — fixed in riscv-dbg PR #4 `7c4155f` |
| DM-009-C | Check | Debug ROM `HALTED`/`GOING`/`RESUMING`/`EXCEPTION` addresses agree with `dm_mem`'s decode | `debug_module.html` | P0 | Pass | The defect above: ROM used an 8-byte stride, `dm_mem` decoded 4 |
| DM-010-V | Cover | `dcsr.cause` = {1 ebreak, 2 trigger, 3 haltreq, 4 step, 5 resethaltreq} | `Sdext.html#csr-dcsr` | P0 | Not started | Every cause reachable — the real coverage goal |
| DM-011-V | Cover | Entry privilege `dcsr.prv` = {M, S, U} | `Sdext.html#csr-dcsr` | P1 | Not started | |

## 3.12 Triggers (Sdtrig)

**Intent.** Halt on a condition rather than on a debugger request. The largest
untested area in this plan.

| ID | Type | Action / Check / Cover | Reference | Pri | Status | Remarks |
|---|---|---|---|---|---|---|
| TRIG-001-S | Stimulate | Walk `tselect` from 0 upward, reading `tdata1` at each index | `Sdtrig.html#enumeration` | P0 | Pass | `trigger_uvm` (13/13) |
| TRIG-001-C | Check | Trigger count and each trigger's `type` are discoverable | `Sdtrig.html#enumeration` | P0 | Pass | |
| TRIG-002-S | Stimulate | Write `tselect` beyond the implemented count | `Sdtrig.html` | P1 | Pass | |
| TRIG-002-C | Check | `tselect` reads back a legal (implemented) index | `Sdtrig.html` | P1 | Pass | |
| TRIG-003-S | Stimulate | Configure `mcontrol6` as an execute trigger at a known instruction address; run | `Sdtrig.html#mcontrol6` | P0 | Not started | |
| TRIG-003-C | Check | Debug Mode entered at that address; `dcsr.cause=2` (trigger) | `Sdext.html#csr-dcsr` | P0 | Not started | |
| TRIG-004-S | Stimulate | Configure `mcontrol6` as a load trigger on a known data address; run a load | `Sdtrig.html#mcontrol6` | P0 | Not started | |
| TRIG-004-C | Check | `dcsr.cause=2`; `dpc` is the load instruction | `Sdtrig.html#mcontrol6` | P0 | Not started | |
| TRIG-005-S | Stimulate | Configure a store trigger; run a store | `Sdtrig.html#mcontrol6` | P0 | Not started | |
| TRIG-005-C | Check | `dcsr.cause=2` | `Sdtrig.html#mcontrol6` | P0 | Not started | |
| TRIG-006-S | Stimulate | Write `tdata1=0` for a configured trigger; re-run the matching access | `Sdtrig.html` | P1 | Pass | |
| TRIG-006-C | Check | No trigger fires | `Sdtrig.html` | P1 | Pass | |
| TRIG-007-S | Stimulate | Attempt `tdata1` writes while the hart is running | `Sdtrig.html` | P1 | Not started | |
| TRIG-007-C | Check | Behaviour matches the spec's restriction on updates from a running hart | `Sdtrig.html` | P1 | Not started | |
| TRIG-008-S | Stimulate | Configure `icount` with `count=1` | `Sdtrig.html#icount` | P2 | Not started | Feeds §3.10 |
| TRIG-008-C | Check | Fires after exactly one instruction | `Sdtrig.html#icount` | P2 | Not started | |
| TRIG-009-S | Stimulate | Configure `itrigger` and `etrigger` | `Sdtrig.html#itrigger` | P2 | Not started | |
| TRIG-009-C | Check | Fire on the configured interrupt and exception respectively | `Sdtrig.html#itrigger` | P2 | Not started | |
| TRIG-010-C | Check | Trigger priority against a simultaneous exception matches §5.1.3 | `Sdtrig.html#5-1-3-priority` | P2 | Not started | |
| TRIG-011-V | Cover | Trigger type = {execute, load, store, `icount`, `itrigger`, `etrigger`} | P1 | Not started | |
| TRIG-012-V | Cover | Privilege enable bits = {m, s, u} × fired/not-fired | P1 | Not started | |

## 3.13 Halt and resume groups

| ID | Type | Action / Check / Cover | Reference | Pri | Status | Remarks |
|---|---|---|---|---|---|---|
| HG-001-S | Stimulate | Write `dmcs2` with `grouptype=0`, a group number, `hgselect=0`, `hgwrite=1` | `debug_module.html#dmcs2` | P2 | Not started | |
| HG-001-C | Check | Read-back reports the hart in that halt group | `debug_module.html#dmcs2` | P2 | Not started | |
| HG-002-S | Stimulate | Halt one member of a multi-hart halt group | `debug_module.html#halt-groups` | P2 | N/A | Single-hart DUT — cannot be demonstrated |
| HG-003-S | Stimulate | Assert the external trigger configured in `dmcs2.dmexttrigger` | `debug_module.html#dmcs2` | P2 | Pass | `external_trigger_uvm` (3/3) |
| HG-003-C | Check | The group halts in response | `debug_module.html#dmcs2` | P2 | Pass | |
| HG-004-C | Check | A group halt drives the outgoing external trigger | `debug_module.html#dmcs2` | P2 | Not started | |

## 3.14 Authentication

| ID | Type | Action / Check / Cover | Reference | Pri | Status | Remarks |
|---|---|---|---|---|---|---|
| AUTH-001-C | Check | `dmstatus.authenticated=1` on a DM with no authentication implemented | `debug_module.html#dmstatus` | P1 | Not started | The only row applying to this DUT |
| AUTH-002-S | Stimulate | Attempt DM register access with `authenticated=0` | `debug_module.html#authdata` | P3 | N/A | Not implemented |
| AUTH-003-S | Stimulate | Perform the `authdata` challenge/response exchange | `debug_module.html#authdata` | P3 | N/A | |

## 3.15 DTM and DMI transport

| ID | Type | Action / Check / Cover | Reference | Pri | Status | Remarks |
|---|---|---|---|---|---|---|
| DTM-001-S | Stimulate | Drive TMS sequences through every JTAG TAP state | `dtm.html` | P0 | Pass | Underpins every other test |
| DTM-001-C | Check | Each state is reached and exits correctly | `dtm.html` | P0 | Pass | |
| DTM-002-C | Check | IDCODE reads the expected device value | `dtm.html` | P0 | Pass | `discovery_uvm` |
| DTM-003-S | Stimulate | DMI read (`op=1`) and write (`op=2`) to a known DM register | `dtm.html#dmi` | P0 | Pass | |
| DTM-003-C | Check | `op` returns 0 (success); data matches | `dtm.html#dmi` | P0 | Pass | |
| DTM-004-S | Stimulate | Issue DMI accesses faster than the DM can service | `dtm.html#dmi` | P0 | Not started | |
| DTM-004-C | Check | `op=3` (busy) is returned; retrying after `dmireset` succeeds | `dtm.html#dmi` | P0 | Not started | |
| DTM-005-C | Check | A DMI error is sticky — subsequent accesses keep failing until `dmireset` | `dtm.html#dtmcs` | P0 | Not started | See RST-020 |
| DTM-006-S | Stimulate | Issue a DMI access with `op=0` and with undefined `op` encodings | `dtm.html#dmi` | P2 | Not started | |
| DTM-006-C | Check | No hang; the DM remains usable | `dtm.html#dmi` | P2 | Not started | |
| DTM-007-S | Stimulate | Address a DMI location beyond `dtmcs.abits` | `dtm.html#dmi` | P2 | Not started | |
| DTM-007-C | Check | Access is ignored or flagged; no hang | `dtm.html#dmi` | P2 | Not started | |
| DTM-008-S | Stimulate | Reset the TAP mid-DMI-transaction | `dtm.html` | P2 | Not started | |
| DTM-008-C | Check | DTM returns to a known state; the next access succeeds | `dtm.html` | P2 | Not started | |
| DTM-009-V | Cover | `dmi.op` result = {0 success, 2 failed, 3 busy}; `dtmcs.dmistat` = {0, 2, 3} | P1 | Not started | |

---

## Provenance

Normative text is quoted from the ratified v1.0 specification, cached per page
with its anchor, so every `Reference` resolves to the exact paragraph. The
harvested obligation set and generated cross-reference live under
`testplans/generated/` for audit; this document is the plan of record.

Debugger workflows come from the specification's Appendix A
(`debugger_implementation.html`). Rows derived from OpenOCD
(`src/target/riscv/`) cite file and line and assert only that the DM tolerates
the sequence — **debugger behaviour is evidence of convention, never of
requirement**.

### Open defects referenced above

| Finding | Rows | Status |
|---|---|---|
| Single-step over `wfi` deadlocks the hart | SSTEP-004 | `openhwgroup/cva6#3549`, dup of #3497 — PR #3525 open upstream |
| `sbcs.sbaccess` hardwired | RST-038, RAP-007, all of §3.8 | 10x `riscv-dbg` PR #4 regression, absent in pulp upstream. **Unfiled** |
| `allrunning=1` for a nonexistent hart | HS-002-C2 | Issue #130; reproduces on both DUTs |
| `dmstatus` mismatch on hart selection | HS-001 | `hart_selection_uvm` aborts before verdict |
| `dscratch0/1` clobbered by the DM | RAP-023 | **Testplan expectation is wrong** — `nscratch=2`. Re-specify, do not file |

### Rows marked `N/A`

Features absent from this DUT: Quick Access, Access Memory, hart array, Zawrs,
authentication, multi-hart, halt-on-reset (`hasresethaltreq=0`). Retained rather
than deleted so the exclusion stays auditable, and so the plan stays valid for a
DUT that implements them.
