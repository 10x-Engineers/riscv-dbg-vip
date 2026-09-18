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
| RST-038-S | Stimulate | Read `sbcs` immediately after reset, before any other `sbcs` write | P0 | Not started | Both values recorded so far carry `sbreadonaddr=1`, whose reset is 0 — **neither was a post-reset read** |
| RST-038-C | Check | `sbcs` == `0x20040808` for this DUT's presets (`sbasize=64`, `sbaccess64=1`), with `sbversion=1`, `sbbusy=0`, `sberror=0`, `sbreadonaddr=0` | P0 | Not started | Computed from the spec's per-field reset column, not observed |
| RST-038-C2 | Check | `sbcs.sbaccess` == **2** after reset | P0 | **Fail** | Spec gives `sbaccess` a reset of constant `2`, **not** `Preset`, with no exception for a DM that lacks 32-bit support. RTL forces 3 at `dm_csrs.sv:618`: `sbaccess = (BusWidth == 64) ? 3 : 2` |
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
| RST-051-S | Stimulate | Start an SBA transfer; assert `ndmreset` while `sbcs.sbbusy=1` | P2 | Blocked | Blocked by the `sbaccess` mismatch, RST-038-C2 |
| RST-051-C | Check | `sbbusy` clears; a subsequent SBA access succeeds | P2 | Blocked | |
| RST-052-S | Stimulate | Assert reset between a DMI request and its response | P2 | Not started | |
| RST-052-C | Check | DTM returns to idle; no stuck busy | P2 | Not started | |
| RST-053-S | Stimulate | Assert `ndmreset`, write `dmcontrol.haltreq=1` while held, release reset | P1 | Pass | The portable substitute for halt-on-reset when `hasresethaltreq=0` |
| RST-053-C | Check | Hart is not reported halted during reset; enters Debug Mode on release | P1 | Pass | |
| RST-054-C | Check | While `ndmreset` asserted, DMI accesses other than `dmcontrol` do not hang the DM | P2 | Not started | Spec says UNSPECIFIED — check for absence of hang, assert no value |
| RST-055-S | Stimulate | Ten back-to-back `ndmreset` assert/deassert pairs with no settling time | P2 | Not started | |
| RST-055-C | Check | DM reaches a consistent state; `dmstatus` readable after the last one | P2 | Not started | |
| RST-056-S | Stimulate | Assert `ndmreset` with the DM idle — no command, no SBA, no DMI in flight | P2 | Not started | Coverage: the baseline every other reset-activity cell is compared against |
| RST-056-C | Check | Reset completes and every DM register reads its reset value | P2 | Not started |  |

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
| RST-065-V | Cover | Reset source × DM activity at assertion | P1 | Not started | `cg_reset.x_source_x_activity` — which reset lands mid-operation decides what must survive |
| RST-066-V | Cover | Reset source × `havereset` lifecycle | P1 | Not started | `x_source_x_havereset` — catches a DM tracking `ndmreset` but missing an external reset |

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
| RAP-007-C | Check | Fields the spec permits an implementation to tie (`hartsel` high bits, `hartarraymask`, `dcsr` bits marked hardwireable) read their fixed value regardless of what is written | P1 | Not started | The spec grants tying **explicitly** where it means to; this row covers only those |
| RAP-007-C2 | Check | `sbcs.sbaccess` is writable — write each value 0..4 and read it back | P1 | **Fail** | `sbaccess` is declared **`R/W`**, not `WARL` and not `R`. RTL clobbers it: `dm_csrs.sv:513` applies the DMI write, then line 618 unconditionally overwrites `sbaccess` later in the same `always_comb`, so no debugger write can ever stick. **No clause anywhere in the spec permits tying this field** |
| RAP-007-C3 | Check | Writing an unsupported size to `sbaccess`, then starting a bus access, sets `sberror=4` | P1 | **Fail** | Spec: "If `sbaccess` has an unsupported value when the DM starts a bus access, the access is not performed and `sberror` is set to 4." Hardwiring makes this specified error path **unreachable** — the clause presupposes the field can hold an unsupported value |
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
| RAP-023-S | Stimulate | Debugger writes `0xDEADBEEF` to `dscratch0`, then executes any program-buffer command | `Sdext.html#csr-dscratch0` | P1 | Pass | `csr_access_uvm` TC-DCSR-003 |
| RAP-023-C | Check | With `hartinfo.nscratch=2`, `dscratch0/1` are DM scratch — the debugger's value is **not** expected to survive | `debug_module.html#hartinfo` | P1 | Pass | Re-specified: with `nscratch`=2 the DM owns `dscratch0/1`, so the check requires them to hold while halted and to stay accessible after the DM uses them -- measured: clobbered to 0x8/0xa by the resume, as declared |
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
| RAP-031-V | Cover | Interface = {DMI, hart CSR, hart load/store, SBA, program buffer} × register class | `debug_module.html` | P1 | Not started | |

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
| RAP-045-V | Cover | Gating state = {`dmactive=0`, `ndmreset=1`, `busy=1`, `sbbusy=1`, `authenticated=0`} | `debug_module.html` | P1 | Not started | |
| RAP-046-V | Cover | Interface × register class | `debug_module.html` | P1 | Not started | `x_interface_x_register` — which interfaces reach which storage at all |
| RAP-047-V | Cover | Interface × access type | `introduction.html#1-1-3-3-register-definition-format` | P0 | Not started | `x_interface_x_access_type` — a type is declared per field but **enforced per interface**. A DM enforcing it only on its DMI decode passes the per-field check while being wrong everywhere else |
| RAP-048-V | Cover | Register class × gating state | `debug_module.html` | P1 | Not started | `x_class_x_gating` — `dmcontrol` survives `dmactive=0`; debug CSRs go unreachable when the hart is not halted |

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
| ACT-005-V | Cover | `dmactive` transition × post-activation register read | `debug_module.html#dmcontrol` | P1 | Not started | `x_transition_x_post_read` — the same read proves opposite things: reset values after a reactivate, unchanged after an idempotent write |

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
| DIS-008-S | Stimulate | Issue DMI accesses idling far more than `dtmcs.idle` requires | `dtm.html#dtmcs` | P2 | Not started | Coverage: the generous-idling baseline every other test implicitly runs at |
| DIS-008-C | Check | Every access succeeds; no busy response | `dtm.html#dmi` | P2 | Not started |  |

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
| HS-005-V | Cover | Hart state reported = {running, halted, unavailable, nonexistent, in reset} | `debug_module.html#dmstatus` | P1 | Not started | |
| HS-006-V | Cover | `hartsel` = {0, max implemented, first nonexistent, all-ones} | `debug_module.html#dmcontrol` | P1 | Not started | |
| HS-007-S | Stimulate | Select the highest implemented hart index | `debug_module.html#dmcontrol` | P1 | Not started | Coverage: the boundary the DM must still decode |
| HS-007-C | Check | That hart's state is reported; `anynonexistent=0` | `debug_module.html#dmstatus` | P1 | Not started |  |
| HS-008-C | Check | With no selected hart in a given state, both its `all` and `any` bits read 0 | `debug_module.html#dmstatus` | P1 | Not started | Coverage: the neither cell, unreachable by a test that only checks the asserted case |
| HS-009-V | Cover | `hartsel` class × reported hart state | `debug_module.html#dmstatus` | P0 | Not started | `x_hartsel_x_state` — carries issue #130 as an illegal cell. A stale mux looks correct on either coverpoint alone |
| HS-010-V | Cover | `hartsel` class × all/any aggregation | `debug_module.html#dmstatus` | P1 | Not started | `x_hartsel_x_all_any` — `some_not_all` needs several harts selected; excluded here, retained for a multi-hart DUT |

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
| HALT-009-V | Cover | Hart activity at halt = {ordinary insn, `wfi`, taking a trap, in a tight loop, executing a load/store} | `debug_module.html#dmcontrol` | P1 | Not started | |
| HALT-010-S | Stimulate | Select multiple harts and assert `haltreq` | `debug_module.html#dmstatus` | P1 | N/A | Single-hart DUT — `allhalted` vs `anyhalted` cannot be distinguished |
| HALT-011-C | Check | A halt on a hart executing ordinary instructions completes within ~10 cycles | `debug_module.html#dmcontrol` | P2 | Not started | Coverage: the immediate-latency bin. Separating it from the stalled case stops a slow path hiding behind the bound |

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
| RES-007-V | Cover | `haltreq` × `resumereq` = {`1,0`}, {`0,1`}, {`1,1`}, {`0,0`} | `debug_module.html#dmcontrol` | P1 | Pass | |
| RES-008-V | Cover | `resumereq` × prior state = {halted, running, in reset} | `debug_module.html#dmcontrol` | P1 | Pass | |
| RES-009-V | Cover | Hart transition × `resumeack` | `debug_module.html#dmstatus` | P1 | Not started | `x_transition_x_resumeack` — the §3.5 asymmetry exists only as the pairing |
| RES-010-V | Cover | Request × prior state × halt latency | `debug_module.html#dmcontrol` | P2 | Not started | `x_request_x_latency` — ignored requests have no latency; conflating them hides a slow path |

