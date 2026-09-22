# ibex-debug-vip — regression and Debug Module coverage

The Ibex side of the DM-only target: the same VIP, the same scenarios and the
same reference model as CVA6, against a different Debug Module. `ibex-demo-system`
vendors **pulp upstream untouched**; CVA6 carries the 10x fork of PR #4. Where a
result differs between the two, the DM differs — which is the reason for running
both.

    python3 mk/run_regression.py --dut ibex --coverage
    bash mk/dm_cov.sh ibex_sim/sim_outputs/coverage out_ibex/ ibex

## Regression

**22 tests: 20 pass, 1 partial, 1 error — every result matches its declared
`expect`.** The suite lists every `*_uvm.json` config in `ibex_sim/configs`, so
a scenario cannot be quietly left out of it.

| Test | Result | Expected | Steps | UVM errors | Covers |
|---|---|---|---:|---:|---|
| discovery | pass | pass | 2/2 | 0 | `DIS-001`, `DIS-002`, `RST-025` |
| dm_activation | pass | pass | 3/3 | 0 | `ACT-001`, `ACT-002`, `ACT-003`, `RAP-040` |
| read_dmstatus | pass | pass | 1/1 | 0 | `RST-031`, `DIS-001` |
| halt | pass | pass | 8/8 | 0 | `HALT-001`, `HALT-002`, `RC-001` |
| run_control | pass | pass | 9/9 | 0 | `HALT-001`, `RES-001`, `RES-002`, `RES-003`, `RES-007-V` |
| report_halt_status | pass | pass | 4/4 | 0 | `DHS-001` |
| hart_selection | partial | partial | - | 1 | `HS-001`, `HS-002`, `HS-003` |
| reset_ctrl | pass | pass | 11/11 | 0 | `RST-001` … `RST-006` |
| halt_on_reset | pass | pass | 6/6 | 0 | `HOR-001` … `HOR-005` |
| gpr_write | pass | pass | 4/4 | 0 | `AC-001`, `AC-002`, `AC-004` |
| csr_access | pass | pass | 5/5 | 0 | `DCSR-001`, `DCSR-002`, `DCSR-003`, `AC-005` |
| program_buffer | pass | pass | 6/6 | 0 | `PB-001`, `PB-002`, `PB-003`, `AC-010` |
| sw_breakpoint_progbuf | pass | pass | 3/3 | 0 | `PB-004`, `SB-001` |
| single_step | pass | pass | 9/9 | 0 | `SSTEP-001`, `SSTEP-002`, `DCSR-001` |
| trigger | pass | pass | 15/15 | 0 | `TRIG-001`, `TRIG-002`, `TRIG-004`, `TRIG-006` |
| sba | pass | pass | 11/11 | 0 | `SBA-001` … `SBA-004`, `SBA-019-V` |
| cmderr | pass | pass | 17/17 | 0 | `AC-022-V` |
| cmd_busy | pass | pass | 11/11 | 0 | `AC-021-S` |
| dm_corners | error | error | - | 1 | `DMC-005-S`, `DMC-008-C` |
| mem_scan | pass | pass | 18/18 | 0 | `PB-005`, `AC-014-S` |
| dmi_error | pass | pass | 11/11 | 0 | `DTM-002`, `DTM-010`, `DTM-011`, `DTM-017`, `DTM-018` |
| external_trigger | pass | pass | 3/3 | 0 | `HG-001` |

The two non-passes are known and recorded, not open questions:

