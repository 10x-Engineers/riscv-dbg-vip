# fcov_exclusions.tcl -- functional-coverage bins this DUT cannot produce.
#
# Sourced by mk/dm_cov.sh for the *_excl functional reports. Every entry names
# the RTL line or configuration that makes the bin unreachable; a bin that is
# merely hard to reach belongs in a test, not here. A bin unreachable only
# because of a known RTL defect is not excluded either: it stays a hole until
# the fix lands. The unexcluded report is always written alongside, so
# nothing here hides a number.
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

# ── SBA bus timeout ────────────────────────────────────────────────────────
# dm_sba has no timeout, and the testplan defers it as out of design scope
# (SBA-012). The other sberror values and the 8/16/32/128-bit widths are left
# as holes on purpose: they are unreachable only because of RTL-002 (#147,
# sbaccess hardwired) and the missing bus-error input (SBA-008), and a known
# RTL defect is never excluded.
exclude -inst $I -coverbin cg_sba.cp_sberror.timeout \
    -comment "dm_sba has no bus timeout; deferred as out of design scope (SBA-012)"

# ── Abstract-command outcome: cmderr "bus" (5) and "other" (7) ─────────────
# dm_mem.sv assigns cmderror_o only HaltResume, NotSupported and Exception
# (lines 154, 198, 203) and dm_csrs.sv only Busy; CmdErrorBus and
# CmdErrorOther are declared in dm_pkg.sv:176 and never driven.
set why "cmderr 5/7 never assigned (dm_mem.sv:154,198,203; dm_csrs.sv Busy only; dm_pkg.sv:176)"
exclude -inst $I -coverbin cg_cmd_outcome.cp_outcome.bus                           -comment $why
exclude -inst $I -coverbin cg_cmd_outcome.cp_outcome.other                         -comment $why
exclude -inst $I -coverbin cg_cmd_outcome.x_cmdtype_x_cmderr.access_register?other -comment $why
foreach f {transfer_only postexec_only transfer_postexec} {
    exclude -inst $I -coverbin cg_cmd_outcome.x_flags_x_cmderr.$f?other -comment $why
}

# ── Selected-hart state: unavailable and nonexistent ───────────────────────
# ariane_testharness.sv:295 ties dm_top's unavailable_i to '0, so no hart is
# ever unavailable (testplan HS-004, deferred as out of design scope).
set why "unavailable_i tied to '0 (ariane_testharness.sv:295)"
exclude -inst $I -coverbin cg_hartsel_state.cp_state.unavailable            -comment $why
exclude -inst $I -coverbin cg_hartsel_state.x_sel_x_state.zero?unavailable  -comment $why
