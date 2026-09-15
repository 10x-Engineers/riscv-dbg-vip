# RISC-V Debug Specification — Verification Test Plan — v1.0

> **Generated document — do not edit by hand.**
> Source of truth is `testplans/generated/testplan.yaml`; this file is rendered
> from it by `debug-testplan/scripts/render_markdown.py`. Edits here are lost on
> the next render.

Derived from the ratified [RISC-V Debug Specification v1.0](https://docs.riscv.org/reference/debug/v1.0/index.html). Every row carries
the verbatim normative sentence it tests and a citable spec anchor.

- **Generated:** 2026-09-13
- **DUT profile:** `cva6-10x-fork`
- **Behaviours:** 515  |  **Test items:** 1279  |  **Total weight:** 171.55

## Status of this document

**Nothing in this plan has been run.** Every item reads `Not started` and every
*Final Remarks* cell is empty. Those two columns are where the plan earns its
keep — a failure recorded against a test item, with the issue it was filed as, is
the audit trail. A row with no stimulus behind it is a *specification*, not
coverage.

Rows are generated candidates: summaries are the spec sentence verbatim rather
than written objectives, behaviours still need merging where several describe one
thing, and field-value variants still need demoting to coverage bins.

## Method

Each behaviour is one normative sentence, decomposed into the verification
activities it needs — **Stimulate** to drive it, **Check** to verify the outcome,
**Cover** to close the value space. Which apply follows from the RFC 2119 modality,
so priority and milestone are derived rather than hand-assigned:

| Modality | Activities | Priority |
|---|---|---|
| `MUST` | Stimulate, Check, Cover | P1 / P2 / P2 |
| `MUST_NOT` | Check, Cover | P1 / P2 |
| `CONDITIONAL` | Stimulate, Check, Cover | P1 / P2 / P2 |
| `SHOULD` | Stimulate, Check | P2 |
| `SHOULD_NOT` | Check | P2 |
| `MAY` | Stimulate, Cover | P2 / P3 |
| `UNSPECIFIED` | Check only — *does not hang*, no asserted value | P3 |

Weight is effort, not importance: a Cover item over a combination space costs more
to close than a single directed stimulus.

## Summary

| | Stimulate | Check | Cover | Total |
|---|---:|---:|---:|---:|
| Items | 459 | 397 | 423 | 1279 |

| Milestone | Items | | Priority | Items |
|---|---:|---|---|---:|
| Main | 295 | | P1 | 295 |
| Full | 834 | | P2 | 834 |
| Deferred | 150 | | P3 | 150 |

### Coverage by feature area

| Prefix | Area | Behaviours | Items |
|---|---|---:|---:|
| `TRIG` | Triggers (Sdtrig) | 178 | 454 |
| `AC` | Abstract commands | 53 | 135 |
| `DCSR` | Debug Mode — dcsr/dpc/dscratch | 50 | 122 |
| `SBA` | System Bus Access | 32 | 84 |
| `RC` | Run control — halt/resume | 27 | 71 |
| `GEN` | Unclassified | 29 | 69 |
| `DTM` | Debug Transport Module | 26 | 58 |
| `DIS` | Discovery & version detection | 18 | 49 |
| `SSTEP` | Single-step | 15 | 40 |
| `DMI` | DMI protocol | 17 | 40 |
| `HG` | Halt / resume groups | 13 | 39 |
| `PB` | Program Buffer | 13 | 35 |
| `RST` | Reset control | 14 | 35 |
| `HS` | Hart selection & states | 13 | 26 |
| `AUTH` | Authentication | 5 | 10 |
| `AM` | Abstract memory access | 9 | 9 |
| `QA` | Quick Access | 3 | 3 |

---

## TRIG — Triggers (Sdtrig)

### 4.1.5.2. Icount Trigger

**Debuggers that want to disable interrupts while stepping must disable them by changing mstatus, and specially handle instructions that read mstatus. wfi instructions are not treate**

`MUST` · [Sdext.html#stepicount](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#stepicount) · obligation `OB-B9A3E98D`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-001-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-001-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-001-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Systems that only support M-Mode can use icount as well, but count must be able to count several instructions (depending on the software implementation).**

`MUST` · [Sdext.html#stepicount](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#stepicount) · obligation `OB-D006BECC`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-002-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-002-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-002-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### 5.1.1. Enumeration

**If this results in an illegal instruction exception, then there are no triggers implemented.**

`CONDITIONAL` · [Sdtrig.html#5-1-1-enumeration](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-1-enumeration) · obligation `OB-811A6EBE`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-003-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-003-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-003-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If that caused an exception, the debugger must read tdata1 to discover the type. (If type is 0, this trigger doesn’t exist.**

`MUST` · [Sdtrig.html#5-1-1-enumeration](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-1-enumeration) · obligation `OB-90A1E417`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-004-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-004-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-004-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Each trigger may support a variety of features.**

`MAY` · [Sdtrig.html#5-1-1-enumeration](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-1-enumeration) · obligation `OB-B932B7D6`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-005-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-005-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

### 5.1.2. Actions

**Table 1. action encoding Value Description 0 Raise a breakpoint exception. (Used when software wants to use the trigger module without an external debugger attached.) xepc must con**

`MUST` · [Sdtrig.html#5-1-2-actions](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-2-actions) · obligation `OB-B9D6932F`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-006-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-006-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-006-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Since tdata1 is WARL, hardware must prevent it from containing dmode=0 and action=1.**

`MUST` · [Sdtrig.html#5-1-2-actions](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-2-actions) · obligation `OB-F287152E`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-007-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-007-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-007-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### 5.1.3. Priority

**If this is not implemented, then the hart must enter Debug Mode and ignore the breakpoint exception.**

`MUST` · [Sdtrig.html#5-1-3-priority](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-3-priority) · obligation `OB-1FD807EA`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-008-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-008-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-008-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**In the latter case, hit of the trigger whose action is 0 must still be set, giving a debugger an opportunity to handle this case.**

`MUST` · [Sdtrig.html#5-1-3-priority](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-3-priority) · obligation `OB-442235EA`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-009-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-009-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-009-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If more than one of these triggers has action=0 then tval is updated in accordance with one of them, but which one is UNSPECIFIED .**

`UNSPECIFIED` · [Sdtrig.html#5-1-3-priority](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-3-priority) · obligation `OB-5D9818BC`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-010-C` | Check | P3 | 0.10 | Deferred | Not started | 0 | — | 1 | — |

> Spec says UNSPECIFIED -- check the DM does not hang; do not assert a value.

**When triggers are chained, the priority is the lowest priority of the triggers in the chain.**

`CONDITIONAL` · [Sdtrig.html#5-1-3-priority](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-3-priority) · obligation `OB-8A4EBAA6`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-011-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-011-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-011-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If this table contradicts the table in the Privileged Spec, then the latter takes precedence.**

`CONDITIONAL` · [Sdtrig.html#5-1-3-priority](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-3-priority) · obligation `OB-F7FAC044`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-012-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-012-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-012-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If one of these triggers has the "enter Debug Mode" action (1) and another trigger has the "raise a breakpoint exception" action (0), the preferred behavior is to have both actions**

`CONDITIONAL` · [Sdtrig.html#5-1-3-priority](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-3-priority) · obligation `OB-FA5F4F78`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-013-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-013-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-013-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### 5.1.5.1. A Extension

**If the A extension is supported, then triggers on loads/stores treat them as follows: lr instructions are loads.**

`CONDITIONAL` · [Sdtrig.html#5-1-5-1-a-extension](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-5-1-a-extension) · obligation `OB-09F6CC19`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-014-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-014-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-014-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If the destination register of any load or AMO is zero then it is UNSPECIFIED whether a data load trigger will match.**

`UNSPECIFIED` · [Sdtrig.html#5-1-5-1-a-extension](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-5-1-a-extension) · obligation `OB-97334823`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-015-C` | Check | P3 | 0.10 | Deferred | Not started | 0 | — | 1 | — |

> Spec says UNSPECIFIED -- check the DM does not hang; do not assert a value.

**Whether data store triggers match on AMOs is UNSPECIFIED.**

`UNSPECIFIED` · [Sdtrig.html#5-1-5-1-a-extension](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-5-1-a-extension) · obligation `OB-A989500A`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-016-C` | Check | P3 | 0.10 | Deferred | Not started | 0 | — | 1 | — |

> Spec says UNSPECIFIED -- check the DM does not hang; do not assert a value.

**It is UNSPECIFIED whether failing sc instructions are stores or not.**

`UNSPECIFIED` · [Sdtrig.html#5-1-5-1-a-extension](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-5-1-a-extension) · obligation `OB-DF94CEB9`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-017-C` | Check | P3 | 0.10 | Deferred | Not started | 0 | — | 1 | — |

> Spec says UNSPECIFIED -- check the DM does not hang; do not assert a value.

### 5.1.5.2. Combined Accesses

**E.g. a vector load should be treated as if it performed multiple loads of size SEW (selected element width), and cm.push should be treated as if it performed multiple stores of siz**

`SHOULD` · [Sdtrig.html#5-1-5-2-combined-accesses](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-5-2-combined-accesses) · obligation `OB-33C53BBA`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-018-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-018-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**The Trigger Module should match such accesses as if they all happened individually.**

`SHOULD` · [Sdtrig.html#5-1-5-2-combined-accesses](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-5-2-combined-accesses) · obligation `OB-CCDDA3DE`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-019-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-019-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

### 5.1.5.3. Cache Operations

**For the purposes of debug triggers, two classes of cache operations must match as stores: Cache operations that enable software to maintain coherence between otherwise non-coherent**

`MUST` · [Sdtrig.html#5-1-5-3-cache-operations](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-5-3-cache-operations) · obligation `OB-03F99DF4`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-020-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-020-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-020-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Implementations must implement one of the following options.**

`MUST` · [Sdtrig.html#5-1-5-3-cache-operations](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-5-3-cache-operations) · obligation `OB-EB4F728A`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-021-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-021-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-021-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### 5.1.5.4.1. Invalid Addresses

**For invalid instruction fetch addresses and load and store effective addresses, the compare value may be changed to a different invalid address.**

`MAY` · [Sdtrig.html#5-1-5-4-1-invalid-addresses](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-5-4-1-invalid-addresses) · obligation `OB-23BDABB0`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-022-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-022-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**If tdata2 can hold any invalid addresses, then writes of an invalid address that can not be represented as-is should be converted to a different invalid address that can be represe**

`SHOULD` · [Sdtrig.html#5-1-5-4-1-invalid-addresses](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-5-4-1-invalid-addresses) · obligation `OB-934DD1FC`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-023-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-023-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**In addition, an implementation may choose to inhibit all trigger matching against invalid addresses, especially if there is no support for storage of any invalid address values in**

`MAY` · [Sdtrig.html#5-1-5-4-1-invalid-addresses](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-5-4-1-invalid-addresses) · obligation `OB-FE32BA11`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-024-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-024-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

### 5.1.5.4. Address Matches

**An implementation may be able to optimize the storage required, depending on the widest addresses it supports.**

`MAY` · [Sdtrig.html#5-1-5-4-address-matches](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-5-4-address-matches) · obligation `OB-1BEE603C`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-025-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-025-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**If virtual addresses are less than XLEN bits wide, they are sign-extended. tdata2 must be implemented with enough bits of storage to represent the full range of supported physical**

`MUST` · [Sdtrig.html#5-1-5-4-address-matches](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-5-4-address-matches) · obligation `OB-2B14D073`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-026-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-026-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-026-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**For address matches without a mask, tdata2 must be able to hold all valid addresses in all supported translation modes.**

`MUST` · [Sdtrig.html#5-1-5-4-address-matches](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-5-4-address-matches) · obligation `OB-52E51B4F`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-027-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-027-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-027-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If physical addresses are less than XLEN bits wide, they are zero-extended.**

`CONDITIONAL` · [Sdtrig.html#5-1-5-4-address-matches](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-5-4-address-matches) · obligation `OB-5581CFB4`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-028-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-028-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-028-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### 5.1.7. Trigger Module Registers

**Writes to one tdata register must not modify the contents of other tdata registers, nor the configuration of any trigger besides the one that is currently selected.**

`MUST_NOT` · [Sdtrig.html#5-1-7-trigger-module-registers](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-7-trigger-module-registers) · obligation `OB-8BDD4DD9`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-029-C` | Check | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-029-C` | Cover | P2 | 0.10 | Full | Not started | 0 | — | 2 | — |

**This means that a debugger must always read back values it writes to tdata registers, unless it already knows what is supported.**

`MUST` · [Sdtrig.html#5-1-7-trigger-module-registers](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-7-trigger-module-registers) · obligation `OB-9B1EC118`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-030-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-030-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-030-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

> ⚠ Requirement text may be truncated by an empty cross-reference in the published HTML -- verify against the AsciiDoc source.

**Code that restores CSR context of triggers that might be configured to fire in the current privilege mode must use this same sequence to restore the triggers.**

`MUST` · [Sdtrig.html#5-1-7-trigger-module-registers](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-7-trigger-module-registers) · obligation `OB-A7C3DDB5`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-031-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-031-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-031-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If a debugger writes an unsupported configuration, the register will read back a value that is supported (which may simply be a disabled trigger).**

`MAY` · [Sdtrig.html#5-1-7-trigger-module-registers](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#5-1-7-trigger-module-registers) · obligation `OB-E13BBA70`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-032-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-032-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

### Exception Trigger (etrigger, at 0x7a1)

**If the breakpoint trap does not go to a higher privilege mode, this will lose CSR information for the original trap.**

`CONDITIONAL` · [Sdtrig.html#csr-etrigger](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-etrigger) · obligation `OB-0499428E`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-033-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-033-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-033-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If the bit is not implemented, it is always 0 and writing it has no effect.**

`CONDITIONAL` · [Sdtrig.html#csr-etrigger](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-etrigger) · obligation `OB-19247AC3`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-034-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-034-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-034-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If textra32 or textra64 are implemented for this trigger, it only matches when the conditions set there are satisfied.**

`CONDITIONAL` · [Sdtrig.html#csr-etrigger](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-etrigger) · obligation `OB-57452DA5`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-035-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-035-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-035-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**This trigger may fire on up to XLEN of the Exception Codes defined in mcause (described in the Privileged Spec, with Interrupt=0).**

`MAY` · [Sdtrig.html#csr-etrigger](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-etrigger) · obligation `OB-6BF0589C`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-036-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-036-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**Hardware may support only a subset of exceptions.**

`MAY` · [Sdtrig.html#csr-etrigger](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-etrigger) · obligation `OB-A431FA7B`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-037-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-037-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**When the trigger matches, it fires after the trap occurs, just before the first instruction of the trap handler is executed.**

`CONDITIONAL` · [Sdtrig.html#csr-etrigger](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-etrigger) · obligation `OB-C9AD34AA`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-038-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-038-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-038-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If action=0, the standard CSRs are updated for taking the breakpoint trap, and zero is written to the relevant tval CSR.**

`CONDITIONAL` · [Sdtrig.html#csr-etrigger](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-etrigger) · obligation `OB-DB29A6E2`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-039-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-039-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-039-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**A debugger must read back tdata2 after writing it to confirm the requested functionality is actually supported.**

`MUST` · [Sdtrig.html#csr-etrigger](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-etrigger) · obligation `OB-EE104FDE`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-040-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-040-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-040-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### Hypervisor Context (hcontext, at 0x6a8)

**If it is implemented, mcontext must also be implemented.**

`MUST` · [Sdtrig.html#csr-hcontext](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-hcontext) · obligation `OB-730B372D`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-041-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-041-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-041-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**This optional register may be implemented only if the H extension is implemented.**

`MAY` · [Sdtrig.html#csr-hcontext](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-hcontext) · obligation `OB-8B59ED72`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-042-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-042-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**If Smstateen is implemented, then accessibility of in HS-Mode is controlled by mstateenzero[57].**

`CONDITIONAL` · [Sdtrig.html#csr-hcontext](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-hcontext) · obligation `OB-C35B2B26`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-043-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-043-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-043-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### Instruction Count (icount, at 0x7a1)

**If more than one of the above events occur during a single instruction execution, the trigger still only matches once for that instruction.**

`CONDITIONAL` · [Sdtrig.html#csr-icount](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-icount) · obligation `OB-08418D43`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-044-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-044-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-044-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If the bit is not implemented, it is always 0 and writing it has no effect.**

`CONDITIONAL` · [Sdtrig.html#csr-icount](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-icount) · obligation `OB-08BE3BCD`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-045-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-045-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-045-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When count is greater than 1 and the trigger matches, then count is decremented by 1.**

`CONDITIONAL` · [Sdtrig.html#csr-icount](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-icount) · obligation `OB-44126EA0`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-046-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-046-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-046-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If the trigger fires with action=0 then zero is written to the tval CSR on the breakpoint trap.**

`CONDITIONAL` · [Sdtrig.html#csr-icount](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-icount) · obligation `OB-5806ECD8`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-047-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-047-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-047-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**For use in single step, icount must match for traps where the instruction will not be reexecuted after the handler, such as illegal instructions that are emulated by privileged sof**

`MUST` · [Sdtrig.html#csr-icount](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-icount) · obligation `OB-5F2CFA19`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-048-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-048-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-048-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If textra32 or textra64 are implemented for this trigger, it only matches when the conditions set there are satisfied.**

`CONDITIONAL` · [Sdtrig.html#csr-icount](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-icount) · obligation `OB-6E4A7155`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-049-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-049-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-049-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When count is 0 it stays at 0 until explicitly written.**

`CONDITIONAL` · [Sdtrig.html#csr-icount](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-icount) · obligation `OB-8DEE01F2`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-050-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-050-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-050-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When pending is set, the trigger fires just before any further instructions are executed in a mode where the trigger is enabled.**

`CONDITIONAL` · [Sdtrig.html#csr-icount](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-icount) · obligation `OB-AFA85424`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-051-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-051-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-051-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When count is 1 and the trigger matches, then pending becomes set.**

`CONDITIONAL` · [Sdtrig.html#csr-icount](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-icount) · obligation `OB-FD888007`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-052-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-052-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-052-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### Interrupt Trigger (itrigger, at 0x7a1)

**Hardware may only support a subset of interrupts for this trigger.**

`MAY` · [Sdtrig.html#csr-itrigger](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-itrigger) · obligation `OB-1C8CD92F`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-053-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-053-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**If the bit is not implemented, it is always 0 and writing it has no effect.**

`CONDITIONAL` · [Sdtrig.html#csr-itrigger](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-itrigger) · obligation `OB-5E1F7B80`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-054-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-054-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-054-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If textra32 or textra64 are implemented for this trigger, it only matches when the conditions set there are satisfied.**

`CONDITIONAL` · [Sdtrig.html#csr-itrigger](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-itrigger) · obligation `OB-5FFE2228`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-055-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-055-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-055-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When the trigger matches, it fires after the trap occurs, just before the first instruction of the trap handler is executed.**

`CONDITIONAL` · [Sdtrig.html#csr-itrigger](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-itrigger) · obligation `OB-77CBC2C2`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-056-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-056-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-056-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If XLEN is 32, then it is not possible to set a trigger for interrupts with Exception Code larger than 31.**

`CONDITIONAL` · [Sdtrig.html#csr-itrigger](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-itrigger) · obligation `OB-9A3DE48A`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-057-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-057-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-057-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If action=0, the standard CSRs are updated for taking the breakpoint trap, and zero is written to the relevant tval CSR.**

`CONDITIONAL` · [Sdtrig.html#csr-itrigger](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-itrigger) · obligation `OB-AFE39A9C`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-058-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-058-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-058-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**A debugger must read back tdata2 after writing it to confirm the requested functionality is actually supported.**

`MUST` · [Sdtrig.html#csr-itrigger](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-itrigger) · obligation `OB-BD3D2338`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-059-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-059-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-059-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If the breakpoint trap does not go to a higher privilege mode, this will lose CSR information for the original trap.**

`CONDITIONAL` · [Sdtrig.html#csr-itrigger](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-itrigger) · obligation `OB-C501790D`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-060-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-060-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-060-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### Machine Context (mcontext, at 0x7a8)

**This register must be implemented if hcontext is implemented, and is optional otherwise.**

`MUST` · [Sdtrig.html#csr-mcontext](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontext) · obligation `OB-128AD42B`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-061-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-061-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-061-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**An implementation may tie any number of upper bits in this field to 0.**

`MAY` · [Sdtrig.html#csr-mcontext](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontext) · obligation `OB-900643C1`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-062-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-062-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**If the H extension is implemented, it’s recommended to implement 7 bits on RV32 and 14 bits on RV64.**

`CONDITIONAL` · [Sdtrig.html#csr-mcontext](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontext) · obligation `OB-AA5FF870`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-063-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-063-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-063-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If the H extension is not implemented, it’s recommended to implement 6 bits on RV32 and 13 bits on RV64 (as visible through the mcontext register).**

`CONDITIONAL` · [Sdtrig.html#csr-mcontext](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontext) · obligation `OB-CE90F8DD`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-064-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-064-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-064-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### Match Control (mcontrol, at 0x7a1)

**When an implementation supports data value triggers (select=1), it is recommended that those triggers support every access size up to XLEN that the hart supports, as well as for ev**

`SHOULD` · [Sdtrig.html#csr-mcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol) · obligation `OB-017981C2`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-065-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-065-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**It is undefined when exactly such a chain fires.**

`UNSPECIFIED` · [Sdtrig.html#csr-mcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol) · obligation `OB-10D251F5`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-066-C` | Check | P3 | 0.10 | Deferred | Not started | 0 | — | 1 | — |

> Spec says UNSPECIFIED -- check the DM does not hang; do not assert a value.

**Debuggers must avoid the latter case by checking chain on the previous trigger if they’re writing mcontrol.**

`MUST` · [Sdtrig.html#csr-mcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol) · obligation `OB-1F89A3BD`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-067-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-067-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-067-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**In addition hardware should ignore writes to mcontrol that set dmode to 1 if the previous trigger has both dmode of 0 and chain of 1.**

`SHOULD` · [Sdtrig.html#csr-mcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol) · obligation `OB-32D66181`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-068-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-068-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

> ⚠ Requirement text may be truncated by an empty cross-reference in the published HTML -- verify against the AsciiDoc source.

**Debuggers should consider this when setting such breakpoints on, for example, memory-mapped I/O addresses.**

`SHOULD` · [Sdtrig.html#csr-mcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol) · obligation `OB-3598F677`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-069-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-069-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**An implementation must support the value of 0, but all other values are optional.**

`MUST` · [Sdtrig.html#csr-mcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol) · obligation `OB-3CE2B935`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-070-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-070-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-070-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When select=1 and access size is N, this is further reduced, and comparisons only look at the lower N bits of the compare values and of tdata2.**

`CONDITIONAL` · [Sdtrig.html#csr-mcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol) · obligation `OB-40C96667`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-071-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-071-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-071-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Debuggers should not terminate a chain with a trigger with a different type.**

`SHOULD_NOT` · [Sdtrig.html#csr-mcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol) · obligation `OB-4DEC4559`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-072-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**Debuggers should only write values to tdata2 such that M + maskmax ≥ XLEN and M > 0, otherwise it’s undefined on what conditions the trigger will match. 2 (ge): Matches when any co**

`SHOULD` · [Sdtrig.html#csr-mcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol) · obligation `OB-54FE9A68`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-073-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-073-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**Custom extensions may also support instructions that are wider than XLEN.**

`MAY` · [Sdtrig.html#csr-mcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol) · obligation `OB-62CDF75E`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-074-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-074-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**If multiple mcontrol triggers are chained then the faulting virtual address is the address which caused any of the chained triggers to fire.**

`CONDITIONAL` · [Sdtrig.html#csr-mcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol) · obligation `OB-63A2C8AF`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-075-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-075-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-075-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Hardware may implement the bit fully writable, in which case the debugger has a little more control.**

`MAY` · [Sdtrig.html#csr-mcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol) · obligation `OB-6F7EAA7A`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-076-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-076-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**If an instruction matches this trigger and the instruction performs multiple memory accesses, it is UNSPECIFIED which memory accesses have completed before the trigger fires. 1 (af**

`UNSPECIFIED` · [Sdtrig.html#csr-mcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol) · obligation `OB-7FACBC59`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-077-C` | Check | P3 | 0.10 | Deferred | Not started | 0 | — | 1 | — |

> Spec says UNSPECIFIED -- check the DM does not hang; do not assert a value.

**If this is combined with load and select=1 then a memory access will be performed (including any side effects of performing such an access) even though the load will not update its**

`CONDITIONAL` · [Sdtrig.html#csr-mcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol) · obligation `OB-86F2FD32`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-078-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-078-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-078-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**It is recommended that there are additional compare values for the other accessed virtual addresses. (E.g. on a 32-bit read from 0x4000, the lowest address is 0x4000 and the other**

`SHOULD` · [Sdtrig.html#csr-mcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol) · obligation `OB-89717419`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-079-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-079-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**Because chain affects the next trigger, hardware must zero it in writes to mcontrol that set dmode to 0 if the next trigger has dmode of 1.**

`MUST` · [Sdtrig.html#csr-mcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol) · obligation `OB-99DCB478`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-080-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-080-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-080-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

> ⚠ Requirement text may be truncated by an empty cross-reference in the published HTML -- verify against the AsciiDoc source.

**To accommodate various implementations, execute, load, and store address/data triggers may fire at whatever point in time is most convenient for the implementation.**

`MAY` · [Sdtrig.html#csr-mcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol) · obligation `OB-9EBF2B70`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-081-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-081-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**For data load triggers, debuggers must first attempt to set the breakpoint with timing of 1.**

`MUST` · [Sdtrig.html#csr-mcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol) · obligation `OB-A3468DC8`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-082-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-082-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-082-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If the bit is not implemented, it is always 0 and writing it has no effect.**

`CONDITIONAL` · [Sdtrig.html#csr-mcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol) · obligation `OB-A8D1452C`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-083-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-083-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-083-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Implementations that wish to limit the maximum length of a trigger chain (eg. to meet timing requirements) may do so by zeroing chain in writes to mcontrol that would make the chai**

`MAY` · [Sdtrig.html#csr-mcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol) · obligation `OB-B82496D0`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-084-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-084-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

> ⚠ Requirement text may be truncated by an empty cross-reference in the published HTML -- verify against the AsciiDoc source.

**WARL 0 timing 0 (before): The action for this trigger will be taken just before the instruction that triggered it is retired, but after all preceding instructions are retired. xepc**

`MUST` · [Sdtrig.html#csr-mcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol) · obligation `OB-B8A95BEA`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-085-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-085-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-085-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If textra32 or textra64 are implemented for this trigger, it only matches when the conditions set there are satisfied.**

`CONDITIONAL` · [Sdtrig.html#csr-mcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol) · obligation `OB-BE5AAD05`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-086-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-086-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-086-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When an implementation supports address triggers (select=0), it is recommended that those triggers support every access size that the hart supports, as well as for every instructio**

`SHOULD` · [Sdtrig.html#csr-mcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol) · obligation `OB-C0E3DB5B`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-087-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-087-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**It should be taken before the next instruction is retired, but it is better to implement triggers imprecisely than to not implement them at all. xepc or dpc (depending on action) m**

`MUST` · [Sdtrig.html#csr-mcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol) · obligation `OB-CA052A69`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-088-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-088-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-088-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**The debugger may request specific timings as described in timing.**

`MAY` · [Sdtrig.html#csr-mcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol) · obligation `OB-DC9F205D`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-089-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-089-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**WARL 0 hit If this bit is implemented then it must become set when this trigger fires and may become set when this trigger matches.**

`MUST` · [Sdtrig.html#csr-mcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol) · obligation `OB-DF177553`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-090-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-090-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-090-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**That means to implement the suggestions in Table 4, both timings should be supported on load address triggers that can be chained with a load data trigger.**

`SHOULD` · [Sdtrig.html#csr-mcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol) · obligation `OB-E6A338DF`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-091-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-091-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**If a trigger with timing of 0 matches, it is implementation-dependent whether that prevents a trigger with timing of 1 matching as well.**

`CONDITIONAL` · [Sdtrig.html#csr-mcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol) · obligation `OB-F2150C32`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-092-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-092-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-092-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### Match Control Type 6 (mcontrol6, at 0x7a1)

**In addition hardware should ignore writes to mcontrol6 that set dmode to 1 if the previous trigger has both dmode of 0 and chain of 1.**

`SHOULD` · [Sdtrig.html#csr-mcontrol6](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol6) · obligation `OB-01DC3821`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-093-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-093-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

> ⚠ Requirement text may be truncated by an empty cross-reference in the published HTML -- verify against the AsciiDoc source.

**An implementation must support the value of 0, but all other values are optional.**

`MUST` · [Sdtrig.html#csr-mcontrol6](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol6) · obligation `OB-02698A9C`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-094-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-094-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-094-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If either of the bits is not implemented, the unimplemented bits will be read-only 0. 0 (false): The trigger did not fire. 1 (before): The trigger fired before the instruction that**

`CONDITIONAL` · [Sdtrig.html#csr-mcontrol6](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol6) · obligation `OB-06C64E07`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-095-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-095-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-095-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**In implementations that support match mode 1 (NAPOT), not all NAPOT ranges may be supported.**

`MAY` · [Sdtrig.html#csr-mcontrol6](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol6) · obligation `OB-0DC5D424`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-096-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-096-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**When an implementation supports address triggers (select=0), it is recommended that those triggers support every access size that the hart supports, as well as for every instructio**

`SHOULD` · [Sdtrig.html#csr-mcontrol6](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol6) · obligation `OB-1132158B`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-097-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-097-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**If the instruction performed multiple memory accesses, all of them have been completed.**

`CONDITIONAL` · [Sdtrig.html#csr-mcontrol6](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol6) · obligation `OB-1698F3A3`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-098-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-098-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-098-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Implementations that wish to limit the maximum length of a trigger chain (eg. to meet timing requirements) may do so by zeroing chain in writes to mcontrol6 that would make the cha**

`MAY` · [Sdtrig.html#csr-mcontrol6](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol6) · obligation `OB-1ED3D947`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-099-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-099-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

> ⚠ Requirement text may be truncated by an empty cross-reference in the published HTML -- verify against the AsciiDoc source.

**Custom extensions may also support instructions that are wider than XLEN.**

`MAY` · [Sdtrig.html#csr-mcontrol6](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol6) · obligation `OB-4D3A997B`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-100-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-100-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**If textra32 or textra64 are implemented for this trigger, it only matches when the conditions set there are satisfied. uncertain and uncertainen exist to accommodate systems where**

`CONDITIONAL` · [Sdtrig.html#csr-mcontrol6](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol6) · obligation `OB-51D2FA20`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-101-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-101-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-101-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Debuggers should not terminate a chain with a trigger with a different type.**

`SHOULD_NOT` · [Sdtrig.html#csr-mcontrol6](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol6) · obligation `OB-637C9969`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-102-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**While the uncertain mechanism exists to deal with these situations, it can lead to an unusable number of false positives.**

`CONDITIONAL` · [Sdtrig.html#csr-mcontrol6](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol6) · obligation `OB-641C3117`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-103-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-103-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-103-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Debuggers must avoid the latter case by checking chain on the previous trigger if they’re writing mcontrol6.**

`MUST` · [Sdtrig.html#csr-mcontrol6](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol6) · obligation `OB-6888F4EE`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-104-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-104-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-104-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**In addition, it is recommended that there are additional compare values for the other accessed virtual addresses match. (E.g. on a 32-bit read from 0x4000, the lowest address is 0x**

`SHOULD` · [Sdtrig.html#csr-mcontrol6](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol6) · obligation `OB-8DD1659F`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-105-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-105-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**Multiple State Change Instructions. xepc or dpc (depending on action) must be set to the virtual address of the instruction that matched. 2 (after): The trigger fired after the ins**

`MUST` · [Sdtrig.html#csr-mcontrol6](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol6) · obligation `OB-92A6C8BF`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-106-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-106-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-106-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Because chain affects the next trigger, hardware must zero it in writes to mcontrol6 that set dmode to 0 if the next trigger has dmode of 1.**

`MUST` · [Sdtrig.html#csr-mcontrol6](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol6) · obligation `OB-9AA78A6E`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-107-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-107-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-107-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

> ⚠ Requirement text may be truncated by an empty cross-reference in the published HTML -- verify against the AsciiDoc source.

**To accommodate various implementations, execute, load, and store address/data triggers may fire at whatever point in time is most convenient for the implementation.**

`MAY` · [Sdtrig.html#csr-mcontrol6](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol6) · obligation `OB-A49F0FED`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-108-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-108-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**When an implementation supports data value triggers (select=1), it is recommended that those triggers support every access size up to XLEN that the hart supports, as well as for ev**

`SHOULD` · [Sdtrig.html#csr-mcontrol6](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol6) · obligation `OB-B8651EBD`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-109-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-109-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**If it is not 1 then NAPOT matching is not supported.**

`CONDITIONAL` · [Sdtrig.html#csr-mcontrol6](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol6) · obligation `OB-BA42D32B`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-110-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-110-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-110-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When select=1 and access size is N, this is further reduced, and comparisons only look at the lower N bits of the compare values and of tdata2.**

`CONDITIONAL` · [Sdtrig.html#csr-mcontrol6](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol6) · obligation `OB-BC0EA380`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-111-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-111-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-111-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Implementing this trigger as described here requires that version is 1 or higher, which in turn means tinfo must be implemented.**

`MUST` · [Sdtrig.html#csr-mcontrol6](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol6) · obligation `OB-D898401F`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-112-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-112-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-112-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**It is undefined when exactly such a chain fires.**

`UNSPECIFIED` · [Sdtrig.html#csr-mcontrol6](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol6) · obligation `OB-E61FF669`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-113-C` | Check | P3 | 0.10 | Deferred | Not started | 0 | — | 1 | — |

> Spec says UNSPECIFIED -- check the DM does not hang; do not assert a value.

**Suggested Trigger Timings Match Type Suggested Trigger Timing Execute Address Before Execute Instruction Before Execute Address+Instruction Before Load Address Before Load Data Aft**

`MUST` · [Sdtrig.html#csr-mcontrol6](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol6) · obligation `OB-E843D8C4`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-114-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-114-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-114-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If multiple mcontrol6 triggers are chained then the faulting virtual address is the address which caused any of the chained triggers to fire.**

`CONDITIONAL` · [Sdtrig.html#csr-mcontrol6](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol6) · obligation `OB-F416713B`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-115-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-115-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-115-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**M is XLEN-1 minus the index of the least-significant bit containing 0 in tdata2. tdata2 is WARL and if bits maskmax6-1:0 are written with all ones then bit maskmax6-1 will be set t**

`UNSPECIFIED` · [Sdtrig.html#csr-mcontrol6](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-mcontrol6) · obligation `OB-FE9F0537`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-116-C` | Check | P3 | 0.10 | Deferred | Not started | 0 | — | 1 | — |

> Spec says UNSPECIFIED -- check the DM does not hang; do not assert a value.

### Supervisor Context (scontext, at 0x5a8)

**An implementation may tie any number of high bits in this field to 0.**

`MAY` · [Sdtrig.html#csr-scontext](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-scontext) · obligation `OB-D6E5BD74`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-117-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-117-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

### Trigger Control (tcontrol, at 0x7a5)

**When mret is executed, mte is set to the value of mpte.**

`CONDITIONAL` · [Sdtrig.html#csr-tcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-tcontrol) · obligation `OB-02213F12`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-118-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-118-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-118-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When any trap into M-mode is taken, mte is set to 0.**

`CONDITIONAL` · [Sdtrig.html#csr-tcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-tcontrol) · obligation `OB-76B6FD7E`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-119-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-119-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-119-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When any trap into M-mode is taken, mpte is set to the value of mte.**

`CONDITIONAL` · [Sdtrig.html#csr-tcontrol](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-tcontrol) · obligation `OB-80D43B2B`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-120-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-120-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-120-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### Trigger Data 1 (tdata1, at 0x7a1)

**Writing 0 to this register must result in a trigger that is disabled.**

`MUST` · [Sdtrig.html#csr-tdata1](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-tdata1) · obligation `OB-3482D902`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-121-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-121-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-121-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**This is similar to a type 2 trigger, but provides additional functionality and should be used instead of type 2 in newer implementations. 7 (tmexttrigger): The trigger is a trigger**

`SHOULD` · [Sdtrig.html#csr-tdata1](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-tdata1) · obligation `OB-57F58162`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-122-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-122-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**These should not be implemented and aren’t further documented here. 2 (mcontrol): The trigger is an address/data match trigger.**

`SHOULD_NOT` · [Sdtrig.html#csr-tdata1](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-tdata1) · obligation `OB-7268188E`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-123-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**If this trigger supports multiple types, then the hardware should disable it by changing type to 15.**

`SHOULD` · [Sdtrig.html#csr-tdata1](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-tdata1) · obligation `OB-A01C0FEE`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-124-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-124-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**When clearing this bit, debuggers should also set the action field (whose location depends on type) to something other than 1.**

`SHOULD` · [Sdtrig.html#csr-tdata1](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-tdata1) · obligation `OB-BC7D4ECD`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-125-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-125-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

### Trigger Data 2 (tdata2, at 0x7a2)

**If the trigger is disabled, then this register can be written with any value supported by any of the trigger types supported by this trigger.**

`CONDITIONAL` · [Sdtrig.html#csr-tdata2](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-tdata2) · obligation `OB-06A5C122`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-126-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-126-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-126-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If XLEN is less than DXLEN, writes to this register are sign-extended.**

`CONDITIONAL` · [Sdtrig.html#csr-tdata2](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-tdata2) · obligation `OB-894F5BEF`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-127-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-127-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-127-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

> ⚠ Requirement text may be truncated by an empty cross-reference in the published HTML -- verify against the AsciiDoc source.

### Trigger Data 3 (tdata3, at 0x7a3)

**If the trigger is disabled, then this register can be written with any value supported by any of the trigger types supported by this trigger.**

`CONDITIONAL` · [Sdtrig.html#csr-tdata3](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-tdata3) · obligation `OB-27CAFF80`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-128-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-128-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-128-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If XLEN is less than DXLEN, writes to this register are sign-extended.**

`CONDITIONAL` · [Sdtrig.html#csr-tdata3](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-tdata3) · obligation `OB-C32A3527`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-129-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-129-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-129-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

> ⚠ Requirement text may be truncated by an empty cross-reference in the published HTML -- verify against the AsciiDoc source.

### Trigger Extra (RV32) (textra32, at 0x7a3)

**If DXLEN >= 64, then this register provides access to the low bits of each field defined in textra64.**

`CONDITIONAL` · [Sdtrig.html#csr-textra32](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-textra32) · obligation `OB-0B121B4E`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-130-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-130-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-130-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If the H extension is not supported, the only legal values are 0 and 4.**

`CONDITIONAL` · [Sdtrig.html#csr-textra32](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-textra32) · obligation `OB-0C6D659A`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-131-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-131-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-131-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If desired, debuggers can use a trigger’s mode filtering bits to restrict the matching to modes where it considers ASID/VMID/scontext/hcontext to be active.**

`CONDITIONAL` · [Sdtrig.html#csr-textra32](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-textra32) · obligation `OB-3C49DBE0`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-132-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-132-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-132-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When the next most significant bit of this field is 1, it causes bits 15:8 to be ignored in the comparison, when sselect=1.**

`CONDITIONAL` · [Sdtrig.html#csr-textra32](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-textra32) · obligation `OB-40D7929B`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-133-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-133-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-133-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**This field should be tied to 0 when S-mode is not supported.**

`SHOULD` · [Sdtrig.html#csr-textra32](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-textra32) · obligation `OB-6FCBFC58`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-134-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-134-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-135-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-135-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**Any number of upper bits of mhvalue and svalue may be tied to 0. mhselect and sselect may only support 0 (ignore).**

`MAY` · [Sdtrig.html#csr-textra32](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-textra32) · obligation `OB-AC832F1C`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-136-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-136-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

### Trigger Extra (RV64) (textra64, at 0x7a3)

**When XLEN=32 some of the bits can be accessed through textra32.**

`CONDITIONAL` · [Sdtrig.html#csr-textra64](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-textra64) · obligation `OB-E70E4574`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-137-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-137-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-137-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### Trigger Info (tinfo, at 0x7a4)

**If the currently selected trigger doesn’t exist, this field contains 1.**

`CONDITIONAL` · [Sdtrig.html#csr-tinfo](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-tinfo) · obligation `OB-E0FCE46E`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-138-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-138-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-138-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If the bit is set, then that type is supported by the currently selected trigger.**

`CONDITIONAL` · [Sdtrig.html#csr-tinfo](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-tinfo) · obligation `OB-EECB6BC2`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-139-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-139-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-139-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### Trigger Select (tselect, at 0x7a0)

**Writes of values greater than or equal to the number of supported triggers may result in a different value in this register than what was written or may point to a trigger where ty**

`MAY` · [Sdtrig.html#csr-tselect](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-tselect) · obligation `OB-0DE691B9`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-140-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-140-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**The set of accessible triggers must start at 0, and be contiguous.**

`MUST` · [Sdtrig.html#csr-tselect](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-tselect) · obligation `OB-573DC225`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-141-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-141-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-141-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Since triggers can be used both by Debug Mode and M-mode, the external debugger must restore this register if it modifies it.**

`MUST` · [Sdtrig.html#csr-tselect](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-tselect) · obligation `OB-AA652C80`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-142-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-142-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-142-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### 5.1.6. Multiple State Change Instructions

**When they resume execution, they will execute the same instruction once more.**

`CONDITIONAL` · [Sdtrig.html#multistate](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#multistate) · obligation `OB-BC3EEA7F`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-143-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-143-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-143-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Alternatively, it may state that partial execution is not allowed, implying that a mid-execution trigger must prevent any architectural state changes from occurring.**

`MUST` · [Sdtrig.html#multistate](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#multistate) · obligation `OB-CBBF5EB9`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-144-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-144-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-144-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### 5.1.4. Native Triggers

**Debuggers should use other mechanisms to debug these cases, such as patching the handler or setting a breakpoint on the instruction after MIE is cleared.**

`SHOULD` · [Sdtrig.html#nativetrigger](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#nativetrigger) · obligation `OB-0C4BDCDC`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-145-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-145-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**If etrigger/itrigger is set to trigger on exception/interrupt X and if X is delegated to mode Y then the trigger will cause a breakpoint exception that is taken from mode Y to mode**

`MAY` · [Sdtrig.html#nativetrigger](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#nativetrigger) · obligation `OB-65B84BD6`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-146-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-146-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**If medeleg [3]=1 and hedeleg [3]=1 then it prevents triggers with action=0 from matching or firing while in VS-mode and while SIE in vstatus is 0. mte and mpte in tcontrol is imple**

`CONDITIONAL` · [Sdtrig.html#nativetrigger](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#nativetrigger) · obligation `OB-72667843`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-147-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-147-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-147-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If medeleg [3]=1 then it prevents triggers with action=0 from matching or firing while in S-mode and while SIE in sstatus is 0.**

`CONDITIONAL` · [Sdtrig.html#nativetrigger](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#nativetrigger) · obligation `OB-779B3232`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-148-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-148-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-148-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**In these cases such a trigger may cause a breakpoint exception while already in a trap handler.**

`MAY` · [Sdtrig.html#nativetrigger](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#nativetrigger) · obligation `OB-B7C020E6`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-149-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-149-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**Harts that support triggers with action=0 should implement one of the following two solutions to solve the problem of reentrancy: The hardware prevents triggers with action=0 from**

`SHOULD` · [Sdtrig.html#nativetrigger](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#nativetrigger) · obligation `OB-E421E9E5`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-150-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-150-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**If supported by the hart and desired by the debugger, triggers will often be programmed to have m=0 so that when they fire they cause a breakpoint exception to trap to a more privi**

`CONDITIONAL` · [Sdtrig.html#nativetrigger](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#nativetrigger) · obligation `OB-EBE53751`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-151-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-151-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-151-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### Debug Module Control (dmcontrol, at 0x10)

**No other mechanism should exist that may result in resetting the Debug Module after power up.**

`SHOULD` · [debug_module.html#dm-dmcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcontrol) · obligation `OB-01315BF7`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-152-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-152-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**Writes to this bit should be ignored while an abstract command is executing.**

`SHOULD` · [debug_module.html#dm-dmcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcontrol) · obligation `OB-07399E10`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-153-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-153-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-154-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-154-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-155-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-155-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-156-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-156-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-157-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-157-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**To place the Debug Module into a known state, a debugger should write 0 to dmactive, poll until dmactive is observed 0, write 1 to dmactive, and poll until dmactive is observed 1.**

`SHOULD` · [debug_module.html#dm-dmcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcontrol) · obligation `OB-2E8AAD38`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-158-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-158-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**When it is set, it suggests that the hardware should attempt to keep the hart available for the debugger, e.g. by keeping it from entering a low-power state once powered on.**

`SHOULD` · [debug_module.html#dm-dmcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcontrol) · obligation `OB-3144B345`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-159-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-159-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**The others must be written 0.**

`MUST` · [debug_module.html#dm-dmcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcontrol) · obligation `OB-387C8D06`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-160-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-160-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-160-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**An implementation which does not implement the hart array mask register must tie this field to 0.**

`MUST` · `rtl-unsupported` · [debug_module.html#dm-dmcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcontrol) · obligation `OB-4268BEC1`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-161-C` | Cover | P3 | 0.25 | Deferred | Not started | 0 | — | 2 | — |

> hart_array is absent on this DUT (dut-profile absent[]); the row would pass for the wrong reason or be unreachable.

**It must be at least 0 and at most 20.**

`MUST` · [debug_module.html#dm-dmcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcontrol) · obligation `OB-45A50BE4`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-162-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-162-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-162-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**While this bit is 1, the debugger must not change which harts are selected.**

`MUST_NOT` · [debug_module.html#dm-dmcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcontrol) · obligation `OB-50A5BF54`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-163-C` | Check | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-163-C` | Cover | P2 | 0.10 | Full | Not started | 0 | — | 2 | — |

**Any accesses to the module may fail.**

`MAY` · [debug_module.html#dm-dmcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcontrol) · obligation `OB-59621783`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-164-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-164-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**When this value is written, the DM may ignore any other bits written to `dmcontrol` in the same write. 1 (active): The module functions normally.**

`MAY` · [debug_module.html#dm-dmcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcontrol) · obligation `OB-60AFAED8`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-165-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-165-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**While the spec allows for 20 `hartsel` bits, an implementation may choose to implement fewer than that.**

`MAY` · [debug_module.html#dm-dmcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcontrol) · obligation `OB-634284F6`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-166-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-166-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**This may cancel outstanding halt requests for those harts.**

`MAY` · [debug_module.html#dm-dmcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcontrol) · obligation `OB-6941FBAA`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-167-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-167-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**The signal should reset every part of the hardware platform, including every hart, except for the DM and any logic required to access the DM.**

`SHOULD` · [debug_module.html#dm-dmcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcontrol) · obligation `OB-7429F88E`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-168-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-168-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**On any given write, a debugger may only write 1 to at most one of the following bits: resumereq, hartreset, ackhavereset, setresethaltreq, and clrresethaltreq.**

`MAY` · [debug_module.html#dm-dmcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcontrol) · obligation `OB-78B09A4C`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-169-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-169-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**W1 - hasel Selects the definition of currently selected harts. 0 (single): There is a single currently selected hart, that is selected by `hartsel`. 1 (multiple): There may be mult**

`MAY` · `rtl-unsupported` · [debug_module.html#dm-dmcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcontrol) · obligation `OB-7C245867`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-170-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

> hart_array is absent on this DUT (dut-profile absent[]); the row would pass for the wrong reason or be unreachable.

**A debugger which wishes to use the hart array mask register feature should set this bit and read back to see if the functionality is supported.**

`SHOULD` · `rtl-unsupported` · [debug_module.html#dm-dmcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcontrol) · obligation `OB-7DCFCB55`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-171-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

> hart_array is absent on this DUT (dut-profile absent[]); the row would pass for the wrong reason or be unreachable.

**When set to 1, each selected hart will halt upon the next deassertion of its reset.**

`CONDITIONAL` · [debug_module.html#dm-dmcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcontrol) · obligation `OB-8C7C97F1`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-172-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-172-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-172-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Hardware should enforce this by ignoring changes to `hartsel` while busy is set.**

`SHOULD` · [debug_module.html#dm-dmcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcontrol) · obligation `OB-9678E673`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-173-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-173-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**A debugger should discover HARTSELLEN by writing all ones to `hartsel` (assuming the maximum size) and reading back the value to see which bits were actually set.**

`SHOULD` · [debug_module.html#dm-dmcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcontrol) · obligation `OB-A6B5A53C`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-174-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-174-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**Implementations may pay attention to this bit to further aid debugging, for example by preventing the Debug Module from being power gated while debugging is active.**

`MAY` · [debug_module.html#dm-dmcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcontrol) · obligation `OB-AC404D1B`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-175-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-175-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**After changing the value of this bit, the debugger must poll dmcontrol until dmactive has taken the requested value before performing any action that assumes the requested dmactive**

`MUST` · [debug_module.html#dm-dmcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcontrol) · obligation `OB-B10A0637`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-176-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-176-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-176-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**During this time, the DM may ignore any register writes. 0 (inactive): The module’s state, including authentication mechanism, takes its reset values (the dmactive bit is the only**

`MAY` · [debug_module.html#dm-dmcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcontrol) · obligation `OB-C9F7A1E5`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-177-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-177-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**If this feature is not implemented, the bit always stays 0, so after writing 1 the debugger can read the register back to see if the feature is supported.**

`CONDITIONAL` · [debug_module.html#dm-dmcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcontrol) · obligation `OB-E9BB65A9`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-178-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-178-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-178-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**The debugger must write to clrresethaltreq to clear it.**

`MUST` · [debug_module.html#dm-dmcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcontrol) · obligation `OB-ECF4D772`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-179-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-179-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-179-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Debuggers must not change `hartsel` while an abstract command is executing.**

`MUST_NOT` · [debug_module.html#dm-dmcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcontrol) · obligation `OB-F2586FCE`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-180-C` | Check | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-180-C` | Cover | P2 | 0.10 | Full | Not started | 0 | — | 2 | — |

**If hasresethaltreq is 0, this field is not implemented.**

`CONDITIONAL` · [debug_module.html#dm-dmcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcontrol) · obligation `OB-F29C40A3`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-181-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-181-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-181-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Hardware may take an arbitrarily long time to complete activation or deactivation and will indicate completion by setting dmactive to the requested value.**

`MAY` · [debug_module.html#dm-dmcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcontrol) · obligation `OB-F9D15BA0`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-182-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-182-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

### Triggers

**When a debugger wants to set a trigger, it writes the desired configuration, and then reads back to see if that configuration is supported.**

`CONDITIONAL` · [debugger_implementation.html#triggers](https://docs.riscv.org/reference/debug/v1.0/debugger_implementation.html#triggers) · obligation `OB-F823F66C`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-TRIG-183-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-TRIG-183-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-TRIG-183-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

## AC — Abstract commands

### 3.1.7. Abstract Commands

**If an abstract command does not complete in the expected time and appears to be hung, the debugger can try to reset the hart (using hartreset or ndmreset).**

`CONDITIONAL` · [debug_module.html#abstractcommands](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#abstractcommands) · obligation `OB-0100569D`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-001-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-001-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-001-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Commands may fail because a hart is not halted, not running, unavailable, or because they encounter an error during execution.**

`MAY` · [debug_module.html#abstractcommands](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#abstractcommands) · obligation `OB-1019002E`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-002-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-002-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**Example: Every DM must support the Access Register command, but might not support accessing CSRs.**

`MUST` · [debug_module.html#abstractcommands](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#abstractcommands) · obligation `OB-2F51C0F3`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-003-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-003-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-003-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If the command takes arguments, the debugger must write them to the data registers before writing to command.**

`MUST` · [debug_module.html#abstractcommands](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#abstractcommands) · obligation `OB-36C3D0F5`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-004-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-004-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-004-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**While an abstract command is executing (busy in abstractcs is high), a debugger must not change `hartsel`, and must not write 1 to haltreq, resumereq, ackhavereset, setresethaltreq**

`MUST_NOT` · [debug_module.html#abstractcommands](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#abstractcommands) · obligation `OB-3A6DC444`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-005-C` | Check | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-005-C` | Cover | P2 | 0.10 | Full | Not started | 0 | — | 2 | — |

**If an abstract command is started while the selected hart is unavailable or if a hart becomes unavailable while executing an abstract command, then the Debug Module may terminate t**

`MAY` · [debug_module.html#abstractcommands](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#abstractcommands) · obligation `OB-4DABD08C`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-006-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-006-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**If the debugger starts a new command while busy is set, cmderr becomes 1 (busy), the currently executing command still gets to run to completion, but any error generated by the cur**

`CONDITIONAL` · [debug_module.html#abstractcommands](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#abstractcommands) · obligation `OB-55B5756E`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-007-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-007-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-007-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If there is a failure, the interface ensures that no commands execute after the failing one.**

`CONDITIONAL` · [debug_module.html#abstractcommands](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#abstractcommands) · obligation `OB-675A96C8`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-008-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-008-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-008-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Commands may be supported with some options set, but not with other options set.**

`MAY` · [debug_module.html#abstractcommands](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#abstractcommands) · obligation `OB-8698F4F0`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-009-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-009-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**The hardware should not rely on this debugger behavior, but should enforce it by ignoring writes to these bits while busy is high.**

`SHOULD_NOT` · [debug_module.html#abstractcommands](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#abstractcommands) · obligation `OB-88264FCA`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-010-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

> ⚠ Requirement text may be truncated by an empty cross-reference in the published HTML -- verify against the AsciiDoc source.

**If a command returns results, the Debug Module must ensure they are placed in the data registers before busy is cleared.**

`MUST` · [debug_module.html#abstractcommands](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#abstractcommands) · obligation `OB-8EDEE401`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-011-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-011-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-011-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If the debugger requests to read a CSR in that case, the command will return "not supported".**

`CONDITIONAL` · [debug_module.html#abstractcommands](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#abstractcommands) · obligation `OB-B6DC9B48`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-012-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-012-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-012-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If that doesn’t clear busy, then it can try resetting the Debug Module (using dmactive).**

`CONDITIONAL` · [debug_module.html#abstractcommands](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#abstractcommands) · obligation `OB-C0D042EA`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-013-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-013-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-013-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Depending on the implementation, the debugger may be able to perform some abstract commands even when the selected hart is not halted.**

`MAY` · [debug_module.html#abstractcommands](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#abstractcommands) · obligation `OB-F4A656CF`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-014-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-014-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**If a command has unsupported options set or if bits that are defined as 0 aren’t 0, then the DM must set cmderr to 2 (not supported).**

`MUST` · [debug_module.html#abstractcommands](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#abstractcommands) · obligation `OB-F6C94C6E`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-015-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-015-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-015-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### Access Register

**If the failure is that the requested register does not exist in the hart, cmderr must be set to 3 (exception).**

`MUST` · [debug_module.html#ac-accessregister](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-accessregister) · obligation `OB-07AAC19F`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-016-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-016-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-016-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If a register is accessible, then reads of aarsize less than or equal to the register’s actual size must be supported.**

`MUST` · [debug_module.html#ac-accessregister](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-accessregister) · obligation `OB-0A06EFC6`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-017-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-017-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-017-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**It is undefined whether the increment happens when transfer is 0. postexec 0 (disabled): No effect.**

`UNSPECIFIED` · [debug_module.html#ac-accessregister](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-accessregister) · obligation `OB-0B567414`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-018-C` | Check | P3 | 0.10 | Deferred | Not started | 0 | — | 1 | — |

> Spec says UNSPECIFIED -- check the DM does not hang; do not assert a value.

**This variant must be supported, and is the only supported one if progbufsize is 0. 1 (enabled): Execute the program in the Program Buffer exactly once after performing the transfer**

`MUST` · [debug_module.html#ac-accessregister](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-accessregister) · obligation `OB-11DBEB47`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-019-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-019-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-019-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Debug Modules must implement this command and must support read and write access to all GPRs when the selected hart is halted.**

`MUST` · [debug_module.html#ac-accessregister](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-accessregister) · obligation `OB-2DAF5030`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-020-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-020-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-020-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If any of these operations fail, cmderr is set and none of the remaining steps are executed.**

`CONDITIONAL` · [debug_module.html#ac-accessregister](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-accessregister) · obligation `OB-3FFC5310`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-021-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-021-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-021-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**This bit can be used to just execute the Program Buffer without having to worry about placing valid values into aarsize or regno. write When transfer is set: 0 (arg0): Copy data fr**

`MAY` · [debug_module.html#ac-accessregister](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-accessregister) · obligation `OB-4E06FCE7`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-022-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-022-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**It is recommended that if one register in a group is accessible, then all registers in that group are accessible, but each individual register (aside from GPRs) may be supported di**

`SHOULD` · [debug_module.html#ac-accessregister](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-accessregister) · obligation `OB-7E09022C`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-023-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-023-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**Debug Modules may optionally support accessing other registers, or accessing registers when the hart is running.**

`MAY` · [debug_module.html#ac-accessregister](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-accessregister) · obligation `OB-9E69165C`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-024-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-024-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**If write is set and transfer is set, then copy data from the arg0 region of data into the register specified by regno, and perform any side effects that occur when this register is**

`CONDITIONAL` · [debug_module.html#ac-accessregister](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-accessregister) · obligation `OB-A343AEA1`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-025-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-025-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-025-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**The Core Debug Registers ([debreg]) should be accessible if abstract CSR access is implemented.**

`SHOULD` · [debug_module.html#ac-accessregister](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-accessregister) · obligation `OB-B08205DE`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-026-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-026-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**Writing less than the full register may be supported, but what happens to the high bits in that case is UNSPECIFIED.**

`MAY` · [debug_module.html#ac-accessregister](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-accessregister) · obligation `OB-B237B93F`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-027-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-027-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**Incrementing past the highest supported value causes regno to become UNSPECIFIED.**

`UNSPECIFIED` · [debug_module.html#ac-accessregister](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-accessregister) · obligation `OB-B52071A0`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-028-C` | Check | P3 | 0.10 | Deferred | Not started | 0 | — | 1 | — |

> Spec says UNSPECIFIED -- check the DM does not hang; do not assert a value.

**This variant must be supported. 1 (enabled): After a successful register access, regno is incremented.**

`MUST` · [debug_module.html#ac-accessregister](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-accessregister) · obligation `OB-E14C5C30`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-029-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-029-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-029-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If aarpostincrement and transfer are set, increment regno. regno may also be incremented if aarpostincrement is set and transfer is clear.**

`MAY` · [debug_module.html#ac-accessregister](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-accessregister) · obligation `OB-E9456F4D`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-030-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-030-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**An implementation may detect an upcoming failure early, and fail the overall command before it reaches the step that would cause failure.**

`MAY` · [debug_module.html#ac-accessregister](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-accessregister) · obligation `OB-EA02F0C0`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-031-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-031-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**If aarsize specifies a size larger than the register’s actual size, then the access must fail.**

`MUST` · [debug_module.html#ac-accessregister](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-accessregister) · obligation `OB-EB9DDE05`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-032-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-032-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-032-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### Abstract Command Autoexec (abstractauto, at 0x18)

**Other bits must be hard-wired to 0.**

`MUST` · [debug_module.html#dm-abstractauto](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-abstractauto) · obligation `OB-2393302C`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-033-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-033-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-033-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If this register is written while an abstract command is executing then the write is ignored and cmderr becomes 1 (busy) once the command completes (busy becomes 0).**

`CONDITIONAL` · [debug_module.html#dm-abstractauto](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-abstractauto) · obligation `OB-505C0BEA`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-034-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-034-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-034-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If this register is implemented then bits corresponding to implemented progbuf and data registers must be writable.**

`MUST` · [debug_module.html#dm-abstractauto](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-abstractauto) · obligation `OB-A560EA93`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-035-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-035-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-035-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### Abstract Control and Status (abstractcs, at 0x16)

**It may be supported with different options set, but it will not be supported at a later time when the hart or system state are different. 3 (exception): An exception occurred while**

`MAY` · [debug_module.html#dm-abstractcs](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-abstractcs) · obligation `OB-584D4C25`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-036-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-036-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**The details of the latter are implementation-specific. 0 (full checks): Full permission checks apply. 1 (relaxed checks): Relaxed permission checks apply.**

`UNSPECIFIED` · [debug_module.html#dm-abstractcs](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-abstractcs) · obligation `OB-BA502A14`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-037-C` | Check | P3 | 0.10 | Deferred | Not started | 0 | — | 1 | — |

> Spec says UNSPECIFIED -- check the DM does not hang; do not assert a value.

**Writing this register while an abstract command is executing causes cmderr to become 1 (busy) once the command completes (busy becomes 0). datacount must be at least 1 to support R**

`MUST` · [debug_module.html#dm-abstractcs](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-abstractcs) · obligation `OB-C7143C1D`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-038-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-038-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-038-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### Abstract Command (command, at 0x17)

**If cmderr is non-zero, writes to this register are ignored. cmderr inhibits starting a new command to accommodate debuggers that, for performance reasons, send several commands to**

`CONDITIONAL` · [debug_module.html#dm-command](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-command) · obligation `OB-6AC00D11`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-039-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-039-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-039-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

> ⚠ Requirement text may be truncated by an empty cross-reference in the published HTML -- verify against the AsciiDoc source.

### Handling Exceptions

**If there was an exception, it’s left to the debugger to know what must have caused it.**

`MUST` · [debugger_implementation.html#handling-exceptions](https://docs.riscv.org/reference/debug/v1.0/debugger_implementation.html#handling-exceptions) · obligation `OB-3136B540`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-040-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-040-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-040-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**A typical debugger will not know enough about the hardware platform to know what’s going to happen, and must attempt the access to determine the outcome.**

`MUST` · [debugger_implementation.html#handling-exceptions](https://docs.riscv.org/reference/debug/v1.0/debugger_implementation.html#handling-exceptions) · obligation `OB-77AB89C4`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-041-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-041-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-041-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When an exception occurs while executing the Program Buffer, command becomes set.**

`CONDITIONAL` · [debugger_implementation.html#handling-exceptions](https://docs.riscv.org/reference/debug/v1.0/debugger_implementation.html#handling-exceptions) · obligation `OB-C00B3FF2`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-042-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-042-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-042-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### Execution Based

**When ebreak is executed (indicating the end of the Program Buffer code) the hart returns to its park loop.**

`CONDITIONAL` · [implementations.html#execution_based](https://docs.riscv.org/reference/debug/v1.0/implementations.html#execution_based) · obligation `OB-3B16A732`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-043-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-043-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-043-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If an exception is encountered, the hart jumps to an address within the Debug Module.**

`CONDITIONAL` · [implementations.html#execution_based](https://docs.riscv.org/reference/debug/v1.0/implementations.html#execution_based) · obligation `OB-40CE5B27`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-044-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-044-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-044-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**The PMP must not disallow fetches, loads, or stores in the address range associated with the Debug Module when the hart is in Debug Mode, regardless of how the PMP is configured.**

`MUST_NOT` · [implementations.html#execution_based](https://docs.riscv.org/reference/debug/v1.0/implementations.html#execution_based) · obligation `OB-411DA6FF`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-045-C` | Check | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-045-C` | Cover | P2 | 0.10 | Full | Not started | 0 | — | 2 | — |

**Accesses to this memory should be uncached to avoid side effects from debugging operations.**

`SHOULD` · [implementations.html#execution_based](https://docs.riscv.org/reference/debug/v1.0/implementations.html#execution_based) · obligation `OB-60831DD0`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-046-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-046-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**When transfer is set, the DM populates these words with lw <gpr>, 0x400(zero) or sw <gpr>, 0x400(zero). 64- and 128-bit accesses use ld/sd and lq/sq respectively.**

`CONDITIONAL` · [implementations.html#execution_based](https://docs.riscv.org/reference/debug/v1.0/implementations.html#execution_based) · obligation `OB-69C228E5`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-047-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-047-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-047-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When the halt request bit is set, the Debug Module raises a special interrupt to the selected harts.**

`CONDITIONAL` · [implementations.html#execution_based](https://docs.riscv.org/reference/debug/v1.0/implementations.html#execution_based) · obligation `OB-80DC4913`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-048-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-048-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-048-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**The exact address is an implementation detail that a debugger must not rely on.**

`MUST_NOT` · [implementations.html#execution_based](https://docs.riscv.org/reference/debug/v1.0/implementations.html#execution_based) · obligation `OB-985839B9`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-049-C` | Check | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-049-C` | Cover | P2 | 0.10 | Full | Not started | 0 | — | 2 | — |

**If transfer is not set, the DM populates these instructions as nop’s.**

`CONDITIONAL` · [implementations.html#execution_based](https://docs.riscv.org/reference/debug/v1.0/implementations.html#execution_based) · obligation `OB-9DAFE72E`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-050-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-050-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-050-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If postexec is set, execution continues to the debugger-controlled Program Buffer, otherwise the DM causes an ebreak to execute immediately.**

`CONDITIONAL` · [implementations.html#execution_based](https://docs.riscv.org/reference/debug/v1.0/implementations.html#execution_based) · obligation `OB-E205A8B9`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-051-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-051-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-051-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When dret is executed, pc is restored from dpc and normal execution resumes at the privilege set by prv and v, and the ELP state set by pelp. data0 etc. are mapped into regular mem**

`CONDITIONAL` · [implementations.html#execution_based](https://docs.riscv.org/reference/debug/v1.0/implementations.html#execution_based) · obligation `OB-EC50056B`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-052-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-052-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-052-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When taking this jump, pc is saved to dpc and cause is updated in dcsr.**

`CONDITIONAL` · [implementations.html#execution_based](https://docs.riscv.org/reference/debug/v1.0/implementations.html#execution_based) · obligation `OB-F0C212AA`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AC-053-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AC-053-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AC-053-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

## DCSR — Debug Mode — dcsr/dpc/dscratch

### 4.1.2. Load-Reserved/Store-Conditional Instructions

**This is a behavior that debug users must be aware of.**

`MUST` · [Sdext.html#4-1-2-load-reservedstore-conditional-instructions](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#4-1-2-load-reservedstore-conditional-instructions) · obligation `OB-0623EC9D`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-001-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DCSR-001-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-001-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**A higher level debugger may choose to automate this.**

`MAY` · [Sdext.html#4-1-2-load-reservedstore-conditional-instructions](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#4-1-2-load-reservedstore-conditional-instructions) · obligation `OB-2A19CE5B`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-002-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-002-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**The reservation registered by an lr instruction on a memory address may be lost when entering Debug Mode or while in Debug Mode.**

`MAY` · [Sdext.html#4-1-2-load-reservedstore-conditional-instructions](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#4-1-2-load-reservedstore-conditional-instructions) · obligation `OB-6CD8999A`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-003-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-003-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**This means that there may be no forward progress if Debug Mode is entered between lr and sc pairs.**

`MAY` · [Sdext.html#4-1-2-load-reservedstore-conditional-instructions](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#4-1-2-load-reservedstore-conditional-instructions) · obligation `OB-8CC4C274`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-004-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-004-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**If they have a breakpoint set between a lr and sc pair, or are stepping through such code, the sc may never succeed.**

`MUST_NOT` · [Sdext.html#4-1-2-load-reservedstore-conditional-instructions](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#4-1-2-load-reservedstore-conditional-instructions) · obligation `OB-E4C7F69B`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-005-C` | Check | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DCSR-005-C` | Cover | P2 | 0.10 | Full | Not started | 0 | — | 2 | — |

### Debug Control and Status (dcsr, at 0x7b0)

**While all harts have stoptime=1 and are in Debug Mode, mtime is allowed to stop incrementing.**

`MAY` · [Sdext.html#csr-dcsr](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#csr-dcsr) · obligation `OB-2F1A125F`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-006-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-006-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**When leaving Debug Mode, time will reflect the latest value of mtime again.**

`CONDITIONAL` · [Sdext.html#csr-dcsr](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#csr-dcsr) · obligation `OB-664DCB83`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-007-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DCSR-007-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-007-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**On single-hart cores cycle should be stopped, but on multi-hart cores it must keep incrementing.**

`MUST` · [Sdext.html#csr-dcsr](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#csr-dcsr) · obligation `OB-6FA6FEB5`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-008-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DCSR-008-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-008-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**It may be tied to either 0 or 1.**

`MAY` · [Sdext.html#csr-dcsr](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#csr-dcsr) · obligation `OB-8A95398D`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-009-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-009-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**Harts may report 3 for this cause instead. 7 (other): The hart halted for a reason other than the ones mentioned above. extcause may contain a more specific reason.**

`MAY` · [Sdext.html#csr-dcsr](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#csr-dcsr) · obligation `OB-A2A3A8FA`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-010-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-010-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**Since an NMI can indicate a hardware error condition, reliable debugging may no longer be possible once this bit becomes set.**

`MAY` · [Sdext.html#csr-dcsr](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#csr-dcsr) · obligation `OB-A780F203`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-011-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-011-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**If the encoding written is not supported or the debugger is not allowed to change to it, the hart may change to any supported privilege mode.**

`MAY` · [Sdext.html#csr-dcsr](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#csr-dcsr) · obligation `OB-A9E0D915`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-012-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-012-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**When cetrig is 1, resuming from Debug Mode following an entry due to a critical error will result in an immediate re-entry into Debug Mode due to the critical error.**

`CONDITIONAL` · [Sdext.html#csr-dcsr](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#csr-dcsr) · obligation `OB-B4F931A6`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-013-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DCSR-013-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-013-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**The debugger may resume with cetrig set to 0 to allow the platform defined actions on critical-error signal to occur.**

`MAY` · [Sdext.html#csr-dcsr](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#csr-dcsr) · obligation `OB-B54F3500`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-014-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-014-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**Implementations should implement priorities as shown in the table.**

`SHOULD` · [Sdext.html#csr-dcsr](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#csr-dcsr) · obligation `OB-C20B338E`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-015-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-015-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**When there are multiple reasons to enter Debug Mode in a single cycle, hardware should set cause to the cause with the highest priority.**

`SHOULD` · [Sdext.html#csr-dcsr](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#csr-dcsr) · obligation `OB-D1081042`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-016-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-016-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**This value should be supported. 1 (interrupts enabled): Interrupts (including NMI) are enabled during single stepping with step set.**

`SHOULD` · [Sdext.html#csr-dcsr](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#csr-dcsr) · obligation `OB-DD6EE835`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-017-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-017-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**The debugger must not change the value of this bit while the hart is running.**

`MUST_NOT` · [Sdext.html#csr-dcsr](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#csr-dcsr) · obligation `OB-DFD65C76`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-018-C` | Check | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DCSR-018-C` | Cover | P2 | 0.10 | Full | Not started | 0 | — | 2 | — |
| `TC-DCSR-019-C` | Check | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DCSR-019-C` | Cover | P2 | 0.10 | Full | Not started | 0 | — | 2 | — |

**Implementations may hard wire this bit to 0.**

`MAY` · [Sdext.html#csr-dcsr](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#csr-dcsr) · obligation `OB-E4613D8E`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-020-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-020-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**An implementation may hardwire this bit to 0 or 1.**

`MAY` · [Sdext.html#csr-dcsr](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#csr-dcsr) · obligation `OB-F8CA9178`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-021-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-021-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |
| `TC-DCSR-022-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-022-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

### Debug PC (dpc, at 0x7b1)

**Allowing dpc to become UNSPECIFIED upon Program Buffer execution allows for direct implementations that don’t have a separate PC register, and do need to use the PC when executing**

`UNSPECIFIED` · [Sdext.html#csr-dpc](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#csr-dpc) · obligation `OB-117BA64A`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-023-C` | Check | P3 | 0.10 | Deferred | Not started | 0 | — | 1 | — |

> Spec says UNSPECIFIED -- check the DM does not hang; do not assert a value.

**If the trigger is mcontrol and timing is 0 or if the trigger is mcontrol6 and hit1 is 0, this corresponds to the address of the instruction which caused the trigger to fire. halt r**

`CONDITIONAL` · [Sdext.html#csr-dpc](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#csr-dpc) · obligation `OB-447B9D84`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-024-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DCSR-024-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-024-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If the Access Register abstract command supports reading dpc while the hart is running, then the value read should be the address of a recently executed instruction.**

`SHOULD` · [Sdext.html#csr-dpc](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#csr-dpc) · obligation `OB-5F5F139D`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-025-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-025-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**Executing the Program Buffer may cause the value of dpc to become UNSPECIFIED.**

`MAY` · [Sdext.html#csr-dpc](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#csr-dpc) · obligation `OB-7C25B377`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-026-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-026-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**If the Access Register abstract command supports writing dpc while the hart is running, then the executing program should jump to the written address shortly after the write occurs**

`SHOULD` · [Sdext.html#csr-dpc](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#csr-dpc) · obligation `OB-8A224D0A`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-027-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-027-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**A debugger may write dpc to change where the hart resumes.**

`MAY` · [Sdext.html#csr-dpc](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#csr-dpc) · obligation `OB-C89C1926`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-028-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-028-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**In particular, dpc must be able to hold all valid virtual addresses and the writability of the low bits depends on IALIGN.**

`MUST` · [Sdext.html#csr-dpc](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#csr-dpc) · obligation `OB-CFF92650`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-029-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DCSR-029-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-029-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If that is the case, it must be possible to read/write dpc using an abstract command with postexec not set.**

`MUST` · [Sdext.html#csr-dpc](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#csr-dpc) · obligation `OB-DAC9C9EE`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-030-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DCSR-030-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-030-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When resuming, the hart’s PC is updated to the virtual address stored in dpc.**

`CONDITIONAL` · [Sdext.html#csr-dpc](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#csr-dpc) · obligation `OB-DDD43814`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-031-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DCSR-031-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-031-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**The debugger must attempt to save dpc between halting and executing a Program Buffer, and then restore dpc before leaving Debug Mode.**

`MUST` · [Sdext.html#csr-dpc](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#csr-dpc) · obligation `OB-E745032F`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-032-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DCSR-032-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-032-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### Debug Scratch Register 0 (dscratch0, at 0x7b2)

**A debugger must not write to this register unless hartinfo explicitly mentions it (the Debug Module may use this register internally).**

`MUST_NOT` · [Sdext.html#csr-dscratch0](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#csr-dscratch0) · obligation `OB-E9D6A299`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-033-C` | Check | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DCSR-033-C` | Cover | P2 | 0.10 | Full | Not started | 0 | — | 2 | — |

### Debug Scratch Register 1 (dscratch1, at 0x7b3)

**A debugger must not write to this register unless hartinfo explicitly mentions it (the Debug Module may use this register internally).**

`MUST_NOT` · [Sdext.html#csr-dscratch1](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#csr-dscratch1) · obligation `OB-266A72BB`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-034-C` | Check | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DCSR-034-C` | Cover | P2 | 0.10 | Full | Not started | 0 | — | 2 | — |

### 4.1.1. Debug Mode

**All control transfer instructions may act as illegal instructions if their destination is outside the Program Buffer.**

`MAY` · [Sdext.html#debugmode](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#debugmode) · obligation `OB-08232C1C`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-035-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-035-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**When executing code due to an abstract command, the hart stays in Debug Mode and the following apply: All implemented instructions operate just as they do in M-mode, unless an exce**

`CONDITIONAL` · [Sdext.html#debugmode](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#debugmode) · obligation `OB-20BDED99`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-036-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DCSR-036-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-036-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If hardware ties mprven to 0 then the external debugger is expected to simulate all the effects of MPRV, including any extensions that affect memory accesses.**

`CONDITIONAL` · [Sdext.html#debugmode](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#debugmode) · obligation `OB-309768D3`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-037-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DCSR-037-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-037-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Registers that may be updated as part of execution before the exception are allowed to be updated.**

`MAY` · [Sdext.html#debugmode](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#debugmode) · obligation `OB-364C1261`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-038-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-038-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**Almost all instructions that change the privilege mode have UNSPECIFIED behavior.**

`UNSPECIFIED` · [Sdext.html#debugmode](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#debugmode) · obligation `OB-36576034`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-039-C` | Check | P3 | 0.10 | Deferred | Not started | 0 | — | 1 | — |

> Spec says UNSPECIFIED -- check the DM does not hang; do not assert a value.

**If stoptime is 0 then time continues to update.**

`CONDITIONAL` · [Sdext.html#debugmode](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#debugmode) · obligation `OB-3910CF96`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-040-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DCSR-040-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-040-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**How Debug Mode is implemented is not specified here.**

`UNSPECIFIED` · [Sdext.html#debugmode](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#debugmode) · obligation `OB-417BBC79`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-041-C` | Check | P3 | 0.10 | Deferred | Not started | 0 | — | 1 | — |

> Spec says UNSPECIFIED -- check the DM does not hang; do not assert a value.

**If stopcount is 0 then counters continue.**

`CONDITIONAL` · [Sdext.html#debugmode](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#debugmode) · obligation `OB-497CE61E`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-042-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DCSR-042-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-042-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**All control transfer instructions may act as illegal instructions if their destination is in the Program Buffer.**

`MAY` · [Sdext.html#debugmode](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#debugmode) · obligation `OB-69FD1205`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-043-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-043-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**For example, vector load/store instructions which raise exceptions may partially update the destination register and set vstart appropriately.**

`MAY` · [Sdext.html#debugmode](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#debugmode) · obligation `OB-6D4B3094`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-044-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-044-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**All operations are executed with machine mode privilege, except that additional Debug Mode CSRs are accessible and mprv in mstatus may be ignored according to mprven.**

`MAY` · [Sdext.html#debugmode](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#debugmode) · obligation `OB-8FD1FA4F`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-045-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-045-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**If it is 1 then time will not update.**

`CONDITIONAL` · [Sdext.html#debugmode](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#debugmode) · obligation `OB-9F36F03C`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-046-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DCSR-046-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-046-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When mprven, the external debugger can set MPRV and MPP appropriately to have hardware perform memory accesses with the appropriate endianness, address translation, permission chec**

`CONDITIONAL` · [Sdext.html#debugmode](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#debugmode) · obligation `OB-AE7B5FB7`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-047-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DCSR-047-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-047-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Instructions that depend on the value of the PC (e.g. auipc) may act as illegal instructions.**

`MAY` · [Sdext.html#debugmode](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#debugmode) · obligation `OB-C112BA4F`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-048-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-048-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**For these reasons it is recommended to tie mprven to 1.**

`SHOULD` · [Sdext.html#debugmode](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#debugmode) · obligation `OB-DBC18B0D`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-049-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-049-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**If one such instruction acts as an illegal instruction, all such instructions must act as illegal instructions.**

`MUST` · [Sdext.html#debugmode](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#debugmode) · obligation `OB-F8CC43C7`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-050-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DCSR-050-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-050-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |
| `TC-DCSR-051-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DCSR-051-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-051-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If it is 1 then counters are stopped.**

`CONDITIONAL` · [Sdext.html#debugmode](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#debugmode) · obligation `OB-FE2974F0`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-052-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DCSR-052-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-052-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When the Zicfilp extension is implemented, the ELP state is NO_LP_EXPECTED and is not updated by any instructions.**

`CONDITIONAL` · [Sdext.html#debugmode](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#debugmode) · obligation `OB-FEA5186F`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DCSR-053-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DCSR-053-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DCSR-053-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

## SBA — System Bus Access

### System Bus Address 31:0 (sbaddress0, at 0x39)

**If sbasize is 0, then this register is not present.**

`CONDITIONAL` · [debug_module.html#dm-sbaddress0](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-sbaddress0) · obligation `OB-1D4ECB8E`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-001-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SBA-001-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-001-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If the read succeeded and sbautoincrement is set, increment sbaddress.**

`CONDITIONAL` · [debug_module.html#dm-sbaddress0](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-sbaddress0) · obligation `OB-39E5E336`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-002-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SBA-002-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-002-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If sberror is 0, sbbusyerror is 0, and sbreadonaddr is set then writes to this register start the following: Set sbbusy.**

`CONDITIONAL` · [debug_module.html#dm-sbaddress0](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-sbaddress0) · obligation `OB-4B3A25CB`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-003-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SBA-003-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-003-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

> ⚠ Requirement text may be truncated by an empty cross-reference in the published HTML -- verify against the AsciiDoc source.

**When the system bus manager is busy, writes to this register will set sbbusyerror and don’t do anything else.**

`CONDITIONAL` · [debug_module.html#dm-sbaddress0](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-sbaddress0) · obligation `OB-91F031CC`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-004-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SBA-004-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-004-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

> ⚠ Requirement text may be truncated by an empty cross-reference in the published HTML -- verify against the AsciiDoc source.

### System Bus Address 63:32 (sbaddress1, at 0x3a)

**If sbasize is less than 33, then this register is not present.**

`CONDITIONAL` · [debug_module.html#dm-sbaddress1](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-sbaddress1) · obligation `OB-12820A89`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-005-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SBA-005-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-005-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When the system bus manager is busy, writes to this register will set sbbusyerror and don’t do anything else.**

`CONDITIONAL` · [debug_module.html#dm-sbaddress1](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-sbaddress1) · obligation `OB-E7FCEE52`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-006-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SBA-006-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-006-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

> ⚠ Requirement text may be truncated by an empty cross-reference in the published HTML -- verify against the AsciiDoc source.

### System Bus Address 95:64 (sbaddress2, at 0x3b)

**If sbasize is less than 65, then this register is not present.**

`CONDITIONAL` · [debug_module.html#dm-sbaddress2](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-sbaddress2) · obligation `OB-6D94A52F`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-007-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SBA-007-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-007-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When the system bus manager is busy, writes to this register will set sbbusyerror and don’t do anything else.**

`CONDITIONAL` · [debug_module.html#dm-sbaddress2](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-sbaddress2) · obligation `OB-B341DF22`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-008-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SBA-008-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-008-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

> ⚠ Requirement text may be truncated by an empty cross-reference in the published HTML -- verify against the AsciiDoc source.

### System Bus Address 127:96 (sbaddress3, at 0x37)

**When the system bus manager is busy, writes to this register will set sbbusyerror and don’t do anything else.**

`CONDITIONAL` · [debug_module.html#dm-sbaddress3](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-sbaddress3) · obligation `OB-A0ED4DE3`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-009-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SBA-009-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-009-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

> ⚠ Requirement text may be truncated by an empty cross-reference in the published HTML -- verify against the AsciiDoc source.

**If sbasize is less than 97, then this register is not present.**

`CONDITIONAL` · [debug_module.html#dm-sbaddress3](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-sbaddress3) · obligation `OB-B10553EA`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-010-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SBA-010-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-010-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### System Bus Access Control and Status (sbcs, at 0x38)

**While this field is set, no more system bus accesses can be initiated by the Debug Module.**

`CONDITIONAL` · [debug_module.html#dm-sbcs](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-sbcs) · obligation `OB-057E5897`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-011-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SBA-011-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-011-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**While this field is non-zero, no more system bus accesses can be initiated by the Debug Module.**

`CONDITIONAL` · [debug_module.html#dm-sbcs](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-sbcs) · obligation `OB-2B0490C7`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-012-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SBA-012-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-012-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Writes to sbcs while sbbusy is high result in undefined behavior.**

`UNSPECIFIED` · [debug_module.html#dm-sbcs](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-sbcs) · obligation `OB-65EAE27E`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-013-C` | Check | P3 | 0.10 | Deferred | Not started | 0 | — | 1 | — |

> Spec says UNSPECIFIED -- check the DM does not hang; do not assert a value.

**A debugger must not write to sbcs until it reads sbbusy as 0.**

`MUST_NOT` · [debug_module.html#dm-sbcs](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-sbcs) · obligation `OB-94F5A044`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-014-C` | Check | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SBA-014-C` | Cover | P2 | 0.10 | Full | Not started | 0 | — | 2 | — |

**An implementation may report ``Other'' (7) for any error condition. 0 (none): There was no bus error. 1 (timeout): There was a timeout. 2 (address): A bad address was accessed. 3 (**

`MAY` · [debug_module.html#dm-sbcs](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-sbcs) · obligation `OB-A5194D4F`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-015-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-015-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

### System Bus Data 31:0 (sbdata0, at 0x3c)

**If sbautoincrement is set and the read was successful, increment sbaddress.**

`CONDITIONAL` · [debug_module.html#dm-sbdata0](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-sbdata0) · obligation `OB-20CBEE7D`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-016-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SBA-016-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-016-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**On systems that have buses wider than 32 bits, a debugger should access sbdata0 after accessing the other sbdata registers.**

`SHOULD` · [debug_module.html#dm-sbdata0](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-sbdata0) · obligation `OB-3857257F`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-017-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-017-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**If the write succeeded and sbautoincrement is set, increment sbaddress.**

`CONDITIONAL` · [debug_module.html#dm-sbdata0](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-sbdata0) · obligation `OB-676C626B`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-018-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SBA-018-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-018-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If either sberror or sbbusyerror isn’t 0 then accesses do nothing.**

`CONDITIONAL` · [debug_module.html#dm-sbdata0](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-sbdata0) · obligation `OB-69647D83`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-019-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SBA-019-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-019-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If the bus manager is busy then accesses set sbbusyerror, and don’t do anything else.**

`CONDITIONAL` · [debug_module.html#dm-sbdata0](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-sbdata0) · obligation `OB-8ECFAB58`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-020-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SBA-020-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-020-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If the width of the read access is less than the width of sbdata, the contents of the remaining high bits may take on any value.**

`MAY` · [debug_module.html#dm-sbdata0](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-sbdata0) · obligation `OB-EFA20AFE`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-021-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-021-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**If sbreadondata is set: Perform a system bus read from the address contained in sbaddress, placing the result in sbdata.**

`CONDITIONAL` · [debug_module.html#dm-sbdata0](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-sbdata0) · obligation `OB-F92A60E7`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-022-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SBA-022-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-022-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If all of the sbaccess bits in sbcs are 0, then this register is not present.**

`CONDITIONAL` · [debug_module.html#dm-sbdata0](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-sbdata0) · obligation `OB-FA15770A`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-023-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SBA-023-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-023-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### System Bus Data 63:32 (sbdata1, at 0x3d)

**If sbaccess64 and sbaccess128 are 0, then this register is not present.**

`CONDITIONAL` · [debug_module.html#dm-sbdata1](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-sbdata1) · obligation `OB-95214F7D`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-024-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SBA-024-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-024-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If the bus manager is busy then accesses set sbbusyerror, and don’t do anything else.**

`CONDITIONAL` · [debug_module.html#dm-sbdata1](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-sbdata1) · obligation `OB-BACE5E9D`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-025-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SBA-025-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-025-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### System Bus Data 95:64 (sbdata2, at 0x3e)

**If the bus manager is busy then accesses set sbbusyerror, and don’t do anything else.**

`CONDITIONAL` · [debug_module.html#dm-sbdata2](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-sbdata2) · obligation `OB-2DC1C314`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-026-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SBA-026-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-026-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### System Bus Data 127:96 (sbdata3, at 0x3f)

**If the bus manager is busy then accesses set sbbusyerror, and don’t do anything else.**

`CONDITIONAL` · [debug_module.html#dm-sbdata3](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-sbdata3) · obligation `OB-3966132C`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-027-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SBA-027-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-027-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### 3.1.10. System Bus Access

**Second, it may improve performance when accessing memory.**

`MAY` · [debug_module.html#systembusaccess](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#systembusaccess) · obligation `OB-0016C84C`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-028-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-028-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**The System Bus Access block may support 8-, 16-, 32-, 64-, and 128-bit accesses.**

`MAY` · [debug_module.html#systembusaccess](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#systembusaccess) · obligation `OB-2D7FF24A`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-029-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-029-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**Third, it may provide access to devices that a hart does not have access to.**

`MAY` · [debug_module.html#systembusaccess](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#systembusaccess) · obligation `OB-820B57A9`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-030-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-030-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**Possibilities may include writing to special memory-mapped locations, or executing special instructions via the Program Buffer.**

`MAY` · [debug_module.html#systembusaccess](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#systembusaccess) · obligation `OB-C5807841`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-031-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SBA-031-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**A debugger can access memory from a hart’s point of view using a Program Buffer or the Abstract Access Memory command. (Both these features are optional.) A Debug Module may also i**

`MAY` · `rtl-unsupported` · [debug_module.html#systembusaccess](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#systembusaccess) · obligation `OB-E4E58F04`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SBA-032-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

> abstract_access_memory is absent on this DUT (dut-profile absent[]); the row would pass for the wrong reason or be unreachable.

## RC — Run control — halt/resume

### 4.1.7. Halt

**When a hart halts: cause is updated. prv and v are set to reflect current privilege mode and virtualization mode.**

`CONDITIONAL` · [Sdext.html#4-1-7-halt](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#4-1-7-halt) · obligation `OB-0E658809`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RC-001-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-RC-001-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RC-001-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If the current instruction can be partially executed and should be restarted to complete, then the relevant state for that is updated.**

`SHOULD` · [Sdext.html#4-1-7-halt](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#4-1-7-halt) · obligation `OB-DAEC5018`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RC-002-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RC-002-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**If the Zicfilp extension is implemented, pelp is set to the current ELP state and ELP is set to NO_LP_EXPECTED dpc is set to the next instruction that should be executed.**

`SHOULD` · [Sdext.html#4-1-7-halt](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#4-1-7-halt) · obligation `OB-DED87815`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RC-003-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RC-003-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

### 4.1.8. Resume

**When a hart resumes: pc changes to the value stored in dpc.**

`CONDITIONAL` · [Sdext.html#4-1-8-resume](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#4-1-8-resume) · obligation `OB-22F8CCE2`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RC-004-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-RC-004-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RC-004-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If the Ssdbltrp extension is implemented and the new privilege mode is U, VS, or VU, then sstatus.SDT is set to 0.**

`CONDITIONAL` · [Sdext.html#4-1-8-resume](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#4-1-8-resume) · obligation `OB-4ABB0B8F`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RC-005-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-RC-005-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RC-005-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If the Zicfilp extension is enabled at the new privilege mode, the current ELP state is changed to that specified by pelp else it is set to NO_LP_EXPECTED. pelp is set to NO_LP_EXP**

`CONDITIONAL` · [Sdext.html#4-1-8-resume](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#4-1-8-resume) · obligation `OB-C632BA74`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RC-006-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-RC-006-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RC-006-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If the new privilege mode is less privileged than M-mode, MPRV in mstatus is cleared.**

`CONDITIONAL` · [Sdext.html#4-1-8-resume](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#4-1-8-resume) · obligation `OB-D33286E8`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RC-007-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-RC-007-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RC-007-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If the Smdbltrp extension is implemented and the new privilege mode is not M, then the MDT bit is set to 0.**

`CONDITIONAL` · [Sdext.html#4-1-8-resume](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#4-1-8-resume) · obligation `OB-FE6F2704`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RC-008-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-RC-008-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RC-008-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### Debug Module Control and Status 2 (dmcs2, at 0x32)

**If groups aren’t implemented, then this entire field is 0.**

`CONDITIONAL` · [debug_module.html#dm-dmcs2](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcs2) · obligation `OB-04805E69`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RC-009-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-RC-009-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RC-009-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If halt groups are not implemented, then group will always be 0 when grouptype is 0.**

`CONDITIONAL` · [debug_module.html#dm-dmcs2](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcs2) · obligation `OB-12247C16`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RC-010-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-RC-010-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RC-010-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Implementations may also change the group of a minimal set of unselected harts in the same way, if that is necessary due to a hardware limitation.**

`MAY` · [debug_module.html#dm-dmcs2](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcs2) · obligation `OB-2189F35B`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RC-011-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RC-011-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**Debuggers should read back this field after writing to confirm they are using a hart group that is supported.**

`SHOULD` · [debug_module.html#dm-dmcs2](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcs2) · obligation `OB-488DD661`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RC-012-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RC-012-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**The DM external triggers available to add to halt groups may be the same as or distinct from the DM external triggers available to add to resume groups.**

`MAY` · [debug_module.html#dm-dmcs2](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcs2) · obligation `OB-801BF5E9`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RC-013-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RC-013-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**When 1 is written and hgselect is 1, the DM will change the group of the DM external trigger selected by dmexttrigger to the value written to group, if the hardware supports that g**

`CONDITIONAL` · [debug_module.html#dm-dmcs2](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcs2) · obligation `OB-98097CE3`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RC-014-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-RC-014-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RC-014-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If there are no DM external triggers, this field must be tied to 0.**

`MUST` · [debug_module.html#dm-dmcs2](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcs2) · obligation `OB-A43F9589`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RC-015-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-RC-015-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RC-015-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If a non-existent trigger value is written here, the hardware will change it to a valid one or 0 if no DM external triggers exist.**

`CONDITIONAL` · [debug_module.html#dm-dmcs2](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcs2) · obligation `OB-ACDAE456`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RC-016-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-RC-016-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RC-016-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If resume groups are not implemented, then grouptype will remain 0 even after 1 is written there.**

`CONDITIONAL` · [debug_module.html#dm-dmcs2](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcs2) · obligation `OB-B2AA28A5`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RC-017-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-RC-017-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RC-017-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When hgselect is 1, contains the group of the DM external trigger selected by dmexttrigger.**

`CONDITIONAL` · [debug_module.html#dm-dmcs2](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmcs2) · obligation `OB-B91C10EF`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RC-018-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-RC-018-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RC-018-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### 3.1.5. Run Control

**When a debugger writes 1 to resumereq, each selected hart’s resume ack bit is cleared and each selected, halted hart is sent a resume request.**

`CONDITIONAL` · [debug_module.html#runcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#runcontrol) · obligation `OB-374E382F`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RC-019-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-RC-019-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RC-019-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When halt or resume is requested, a hart must respond in less than one second, unless it is unavailable. (How this is implemented is not further specified.**

`MUST` · [debug_module.html#runcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#runcontrol) · obligation `OB-4C89EE63`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RC-020-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-RC-020-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RC-020-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When a hart’s halt-on-reset request bit is set, the hart will immediately enter debug mode on the next deassertion of its reset.**

`CONDITIONAL` · [debug_module.html#runcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#runcontrol) · obligation `OB-B94D3BEB`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RC-021-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-RC-021-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RC-021-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If the DM is reset while a hart is halted, it is UNSPECIFIED whether that hart resumes.**

`UNSPECIFIED` · [debug_module.html#runcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#runcontrol) · obligation `OB-C71E58C5`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RC-022-C` | Check | P3 | 0.10 | Deferred | Not started | 0 | — | 1 | — |

> Spec says UNSPECIFIED -- check the DM does not hang; do not assert a value.

**When a debugger writes 1 to haltreq, each selected hart’s halt request bit is set.**

`CONDITIONAL` · [debug_module.html#runcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#runcontrol) · obligation `OB-C87DB74D`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RC-023-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-RC-023-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RC-023-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When a running hart, or a hart just coming out of reset, sees its halt request bit high, it responds by halting, deasserting its running signal, and asserting its halted signal.**

`CONDITIONAL` · [debug_module.html#runcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#runcontrol) · obligation `OB-E5C9DC7C`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RC-024-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-RC-024-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RC-024-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Debuggers should use resumereq to explicitly resume harts before clearing dmactive and disconnecting.**

`SHOULD` · [debug_module.html#runcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#runcontrol) · obligation `OB-EAD61D48`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RC-025-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RC-025-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**For every hart, the Debug Module tracks 4 conceptual bits of state: halt request, resume ack, halt-on-reset request, and hart reset. (The hart reset and halt-on-reset request bits**

`MAY` · [debug_module.html#runcontrol](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#runcontrol) · obligation `OB-F61B8B4B`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RC-026-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RC-026-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

### Checking for Halted Harts

**Depending on how many harts exist, the process should start at one of the lower haltsum registers.**

`SHOULD` · [debugger_implementation.html#checking-for-halted-harts](https://docs.riscv.org/reference/debug/v1.0/debugger_implementation.html#checking-for-halted-harts) · obligation `OB-FA75264B`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RC-027-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RC-027-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

## GEN — Unclassified

### 4.1.3. Wait for Interrupt Instruction

**If halt is requested while wfi is executing, then the hart must leave the stalled state, completing this instruction’s execution, and then enter Debug Mode.**

`MUST` · [Sdext.html#4-1-3-wait-for-interrupt-instruction](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#4-1-3-wait-for-interrupt-instruction) · obligation `OB-41B6439E`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-001-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-GEN-001-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-GEN-001-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### 4.1.4. Wait-on-Reservation-Set Instructions

**If halt is requested while wrs.sto or wrs.nto is executing, then the hart must leave the stalled state, completing this instruction’s execution, and then enter Debug Mode.**

`MUST` · `rtl-unsupported` · [Sdext.html#4-1-4-wait-on-reservation-set-instructions](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#4-1-4-wait-on-reservation-set-instructions) · obligation `OB-3C2F3C6F`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-002-C` | Cover | P3 | 0.25 | Deferred | Not started | 0 | — | 2 | — |

> zawrs is absent on this DUT (dut-profile absent[]); the row would pass for the wrong reason or be unreachable.

### 4.1.6. Reset

**If the halt signal (driven by the hart’s halt request bit in the Debug Module) or hasresethaltreq are asserted when a hart comes out of reset, the hart must enter Debug Mode before**

`MUST` · [Sdext.html#4-1-6-reset](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#4-1-6-reset) · obligation `OB-0C42DDA8`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-003-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-GEN-003-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-GEN-003-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### 4.1.9. Core Debug Registers

**The supported Core Debug Registers must be implemented for each hart that can be debugged.**

`MUST` · [Sdext.html#debreg](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#debreg) · obligation `OB-FC557430`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-004-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-GEN-004-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-GEN-004-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### Privilege Mode (priv, at virtual)

**The user should not access dcsr directly, because doing so might interfere with the debugger.**

`SHOULD_NOT` · [Sdext.html#virt-priv](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#virt-priv) · obligation `OB-091C0ADE`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-005-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

### 4.1.10. Virtual Debug Registers

**Debug software should implement them, but hardware can skip this section.**

`SHOULD` · [Sdext.html#virtreg](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#virtreg) · obligation `OB-82F9818A`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-006-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-GEN-006-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

### 3.1.11. Minimally Intrusive Debugging

**First, an implementation may allow some abstract commands to execute without halting the hart.**

`MAY` · [debug_module.html#3-1-11-minimally-intrusive-debugging](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#3-1-11-minimally-intrusive-debugging) · obligation `OB-0C163BA1`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-007-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-GEN-007-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

### 3.1.3.1. Selecting a Single Hart

**All debug modules must support selecting a single hart.**

`MUST` · [debug_module.html#3-1-3-1-selecting-a-single-hart](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#3-1-3-1-selecting-a-single-hart) · obligation `OB-4A63EC3E`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-008-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-GEN-008-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-GEN-008-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### 3.1. Debug Module (DM) (non-ISA extension)

**When any hart in the group halts, they all halt. (Optional) Respond to external triggers by halting each hart in a configured group. (Optional) Signal an external trigger when a ha**

`MUST` · [debug_module.html#dm](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm) · obligation `OB-881C3791`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-009-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-GEN-009-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-GEN-009-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### Custom Features (custom, at 0x1f)

**This optional register may be used for non-standard features.**

`MAY` · [debug_module.html#dm-custom](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-custom) · obligation `OB-E8964912`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-010-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-GEN-010-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

### Custom Features 0 (custom0, at 0x70)

**The optional custom0 through custom15 registers may be used for non-standard features.**

`MAY` · [debug_module.html#dm-custom0](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-custom0) · obligation `OB-83F72B6A`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-011-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-GEN-011-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

### Abstract Data 0 (data0, at 0x04)

**If the command fails, no assumptions can be made about the contents of these registers.**

`CONDITIONAL` · [debug_module.html#dm-data0](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-data0) · obligation `OB-72E1861A`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-012-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-GEN-012-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-GEN-012-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**data0 through data11 are registers that may be read or changed by abstract commands. datacount indicates how many of them are implemented, starting at data0, counting up.**

`MAY` · [debug_module.html#dm-data0](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-data0) · obligation `OB-B082EA41`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-013-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-GEN-013-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

### Next Debug Module (nextdm, at 0x1d)

**If there is more than one DM accessible on this DMI, this register contains the base address of the next one in the chain, or 0 if this is the last one in the chain.**

`CONDITIONAL` · [debug_module.html#dm-nextdm](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-nextdm) · obligation `OB-F9B0D91E`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-014-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-GEN-014-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-GEN-014-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### Using Abstract Memory Access

**Abstract memory accesses act as if they are performed by the hart, although the actual implementation may differ.**

`MAY` · [debugger_implementation.html#deb:mrabstract](https://docs.riscv.org/reference/debug/v1.0/debugger_implementation.html#deb:mrabstract) · obligation `OB-F0AB699A`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-015-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-GEN-015-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**Abstract memory accesses act as if they are performed by the hart, although the actual implementation may differ.**

`MAY` · [debugger_implementation.html#deb:mwabstract](https://docs.riscv.org/reference/debug/v1.0/debugger_implementation.html#deb:mwabstract) · obligation `OB-49511D4C`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-016-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-GEN-016-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

### Running

**Once allresumeack is set, the debugger knows the selected harts have resumed.**

`CONDITIONAL` · [debugger_implementation.html#running](https://docs.riscv.org/reference/debug/v1.0/debugger_implementation.html#running) · obligation `OB-8DF53D9D`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-017-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-GEN-017-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-GEN-017-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**First, the debugger should restore any registers that it has overwritten.**

`SHOULD` · [debugger_implementation.html#running](https://docs.riscv.org/reference/debug/v1.0/debugger_implementation.html#running) · obligation `OB-EFF04B65`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-018-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-GEN-018-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

### Debug Module Interface Signals

**When this is the case REQ_OP can be set to 1 for a read or 2 for a write request.**

`CONDITIONAL` · [implementations.html#dmi_signals](https://docs.riscv.org/reference/debug/v1.0/implementations.html#dmi_signals) · obligation `OB-2F449452`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-019-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-GEN-019-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-GEN-019-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**The DM must respond to a request from the DTM when RSP_READY is high.**

`MUST` · [implementations.html#dmi_signals](https://docs.riscv.org/reference/debug/v1.0/implementations.html#dmi_signals) · obligation `OB-9EBAAE8B`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-020-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-GEN-020-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-GEN-020-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### 1.1.2.1.3. Minor Changes from 0.13 to 1.0

**Technically backwards incompatible, but unlikely to be noticeable: stopcount only applies to hart-local counters. #405 version may be invalid when dmactive=0. #414 Address triggers**

`SHOULD` · `rtl-unsupported` · [introduction.html#1-1-2-1-3-minor-changes-from-0-13-to-1-0](https://docs.riscv.org/reference/debug/v1.0/introduction.html#1-1-2-1-3-minor-changes-from-0-13-to-1-0) · obligation `OB-7387CD43`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-021-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

> quick_access is absent on this DUT (dut-profile absent[]); the row would pass for the wrong reason or be unreachable.

### 1.1.2.1.4. New Features from 0.13 to 1.0

**See custom, and custom0 through custom15. #406 Reserve trigger type values for non-standard use. #417 Add nmi bit to itrigger. #408 and #709 Recommend matching on every accessed ad**

`MUST` · [introduction.html#1-1-2-1-4-new-features-from-0-13-to-1-0](https://docs.riscv.org/reference/debug/v1.0/introduction.html#1-1-2-1-4-new-features-from-0-13-to-1-0) · obligation `OB-AA3E9B6B`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-022-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-GEN-022-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-GEN-022-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### 1.1.2.1.5. Incompatible Changes During 1.0 Stable

**It may not be possible to read the contents of the Program Buffer using the progbuf registers. #731 tcontrol fields apply to all traps, not just breakpoint traps.**

`MAY` · [introduction.html#1-1-2-1-5-incompatible-changes-during-1-0-stable](https://docs.riscv.org/reference/debug/v1.0/introduction.html#1-1-2-1-5-incompatible-changes-during-1-0-stable) · obligation `OB-FF80860E`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-023-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-GEN-023-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

### 1.1.3.3. Register Definition Format

**Hardware must return 0 when those fields are read, and ignore the value written to them.**

`MUST` · [introduction.html#1-1-3-3-register-definition-format](https://docs.riscv.org/reference/debug/v1.0/introduction.html#1-1-3-3-register-definition-format) · obligation `OB-7695BA34`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-024-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-GEN-024-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-GEN-024-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Software must only write 0 to those fields, and ignore their value while reading.**

`MUST` · [introduction.html#1-1-3-3-register-definition-format](https://docs.riscv.org/reference/debug/v1.0/introduction.html#1-1-3-3-register-definition-format) · obligation `OB-8C432E52`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-025-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-GEN-025-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-GEN-025-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**The reset value is either a constant or "Preset." The latter means it is an implementation-specific legal value.**

`UNSPECIFIED` · [introduction.html#1-1-3-3-register-definition-format](https://docs.riscv.org/reference/debug/v1.0/introduction.html#1-1-3-3-register-definition-format) · obligation `OB-A0A86388`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-026-C` | Check | P3 | 0.10 | Deferred | Not started | 0 | — | 1 | — |

> Spec says UNSPECIFIED -- check the DM does not hang; do not assert a value.

### 1.1. Introduction

**When a design progresses from simulation to hardware implementation, a user’s control and understanding of the system’s current state drops dramatically.**

`CONDITIONAL` · [introduction.html#intro](https://docs.riscv.org/reference/debug/v1.0/introduction.html#intro) · obligation `OB-2BC5A5AF`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-027-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-GEN-027-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-GEN-027-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**System designers may choose to add additional hardware debug support, but this specification defines a standard interface for common functionality.**

`MAY` · [introduction.html#intro](https://docs.riscv.org/reference/debug/v1.0/introduction.html#intro) · obligation `OB-36EEBE64`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-028-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-GEN-028-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**When a robust OS is running on a core, software can handle many debugging tasks.**

`CONDITIONAL` · [introduction.html#intro](https://docs.riscv.org/reference/debug/v1.0/introduction.html#intro) · obligation `OB-5B68FD10`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-GEN-029-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-GEN-029-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-GEN-029-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

## DTM — Debug Transport Module

### 6.1.1.2. JTAG DTM Registers

**JTAG TAPs used as a DTM must have an IR of at least 5 bits.**

`MUST` · [dtm.html#6-1-1-2-jtag-dtm-registers](https://docs.riscv.org/reference/debug/v1.0/dtm.html#6-1-1-2-jtag-dtm-registers) · obligation `OB-0273DDE1`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DTM-001-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DTM-001-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DTM-001-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If the IR actually has more than 5 bits, then the encodings in Table 1 should be extended with 0’s in their most significant bits, except for the 0x1f encoding of BYPASS, which mus**

`MUST` · [dtm.html#6-1-1-2-jtag-dtm-registers](https://docs.riscv.org/reference/debug/v1.0/dtm.html#6-1-1-2-jtag-dtm-registers) · obligation `OB-1AAC7474`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DTM-002-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DTM-002-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DTM-002-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When the TAP is reset, IR must default to 00001, selecting the IDCODE instruction.**

`MUST` · [dtm.html#6-1-1-2-jtag-dtm-registers](https://docs.riscv.org/reference/debug/v1.0/dtm.html#6-1-1-2-jtag-dtm-registers) · obligation `OB-69EADA5F`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DTM-003-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DTM-003-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DTM-003-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Unimplemented instructions must select the BYPASS register.**

`MUST` · [dtm.html#6-1-1-2-jtag-dtm-registers](https://docs.riscv.org/reference/debug/v1.0/dtm.html#6-1-1-2-jtag-dtm-registers) · obligation `OB-C82CFCE2`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DTM-004-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DTM-004-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DTM-004-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### 6.1.1.3.2. Alternate JTAG Connector

**Pins whose functionality isn’t needed may be left unconnected.**

`MAY` · [dtm.html#6-1-1-3-2-alternate-jtag-connector](https://docs.riscv.org/reference/debug/v1.0/dtm.html#6-1-1-3-2-alternate-jtag-connector) · obligation `OB-1A650D65`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DTM-005-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DTM-005-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**This signal should only be used to support legacy components that rely on this functionality. nTRST_PD Test reset pull-down, driven by the debug adapter.**

`SHOULD` · [dtm.html#6-1-1-3-2-alternate-jtag-connector](https://docs.riscv.org/reference/debug/v1.0/dtm.html#6-1-1-3-2-alternate-jtag-connector) · obligation `OB-264C72EE`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DTM-006-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DTM-006-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**This signal should only be used to support legacy components that rely on this functionality.**

`SHOULD` · [dtm.html#6-1-1-3-2-alternate-jtag-connector](https://docs.riscv.org/reference/debug/v1.0/dtm.html#6-1-1-3-2-alternate-jtag-connector) · obligation `OB-30495D6E`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DTM-007-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DTM-007-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**KEY This pin may be cut on the male and plugged on the female header to ensure the header is always plugged in correctly.**

`MAY` · [dtm.html#6-1-1-3-2-alternate-jtag-connector](https://docs.riscv.org/reference/debug/v1.0/dtm.html#6-1-1-3-2-alternate-jtag-connector) · obligation `OB-4EBB9AFF`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DTM-008-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DTM-008-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**A target may relay the TCK signal here once it has processed it, allowing a debugger to adjust its TCK frequency in response.**

`MAY` · [dtm.html#6-1-1-3-2-alternate-jtag-connector](https://docs.riscv.org/reference/debug/v1.0/dtm.html#6-1-1-3-2-alternate-jtag-connector) · obligation `OB-5C7970C0`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DTM-009-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DTM-009-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**Asserting reset should reset any RISC-V cores as well as any other peripherals on the PCB.**

`SHOULD` · [dtm.html#6-1-1-3-2-alternate-jtag-connector](https://docs.riscv.org/reference/debug/v1.0/dtm.html#6-1-1-3-2-alternate-jtag-connector) · obligation `OB-79B338B8`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DTM-010-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DTM-010-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**It should not reset the debug logic.**

`SHOULD_NOT` · [dtm.html#6-1-1-3-2-alternate-jtag-connector](https://docs.riscv.org/reference/debug/v1.0/dtm.html#6-1-1-3-2-alternate-jtag-connector) · obligation `OB-89715BB2`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DTM-011-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**A shrouded connector should be used to prevent the cable from being plugged in incorrectly.**

`SHOULD` · [dtm.html#6-1-1-3-2-alternate-jtag-connector](https://docs.riscv.org/reference/debug/v1.0/dtm.html#6-1-1-3-2-alternate-jtag-connector) · obligation `OB-979715B3`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DTM-012-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DTM-012-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**The MIPI-10 connector should provide plenty of signals for all modern hardware.**

`SHOULD` · [dtm.html#6-1-1-3-2-alternate-jtag-connector](https://docs.riscv.org/reference/debug/v1.0/dtm.html#6-1-1-3-2-alternate-jtag-connector) · obligation `OB-B5A0374F`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DTM-013-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DTM-013-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**This pin is optional but strongly encouraged. nRESET should never be connected to the TAP reset, otherwise the debugger might not be able to debug through a reset to discover the c**

`SHOULD` · [dtm.html#6-1-1-3-2-alternate-jtag-connector](https://docs.riscv.org/reference/debug/v1.0/dtm.html#6-1-1-3-2-alternate-jtag-connector) · obligation `OB-C2D3D7FB`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DTM-014-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DTM-014-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**The signal may be used bi-directional to drive or sense the target reset signal.**

`MAY` · [dtm.html#6-1-1-3-2-alternate-jtag-connector](https://docs.riscv.org/reference/debug/v1.0/dtm.html#6-1-1-3-2-alternate-jtag-connector) · obligation `OB-C9753D1E`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DTM-015-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DTM-015-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**If a design does need legacy JTAG signals, then the MIPI-20 connector should be used.**

`SHOULD` · [dtm.html#6-1-1-3-2-alternate-jtag-connector](https://docs.riscv.org/reference/debug/v1.0/dtm.html#6-1-1-3-2-alternate-jtag-connector) · obligation `OB-D4554185`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DTM-016-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DTM-016-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

### 6.1.1.4. cJTAG

**Pins whose functionality isn’t needed may be left unconnected.**

`MAY` · [dtm.html#6-1-1-4-cjtag](https://docs.riscv.org/reference/debug/v1.0/dtm.html#6-1-1-4-cjtag) · obligation `OB-5153C8AA`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DTM-017-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DTM-017-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**When implementing cJTAG access to a JTAG DTM, the MIPI 10-pin Narrow JTAG connector should be used.**

`SHOULD` · [dtm.html#6-1-1-4-cjtag](https://docs.riscv.org/reference/debug/v1.0/dtm.html#6-1-1-4-cjtag) · obligation `OB-E8221643`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DTM-018-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DTM-018-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

### 6.1. Debug Transport Module (DTM) (non-ISA extension)

**In that case it must be advertised as conforming to "RISC-V Debug Specification, with custom DTM." If the JTAG DTM described here is implemented, it must be advertised as conformin**

`MUST` · [dtm.html#dtm](https://docs.riscv.org/reference/debug/v1.0/dtm.html#dtm) · obligation `OB-1BC5D4F2`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DTM-019-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DTM-019-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DTM-019-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**There may be multiple DTMs in a single hardware platform.**

`MAY` · [dtm.html#dtm](https://docs.riscv.org/reference/debug/v1.0/dtm.html#dtm) · obligation `OB-54813EE5`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DTM-020-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DTM-020-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**Additional DTMs may be added in future versions of this specification.**

`MAY` · [dtm.html#dtm](https://docs.riscv.org/reference/debug/v1.0/dtm.html#dtm) · obligation `OB-772A3799`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DTM-021-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DTM-021-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

### DTM Control and Status (dtmcs, at 0x10)

**In general this should only be used when the Debugger has reason to expect that the outstanding DMI transaction will never complete (e.g. a reset condition caused an inflight DMI t**

`SHOULD` · [dtm.html#dtm-dtmcs](https://docs.riscv.org/reference/debug/v1.0/dtm.html#dtm-dtmcs) · obligation `OB-05D1BDB8`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DTM-022-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DTM-022-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**A debugger must still check dmistat when necessary. 0: It is not necessary to enter Run-Test/Idle at all. 1: Enter Run-Test/Idle and leave it immediately. 2: Enter Run-Test/Idle an**

`MUST` · [dtm.html#dtm-dtmcs](https://docs.riscv.org/reference/debug/v1.0/dtm.html#dtm-dtmcs) · obligation `OB-4EFDFF24`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DTM-023-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DTM-023-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DTM-023-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**W1 - idle This is a hint to the debugger of the minimum number of cycles a debugger should spend in Run-Test/Idle after every DMI scan to avoid a `busy' return code (dmistat of 3).**

`SHOULD` · [dtm.html#dtm-dtmcs](https://docs.riscv.org/reference/debug/v1.0/dtm.html#dtm-dtmcs) · obligation `OB-DE3C95F0`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DTM-024-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DTM-024-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**Field Description Access Reset errinfo This optional field may provide additional detail about an error that occurred when communicating with a DM.**

`MAY` · [dtm.html#dtm-dtmcs](https://docs.riscv.org/reference/debug/v1.0/dtm.html#dtm-dtmcs) · obligation `OB-DFC7E0AC`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DTM-025-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DTM-025-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

### IDCODE (at 0x01)

**Bits 6:0 must be bits 6:0 of the designer/manufacturer’s Identification Code as assigned by JEDEC Standard JEP106.**

`MUST` · [dtm.html#dtm-idcode](https://docs.riscv.org/reference/debug/v1.0/dtm.html#dtm-idcode) · obligation `OB-BD58176C`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DTM-026-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DTM-026-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DTM-026-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

## DIS — Discovery & version detection

### 3.1.13. Version Detection

**If it was necessary to clear ndmreset, this might have the following side effects: haltreq is cleared, potentially preventing a halt request made by a previous debugger from taking**

`CONDITIONAL` · [debug_module.html#3-1-13-version-detection](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#3-1-13-version-detection) · obligation `OB-3A5A1CDE`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DIS-001-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DIS-001-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DIS-001-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If dmactive is 0 or ndmreset is 1: Write dmcontrol, preserving hartreset, hasel, hartsello, and hartselhi from the value that was read, setting dmactive, and clearing all the other**

`CONDITIONAL` · `rtl-unsupported` · [debug_module.html#3-1-13-version-detection](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#3-1-13-version-detection) · obligation `OB-DD957B93`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DIS-002-C` | Cover | P3 | 0.25 | Deferred | Not started | 0 | — | 2 | — |

> hart_array is absent on this DUT (dut-profile absent[]); the row would pass for the wrong reason or be unreachable.

### Configuration Structure Pointer 0 (confstrptr0, at 0x19)

**Otherwise, this must be an address that can be used to access the configuration structure from the hart with ID 0.**

`MUST` · [debug_module.html#dm-confstrptr0](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-confstrptr0) · obligation `OB-934D84D3`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DIS-003-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DIS-003-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DIS-003-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When confstrptrvalid is set, reading this register returns bits 31:0 of the configuration structure pointer.**

`CONDITIONAL` · [debug_module.html#dm-confstrptr0](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-confstrptr0) · obligation `OB-99F62644`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DIS-004-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DIS-004-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DIS-004-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If confstrptrvalid is 0, then the confstrptr registers hold identifier information which is not further specified in this document.**

`CONDITIONAL` · [debug_module.html#dm-confstrptr0](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-confstrptr0) · obligation `OB-A7559BE4`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DIS-005-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DIS-005-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DIS-005-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When system bus access is implemented, this must be an address that can be used with the System Bus Access module.**

`MUST` · [debug_module.html#dm-confstrptr0](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-confstrptr0) · obligation `OB-F4F62B81`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DIS-006-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DIS-006-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DIS-006-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### Configuration Structure Pointer 1 (confstrptr1, at 0x1a)

**When confstrptrvalid is set, reading this register returns bits 63:32 of the configuration structure pointer.**

`CONDITIONAL` · [debug_module.html#dm-confstrptr1](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-confstrptr1) · obligation `OB-0BE457D5`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DIS-007-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DIS-007-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DIS-007-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### Configuration Structure Pointer 2 (confstrptr2, at 0x1b)

**When confstrptrvalid is set, reading this register returns bits 95:64 of the configuration structure pointer.**

`CONDITIONAL` · [debug_module.html#dm-confstrptr2](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-confstrptr2) · obligation `OB-5A152AE4`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DIS-008-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DIS-008-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DIS-008-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### Configuration Structure Pointer 3 (confstrptr3, at 0x1c)

**When confstrptrvalid is set, reading this register returns bits 127:96 of the configuration structure pointer.**

`CONDITIONAL` · [debug_module.html#dm-confstrptr3](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-confstrptr3) · obligation `OB-1666B3BD`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DIS-009-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DIS-009-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DIS-009-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### Debug Module Status (dmstatus, at 0x11)

**Accessing authdata results in unspecified behavior. authbusy only becomes set in immediate response to an access to authdata.**

`UNSPECIFIED` · [debug_module.html#dm-dmstatus](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmstatus) · obligation `OB-66712737`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DIS-010-C` | Check | P3 | 0.10 | Deferred | Not started | 0 | — | 1 | — |

> Spec says UNSPECIFIED -- check the DM does not hang; do not assert a value.

**This must be 1 when progbufsize is 1.**

`MUST` · [debug_module.html#dm-dmstatus](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmstatus) · obligation `OB-BC2186F3`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DIS-011-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DIS-011-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DIS-011-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Once they are set, they will not clear until the debugger acknowledges them using ackunavail.**

`CONDITIONAL` · [debug_module.html#dm-dmstatus](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmstatus) · obligation `OB-D6A08D5A`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DIS-012-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DIS-012-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DIS-012-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**On components that don’t implement authentication, this bit must be preset as 1.**

`MUST` · [debug_module.html#dm-dmstatus](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-dmstatus) · obligation `OB-D9BC6E5C`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DIS-013-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DIS-013-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DIS-013-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### Hart Info (hartinfo, at 0x12)

**If this register is included, the debugger can do more with the Program Buffer by writing programs which explicitly access the data and/or dscratch registers.**

`CONDITIONAL` · [debug_module.html#dm-hartinfo](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-hartinfo) · obligation `OB-32A61DFD`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DIS-014-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DIS-014-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DIS-014-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If dataaccess is 1: Address of RAM where the data registers are shadowed.**

`CONDITIONAL` · [debug_module.html#dm-hartinfo](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-hartinfo) · obligation `OB-713A614B`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DIS-015-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DIS-015-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DIS-015-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If it is not present it should read all-zero.**

`SHOULD` · [debug_module.html#dm-hartinfo](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-hartinfo) · obligation `OB-9A89C487`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DIS-016-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DIS-016-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**Since there are at most 12 data registers, the value in this register must be 12 or smaller.**

`MUST` · [debug_module.html#dm-hartinfo](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-hartinfo) · obligation `OB-C432B15B`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DIS-017-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DIS-017-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DIS-017-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If dataaccess is 1: Number of 32-bit words in the memory map dedicated to shadowing the data registers.**

`CONDITIONAL` · [debug_module.html#dm-hartinfo](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-hartinfo) · obligation `OB-FAECE020`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DIS-018-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DIS-018-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DIS-018-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

## SSTEP — Single-step

### 4.1.5.1. Step Bit In Dcsr

**If control is transferred to a trap handler while executing the instruction, then Debug Mode is re-entered immediately after the PC is changed to the trap handler, and the appropri**

`CONDITIONAL` · [Sdext.html#stepbit](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#stepbit) · obligation `OB-21432296`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SSTEP-001-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SSTEP-001-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SSTEP-001-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If executing or fetching the instruction causes a trigger to fire with action=1, Debug Mode is re-entered immediately after that trigger has fired.**

`CONDITIONAL` · [Sdext.html#stepbit](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#stepbit) · obligation `OB-458FEB4A`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SSTEP-002-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SSTEP-002-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SSTEP-002-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If the instruction that is executed causes the PC to change to an address where an instruction fetch causes an exception, that exception does not occur until the next time the hart**

`CONDITIONAL` · [Sdext.html#stepbit](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#stepbit) · obligation `OB-84D439AC`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SSTEP-003-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SSTEP-003-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SSTEP-003-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If the instruction being stepped over would normally stall the hart, then instead the instruction is treated as a nop.**

`CONDITIONAL` · [Sdext.html#stepbit](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#stepbit) · obligation `OB-8D727FC3`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SSTEP-004-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SSTEP-004-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SSTEP-004-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If step is set when a hart resumes then it will single step, regardless of the reason for resuming.**

`CONDITIONAL` · [Sdext.html#stepbit](https://docs.riscv.org/reference/debug/v1.0/Sdext.html#stepbit) · obligation `OB-94557B58`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SSTEP-005-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SSTEP-005-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SSTEP-005-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### Single Step

**To help users out, debuggers should detect when a single step restarted an instruction, and then step again.**

`SHOULD` · [debugger_implementation.html#nativestep](https://docs.riscv.org/reference/debug/v1.0/debugger_implementation.html#nativestep) · obligation `OB-1C54EC01`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SSTEP-006-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SSTEP-006-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**If neither of these features exist, then single step is doable, but tricky to get right.**

`CONDITIONAL` · [debugger_implementation.html#nativestep](https://docs.riscv.org/reference/debug/v1.0/debugger_implementation.html#nativestep) · obligation `OB-2BBF0054`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SSTEP-007-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SSTEP-007-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SSTEP-007-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**The debugger should perform this extra step when the PC doesn’t change during a regular step.**

`SHOULD` · [debugger_implementation.html#nativestep](https://docs.riscv.org/reference/debug/v1.0/debugger_implementation.html#nativestep) · obligation `OB-333EB526`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SSTEP-008-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SSTEP-008-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**An instruction may cause an exception into a more privileged mode where the trigger is not enabled.**

`MAY` · [debugger_implementation.html#nativestep](https://docs.riscv.org/reference/debug/v1.0/debugger_implementation.html#nativestep) · obligation `OB-687501FB`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SSTEP-009-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SSTEP-009-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**If hardware implements mpte and mte, then stepping through non-trap code which doesn’t allow for nested interrupts is also straightforward.**

`CONDITIONAL` · [debugger_implementation.html#nativestep](https://docs.riscv.org/reference/debug/v1.0/debugger_implementation.html#nativestep) · obligation `OB-90E3569C`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SSTEP-010-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SSTEP-010-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SSTEP-010-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If hardware automatically prevents action=0 triggers from matching when entering a trap handler as described in Sdtrig.adoc#nativetrigger, then a carefully written trap handler can**

`MUST_NOT` · [debugger_implementation.html#nativestep](https://docs.riscv.org/reference/debug/v1.0/debugger_implementation.html#nativestep) · obligation `OB-93B92434`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SSTEP-011-C` | Check | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SSTEP-011-C` | Cover | P2 | 0.10 | Full | Not started | 0 | — | 2 | — |

**To avoid an infinite loop if the exception handler does not address the cause of the exception, the debugger must execute no more than a single extra step.**

`MUST` · [debugger_implementation.html#nativestep](https://docs.riscv.org/reference/debug/v1.0/debugger_implementation.html#nativestep) · obligation `OB-BC4993CF`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SSTEP-012-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SSTEP-012-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SSTEP-012-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When a user is single stepping through such code, they will have to step twice to get past the restarted instruction.**

`CONDITIONAL` · [debugger_implementation.html#nativestep](https://docs.riscv.org/reference/debug/v1.0/debugger_implementation.html#nativestep) · obligation `OB-DFAFCCCE`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SSTEP-013-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SSTEP-013-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SSTEP-013-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When a step is required, the OS or debug stub writes count=1, action=0, m=0 before returning control to the lower user program with an mret instruction.**

`CONDITIONAL` · [debugger_implementation.html#nativestep](https://docs.riscv.org/reference/debug/v1.0/debugger_implementation.html#nativestep) · obligation `OB-E2067229`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SSTEP-014-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-SSTEP-014-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SSTEP-014-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**The hart behaves exactly as in the running case, except that interrupts may be disabled (depending on stepie) and it only fetches and executes a single instruction before re-enteri**

`MAY` · [debugger_implementation.html#single-step](https://docs.riscv.org/reference/debug/v1.0/debugger_implementation.html#single-step) · obligation `OB-235FC342`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-SSTEP-015-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-SSTEP-015-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

## DMI — DMI protocol

### 3.1.1. Debug Module Interface (DMI)

**If there are additional DMs on this DMI, the base address of the next DM in the DMI address space is given in nextdm.**

`CONDITIONAL` · [debug_module.html#dmi](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dmi) · obligation `OB-44B48B91`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DMI-001-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DMI-001-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DMI-001-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### Debug Module Interface Access

**This process must be repeated until op returns 0.**

`MUST` · [debugger_implementation.html#dmiaccess](https://docs.riscv.org/reference/debug/v1.0/debugger_implementation.html#dmiaccess) · obligation `OB-173862A8`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DMI-002-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DMI-002-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DMI-002-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**It should almost never be necessary to scan IR, avoiding a big part of the inefficiency in typical JTAG use.**

`SHOULD` · [debugger_implementation.html#dmiaccess](https://docs.riscv.org/reference/debug/v1.0/debugger_implementation.html#dmiaccess) · obligation `OB-40E5C5BF`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DMI-003-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DMI-003-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**The busy condition must be cleared by writing dmireset in dtmcs, and then the second scan scan must be performed again.**

`MUST` · [debugger_implementation.html#dmiaccess](https://docs.riscv.org/reference/debug/v1.0/debugger_implementation.html#dmiaccess) · obligation `OB-69E787E6`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DMI-004-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DMI-004-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DMI-004-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**In later operations the debugger should allow for more time between Update-DR and Capture-DR.**

`SHOULD` · [debugger_implementation.html#dmiaccess](https://docs.riscv.org/reference/debug/v1.0/debugger_implementation.html#dmiaccess) · obligation `OB-7AECBFE5`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DMI-005-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DMI-005-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**If the operation didn’t complete in time, op will be 3 and the value in data must be ignored.**

`MUST` · [debugger_implementation.html#dmiaccess](https://docs.riscv.org/reference/debug/v1.0/debugger_implementation.html#dmiaccess) · obligation `OB-DB14A7D2`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DMI-006-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DMI-006-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DMI-006-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### Debug Module Interface Access (dmi, at 0x11)

**This operation leaves the values in address and data UNSPECIFIED. 1 (read): Read from address.**

`UNSPECIFIED` · [dtm.html#dtm-dmi](https://docs.riscv.org/reference/debug/v1.0/dtm.html#dtm-dmi) · obligation `OB-0C7BEBF9`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DMI-007-C` | Check | P3 | 0.10 | Deferred | Not started | 0 | — | 1 | — |

> Spec says UNSPECIFIED -- check the DM does not hang; do not assert a value.

**When this operation succeeds, address contains the address that was read from, and data contains the value that was read. 2 (write): Write data to address.**

`CONDITIONAL` · [dtm.html#dtm-dmi](https://docs.riscv.org/reference/debug/v1.0/dtm.html#dtm-dmi) · obligation `OB-1853C145`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DMI-008-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DMI-008-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DMI-008-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**The still-in-progress status is sticky to accommodate debuggers that batch together a number of scans, which must all be executed or stop as soon as there’s a problem.**

`MUST` · [dtm.html#dtm-dmi](https://docs.riscv.org/reference/debug/v1.0/dtm.html#dtm-dmi) · obligation `OB-2F8D0289`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DMI-009-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DMI-009-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DMI-009-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If a debugger sees this status, it needs to give the target more TCK edges between Update-DR and Capture-DR.**

`CONDITIONAL` · [dtm.html#dtm-dmi](https://docs.riscv.org/reference/debug/v1.0/dtm.html#dtm-dmi) · obligation `OB-3CE8C55D`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DMI-010-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DMI-010-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DMI-010-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If a debugger sees this status, there might be additional information in errinfo. 3 (busy): A DMI operation was attempted while a prior DMI operation was still in progress.**

`CONDITIONAL` · [dtm.html#dtm-dmi](https://docs.riscv.org/reference/debug/v1.0/dtm.html#dtm-dmi) · obligation `OB-4D7C060E`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DMI-011-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DMI-011-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DMI-011-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When the debugger reads this field, it means the following: 0 (success): The previous operation completed successfully. 1 (reserved): Reserved. 2 (failed): A previous operation fai**

`CONDITIONAL` · [dtm.html#dtm-dmi](https://docs.riscv.org/reference/debug/v1.0/dtm.html#dtm-dmi) · obligation `OB-713437CA`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DMI-012-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-DMI-012-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DMI-012-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**This operation leaves the values in address and data UNSPECIFIED. 3 (reserved): Reserved.**

`UNSPECIFIED` · [dtm.html#dtm-dmi](https://docs.riscv.org/reference/debug/v1.0/dtm.html#dtm-dmi) · obligation `OB-765F059B`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DMI-013-C` | Check | P3 | 0.10 | Deferred | Not started | 0 | — | 1 | — |

> Spec says UNSPECIFIED -- check the DM does not hang; do not assert a value.

**For instance a series of scans may write a Debug Program and execute it.**

`MAY` · [dtm.html#dtm-dmi](https://docs.riscv.org/reference/debug/v1.0/dtm.html#dtm-dmi) · obligation `OB-895941E6`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DMI-014-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DMI-014-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**If one of the writes fails but the execution continues, then the Debug Program may hang or have other unexpected side effects.**

`MAY` · [dtm.html#dtm-dmi](https://docs.riscv.org/reference/debug/v1.0/dtm.html#dtm-dmi) · obligation `OB-AA0F5B7A`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DMI-015-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DMI-015-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**The address and data reported in the following Capture-DR are undefined.**

`UNSPECIFIED` · [dtm.html#dtm-dmi](https://docs.riscv.org/reference/debug/v1.0/dtm.html#dtm-dmi) · obligation `OB-AEDFF545`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DMI-016-C` | Check | P3 | 0.10 | Deferred | Not started | 0 | — | 1 | — |

> Spec says UNSPECIFIED -- check the DM does not hang; do not assert a value.

**This operation should never affect DMI busy or error status.**

`SHOULD` · [dtm.html#dtm-dmi](https://docs.riscv.org/reference/debug/v1.0/dtm.html#dtm-dmi) · obligation `OB-DE0342C3`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-DMI-017-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-DMI-017-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

## HG — Halt / resume groups

### External Trigger (tmexttrigger, at 0x7a1)

**Hardware may support none or just a few TM external trigger inputs (starting with TM external trigger input 0 and continuing sequentially).**

`MAY` · [Sdtrig.html#csr-tmexttrigger](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-tmexttrigger) · obligation `OB-75E8DBC5`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-HG-001-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-HG-001-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**An implementation may either ignore the signal altogether when it cannot fire (dropping the trigger event) or it may hold the action as pending and fire the trigger once it is lega**

`MAY` · [Sdtrig.html#csr-tmexttrigger](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-tmexttrigger) · obligation `OB-8BBB0165`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-HG-002-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-HG-002-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**If the trigger fires with action=0 then zero is written to the tval CSR on the breakpoint trap.**

`CONDITIONAL` · [Sdtrig.html#csr-tmexttrigger](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-tmexttrigger) · obligation `OB-C7DF8E9B`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-HG-003-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-HG-003-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-HG-003-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If the bit is not implemented, it is always 0 and writing it has no effect.**

`CONDITIONAL` · [Sdtrig.html#csr-tmexttrigger](https://docs.riscv.org/reference/debug/v1.0/Sdtrig.html#csr-tmexttrigger) · obligation `OB-FD764B83`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-HG-004-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-HG-004-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-HG-004-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### 3.1.6. Halt Groups, Resume Groups, and External Triggers

**When an external trigger that’s a member of the resume group fires: All the harts in that group that are halted will quickly resume as soon as any currently executing abstract comm**

`CONDITIONAL` · [debug_module.html#hrgroups](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#hrgroups) · obligation `OB-0EEA3282`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-HG-005-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-HG-005-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-HG-005-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When any hart in a resume group resumes: All the other harts in that group that are halted will quickly resume as soon as any currently executing abstract commands have completed.**

`CONDITIONAL` · [debug_module.html#hrgroups](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#hrgroups) · obligation `OB-2C7135A4`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-HG-006-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-HG-006-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-HG-006-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When the DM is reset, all harts must be placed in the lowest-numbered halt and resume groups that they can be in. (This will usually be group 0.) Some designs may choose to hardcod**

`MUST` · [debug_module.html#hrgroups](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#hrgroups) · obligation `OB-2D73E1EE`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-HG-007-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-HG-007-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-HG-007-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When an external trigger that’s a member of the halt group fires: All the harts in the halt group that are running will quickly halt. cause for those harts should be set to 6, but**

`SHOULD` · [debug_module.html#hrgroups](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#hrgroups) · obligation `OB-6FE51F06`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-HG-008-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-HG-008-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**All the other harts in the halt group that are running will quickly halt. cause for those harts should be set to 6, but may be set to 3.**

`SHOULD` · [debug_module.html#hrgroups](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#hrgroups) · obligation `OB-AE674FDB`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-HG-009-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-HG-009-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**Other harts in the halt group that are halted but have started the process of resuming must also quickly become halted, even if they do resume briefly.**

`MUST` · [debug_module.html#hrgroups](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#hrgroups) · obligation `OB-B8D6518D`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-HG-010-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-HG-010-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-HG-010-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |
| `TC-HG-011-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-HG-011-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-HG-011-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When any hart in a halt group halts: That hart halts normally, with cause reflecting the original cause of the halt.**

`CONDITIONAL` · [debug_module.html#hrgroups](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#hrgroups) · obligation `OB-BB0D78DF`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-HG-012-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-HG-012-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-HG-012-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Harts that are in the process of halting should complete that process and stay halted.**

`SHOULD` · [debug_module.html#hrgroups](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#hrgroups) · obligation `OB-BB705A10`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-HG-013-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-HG-013-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-HG-014-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-HG-014-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**In that case it must be possible to discover the groups by using dmcs2 even if it’s not possible to change the configuration.**

`MUST` · [debug_module.html#hrgroups](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#hrgroups) · obligation `OB-F85DDCA8`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-HG-015-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-HG-015-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-HG-015-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

## PB — Program Buffer

### Program Buffer 0 (progbuf0, at 0x20)

**It may also be possible for the debugger to read from the program buffer through these registers.**

`MAY` · [debug_module.html#dm-progbuf0](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-progbuf0) · obligation `OB-3BB9820E`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-PB-001-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-PB-001-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**progbuf0 through progbuf15 must provide write access to the optional program buffer.**

`MUST` · [debug_module.html#dm-progbuf0](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-progbuf0) · obligation `OB-78D05CBF`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-PB-002-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-PB-002-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-PB-002-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If reading is not supported, then all reads return 0. progbufsize indicates how many progbuf registers are implemented starting at progbuf0, counting up.**

`CONDITIONAL` · [debug_module.html#dm-progbuf0](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-progbuf0) · obligation `OB-96A4A892`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-PB-003-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-PB-003-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-PB-003-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### 3.1.8. Program Buffer

**If the debugger executes a program that doesn’t terminate with an ebreak instruction, the hart will remain in Debug Mode and the debugger will lose control of the hart.**

`CONDITIONAL` · [debug_module.html#programbuffer](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#programbuffer) · obligation `OB-05B47EDA`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-PB-004-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-PB-004-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-PB-004-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**DMs that support all necessary functionality using abstract commands only may choose to omit the Program Buffer.**

`MAY` · [debug_module.html#programbuffer](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#programbuffer) · obligation `OB-107E0AB3`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-PB-005-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-PB-005-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**If the debugger writes a compressed instruction into the Program Buffer, it must be placed into the lower 16 bits and accompanied by a compressed nop in the upper 16 bits.**

`MUST` · [debug_module.html#programbuffer](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#programbuffer) · obligation `OB-46F168A6`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-PB-006-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-PB-006-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-PB-006-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If an exception is encountered during execution of the Program Buffer, no more instructions are executed, the hart remains in Debug Mode, and cmderr is set to 3 (exception error).**

`CONDITIONAL` · [debug_module.html#programbuffer](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#programbuffer) · obligation `OB-6F0BB28B`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-PB-007-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-PB-007-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-PB-007-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**An implementation may support an implicit ebreak that is executed when a hart runs off the end of the Program Buffer.**

`MAY` · [debug_module.html#programbuffer](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#programbuffer) · obligation `OB-8C5B1904`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-PB-008-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-PB-008-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**The Program Buffer may be implemented as RAM which is accessible to the hart.**

`MAY` · [debug_module.html#programbuffer](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#programbuffer) · obligation `OB-9074ADA2`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-PB-009-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-PB-009-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**If so, the debugger has more flexibility in what it can do with the program buffer.**

`CONDITIONAL` · [debug_module.html#programbuffer](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#programbuffer) · obligation `OB-954248D0`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-PB-010-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-PB-010-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-PB-010-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**While these programs are executed, the hart does not leave Debug Mode (see Sdext.adoc#debugmode).**

`CONDITIONAL` · [debug_module.html#programbuffer](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#programbuffer) · obligation `OB-9D5EA091`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-PB-011-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-PB-011-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-PB-011-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If progbufsize is 1 then the following apply: impebreak must be 1.**

`MUST` · [debug_module.html#programbuffer](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#programbuffer) · obligation `OB-BE895C5E`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-PB-012-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-PB-012-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-PB-012-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**The debugger can write whatever program it likes (including jumps out of the Program Buffer), but the program must end with ebreak or c.ebreak.**

`MUST` · [debug_module.html#programbuffer](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#programbuffer) · obligation `OB-FBD55F90`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-PB-013-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-PB-013-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-PB-013-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

## RST — Reset control

### 3.1.2. Reset Control

**While ndmreset or any external reset is asserted, the only supported DM operations are reading/writing dmcontrol and reading ndmresetpending.**

`CONDITIONAL` · [debug_module.html#reset](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#reset) · obligation `OB-02126F63`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RST-001-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-RST-001-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RST-001-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If there is another mechanism to reset the DM, this mechanism must also reset all the harts accessible to the DM.**

`MUST` · [debug_module.html#reset](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#reset) · obligation `OB-376EA57A`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RST-002-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-RST-002-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RST-002-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**While the reset is on-going, harts are either in the running state, indicating it’s possible to perform some abstract commands during this time, or in the unavailable state, indica**

`CONDITIONAL` · [debug_module.html#reset](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#reset) · obligation `OB-4E491BF3`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RST-003-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-RST-003-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RST-003-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**The Debug Module’s own state and registers should only be reset at power-up and while dmactive in dmcontrol is 0.**

`SHOULD` · [debug_module.html#reset](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#reset) · obligation `OB-512F79E4`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RST-004-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RST-004-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**The reset itself may also take an arbitrarily long time.**

`MAY` · [debug_module.html#reset](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#reset) · obligation `OB-55353F21`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RST-005-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RST-005-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**Once a hart’s reset is complete, havereset becomes set.**

`CONDITIONAL` · [debug_module.html#reset](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#reset) · obligation `OB-6E938BEE`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RST-006-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-RST-006-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RST-006-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Otherwise, if the hart was initially running it will execute normally (running state) and if the hart was initially halted it should now be running but may be halted.**

`SHOULD` · [debug_module.html#reset](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#reset) · obligation `OB-891C5A28`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RST-007-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RST-007-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**When a hart comes out of reset and haltreq or resethaltreq are set, the hart will immediately enter Debug Mode (halted state).**

`CONDITIONAL` · [debug_module.html#reset](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#reset) · obligation `OB-927ACB75`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RST-008-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-RST-008-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RST-008-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**The behavior of other accesses is undefined.**

`UNSPECIFIED` · [debug_module.html#reset](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#reset) · obligation `OB-B3B5EA02`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RST-009-C` | Check | P3 | 0.10 | Deferred | Not started | 0 | — | 1 | — |

> Spec says UNSPECIFIED -- check the DM does not hang; do not assert a value.

**Exactly what is affected by this reset is implementation dependent, but it must be possible to debug programs from the first instruction executed. hartreset resets all the currentl**

`MUST` · [debug_module.html#reset](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#reset) · obligation `OB-B845B423`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RST-010-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-RST-010-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RST-010-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**When harts have been reset, they must set a sticky havereset state bit.**

`MUST` · [debug_module.html#reset](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#reset) · obligation `OB-B8A26943`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RST-011-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-RST-011-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RST-011-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**These bits must be set regardless of the cause of the reset.**

`MUST` · [debug_module.html#reset](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#reset) · obligation `OB-C5923002`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RST-012-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-RST-012-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RST-012-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**The actual reset may start as soon as the bit is asserted, but may start an arbitrarily long time after the bit is deasserted.**

`MAY` · [debug_module.html#reset](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#reset) · obligation `OB-C860E223`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RST-013-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RST-013-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**In this case an implementation may reset more harts than just the ones that are selected.**

`MAY` · [debug_module.html#reset](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#reset) · obligation `OB-FF62EF3E`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-RST-014-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-RST-014-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

## HS — Hart selection & states

### 3.1.4. Hart DM States

**In order to let the debugger discover all harts, they must show up as unavailable even if there is no chance of them ever becoming available.**

`MUST` · [debug_module.html#3-1-4-hart-dm-states](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#3-1-4-hart-dm-states) · obligation `OB-2CC037E5`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-HS-001-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-HS-001-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-HS-001-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**Debuggers may assume that a hardware platform has no harts with indexes higher than the first nonexistent one.**

`MAY` · [debug_module.html#3-1-4-hart-dm-states](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#3-1-4-hart-dm-states) · obligation `OB-6D10A122`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-HS-002-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-HS-002-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**Hardware platforms with very large number of harts may permanently disable some during manufacturing, leaving holes in the otherwise continuous hart index space.**

`MAY` · [debug_module.html#3-1-4-hart-dm-states](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#3-1-4-hart-dm-states) · obligation `OB-8F42D686`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-HS-003-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-HS-003-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**Harts may be unavailable for a variety of reasons including being reset, temporarily powered down, and not being plugged into the hardware platform.**

`MAY` · [debug_module.html#3-1-4-hart-dm-states](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#3-1-4-hart-dm-states) · obligation `OB-AAB99703`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-HS-004-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-HS-004-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**Harts may be unavailable while reset is asserted, and some time after reset is deasserted.**

`MAY` · [debug_module.html#3-1-4-hart-dm-states](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#3-1-4-hart-dm-states) · obligation `OB-CE92313B`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-HS-005-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-HS-005-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**That means harts might become available or unavailable at any time, although these events should be rare in hardware platforms built to be easily debugged.**

`SHOULD` · [debug_module.html#3-1-4-hart-dm-states](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#3-1-4-hart-dm-states) · obligation `OB-D166808B`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-HS-006-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-HS-006-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

### Hart Array Window (hawindow, at 0x15)

**Since some bits in the hart array mask register may be constant 0, some bits in this register may be constant 0, depending on the current value of hawindowsel.**

`MAY` · `rtl-unsupported` · [debug_module.html#dm-hawindow](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-hawindow) · obligation `OB-135336B9`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-HS-007-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

> hart_array is absent on this DUT (dut-profile absent[]); the row would pass for the wrong reason or be unreachable.

### Hart Array Window Select (hawindowsel, at 0x14)

**Field Description Access Reset hawindowsel The high bits of this field may be tied to 0, depending on how large the array mask register is.**

`MAY` · `rtl-unsupported` · [debug_module.html#dm-hawindowsel](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-hawindowsel) · obligation `OB-25C68870`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-HS-008-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

> hart_array is absent on this DUT (dut-profile absent[]); the row would pass for the wrong reason or be unreachable.

**E.g. on a hardware platform with 48 harts only bit 0 of this field may actually be writable.**

`MAY` · `rtl-unsupported` · [debug_module.html#dm-hawindowsel](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-hawindowsel) · obligation `OB-98C38078`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-HS-009-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

> hart_array is absent on this DUT (dut-profile absent[]); the row would pass for the wrong reason or be unreachable.

### 3.1.3.2. Selecting Multiple Harts

**Debug Modules may implement a Hart Array Mask register to allow selecting multiple harts at once.**

`MAY` · `rtl-unsupported` · [debug_module.html#hartarraymask](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#hartarraymask) · obligation `OB-6969F74F`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-HS-010-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

> hart_array is absent on this DUT (dut-profile absent[]); the row would pass for the wrong reason or be unreachable.

**If this feature is supported, multiple harts can be halted, resumed, and reset simultaneously.**

`CONDITIONAL` · [debug_module.html#hartarraymask](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#hartarraymask) · obligation `OB-76553A0D`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-HS-011-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-HS-011-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-HS-011-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

**If the bit is 1 then the hart is selected.**

`CONDITIONAL` · [debug_module.html#hartarraymask](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#hartarraymask) · obligation `OB-A28E8B3F`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-HS-012-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-HS-012-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-HS-012-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

### 3.1.3. Selecting Harts

**To enumerate all the harts, a debugger must first determine HARTSELLEN by writing all ones to `hartsel` (assuming the maximum size) and reading back the value to see which bits wer**

`MUST` · [debug_module.html#selectingharts](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#selectingharts) · obligation `OB-71273439`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-HS-013-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-HS-013-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-HS-013-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

## AUTH — Authentication

### 3.1.12. Security

**All DM registers should read 0, while writes should be ignored, with the following mandatory exceptions: authenticated in dmstatus is readable. authbusy in dmstatus is readable. ve**

`SHOULD` · [debug_module.html#3-1-12-security](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#3-1-12-security) · obligation `OB-41CC6045`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AUTH-001-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AUTH-001-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

**When authenticated is clear, the DM must not interact with the rest of the hardware platform, nor expose details about the harts connected to the DM.**

`MUST_NOT` · [debug_module.html#3-1-12-security](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#3-1-12-security) · obligation `OB-4463B604`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AUTH-002-C` | Check | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AUTH-002-C` | Cover | P2 | 0.10 | Full | Not started | 0 | — | 2 | — |

**To protect intellectual property it may be desirable to lock access to the Debug Module.**

`MAY` · [debug_module.html#3-1-12-security](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#3-1-12-security) · obligation `OB-A398E5DE`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AUTH-003-S` | Stimulate | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AUTH-003-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

**Implementations where it’s not possible to unlock the DM by using authdata should not implement that register.**

`SHOULD_NOT` · [debug_module.html#3-1-12-security](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#3-1-12-security) · obligation `OB-E4BE0A83`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AUTH-004-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |

### Authentication Data (authdata, at 0x30)

**When authbusy is clear, the debugger can communicate with the authentication module by reading or writing this register.**

`CONDITIONAL` · [debug_module.html#dm-authdata](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#dm-authdata) · obligation `OB-82610EE4`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AUTH-005-S` | Stimulate | P1 | 0.10 | Main | Not started | 0 | — | 1 | — |
| `TC-AUTH-005-C` | Check | P2 | 0.10 | Full | Not started | 0 | — | 1 | — |
| `TC-AUTH-005-C` | Cover | P2 | 0.25 | Full | Not started | 0 | — | 2 | — |

## AM — Abstract memory access

### Access Memory

**An implementation may detect an upcoming failure early, and fail the overall command before it reaches the step that would cause failure.**

`MAY` · `rtl-unsupported` · [debug_module.html#ac-accessmemory](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-accessmemory) · obligation `OB-1A54AF66`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AM-001-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

> abstract_access_memory is absent on this DUT (dut-profile absent[]); the row would pass for the wrong reason or be unreachable.

**If this command supports memory accesses while the hart is running, it must also support memory accesses while the hart is halted.**

`MUST` · `rtl-unsupported` · [debug_module.html#ac-accessmemory](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-accessmemory) · obligation `OB-88FF7056`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AM-002-C` | Cover | P3 | 0.25 | Deferred | Not started | 0 | — | 2 | — |

> abstract_access_memory is absent on this DUT (dut-profile absent[]); the row would pass for the wrong reason or be unreachable.

**An access may only fail if the hart, running M-mode code, might encounter that same failure when it attempts the same access.**

`MAY` · `rtl-unsupported` · [debug_module.html#ac-accessmemory](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-accessmemory) · obligation `OB-93CCD089`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AM-003-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

> abstract_access_memory is absent on this DUT (dut-profile absent[]); the row would pass for the wrong reason or be unreachable.

**Debug Modules may optionally implement this command and may support read and write access to memory locations when the selected hart is running or halted.**

`MAY` · `rtl-unsupported` · [debug_module.html#ac-accessmemory](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-accessmemory) · obligation `OB-9B06478A`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AM-004-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

> abstract_access_memory is absent on this DUT (dut-profile absent[]); the row would pass for the wrong reason or be unreachable.

**The value of the remaining bits of arg0 are UNSPECIFIED. 1 (memory): Copy data from the low bits of arg0 into the memory location specified in arg1. target-specific These bits are**

`UNSPECIFIED` · `rtl-unsupported` · [debug_module.html#ac-accessmemory](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-accessmemory) · obligation `OB-A2378959`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AM-005-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

> Spec says UNSPECIFIED -- check the DM does not hang; do not assert a value.

**Debug Modules on systems without address translation (i.e. virtual addresses equal physical) may optionally allow aamvirtual set to 1, which would produce the same result as that s**

`MAY` · `rtl-unsupported` · [debug_module.html#ac-accessmemory](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-accessmemory) · obligation `OB-D636CFDD`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AM-006-C` | Cover | P3 | 0.10 | Deferred | Not started | 0 | — | 2 | — |

> abstract_access_memory is absent on this DUT (dut-profile absent[]); the row would pass for the wrong reason or be unreachable.

**Field Description cmdtype This is 2 to indicate Access Memory Command. aamvirtual An implementation does not have to implement both virtual and physical accesses, but it must fail**

`MUST` · `rtl-unsupported` · [debug_module.html#ac-accessmemory](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-accessmemory) · obligation `OB-DE0E1893`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AM-007-C` | Cover | P3 | 0.25 | Deferred | Not started | 0 | — | 2 | — |

> abstract_access_memory is absent on this DUT (dut-profile absent[]); the row would pass for the wrong reason or be unreachable.

**If aampostincrement is set, increment arg1.**

`CONDITIONAL` · `rtl-unsupported` · [debug_module.html#ac-accessmemory](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-accessmemory) · obligation `OB-EFD4A7B9`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AM-008-C` | Cover | P3 | 0.25 | Deferred | Not started | 0 | — | 2 | — |

> abstract_access_memory is absent on this DUT (dut-profile absent[]); the row would pass for the wrong reason or be unreachable.

**If any of these operations fail, cmderr is set and none of the remaining steps are executed.**

`CONDITIONAL` · `rtl-unsupported` · [debug_module.html#ac-accessmemory](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-accessmemory) · obligation `OB-F50B7C68`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-AM-009-C` | Cover | P3 | 0.25 | Deferred | Not started | 0 | — | 2 | — |

> abstract_access_memory is absent on this DUT (dut-profile absent[]); the row would pass for the wrong reason or be unreachable.

## QA — Quick Access

### Quick Access

**If the hart halts for some other reason (e.g. breakpoint), the command sets cmderr to ``halt/resume'' and does not continue.**

`CONDITIONAL` · `rtl-unsupported` · [debug_module.html#ac-quickaccess](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-quickaccess) · obligation `OB-4D7EB531`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-QA-001-C` | Cover | P3 | 0.25 | Deferred | Not started | 0 | — | 2 | — |

> quick_access is absent on this DUT (dut-profile absent[]); the row would pass for the wrong reason or be unreachable.

**If an exception occurs, cmderr is set to ``exception,'' the Program Buffer execution ends, and the hart is halted with cause set to 3.**

`CONDITIONAL` · `rtl-unsupported` · [debug_module.html#ac-quickaccess](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-quickaccess) · obligation `OB-8D06AC44`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-QA-002-C` | Cover | P3 | 0.25 | Deferred | Not started | 0 | — | 2 | — |

> quick_access is absent on this DUT (dut-profile absent[]); the row would pass for the wrong reason or be unreachable.

**If the Program Buffer executed without an exception, then resume the hart.**

`CONDITIONAL` · `rtl-unsupported` · [debug_module.html#ac-quickaccess](https://docs.riscv.org/reference/debug/v1.0/debug_module.html#ac-quickaccess) · obligation `OB-E7002892`

| Test Item | Type | Pri | Wt | Milestone | Status | % | Assignee | ETA | Final Remarks |
|---|---|---|---:|---|---|---:|---|---:|---|
| `TC-QA-003-C` | Cover | P3 | 0.25 | Deferred | Not started | 0 | — | 2 | — |

> quick_access is absent on this DUT (dut-profile absent[]); the row would pass for the wrong reason or be unreachable.