## 3.6 Abstract commands

**Intent.** Read and write hart state without the hart executing anything the
debugger supplied — the minimum capability for a hart with no working memory.

**Workflow** (Appendix A `#accessing-registers`). Write `data0..` if writing →
write `command` → poll `abstractcs.busy` → read `cmderr` → read `data0..`.

| ID | Type | Action / Check / Cover | Reference | Pri | Status | Remarks |
|---|---|---|---|---|---|---|
| AC-020-S | Stimulate | Start a long Program-Buffer command via postexec, then read/write `data0` and `progbuf0` while `abstractcs.busy`=1 | `debug_module.html#abstract-commands` | P0 | Pass | `cmd_busy_uvm` — a delay loop holds busy long enough to race over JTAG |
| AC-020-C | Check | `cmderr` becomes 1 (busy) and the in-flight command is not corrupted | `debug_module.html#dm-abstractcs` | P0 | Pass | Observed cmderr=1, guard fired |
| AC-020-C2 | Check | Each of the four accesses is raced against its own command, so every one meets `cmderr`=0 | `debug_module.html#dm-abstractcs` | P0 | Pass | Racing several against one command only reaches the guard's inner arm with the first: it sets `cmderr` |
| AC-021-S | Stimulate | Write `command`, `abstractauto` and `abstractcs` while busy, each against its own command; `abstractcs` twice | `debug_module.html#dm-abstractcs` | P1 | Pass | The second `abstractcs` write meets `cmderr` already set |
| AC-021-C | Check | Every one is refused with `cmderr`=1 | `debug_module.html#dm-abstractcs` | P1 | Pass | |
| AC-022-C | Check | After clearing `cmderr`, a GPR round-trip succeeds — the DM is usable, not wedged | `debug_module.html#dm-abstractcs` | P0 | Pass | |
| AC-023-C | Check | Writes to the R/O `dmstatus` and `hartinfo` are ignored, not errors | `debug_module.html#dm-dmstatus` | P2 | Pass | |
| AC-024-S | Stimulate | Write and read `abstractauto` (0x18) | `debug_module.html#dm-abstractauto` | P2 | Pass | Implemented on this DUT; must be disarmed or later `data0` access re-runs the command |
| AC-025-S | Stimulate | Write `dmcontrol.setkeepalive`, then `clrkeepalive`, then `hasel`/`setresethaltreq`/`clrresethaltreq` | `debug_module.html#dm-dmcontrol` | P2 | Pass | The write is sampled, not its effect, so these are reachable on a single-hart DUT |
| AC-026-S | Stimulate | Issue abstract commands with `regno`[15:14] set, `regno`=0x100A (a0), and `regno`[5] set, each as a write and as a read | `debug_module.html#dm-command` | P1 | Pass | `dm_mem` decodes `regno` separately per direction; write-only left the three read arms uncovered |
| AC-027-C | Check | A resume issued to an already-running hart is a no-op | `debug_module.html#dm-dmcontrol` | P2 | Pass | |
| AC-028-C | Check | `command` reads 0; a write to an address with no register (0x2F) is ignored | `debug_module.html#dm-command` | P2 | Pass | `dm_csrs` case arms nothing else reaches |
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
| AC-017-V | Cover | `regno` class = {GPR, FPR, CSR, unimplemented}; `aarsize` = {32, 64, unsupported} | `debug_module.html#access-register` | P1 | Not started | |
| AC-018-S | Stimulate | Issue a command with an undefined `cmdtype` (3) | `debug_module.html#abstractcs` | P2 | Not started | Coverage: the reserved encoding |
| AC-018-C | Check | DM rejects it and remains usable; no hart state changes | `debug_module.html#abstractcs` | P2 | Not started |  |
| AC-019-S | Stimulate | Issue Access Register with a reserved `aarsize` (0, 1, 5, 6, 7) | `debug_module.html#access-register` | P2 | Not started | Coverage: undefined encodings, distinct from an unsupported-but-defined size |
| AC-019-C | Check | Rejected with `cmderr=2`; no transfer occurs | `debug_module.html#abstractcs` | P2 | Not started |  |
| AC-020-C | Check | If `cmderr=7` (other) is ever reported, the condition is investigated and classified | `debug_module.html#abstractcs` | P2 | Not started | Reaching this bin means the DM could not classify its own failure |
| AC-021-V | Cover | `regno` class × `aarsize` | `debug_module.html#access-register` | P1 | Not started | `x_regno_x_size` — 64-bit to a 32-bit CSR must fail while the same size on a GPR succeeds |
| AC-022-V | Cover | `cmdtype` × `cmderr` | `debug_module.html#abstractcs` | P1 | Not started | `x_cmdtype_x_cmderr` — an unimplemented type must give `cmderr=2`, not whatever the last command left |
| AC-023-V | Cover | Command flags × `cmderr` | `debug_module.html#access-register` | P1 | Not started | `x_flags_x_cmderr` — a transfer-plus-postexec command can fail in either phase; the debugger must tell which |

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
| PB-010-V | Cover | Buffer outcome = {normal `ebreak` return, implicit `ebreak`, exception, illegal instruction, control transfer out} | `debug_module.html#program-buffer` | P1 | Not started | |
| PB-011-S | Stimulate | Fill 2–7 of the 8 `progbuf` words and execute | `debug_module.html#program-buffer` | P2 | Not started | Coverage: the partial-fill case between one word and a full buffer |
| PB-011-C | Check | Only the written words execute; unused slots are not fetched | `debug_module.html#program-buffer` | P2 | Not started |  |
| PB-012-S | Stimulate | Use the program buffer to store to a known memory address | `debug_module.html#program-buffer` | P0 | Not started | Coverage: `memory_write` — PB-002 covers the load, nothing covered the store |
| PB-012-C | Check | Memory holds the written value, honouring the hart's MMU and PMP | `debug_module.html#program-buffer` | P0 | Not started | Contrast with SBA, which bypasses both — RAP-028 |
| PB-013-V | Cover | Buffer outcome × operation performed | `debug_module.html#program-buffer` | P1 | Not started | `x_outcome_x_operation` — an exception during a store leaves different state from one during a register read |
| PB-014-V | Cover | Buffer fill level × outcome | `debug_module.html#abstractcs` | P1 | Not started | `x_fill_x_outcome` — the last slot is where off-by-one errors live |

