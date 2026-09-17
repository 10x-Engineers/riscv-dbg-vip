# fcov_exclusions.tcl -- functional-coverage bins this DUT cannot produce.
#
# Sourced by mk/dm_cov.sh for the *_excl functional reports. Every entry names
# the RTL line or configuration that makes the bin unreachable; a bin that is
# merely hard to reach belongs in a test, not here. The unexcluded report is
# always written alongside, so nothing here hides a number.
#
# The bins stay in covergroups.sv on purpose: the model is DUT-agnostic, and a
# DUT that implements these features is measured against them.
#
# Cross-bin names contain a comma ("nop,failed"), which imc splits arguments
# on, so crosses are named with '?' in its place.

set I uvm_pkg.uvm_test_top.m_env.m_coverage

# ── DMI op status "failed" (2) ─────────────────────────────────────────────
# riscv-dbg dmi_jtag.sv only ever assigns error_d = DMIBusy or DMINoError
# (lines 169, 173); DMIOPFailed is declared and never driven.
set why "dmi_jtag never drives DMIOPFailed (dmi_jtag.sv:169,173 assign only Busy/NoError)"
exclude -inst $I -coverbin cg_dmi_access.cp_status.failed            -comment $why
exclude -inst $I -coverbin cg_dmi_access.x_op_x_status.nop?failed    -comment $why
exclude -inst $I -coverbin cg_dmi_access.x_op_x_status.read?failed   -comment $why
exclude -inst $I -coverbin cg_dmi_access.x_op_x_status.write?failed  -comment $why

# ── cmderr "other" (7) ─────────────────────────────────────────────────────
# dm_csrs.sv and dm_mem.sv assign cmderr only Busy, NotSupported, Exception
# and HaltResume; CmdErrorOther is declared in dm_pkg.sv and never assigned.
exclude -inst $I -coverbin cg_abstract_cmd.cp_cmderr.other \
    -comment "CmdErrorOther is never assigned (dm_pkg.sv:176; no driver in dm_csrs/dm_mem)"

# ── SBA widths and bus errors ──────────────────────────────────────────────
# RTL-002: dm_csrs.sv:618 overwrites sbcs.sbaccess with 3 every cycle, so the
# only widths sbcs_q can hold are 3 and its reset value 0. dm_sba.sv raises
# sberror only for sbaccess > 3 (line 149) and has no bus-error input.
set why "RTL-002: sbaccess hardwired to 3 (dm_csrs.sv:618)"
foreach b {size16 size32 size128 unsupported_written} {
    exclude -inst $I -coverbin cg_sba.cp_sbaccess.$b -comment $why
}
set why "dm_sba.sv sets sberror only for sbaccess>3 (line 149), unreachable under RTL-002; no bus-error input"
foreach b {timeout bad_address alignment unsupported_size other} {
    exclude -inst $I -coverbin cg_sba.cp_sberror.$b -comment $why
}

# ── Trigger-caused debug entry (dcsr.cause=2) ──────────────────────────────
# Triggers fire on this build (cva6_sim/cfg, Sdtrig=1), but RTL-012: CVA6
# reports every action=1 trigger as dcsr.cause=3 -- csr_regfile.sv assigns
# CauseRequest for all DEBUG_REQUEST exceptions and never CauseTrigger.
set why "RTL-012: CVA6 reports a firing trigger as dcsr.cause=3 (csr_regfile.sv:2289)"
exclude -inst $I -coverbin cg_debug_entry.cp_cause.trigger                          -comment $why
exclude -inst $I -coverbin cg_debug_entry.x_cause_x_prv.trigger?*                   -comment $why
exclude -inst $I -coverbin cg_debug_entry.x_cause_x_dpc.trigger?trap_handler_entry  -comment $why
