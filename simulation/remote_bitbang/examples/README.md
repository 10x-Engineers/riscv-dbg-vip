# Examples

| File | What it shows |
|---|---|
| `minimal_rbb_walkthrough.py` | Smallest possible RBB example: connect, activate, halt, read a GPR, read memory, resume. No timing/benchmark logic — read this first. |
| `ibex_halt_over_rbb.json` | A standard pydebug scenario config (`halt`) pointed at the OpenOCD+RBB transport for Ibex — runnable via `pydebug run --config ibex_halt_over_rbb.json` the same way any other scenario config in `ibex_sim/configs/` is. |
| `cva6_halt_over_rbb.json` | Same, for CVA6. |

## Running these

1. Compile + launch a Questa simulation in RBB mode for the DUT you want
   (see `../documentation/architecture.md` for the full flow). The
   fastest way is the existing, already-tested Makefile target:
   ```
   cd ../../../ibex_sim && make soc_openocd OPENOCD_SCENARIO=halt
   ```
   which does everything (compile, start the RBB server, wait for it, start
   OpenOCD, run the `halt` scenario) in one step — this is the same
   scenario as `ibex_halt_over_rbb.json` above, run the "canonical" way.

2. To instead drive one of the example configs directly (e.g. to see the
   raw `pydebug run --config ...` invocation this module's scripts wrap):
   start just the simulator half of step 1's flow, then from `ibex_sim/`:
   ```
   pydebug run --config ../simulation/remote_bitbang/examples/ibex_halt_over_rbb.json
   ```

3. For the timed, apples-to-apples PyDebug-vs-OpenOCD+RBB comparison (not
   a single scenario, both transports back to back with statistics), use
   `../scripts/run_comparison.sh ibex` instead — see
   `../documentation/performance_comparison_ibex.md` for the report it
   already produced on this machine.
