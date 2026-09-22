# ibex-debug-vip — regression and Debug Module coverage

The Ibex side of the DM-only target: the same VIP, the same scenarios and the
same reference model as CVA6, against a different Debug Module. `ibex-demo-system`
vendors **pulp upstream untouched**; CVA6 carries the 10x fork of PR #4. Where a
result differs between the two, the DM differs — which is the reason for running
both.

    python3 mk/run_regression.py --dut ibex --coverage
    bash mk/dm_cov.sh ibex_sim/sim_outputs/coverage out_ibex/ ibex

## Regression

_Numbers in this section are filled from the run recorded at the bottom of this
file._

Two scenarios are recorded as `partial`, both for the same reason: the model
checker reports RTL-003 (a nonexistent hart reads `allnonexistent=1` **and**
`allrunning=1`) as a `UVM_ERROR`, and one error ends the run. That defect
reproduces on both DUTs and is inherited rather than introduced — the two lines
are character-identical in PR #4's DM and in pulp upstream — and it is filed
upstream as [`pulp-platform/riscv-dbg#200`](https://github.com/pulp-platform/riscv-dbg/issues/200).

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

_Filled from the recorded run._

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