- **`hart_selection`** aborts on RTL-003 — a nonexistent hart reads
  `allnonexistent=1` **and** `allrunning=1`. It reproduces on both DUTs and is
  inherited rather than introduced (the two lines are character-identical in
  PR #4's DM and in pulp upstream), and it is filed upstream as
  [`pulp-platform/riscv-dbg#200`](https://github.com/pulp-platform/riscv-dbg/issues/200).
  The checker reports it as a `UVM_ERROR`, and one error ends a run.
- **`dm_corners`** runs 10 of its 12 steps and then ends on an RTL assertion
  rather than a checker error, which is why it is `error` and not `partial`:
  TC-DMC-003 starts an SBA read the bus cannot answer, asserts `ndmreset`, and
  reads `sbdata1` — which comes back X and trips lowRISC's own `DataKnown_A`
  inside the DM's response FIFO. See `rtl_findings.md`; it is recorded rather
  than filed, because the X's origin (the DM or the demo system's bus model) is
  not yet established.

For comparison, the same VIP against CVA6 on the same day: 36 tests, 23 pass,
12 known RTL failures, 1 partial, every result matching `expect`.

## What running a second DUT found

Every item below was invisible while CVA6 was the only DUT measured. None of
them is an Ibex defect; they are places where the VIP had quietly learned one
DUT's shape.

| | What | Where |
|---|---|---|
| 1 | **DMI busy was treated as an error.** Busy is flow control (#6.1.5): the operation did not happen and the debugger retries. Erroring on it ended the run at the first one, which is why three scenarios sat at "no verdict" | `scoreboard.sv` |
| 2 | **The read retry could never terminate.** It polled `while (status == busy)` and never wrote `dtmcs.dmireset` — but busy is *sticky*, so every later access returns busy until exactly that write. 15,281 NOP scans and 17 s of simulated time before the run was killed | `dmi_read_seq.sv` |
| 3 | **The checker could not see a `dmireset`.** The monitor published only `JTAG_DMI` shifts, so after the read sequence cleared a sticky busy and re-issued, the checker still held the original pending read and compared it against whatever the DTM's shift register held | `jtag_monitor.sv`, `dm_checker.sv` |
| 4 | **`cmderr` hardcoded 64-bit register accesses.** `aarsize=3` on an RV32 hart is legitimately "not supported", so five of the six error classes were untestable — every case reported `cmderr=2` whatever it asked | `cmderr_sequence.py` |
| 5 | **A known defect hid the rest of a scenario.** `dm_corners` ran its nonexistent-hart steps *first*, so RTL-003 ended it at step 2 and the ten steps below went unexercised — on Ibex that alone accounted for the `haltsum1-3` and `sbbusy` blocks reading as uncovered | `dm_corners_sequence.py` |
| 6 | **Three CVA6-isms were addresses.** The SBA scratch address, the DM's own base (0 on CVA6, `0x1a110000` here) and the assumption of a 64-bit system bus. Each reached nothing on Ibex; the bus left the read data X, the DM latched and served it, and lowRISC's own `DataKnown_A` assertion fired inside the DM's response FIFO | `dm_corners_sequence.py` |
| 7 | **The model wrote a field the DUT does not have.** `abstractcs.relaxedpriv` is a 1.0 addition; on a 0.13 DM the bit does not exist and reads 0 | `dm_ref_model.sv`, `predictor.py` |
| 8 | **The declared SBA widths were wrong.** `dm_csrs.sv:551-555` derives every `sbaccess*` bit from `BusWidth`, so this DM reports 8-, 16- and 32-bit access; the config declared 32 only, and every `sbcs` read was a mismatch | `dut_configs/ibex.json` |
| 9 | **Narrow SBA widths were never driven.** `sbaccess` selects the width and nothing selected a narrow one, so `dm_sba`'s 8- and 16-bit arms were dead code. Invisible on CVA6, where RTL-002 hardwires the field | `sba_sequence.py` |

## Coverage

Debug-subsystem code coverage, merged across the 22 runs, with CVA6's
exclusions applied unchanged:

| Metric | Raw | With exclusions |
|---|---|---|
| Block | 94.23% (490/520) | **94.96%** (490/516, 18 excluded) |
| Expression | 92.65% (63/68) | **92.65%** (63/68, 8 excluded) |
| Toggle | 45.74% (3627/7929) | **63.91%** (3627/5675, 2254 excluded) |
| FSM state | 100.00% (30/30) | **100.00%** |
| FSM transition | 100.00% (43/43) | **100.00%** |

Functional coverage: 153/286 reachable bins (53.5%), with the same 19
exclusions CVA6 uses. The gap to CVA6's 100% is scenario coverage, not DM
behaviour: this suite runs 22 scenarios to CVA6's 36, and the ones it does not
run are the trigger-enabled, native-debug and privilege-stepping scenarios that
need firmware and core features Ibex's demo system does not provide.

Where this started, for scale: before the nine findings above, the same
measurement read **76.7% block, 77.9% expression, 31.5% toggle, 76.7% FSM
state, 60.5% FSM transition**. None of that improvement came from new DM
stimulus written for Ibex — it came from scenarios that already existed
finally running to completion on it.

The exclusions are CVA6's, applied unchanged. Rules that no longer match are
reported by `mk/dm_cov_exclude.py` rather than deleted silently — that report is
the list of things this DM does differently, and it is worth reading alongside
the numbers.

## Scope

Measured: `dm_top` and everything under it, plus the DTM (`dap`, inside
`dm_top` here, a sibling on CVA6) and the DMI clock crossing down to its
`prim_fifo_async_simple` / `prim_sync_reqack` wrappers. Not measured: the
lowRISC leaf cells below those (`prim_flop`, `prim_cdc_rand_delay`), which are
library primitives — the same line CVA6's list draws at `cdc_2phase`'s
`i_src`/`i_dst`.