## 3.8 System Bus Access

**Intent.** Reach memory with no working CPU — independent of the hart, its MMU
and its PMP.

> **Blocked.** The reference model predicts `sbaccess=2` (the spec's reset
> constant) while the RTL forces 3, so fail-fast aborts these scenarios before
> their verdict. The mismatch is now understood (RST-038-C2, RAP-007-C2) and is
> an RTL defect, not a model defect — but until the comparison is reconciled the
> rows below stay unrun. Specified, not skipped.

| ID | Type | Action / Check / Cover | Reference | Pri | Status | Remarks |
|---|---|---|---|---|---|---|
| SBA-004-S | Stimulate | Set `sbautoincrement`, write a 4-word burst, read `sbaddress0` back | `debug_module.html#dm-sbcs` | P1 | Pass | `sba_uvm`. Stride is read back from `sbcs`, never assumed: this DUT hardwires `sbaccess`, so a test that assumes its own write stuck computes the wrong stride |
| SBA-005-S | Stimulate | Set `sbreadondata` and stream successive words by reading `sbdata0` | `debug_module.html#dm-sbcs` | P1 | Pass | Trigger is the data READ, not the address write |
| SBA-006-C | Check | `sbaddress1`/`sbdata1` decode when `sbasize`>32 | `debug_module.html#dm-sbaddress1` | P2 | Pass | |
| SBA-007-C | Check | An access to an unmapped address sets `sberror`, and writing 1s clears it | `debug_module.html#dm-sbcs` | P1 | Pass | |
| SBA-009-C | Check | Racing `sbdata`/`sbaddress` against a live transfer sets `sbbusyerror`, which clears and leaves the DM usable | `debug_module.html#dm-sbcs` | P2 | Pass | Does not assert the race lands: a DM fast enough to finish first is not wrong |
| SBA-010-C | Check | SBA works with the hart **running** — it is hart-independent | `debug_module.html#system-bus-access` | P1 | Pass | |
| SBA-019-V | Cover | `cg_sba.cp_sbaccess` widths other than the hardwired one | `debug_module.html#dm-sbcs` | P1 | Blocked | Excluded while #147 stands: a hardwired field cannot hold another width |
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
| SBA-011-V | Cover | `sbaccess` = {8, 16, 32, 64, 128, unsupported}; `sberror` = {0,1,2,3,4,7} | `debug_module.html#sbcs` | P1 | Blocked | |
| SBA-012-C | Check | A bus that never responds sets `sberror=1` (timeout) rather than hanging the DM | `debug_module.html#sbcs` | P1 | Blocked | Coverage: the timeout bin, distinct from a bus error |
| SBA-013-C | Check | If `sberror=7` (other) is reported, the condition is investigated and classified | `debug_module.html#sbcs` | P2 | Blocked |  |
| SBA-014-S | Stimulate | With `sbreadonaddr=0` and `sbreadondata=0`, write `sbaddress0` then explicitly access `sbdata0` | `debug_module.html#sbcs` | P1 | Blocked | Coverage: manual mode — the baseline the triggered modes are compared against |
| SBA-014-C | Check | No access occurs until the explicit data access | `debug_module.html#sbcs` | P1 | Blocked |  |
| SBA-015-S | Stimulate | Access an address in the body of mapped RAM, and the last mapped address | `debug_module.html#sbcs` | P1 | Blocked | Coverage: `ram_body` and `ram_top`; SBA-001 only used the base |
| SBA-015-C | Check | Both succeed with `sberror=0`; one past `ram_top` gives `sberror=2` | `debug_module.html#sbcs` | P1 | Blocked |  |
| SBA-016-V | Cover | Access size × alignment | `debug_module.html#sbcs` | P1 | Blocked | `x_size_x_alignment` — address 4 is aligned for 32-bit and misaligned for 64-bit; this is where `sberror=3` arises |
| SBA-017-V | Cover | Trigger mode × `sberror` | `debug_module.html#sbcs` | P1 | Blocked | `x_mode_x_error` — with autoincrement the address has already advanced, so the debugger must tell which word failed |
| SBA-018-V | Cover | Access size × address region | `debug_module.html#sbcs` | P1 | Blocked | `x_size_x_region` — a wide access near the top of memory straddles the boundary where a narrow one does not |

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
| SSTEP-006-C | Check | No interrupt is taken during the step; `dcsr.cause=4`; `mepc` unchanged | `Sdext.html#csr-dcsr` | P1 | Pass | `step_matrix_uvm` — timer interrupt pending via `mie.MTIE`, `mstatus.MIE=0` |
| SSTEP-007-S | Stimulate | Set `dcsr.stepie=1`, raise an enabled interrupt, then step | `Sdext.html#csr-dcsr` | P1 | Pass | `step_matrix_uvm`; pending but not taken in M (`mstatus.MIE=0`) |
| SSTEP-007-C | Check | The interrupt is taken; `dpc` == trap handler entry | `Sdext.html#csr-dcsr` | P1 | Not started | |
| SSTEP-008-S | Stimulate | Step an instruction that traps (e.g. a load from an unmapped address) | `Sdext.html#stepbit` | P1 | Pass | `step_matrix_uvm` — illegal instruction, `ecall`, `wfi` at U, from M/S/U |
| SSTEP-008-C | Check | Debug Mode is re-entered with `dpc` == the handler's first instruction | `Sdext.html#stepbit` | P1 | Fail | RTL-010 (upstream #3429): halts at handler+4, after the first handler instruction ran |
| SSTEP-009-S | Stimulate | Step an `ecall`, an `mret`, and an `sret` | `Sdext.html#stepbit` | P1 | Pass | `step_matrix_uvm` |
| SSTEP-009-C | Check | `dcsr.prv` reflects the privilege **after** the transition | `Sdext.html#csr-dcsr` | P1 | Fail | RTL-011 (#159): xRET step reports `dpc`=pc+4 and the pre-return privilege |
| SSTEP-010-S | Stimulate | Set a trigger at the PC about to be stepped, then step | `Sdtrig.html` | P2 | Not started | OpenOCD removes the breakpoint first (`riscv.c:4201`) — check the DM tolerates both orders |
| SSTEP-010-C | Check | Exactly one of {step, trigger} reports; `dcsr.cause` is unambiguous | `Sdext.html#csr-dcsr` | P2 | Not started | |
| SSTEP-011-S | Stimulate | Enable a watchpoint, then step, then read the trigger registers back | `Sdtrig.html` | P2 | Not started | OpenOCD disables watchpoints around a step (`riscv.c:4213`) — workflow-derived, not required |
| SSTEP-011-C | Check | Trigger registers are restored to their pre-step values | `Sdtrig.html` | P2 | Not started | |
| SSTEP-012-S | Stimulate | Write `dcsr.step=0`, then `resumereq` | `Sdext.html#csr-dcsr` | P0 | Pass | |
| SSTEP-012-C | Check | Hart runs freely; no autonomous re-halt | `debug_module.html#dmstatus` | P0 | Pass | |
| SSTEP-013-S | Stimulate | Step 14 consecutive instructions | `Sdext.html#stepbit` | P1 | Pass | Observed clean |
| SSTEP-013-C | Check | `dpc` advances monotonically; `dcsr.cause=4` every time; no drift | `Sdext.html#csr-dpc` | P1 | Pass | |
| SSTEP-015-S | Stimulate | Step a load and a store to a mapped address | `Sdext.html#stepbit` | P1 | Not started | Coverage hole: `SSTEP-014-V` listed load/store as a cover bin with no item able to reach it |
| SSTEP-015-C | Check | The access completes before Debug Mode is re-entered — destination register updated for the load, memory updated for the store; `dcsr.cause=4` | `Sdext.html#stepbit` | P1 | Not started | |
| SSTEP-014-V | Cover | Stepped instruction class = {ordinary, compressed, taken branch, not-taken branch, `wfi`, trapping, privilege-changing, load, store} | `Sdext.html#stepbit` | P1 | Not started | Owned by `cg_step.cp_stepped_class` |
| SSTEP-017-V | Cover | `stepie` × interrupt-pending = {0,0}, {0,1}, {1,0}, {1,1} | `Sdext.html#csr-dcsr` | P1 | Not started | |
| SSTEP-018-V | Cover | Privilege at step = {M, S, U} | `Sdext.html#csr-dcsr` | P1 | Not started | |
| SSTEP-019-S | Stimulate | Step a branch whose condition is false | `Sdext.html#stepbit` | P1 | Not started | Coverage: `not_taken_branch` — SSTEP-003 covers only the taken case |
| SSTEP-019-C | Check | `dpc` is the sequential next address, not the branch target | `Sdext.html#csr-dpc` | P1 | Not started |  |
| SSTEP-020-S | Stimulate | Step ~32 consecutive instructions across a loop back-edge | `Sdext.html#stepbit` | P1 | Pass | Coverage: `across_loop_backedge` — drift compounds across repeated taken branches |
| SSTEP-020-C | Check | `dpc` follows the branch every iteration; no cumulative drift | `Sdext.html#csr-dpc` | P1 | Pass |  |
| SSTEP-021-V | Cover | Stepped class × privilege | `Sdext.html#stepbit` | P1 | Pass | `x_class_x_privilege` — a trapping instruction from U enters the M handler; from M it stays in M |
| SSTEP-022-V | Cover | Stepped class × {`stepie`, interrupt pending} | `Sdext.html#csr-dcsr` | P0 | Pass | `x_class_x_stepie` — a `wfi` stepped with `stepie=1` and an interrupt pending may legitimately complete; with `stepie=0` it must be a nop. Testing the `wfi` at one setting leaves the harder half unmeasured |
| SSTEP-023-V | Cover | Stepped class × consecutive-step count | `Sdext.html#stepbit` | P2 | Not started | `x_class_x_consecutive` |

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
| NSTEP-001-S | Stimulate | From M-mode, set `icount` with `count=1`, `action=0`, `m=0`; `mret` to U-mode | `Sdext.html#stepicount` | P2 | Pass | `native_icount` (sw/native_icount.S), count 1 and 2 |
| NSTEP-001-C | Check | Exactly one U-mode instruction retires before the trap back to M-mode | `Sdext.html#stepicount` | P2 | Fail | RTL-014 (#163): the count also runs down in M, so the U instruction is never stepped |
| NSTEP-002-S | Stimulate | Repeat NSTEP-001 with an enabled interrupt pending | `Sdext.html#stepicount` | P2 | Not started | |
| NSTEP-002-C | Check | The interrupt fires — `icount` provides **no** masking, unlike `dcsr.stepie` | `Sdext.html#stepicount` | P2 | Not started | Inverts SSTEP-006 |
| NSTEP-003-S | Stimulate | Clear `mstatus.MIE` before stepping, then step | `Sdext.html#stepicount` | P2 | Not started | The spec's prescribed workaround |
| NSTEP-003-C | Check | No interrupt is taken during the step | `Sdext.html#stepicount` | P2 | Not started | |
| NSTEP-004-S | Stimulate | Step an instruction that reads `mstatus` while the debugger has modified it | `Sdext.html#stepicount` | P2 | Not started | |
| NSTEP-004-C | Check | Record whether the program observes the debugger's `mstatus` value | `Sdext.html#stepicount` | P2 | Not started | The spec says such instructions need special handling — this row quantifies the exposure |
| NSTEP-005-S | Stimulate | Step a `wfi` using `icount` with no interrupt pending | `Sdext.html#stepicount` | P2 | Not started | |
| NSTEP-005-C | Check | The `wfi` is **not** treated as a `nop`; the hart may stall until an interrupt arrives | `Sdext.html#stepicount` | P2 | Not started | **Opposite of SSTEP-004.** Confirm the stall is real rather than assuming §3.9's rule applies |
| NSTEP-006-C | Check | Stepping in the same privilege mode as the debug stub behaves per §`nativestep` | `debugger_implementation.html#nativestep` | P3 | Not started | Appendix A flags this case as more complicated |
| NSTEP-007-V | Cover | `icount` step from = {U-mode with M-mode stub, same privilege as stub} | `Sdext.html#stepicount` | P2 | Not started | |
| NSTEP-008-V | Cover | Native-step guarantee × privilege relationship | `Sdext.html#stepicount` | P2 | Not started | `x_guarantee_x_privilege` — stepping at the stub's own privilege makes the `mstatus` edit visible to the program being debugged |

## 3.10a Native debug (Sdtrig `action=0`, no debugger)

Self-checking firmware, run through the `run_elf` scenario, which reads the
program's own verdict from `tohost`. `native_*` programs are in
`cva6_sim/sw/`; `act_*` are riscv-arch-test (ACT4) programs built by
`mk/act_build.sh` with Spike as the reference. Every `native_*` program passes
on Spike. Operation catalog: VERIFICATION_STRATEGY.md, "Sdext & Trigger Module — Native-Debugging Verification Strategy".

| ID | Type | Action / Check / Cover | Reference | Pri | Status | Remarks |
|---|---|---|---|---|---|---|
| NATIVE-OP1-C | Check | `ebreak` with `dcsr.ebreakm=0` is an ordinary breakpoint exception (`mcause=3`, `mepc` at the ebreak) | `Sdext.html#csr-dcsr` | P1 | Pass | `debug_entry_uvm` TC-DCSR-012 |
| NATIVE-OP2-C | Check | `action=0` triggers raise a breakpoint exception: `mcontrol6` execute/load/store, `itrigger`, `etrigger` | `Sdtrig.html#nativetrigger` | P1 | Fail | `act_sdtrig_mcontrol6` (RTL-013), `native_etrigger` (RTL-015), `native_itrigger` (RTL-016) |
| NATIVE-OP3-C | Check | Native single-step with `icount`: fires after `count` instructions in enabled modes, `tval`=0, `pending` cleared | `Sdtrig.html` icount | P1 | Fail | `native_icount`, `act_sdtrig_icount` -- RTL-014 |
| NATIVE-OP4-C | Check | Re-entrancy: an `action=0` trigger does not fire in M-mode while `MIE`=0 (no `tcontrol`) | `Sdtrig.html#nativetrigger` | P2 | Fail | `native_reentrancy` -- RTL-017 (a SHOULD) |
| NATIVE-OP5-C | Check | The hit bits identify which trigger fired; `tval` is the matched address | `Sdtrig.html` mcontrol6 | P1 | Pass | `native_hit` |
| NATIVE-OP6-C | Check | Context-scoped triggers (`mcontext`/`scontext`/`textra`) | `Sdtrig.html` textra | P3 | N/A | This build has `SdtrigSupportTextra=0`: no `textra`, `scontext` or `mcontext` |
| NATIVE-OP7-C | Check | `dcsr`, `dpc`, `dscratch0/1` raise illegal instruction outside Debug Mode | `Sdext.html` | P1 | Pass | `native_dbgcsr` |
| NATIVE-ACT-C | Check | Trigger CSR access from M-mode (`tselect`/`tdata1-2`/`tinfo`) | `Sdtrig.html` | P1 | Pass | `act_sdtrig_access` |

## 3.11 Debug Mode entry and exit

| ID | Type | Action / Check / Cover | Reference | Pri | Status | Remarks |
|---|---|---|---|---|---|---|
| DCSR-010-S | Stimulate | Set `dcsr.ebreakm=1`, point `dpc` at an `ebreak` in the program, resume | `Sdext.html#csr-dcsr` | P0 | Pass | `debug_entry_uvm` — cannot be produced by any DMI write |
| DCSR-010-C | Check | The hart re-enters Debug Mode with `dcsr.cause`=1 (ebreak) | `Sdext.html#csr-dcsr` | P0 | Pass | |
| DCSR-011-S | Stimulate | Arm an mcontrol6 execute trigger (`action`=1) on a known instruction, resume into it | `Sdtrig.html` | P1 | N/A | cv64a6_imafdc_sv39 is built with `SDTRIG=0`; the tdata writes raise cmderr=3 |
| DCSR-011-C | Check | The hart enters Debug Mode with `dcsr.cause`=2 (trigger) | `Sdtrig.html` | P1 | N/A | As DCSR-011-S; the trigger bins are excluded at report time (`mk/fcov_exclusions.tcl`) |
| DCSR-012-C | Check | With `ebreakm=0`, executing `ebreak` does **not** enter Debug Mode; it traps with `mcause`=3 at the ebreak | `Sdext.html#csr-dcsr` | P0 | Pass | Checked BEFORE DCSR-010, or that test passes for the wrong reason |
| DCSR-013-S | Stimulate | With `dcsr.ebreaks=1` / `ebreaku=1`, resume into an `ebreak` at S / U (`dcsr.prv`, PMP entry 0 opened) | `Sdext.html#csr-dcsr` | P0 | Pass | `debug_entry_uvm` |
| DCSR-013-C | Check | Debug Mode entered with `cause`=1, `dpc` == the ebreak, `dcsr.prv` == the level it ran at | `Sdext.html#csr-dcsr` | P0 | Pass | |
| DCSR-014-S | Stimulate | Resume into a spin loop at S / U, then assert `haltreq` | `Sdext.html#csr-dcsr` | P0 | Pass | `debug_entry_uvm` |
| DCSR-014-C | Check | `cause`=3, `dcsr.prv` == S / U, `dpc` == the interrupted instruction | `Sdext.html#csr-dpc` | P0 | Pass | |
| DCSR-015-S | Stimulate | Single-step one ordinary instruction at S / U | `Sdext.html#stepbit` | P0 | Pass | `debug_entry_uvm` |
| DCSR-015-C | Check | `cause`=4, `dcsr.prv` unchanged, `dpc` == the next instruction | `Sdext.html#csr-dpc` | P0 | Pass | |
| DM-001-S | Stimulate | Enable `dcsr.ebreakm=1`; execute `ebreak` in M-mode | `Sdext.html#csr-dcsr` | P0 | Pass | `sw_breakpoint_progbuf_uvm` |
| DM-001-C | Check | Debug Mode entered; `dcsr.cause=1` (ebreak) | `Sdext.html#csr-dcsr` | P0 | Pass | |
| DM-002-S | Stimulate | Set `dcsr.ebreakm=0`; execute `ebreak` in M-mode | `Sdext.html#csr-dcsr` | P0 | Pass | `debug_entry_uvm` (TC-DCSR-012) |
| DM-002-C | Check | Ordinary breakpoint trap, **not** Debug Mode; `mcause=3` | `Sdext.html#csr-dcsr` | P0 | Pass | The mirror of DM-001 — catches a stuck-enabled bit |
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
| DM-011-V | Cover | Entry privilege `dcsr.prv` = {M, S, U} | `Sdext.html#csr-dcsr` | P1 | Not started | Owned by `cg_debug_entry.cp_prv` |
| DM-014-V | Cover | `dcsr.cause` × `dpc` origin | `Sdext.html#csr-dpc` | P0 | Not started | `x_cause_x_dpc` — `dpc` means something different per cause; a DM can get it right for `haltreq` and wrong for `ebreak` |
| DM-015-V | Cover | `dcsr.stopcount` × `dcsr.stoptime` | `Sdext.html#csr-dcsr` | P2 | Not started | `x_stopcount_x_stoptime` — two independent timebases; an implementation wiring them together passes both coverpoints separately while being wrong |
| DM-016-V | Cover | `dret` context × debug-CSR access context | `Sdext.html#dret` | P1 | Not started | `x_dret_x_csr_access` — confirms the check is on Debug Mode itself rather than on machine privilege |
| DM-012-S | Stimulate | Enter Debug Mode by each cause from each privilege the cause can occur in: `ebreak` from M/S/U with the matching `ebreak*` bit set, `haltreq` from M/S/U, step from M/S/U | `Sdext.html#csr-dcsr` | P1 | Not started | Coverage hole: no item drove the cause × privilege combination |
| DM-012-C | Check | `dcsr.cause` and `dcsr.prv` are both correct for every combination reached | `Sdext.html#csr-dcsr` | P1 | Not started | `ebreak` gating is per-privilege, so this cross is where a wrongly-gated `ebreak` shows up — neither coverpoint alone finds it |
| DM-013-V | Cover | `dcsr.cause` × `dcsr.prv`, excluding `resethaltreq` × {S, U} — reset-halt entry always reports the post-reset privilege, which is M by definition | `Sdext.html#csr-dcsr` | P1 | Not started | Owned by `cg_debug_entry.x_cause_x_prv` |

## 3.12 Triggers (Sdtrig)

**Intent.** Halt on a condition rather than on a debugger request. The largest
untested area in this plan.

| ID | Type | Action / Check / Cover | Reference | Pri | Status | Remarks |
|---|---|---|---|---|---|---|
| TRIG-001-S | Stimulate | Walk `tselect` from 0 upward, reading `tdata1` at each index | `Sdtrig.html#enumeration` | P0 | Pass | `trigger_uvm` (13/13) |
| TRIG-001-C | Check | Trigger count and each trigger's `type` are discoverable | `Sdtrig.html#enumeration` | P0 | Pass | |
| TRIG-002-S | Stimulate | Write `tselect` beyond the implemented count | `Sdtrig.html` | P1 | Pass | |
| TRIG-002-C | Check | `tselect` reads back a legal (implemented) index | `Sdtrig.html` | P1 | Pass | |
| TRIG-003-S | Stimulate | Configure `mcontrol6` as an execute trigger at a known instruction address; run | `Sdtrig.html#mcontrol6` | P0 | Pass | `debug_entry_uvm` TC-DCSR-011; the hart runs into the target with no halt request |
| TRIG-003-C | Check | Debug Mode entered at that address; `dcsr.cause=2` (trigger) | `Sdext.html#csr-dcsr` | P0 | Fail | RTL-012 (#161): Debug Mode is entered at the target but `dcsr.cause`=3 |
| TRIG-004-S | Stimulate | Configure `mcontrol6` as a load trigger on a known data address; run a load | `Sdtrig.html#mcontrol6` | P0 | Not started | |
| TRIG-004-C | Check | `dcsr.cause=2`; `dpc` is the load instruction | `Sdtrig.html#mcontrol6` | P0 | Not started | |
| TRIG-005-S | Stimulate | Configure a store trigger; run a store | `Sdtrig.html#mcontrol6` | P0 | Not started | |
| TRIG-005-C | Check | `dcsr.cause=2` | `Sdtrig.html#mcontrol6` | P0 | Not started | |
| TRIG-006-S | Stimulate | Write `tdata1=0` for a configured trigger; re-run the matching access | `Sdtrig.html` | P1 | Pass | `trigger_uvm` TC-TRIG-006 (DMI); riscv-arch-test `SdtrigSm_Mcontrol6-00` (native) |
| TRIG-006-C | Check | No trigger fires | `Sdtrig.html` | P1 | Fail | RTL-013 (#162): on RV64 `tdata1=0` is ignored; the trigger stays armed and fires. Previously marked Pass without being checked |
| TRIG-007-S | Stimulate | Attempt `tdata1` writes while the hart is running | `Sdtrig.html` | P1 | Not started | |
| TRIG-007-C | Check | Behaviour matches the spec's restriction on updates from a running hart | `Sdtrig.html` | P1 | Not started | |
| TRIG-008-S | Stimulate | Configure `icount` with `count=1` | `Sdtrig.html#icount` | P2 | Pass | `native_icount`; riscv-arch-test `SdtrigSm_Icount-00` (enabled by `mk/act_build.sh`) |
| TRIG-008-C | Check | Fires after exactly one instruction | `Sdtrig.html#icount` | P2 | Fail | RTL-014 (#163) |
| TRIG-009-S | Stimulate | Configure `itrigger` and `etrigger` | `Sdtrig.html#itrigger` | P2 | Pass | `native_itrigger`, `native_etrigger` |
| TRIG-009-C | Check | Fire on the configured interrupt and exception respectively | `Sdtrig.html#itrigger` | P2 | Fail | RTL-015 (#164): etrigger never matches in S; RTL-016 (#165): itrigger fires after the handler returns |
| TRIG-010-C | Check | Trigger priority against a simultaneous exception matches §5.1.3 | `Sdtrig.html#5-1-3-priority` | P2 | Not started | |
| TRIG-011-V | Cover | Trigger type = {execute, load, store, `icount`, `itrigger`, `etrigger`} | `Sdtrig.html` | P1 | Not started | |
| TRIG-012-V | Cover | Privilege enable bits = {m, s, u} × fired/not-fired | `Sdtrig.html#mcontrol6` | P1 | Not started | |
| TRIG-015-S | Stimulate | Configure `mcontrol6` with both load and store match, then run each | `Sdtrig.html#mcontrol6` | P1 | Not started | Coverage: `load_and_store` — a watchpoint on any access |
| TRIG-015-C | Check | The trigger fires on both a load and a store to the address | `Sdtrig.html#mcontrol6` | P1 | Not started |  |
| TRIG-016-S | Stimulate | Configure a trigger with m, s and u all enabled; execute the match from each privilege | `Sdtrig.html#mcontrol6` | P1 | Not started | Coverage: `all_privileges` |
| TRIG-016-C | Check | The trigger fires in every privilege mode | `Sdtrig.html#mcontrol6` | P1 | Not started |  |
| TRIG-017-V | Cover | Match event × privilege enables | `Sdtrig.html#mcontrol6` | P0 | Not started | `x_match_x_privilege` — the filter is applied per access class; a core can get it right for execute and wrong for load |
| TRIG-018-V | Cover | Trigger type × privilege enables | `Sdtrig.html#mcontrol6` | P1 | Not started | `x_type_x_privilege` — each type applies the filter through its own matching logic |
| TRIG-019-V | Cover | Trigger type × update context (hart halted vs running) | `Sdtrig.html` | P1 | Not started | `x_type_x_update_context` — each type has a different write path into `tdata1` |

## 3.13 Halt and resume groups

| ID | Type | Action / Check / Cover | Reference | Pri | Status | Remarks |
|---|---|---|---|---|---|---|
| HG-001-S | Stimulate | Write `dmcs2` with `grouptype=0`, a group number, `hgselect=0`, `hgwrite=1` | `debug_module.html#dmcs2` | P2 | Not started | |
| HG-001-C | Check | Read-back reports the hart in that halt group | `debug_module.html#dmcs2` | P2 | Not started | |
| HG-002-S | Stimulate | Halt one member of a multi-hart halt group | `debug_module.html#halt-groups` | P2 | N/A | Single-hart DUT — cannot be demonstrated |
| HG-003-S | Stimulate | Assert the external trigger configured in `dmcs2.dmexttrigger` | `debug_module.html#dmcs2` | P2 | Pass | `external_trigger_uvm` (3/3) |
| HG-003-C | Check | The group halts in response | `debug_module.html#dmcs2` | P2 | Pass | |
| HG-004-C | Check | A group halt drives the outgoing external trigger | `debug_module.html#dmcs2` | P2 | Not started | |
| HG-005-V | Cover | Group configuration × propagation path | `debug_module.html#dmcs2` | P2 | Not started | `x_config_x_propagation` — halt and resume groups propagate through separate logic, the external trigger is a third. `hart_to_hart` excluded on a single-hart DUT, retained since it is the primary purpose of halt groups |

## 3.14 Authentication

| ID | Type | Action / Check / Cover | Reference | Pri | Status | Remarks |
|---|---|---|---|---|---|---|
| AUTH-001-C | Check | `dmstatus.authenticated=1` on a DM with no authentication implemented | `debug_module.html#dmstatus` | P1 | Not started | The only row applying to this DUT |
| AUTH-002-S | Stimulate | Attempt DM register access with `authenticated=0` | `debug_module.html#authdata` | P3 | N/A | Not implemented |
| AUTH-003-S | Stimulate | Perform the `authdata` challenge/response exchange | `debug_module.html#authdata` | P3 | N/A | |
| AUTH-004-C | Check | `dmcontrol` remains accessible while `authenticated=0`, so the DM can still be activated | `debug_module.html#authdata` | P3 | N/A | Coverage: the permitted set. Retained for a DUT that implements authentication |
| AUTH-005-C | Check | `authdata` remains accessible while `authenticated=0` — it is the challenge channel | `debug_module.html#authdata` | P3 | N/A |  |
| AUTH-006-V | Cover | Authentication state × register reachable in that state | `debug_module.html#authdata` | P3 | N/A | `x_auth_x_gated_access` — a gate is a pairing; a state coverpoint alone cannot say what it gates |

## 3.15 DTM and DMI transport

| ID | Type | Action / Check / Cover | Reference | Pri | Status | Remarks |
|---|---|---|---|---|---|---|
| DTM-010-S | Stimulate | Read `dtmcs` (JTAG IR 0x10) with a zero DR; both control bits are W1 so this has no side effect | `dtm.html#dtmcs` | P0 | Pass | `dmi_error_uvm` — needed a new transport op; `dtmcs` has no DMI address |
| DTM-010-C | Check | `dtmcs.version`=1 and `abits`>=7 | `dtm.html#dtmcs` | P0 | Pass | Observed 0x00001071 |
| DTM-011-S | Stimulate | Issue back-to-back DMI accesses with no idle cycles, then write `dtmcs.dmireset` | `dtm.html#dtmcs` | P1 | Pass | |
| DTM-011-C | Check | `dtmcs.dmistat` reads 0 after `dmireset`, and the DMI still responds | `dtm.html#dtmcs` | P1 | Pass | Does NOT assert that busy was provoked: a DM that keeps up with JTAG is not wrong |
| DTM-012-S | Stimulate | Provoke a sticky busy (as DTM-015), then write only `dtmcs.dmihardreset` | `dtm.html#dtmcs` | P1 | Fail | Previously written with no error pending, which a DTM ignoring the bit also passes |
| DTM-012-C | Check | `dtmcs.dmistat`=0 afterwards, and `dmcontrol.dmactive` still 1 — the DM is not on the TAP | `dtm.html#dtmcs` | P1 | Fail | **RTL-009** — `dmistat` stays 3 |
| DTM-013-C | Check | A read of an unimplemented DMI address returns 0 and leaves the DMI usable | `dtm.html` | P2 | Pass | Reaches the DM's `default:` decode arm |
| DTM-014-S | Stimulate | Drive Test-Logic-Reset with five TMS=1 clocks, then re-read `dtmcs` and `dmcontrol` | `dtm.html` | P1 | Pass | The transport's "TAP reset" was an IR scan of BYPASS and never reached Test-Logic-Reset; fixed |
| DTM-014-C | Check | `dmactive` survives a transport reset | `dtm.html` | P1 | Pass | |
| DTM-015-S | Stimulate | Queue a DMI read, then scan DR again with no IR scan in between (three TCK edges), then once more | `dtm.html#dmi` | P0 | Pass | `dmi_error_uvm` — needed a raw DR-scan transport op; the normal path scans IR first, which always gives the DTM time |
| DTM-015-C | Check | The scans capture `dmistat` 0, 3, 3; `dtmcs.dmistat`=3; after `dmireset` it is 0 and the DMI works | `dtm.html#dtmcs` | P0 | Pass | Observed 0/3/3 |
| DTM-001-S | Stimulate | Drive TMS sequences through every JTAG TAP state | `dtm.html` | P0 | Pass | Underpins every other test |
| DTM-001-C | Check | Each state is reached and exits correctly | `dtm.html` | P0 | Pass | |
| DTM-002-C | Check | IDCODE reads the expected device value (0x00000001 on this build), bit 0 set, plain and through Pause-IR/DR | `dtm.html` | P0 | Pass | `dmi_error_uvm` TC-DTM-002. Was marked Pass against `discovery_uvm`, which never scans IDCODE |
| DTM-003-S | Stimulate | DMI read (`op=1`) and write (`op=2`) to a known DM register | `dtm.html#dmi` | P0 | Pass | |
| DTM-003-C | Check | `op` returns 0 (success); data matches | `dtm.html#dmi` | P0 | Pass | |
| DTM-004-S | Stimulate | Issue DMI accesses faster than the DM can service | `dtm.html#dmi` | P0 | Pass | By DTM-015-S |
| DTM-004-C | Check | `op=3` (busy) is returned; retrying after `dmireset` succeeds | `dtm.html#dmi` | P0 | Pass | By DTM-015-C |
| DTM-005-C | Check | A DMI error is sticky — subsequent accesses keep failing until `dmireset` | `dtm.html#dtmcs` | P0 | Pass | By DTM-015-C: the third scan still returns 3. See RST-020 |
| DTM-006-S | Stimulate | Issue a DMI access with `op=0` and with undefined `op` encodings | `dtm.html#dmi` | P2 | Not started | |
| DTM-006-C | Check | No hang; the DM remains usable | `dtm.html#dmi` | P2 | Not started | |
| DTM-007-S | Stimulate | Address a DMI location beyond `dtmcs.abits` | `dtm.html#dmi` | P2 | Not started | |
| DTM-007-C | Check | Access is ignored or flagged; no hang | `dtm.html#dmi` | P2 | Not started | |
| DTM-008-S | Stimulate | Reset the TAP mid-DMI-transaction | `dtm.html` | P2 | Not started | |
| DTM-008-C | Check | DTM returns to a known state; the next access succeeds | `dtm.html` | P2 | Not started | |
| DTM-009-V | Cover | `dmi.op` result = {0 success, 2 failed, 3 busy}; `dtmcs.dmistat` = {0, 2, 3} | `dtm.html#dmi` | P1 | Not started | |
| DTM-010-V | Cover | DMI operation × result | `dtm.html#dmi` | P1 | Not started | `x_op_x_result` — a failed read returns stale data, a failed write may partially apply |
| DTM-011-V | Cover | Idle cycles supplied × DMI result | `dtm.html#dtmcs` | P0 | Not started | `x_idle_x_result` — under-running `dtmcs.idle` is the specified way to provoke busy, the only place that causal link is measured |
| DTM-017-C | Check | BYPASS (IR 0x00 and 0x1f) is a 1-bit delay that captures 0 | `dtm.html` | P2 | Pass | Nothing had ever selected BYPASS |
| DTM-018-C | Check | Shifting all-ones into `dtmcs`'s read-only and reserved bits changes nothing | `dtm.html#dtmcs` | P2 | Pass | |
| DTM-019-S | Stimulate | One TMS walk through every TAP transition scans never take: zero-length DR/IR, Pause and Exit2 both ways, Update straight to Select-DR | `dtm.html` | P1 | Pass | Supersedes DTM-001's claim, which only ever covered the direct path |
| DTM-016-C | Check | A DMI read never returns X or Z in any bit | `dtm.html#dmi` | P0 | Pass | Every read: the bridge carries an X mask beside the value and the transport refuses it. Before this, X reached Python as 0 — see RTL-007 |

## 3.16 Debug Module paths no ordinary flow reaches

**Intent.** Close the Debug Module's code coverage with stimulus rather than
exclusions. Every row here targets code that code coverage showed was never
executed and that is reachable on this DUT. What is not reachable is excluded
by `mk/dm_cov_exclude.py`, one stated reason per rule.

**Workflow.** `dm_corners_uvm`, one session, `sw/halt_probe.elf`. The stalled
transfer (DMC-003) leaves SBA busy until power-on reset, so it runs last.

| ID | Type | Action / Check / Cover | Reference | Pri | Status | Remarks |
|---|---|---|---|---|---|---|
| DMC-001-S | Stimulate | With hart 0 halted, select `hartsel`=1 (no such hart) for several DMI round-trips, then reselect 0 | `debug_module.html#dm-dmcontrol` | P2 | Pass | The parked hart's flag poll misses — a `dm_mem` arm a single-hart flow never takes |
| DMC-001-C | Check | `dmstatus` reads cleanly with `allnonexistent`=1 while selected; hart 0 is still halted afterwards | `debug_module.html#dm-dmstatus` | P2 | Fail | **RTL-008** — bits [13:10] read X. The flag-poll arm is still covered |
| DMC-002-S | Stimulate | Over SBA: write an undecoded DM address (0x0), read hart 0's and another hart's flag word, read `whereto` idle and while `resumereq` is outstanding | `debug_module.html#system-bus-access` | P2 | Pass | The testharness maps the DM's own memory on the bus SBA uses |
| DMC-002-C | Check | Both flag words read 0 with nothing pending; `whereto` with a resume pending is `jal` to the resume entry (0x5040006f) | `debug_module.html` | P2 | Pass | An idle `whereto` returns dm_mem's previous read, which is undefined, so it is not checked |
| DMC-003-S | Stimulate | Assert `ndmreset`, start an SBA read, then write `sbcs`, read `sbdata1`, write `sbaddress1` and `sbdata1` | `debug_module.html#dm-sbcs` | P1 | Pass | `ndmreset` resets the crossbar but not the DM's bus master, so the transfer stays busy. A JTAG scan otherwise outlasts any transfer, so no access had ever met `sbbusy`=1 |
| DMC-003-C | Check | `sbbusy`=1 under reset, and `sbbusyerror`=1 after the accesses | `debug_module.html#dm-sbcs` | P1 | Pass | |
| DMC-004-C | Check | After release: a W1C of `sbbusyerror` is applied only once `sbbusy` has cleared; a `dmactive` cycle clears it; run control still works | `debug_module.html#dm-sbcs` | P1 | Pass | Whether the transfer survives the crossbar reset depends on where it was when reset hit — a testharness property, recorded under the RTL findings' observations |
| DMC-005-S | Stimulate | Write all-ones to `abstractcs`, `abstractauto` and `command` (reserved bit, `aarpostincrement`, `regno`[13]); restore each | `debug_module.html#dm-abstractauto` | P2 | Pass | Toggle coverage named whole fields no scenario ever set |
| DMC-005-C | Check | `relaxedpriv` reads 1; `abstractauto` reads 0x00ff0003 (WARL to 8 progbuf, 2 data bits); the DM stays usable | `debug_module.html#dm-abstractauto` | P2 | Pass | |
| DMC-006-S | Stimulate | 64-bit SBA write/read of all-ones and all-zeros at an address with bits [27:14] set; toggle `sbaddress1`; read every `dm_mem` region (ROM, abstract slots, Program Buffer filled both ways, data) as 64-bit words; 64-bit (`aarsize`=3) GPR round-trips | `debug_module.html#system-bus-access` | P2 | Pass | Every earlier access used 32-bit values, leaving the upper half of every bus untoggled |
| DMC-006-C | Check | Every 64-bit round-trip returns what was written; every ROM word matches `debug_rom.sv`; the Program Buffer and data words read back what was written | `debug_module.html#system-bus-access` | P2 | Pass | The abstract-command slots are read but not checked: their content is the last command's program |
| DMC-007-C | Check | After writing all-ones to `sbcs`, reserved bits [28:23] read 0 | `debug_module.html#dm-sbcs` | P2 | Fail | **RTL-006** — they read back 0x3f. The model masks `sbcs` to predicted fields, so nothing else checks them |
| DMC-008-C | Check | `haltsum1`, `haltsum2` and `haltsum3` read 0 on a single-hart DM | `debug_module.html#dm-haltsum1` | P2 | Fail | **RTL-007** — bit 0 reads X |
| DMC-009-S | Stimulate | Over SBA, write hart id 1 to `dm_mem`'s halted then resuming word; select hart 1 and raise `resumereq` | `debug_module.html` | P2 | Pass | dm_mem indexes its per-hart state by the id written, so the padded second slot is reachable |
| DMC-009-C | Check | Hart 0 is still halted | `debug_module.html` | P2 | Pass | |

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
| `sbcs.sbaccess` hardwired and reset to 3 | RST-038-C2, RAP-007-C2/C3, all of §3.8 | Spec declares it `R/W` with reset constant `2`; RTL forces `(BusWidth==64) ? 3 : 2` at `dm_csrs.sv:618`, clobbering DMI writes. **Not** a PR #4 regression — `git log -L` attributes the line to `17e912c` "Updated 1.0 debug module", which replaced the old v0.13 support-bit block. **Unfiled** |
| `allrunning=1` for a nonexistent hart | HS-002-C2 | Issue #130; reproduces on both DUTs |
| `dmstatus` mismatch on hart selection | HS-001 | `hart_selection_uvm` aborts before verdict |
| `dscratch0/1` clobbered by the DM | RAP-023 | **Testplan expectation is wrong** — `nscratch=2`. Re-specify, do not file |

### Functional coverage gap found on review

The implemented model (`src/pydebug/sv/fcov/covergroups.sv`, 14 covergroups)
samples **only DMI-visible Debug Module registers**. `dcsr` and `dpc` are hart
CSRs reached through an abstract command, and nothing samples them — so there
is no `cp_cause`, no `cp_prv`, no `stepie` coverpoint, and no stepped-
instruction class anywhere in the model.

The consequence is concrete: **the `wfi` single-step defect could not have
appeared as a coverage hole**, because no bin represents "a step over a
stalling instruction". It was found by a directed test that someone thought to
write, which is not a repeatable way to find the next one.

Two covergroups are needed, and the rows above now own their bins:

| Covergroup | Coverpoints | Owning rows |
|---|---|---|
| `cg_debug_entry` | `cp_cause`, `cp_prv`, `x_cause_x_prv` | DM-001-C, HALT-001-C2, SSTEP-001-C2, TRIG-003-C, DM-011-V, DM-013-V |
| `cg_step` | `cp_stepped_class`, `cp_stepie_x_irq`, `cp_step_transition` | SSTEP-001…015, SSTEP-014-V, SSTEP-017-V |

`cp_step_transition` should carry `DEBUG => RUNNING [* 2]` as an **illegal**
bin: two consecutive samples in RUNNING after a step means the hart never
re-entered Debug Mode, which is exactly the deadlock. That makes the defect a
coverage failure rather than a directed-test coincidence.

### Rows marked `N/A`

Features absent from this DUT: Quick Access, Access Memory, hart array, Zawrs,
authentication, multi-hart, halt-on-reset (`hasresethaltreq=0`). Retained rather
than deleted so the exclusion stays auditable, and so the plan stays valid for a
DUT that implements them.
