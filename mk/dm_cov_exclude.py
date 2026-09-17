#!/usr/bin/env python3
"""
dm_cov_exclude.py — generate imc code-coverage exclusions for the Debug Module.

Exclusions are derived from *justified patterns* matched against the coverage
report, never from hand-copied block indices. Indices shift whenever the RTL
moves by a line, and a stale index silently excludes the wrong block -- which
is worse than no exclusion at all, because it inflates coverage while looking
deliberate.

Every rule carries the reason the code is unreachable **on this DUT**, and the
condition that would make it reachable again. A rule that stops matching is
reported rather than ignored: if RTL-002 is fixed, the sbaccess rules stop
matching and the report says so, which is the signal to delete them.

    python3 mk/dm_cov_exclude.py out/dm_code.rpt --out out/dm_exclusions.tcl

Then, in imc:
    load -run <merged>
    source out/dm_exclusions.tcl
    report -detail -all -metrics code -inst <...> -out excluded.rpt
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dm_abstract_cmd_bits import constant_bits as _abstract_cmd_constant_bits  # noqa: E402

_ABSTRACT_CMD_CONSTANT = _abstract_cmd_constant_bits()

#: (rule name, source regex, reason, what would make it reachable[, filters])
#:
#: The source column alone is ambiguous when one statement appears in several
#: places -- dmi_jtag has three `if (dmi_resp_valid)`, and only one is dead.
#: The optional filters narrow a rule without falling back to indices:
#:   inst  regex on the instance path
#:   kind  regex on the block kind ("true part of", "implicit else", ...)
#:   case  regex on the source of the enclosing `case` item
RULES = [
    # ── The DM's bus bridges (generic IP, used in one narrow way) ─────────
    ("dm-slave-single-beat-only",
     r"warp_address|upper_wrap_boundary|cons_addr|WRAP:|case \(ax_req_q\.burst\)"
     r"|FIXED, INCR|slave\.r_last|slave\.w_last|WRITE: begin|slave\.w_valid"
     r"|req_addr_d = addr_o|state_d = SEND_B",
     "the DM's memory slave is only ever addressed by the hart's accesses to "
     "the 4 KiB DM region, which are single-beat (AxLEN=0): the burst-address "
     "arithmetic, the WRAP arm, and the multi-beat READ/WRITE paths cannot be "
     "entered. axi2mem is generic IP used in one narrow way here",
     "a master that issues bursts to the DM region",
     {"inst": r"i_dm_axi2mem$"}),

    ("dm-master-single-request-only",
     r"type_i (!|=)= ariane_pkg::SINGLE_REQ|BURST_SIZE|CRITICAL_WORD_FIRST"
     r"|WAIT_LAST_W_READY|WAIT_AW_READY_BURST|WAIT_R_VALID_MULTIPLE"
     r"|cnt_[dq]|axi_resp_i\.r\.last|index = |axi_req_o\.aw_valid = 1'b1"
     r"|state_d = WAIT_LAST_W_READY|2'b(01|10|11): |default: ;",
     "dm_top's bus master is wired with type_i = SINGLE_REQ and one 64-bit "
     "access at a time (ariane_testharness.sv:352-360), so every burst and "
     "critical-word path of this generic cache adapter is unreachable",
     "a DM that issues bursts",
     {"inst": r"i_dm_axi_master$"}),

    ("dm-master-no-amo",
     r"amo_[qi]|AMO_|ATOP_|amo_returns_data",
     "dm_top's bus master is wired with amo_i = AMO_NONE "
     "(ariane_testharness.sv:353): the adapter's atomic paths cannot be entered",
     "a DM that issues atomics",
     {"inst": r"i_dm_axi_master$"}),

    ("dm-master-one-outstanding",
     r"any_outstanding_aw|outstanding_aw_cnt_q|id_i == id_q",
     "the DM's master waits for each access to complete before starting the "
     "next (dm_sba is a one-at-a-time state machine) and drives id_i = '0, so "
     "there is never a second outstanding write or a second ID",
     "a DM that pipelines system-bus accesses",
     {"inst": r"i_dm_axi_master$"}),

    ("dm-master-bus-never-backpressures",
     r"axi_resp_i\.(aw_ready|w_ready)|WAIT_AW_READY: begin",
     "TESTBENCH LIMIT: the AXI crossbar accepts the DM master's AW and W in "
     "the cycle they are offered in every run so far, so the adapter's "
     "wait-for-ready states are never entered",
     "stimulus that congests the crossbar while an SBA access is in flight",
     {"inst": r"i_dm_axi_master$"}),

    ("dm-slave-wrap-else-arms",
     r"^end else begin$",
     "the remaining arms of the WRAP burst-address arithmetic excluded above",
     "a master that issues wrapping bursts to the DM region",
     {"inst": r"i_dm_axi2mem$", "case": r"WRAP"}),

    ("dm-master-burst-else-arms",
     r"^(end else begin|case \(\{)$",
     "the burst arms of the adapter's write path: the else of "
     "`if (type_i == SINGLE_REQ)` and the aw/w-ready case inside it "
     "(axi_adapter.sv:201, 213, 271, 296). type_i is tied to SINGLE_REQ",
     "a DM that issues bursts",
     {"inst": r"i_dm_axi_master$",
      "case": r"WAIT_LAST_W_READY_AW_READY|2'b11|default: state_d = IDLE;"}),

    ("dm-master-amo-response-arms",
     r"axi_resp_i\.r_valid|RESP_EXOKAY|^end else begin$",
     "the atomic arms of WAIT_B_VALID and the whole WAIT_AMO_R_VALID state "
     "(axi_adapter.sv:349-372, 390): amo_i is tied to AMO_NONE, so no atomic "
     "ever returns data or a store-conditional response",
     "a DM that issues atomics",
     {"inst": r"i_dm_axi_master$", "case": r"WAIT_B_VALID|WAIT_AMO_R_VALID"}),

    ("rstgen-parameter-check",
     r"NumRegs < 1",
     "an elaboration-time parameter check ($fatal); NumRegs is 4",
     "a build with NumRegs < 1, which would not elaborate",
     {"inst": r"i_rstgen"}),

    ("sba-access-size",
     r"3'b(001|010): begin|be_mask\[int'|else\s+be_mask = '1",
     "sbcs.sbaccess is hardwired to 3 (64-bit) by dm_csrs.sv:618, so the "
     "8/16/32-bit byte-enable arms can never be selected",
     "issue #147 (RTL-002) fixed, making sbaccess writable"),

    ("sba-unsupported-size",
     r"sbaccess_i > 3",
     "the spec's sberror=4 path needs sbaccess to hold an unsupported value; "
     "it is hardwired to 3 and cannot",
     "issue #147 (RTL-002) fixed"),

    ("sba-no-bus-error",
     r"if \(sberror_valid_i\)",
     "dm_sba raises sberror_valid only on the sbaccess > 3 path above; dm_top "
     "has no bus-error input, so an AXI error response never reaches it",
     "issue #147 (RTL-002) fixed, or bus-error reporting added to dm_sba"),

    ("readbyteenable-param",
     r"if \(ReadByteEnable\) be = be_mask",
     "ReadByteEnable is a compile-time parameter, so one arm is dead by "
     "parameterisation rather than by stimulus",
     "a build with the opposite ReadByteEnable value"),

    ("datacount-param",
     r"if \(dm::DataCount > 0\)",
     "dm::DataCount is the constant 2, so the arm for a DM without data "
     "registers is dead by parameterisation",
     "a build with DataCount = 0",
     {"kind": r"implicit else"}),

    ("hart-never-unavailable",
     r"stickyunavail_d\[i\]",
     "ariane_testharness.sv ties dm_top's unavailable_i to '0, so no hart can "
     "report unavailable and the sticky bit can never set",
     "an integration that drives unavailable_i"),

    ("keepalive-dead-code",
     r"if\s*\(dmcontrol_d\.(set|clr)keepalive\)",
     "dm_csrs.sv clears dmcontrol_d.setkeepalive/clrkeepalive earlier in the "
     "same always_comb that tests them, so both conditions are constant 0 "
     "(RTL-005); TC-AC-025 writes both bits and they are dropped",
     "issue #148 (RTL-005) fixed"),

    ("dtm-parasitic-state",
     r"if \(dmi_resp_valid\)",
     "the default arm of dmi_jtag's state case only catches the three "
     "unencoded values of a 3-bit, five-state register, which no legal "
     "transition produces; it is entered only at time 0 while state_q is X",
     "a state-register upset",
     {"inst": r"i_dmi_jtag$", "case": r"^default"}),

    ("dtm-request-backpressure",
     r"if \(dmi_req_ready\)",
     "dmi_req_ready is cdc_2phase's source-side ready, low only between a "
     "handshake and its acknowledge. ARGUED FROM THE RTL, not proven: the DTM "
     "re-enters Read/Write only after the previous response has crossed back, "
     "and that response trails the acknowledge, so ready is high there. This "
     "DTM has no dmihardreset (RTL-009) to abandon a transfer early; resetting "
     "only the JTAG half of the CDC with TRST might, and is untested",
     "a DTM that issues a request before the previous acknowledge returns",
     {"inst": r"i_dmi_jtag$", "kind": r"implicit else"}),

    ("dtm-unencoded-error",
     r"error_q == DMIBusy \|\| error_dmi_busy",
     "error_q is only ever assigned DMINoError or DMIBusy, so the arm that "
     "needs it to hold DMIReservedError or DMIOPFailed is unreachable",
     "a DTM that latches the other dmistat values",
     {"inst": r"i_dmi_jtag$", "kind": r"implicit else"}),
]


#: Expression rows: (rule name, expression-source regex, term-vector regex,
#: reason, what would make it reachable, instance regex). The term vector is
#: the row's input columns as the report prints them, e.g. "0 - -".
EXPR_RULES = [
    ("dm-master-single-request-only",
     r"CRITICAL_WORD_FIRST|BURST_SIZE|WAIT_R_VALID_MULTIPLE|type_i != ariane_pkg::SINGLE_REQ",
     r".*",
     "dm_top's bus master is wired with type_i = SINGLE_REQ: the burst and "
     "critical-word arms of this generic cache adapter are unreachable",
     "a DM that issues bursts",
     r"i_dm_axi_master$"),

    ("dm-master-no-amo-or-second-outstanding",
     r"amo_[qi]|any_outstanding_aw|outstanding_aw_cnt_q|id_i == id_q",
     r".*",
     "amo_i is tied to AMO_NONE and the DM issues one access at a time with "
     "id_i = '0, so these terms never take the excluded value",
     "a DM that issues atomics or pipelines accesses",
     r"i_dm_axi_master$"),

    ("dmi-resp-fifo-never-full",
     r"dmi_req_ready_o && dmi_req_valid_i", r"^0 - -$",
     "ARGUED FROM THE RTL, not proven: dmi_req_ready_o is ~resp_queue_full on "
     "a depth-2 FIFO, and the DTM holds one request at a time until its "
     "response is popped (it has no dmihardreset to abandon one, RTL-009), so "
     "the FIFO never holds more than one entry",
     "a DTM that pipelines requests", r"i_dm_csrs$"),

    ("dmi-request-always-ready",
     r"valid_o && ready_i", r"^- 0$",
     "ARGUED FROM THE RTL, not proven: the CDC receivers' ready_i is the DM's "
     "dmi_req_ready_o (a response FIFO that never fills) on the request side "
     "and dmi_jtag's dmi_resp_ready (tied 1) on the response side",
     "a DTM that pipelines requests, or back-pressures responses",
     r"i_cdc_(req|resp)\.i_dst$"),

    ("sba-unsupported-size",
     r"sbaccess_i > 3", r"^1 1$",
     "the spec's sberror=4 path needs sbaccess to hold an unsupported value; "
     "it is hardwired to 3 and cannot",
     "issue #147 (RTL-002) fixed", r"i_dm_sba$"),

    ("dtm-unencoded-error",
     r"error_q == DMIBusy \|\| error_dmi_busy", r"^0 0$",
     "the all-false row needs error_q outside {DMINoError, DMIBusy}, which "
     "dmi_jtag never assigns",
     "a DTM that latches the other dmistat values", r"i_dmi_jtag$"),
]


#: Toggle exclusions are stated per signal or field, not per bit: a field that
#: a parameter fixes is one fact about the DUT, not N facts. The regex is
#: matched against the full name as imc prints it, bit index included, e.g.
#: `dmstatus.version[3]`, so a rule can name exactly the constant bits.
#: (rule name, signal regex, reason, what would make it reachable[, instance regex])
TOGGLE_RULES = [
    # WAIVER, not unreachability: a second power-on reset is legal stimulus
    # this testbench cannot produce from a scenario.
    ("waiver-single-power-on-reset",
     r"^(rst_ni|dmi_rst_ni|dmi_rst_no|src_rst_ni|dst_rst_ni)$",
     "TESTBENCH LIMIT: power-on reset is applied once, at time 0, so its "
     "release is the only edge a run has (dmi_rst_no is rst_ni passed through; "
     "the CDC halves take it or TRST as their reset)",
     "a transport op that re-applies power-on reset"),

    # WAIVER, not unreachability: TRST mid-session is legal stimulus the JTAG
    # agent does not offer. Its effect on dmi_cdc, whose two halves are reset
    # separately, is untested.
    ("waiver-trst-once",
     r"^(trst_ni|jtag_TRSTn)$",
     "TESTBENCH LIMIT: the JTAG agent asserts TRST once, at time 0, and has "
     "no op to pulse it",
     "a transport op that pulses TRST"),

    ("tied-off-inputs",
     r"^(testmode_i|test_mode_i|clk_sel_i|unavailable_i|unavailable_aligned\[\d+\]|unavailable_effective"
     r"|stickyunavail_[dq]|dmstatus\.(allunavail|anyunavail))$",
     "ariane_testharness.sv drives testmode_i (and the TAP's DFT clock-mux "
     "select) from test_en, assigned 1'b0 at :121, and ties dm_top's "
     "unavailable_i to '0 at :295; the rest are functions of unavailable_i",
     "an integration that drives them"),

    ("dmi-response-constants",
     r"^(dmi_resp_o|dmi_resp_i|dmi_resp|jtag_dmi_resp_o|core_dmi_resp_i|data_[io]"
     r"|async_data(_[io])?|data_(src|dst)_q|(src|dst)_data_[io])\.resp\[\d\]$"
     r"|^debug_resp\.resp\[\d\]$"
     r"|^(dmi_resp_ready|jtag_dmi_ready_i)$",
     "dm_csrs drives resp = DTM_SUCCESS and dmi_jtag drives resp_ready = 1, "
     "both constants",
     "a DM that reports DMI-level failures"),

    ("dmi-request-always-ready",
     r"^(dmi_req_ready_o|dmi_req_ready_i|resp_queue_full|core_dmi_ready_i)$"
     r"|^(dst_ready_i|ready_i|debug_req_ready)$",
     "ARGUED FROM THE RTL, not proven: the response FIFO never fills and the "
     "CDC is ready whenever the DTM asks -- see the dmi-resp-fifo-never-full "
     "and dtm-request-backpressure code rules",
     "a DTM that pipelines requests"),

    ("dm-master-axi-attributes-at-the-boundary",
     r"^dm_axi_m_req\.(aw|ar)\.(user|len|atop|id|cache|qos|region|prot|lock|burst|size)"
     r"|^dm_axi_m_req\.w\.user|^dm_axi_m_resp\.[br]\.(user|id|resp)",
     "the same constants as inside the adapter, seen on the DM master's AXI "
     "bus at the testharness: no USER, single 64-bit INCR beats, id '0, no "
     "atomics, and no slave ever answers the DM with an error",
     "a DM that varies its AXI attributes, or a slave that errors",
     r"^tb_top_soc\.dut$"),

    ("testbench-debug-always-enabled",
     r"^debug_enable$",
     "TESTBENCH LIMIT: +debug_disable is never passed, so the testharness's "
     "debug-disable knob holds at 1",
     "a run with +debug_disable, which would keep debug_req_core low",
     r"^tb_top_soc\.dut$"),

    ("dm-bridge-tied-axi-fields",
     r"^(user_[io]|axi_(req_o|resp_i)\.(aw|ar|w|b|r)\.user)(\[\d+\])?$"
     r"|^axi_req_o\.(aw|ar)\.(cache|prot|qos|region|lock|burst|len|size)(\[\d+\])?$"
     r"|^axi_req_o\.aw\.atop(\[\d+\])?$"
     r"|^(id_[idoq]|size_[idq])(\[\d+\])?$"
     r"|^axi_(req_o\.(aw|ar)|resp_i\.(b|r))\.id(\[\d+\])?$",
     "the DM's bus master drives these as constants: AXI USER is unused, the "
     "access is always a single 64-bit INCR with id '0, and cache/prot/qos/"
     "region/lock/atop are tied off (ariane_testharness.sv:343-367)",
     "a DM that varies its AXI attributes",
     r"i_dm_axi(2mem|_master)$"),

    ("dm-bridge-no-bus-error",
     r"^axi_resp_i\.[br]\.resp(\[\d+\])?$",
     "nothing in this SoC returns an AXI error to the DM's master: the DM has "
     "no bus-error input either (see sba-no-bus-error)",
     "a slave that answers the DM with SLVERR or DECERR",
     r"i_dm_axi_master$"),

    ("dm-bridge-single-beat",
     r"^(cnt_[dq]|index|wrap_boundary|upper_wrap_boundary|cons_addr"
     r"|any_outstanding_aw|outstanding_aw_cnt_[dq])(\[\d+\])?$"
     r"|^ax_req_[dq]\.(len|size|id)(\[\d+\])?$",
     "single-beat accesses only: the beat counters, burst-address arithmetic "
     "and AxLEN stay at 0, AxSIZE is fixed, and one access is outstanding at a "
     "time",
     "bursts, or pipelined accesses, to or from the DM",
     r"i_dm_axi(2mem|_master)$"),

    ("dm-region-address-bits",
     r"^(aligned_address|cons_addr|req_addr_[dq]|ax_req_[dq]\.addr)\[\d+\]$",
     "the DM's memory slave answers one 4 KiB region at address 0, so every "
     "address bit above the region never sets",
     "a DM mapped at a higher address, or a larger region",
     r"i_dm_axi2mem$"),

    ("sbaccess-hardwired",
     r"^(sbaccess|sbaccess_[io])\[2\]$|^sbcs_q\.sbaccess\[19\]$",
     "sbcs.sbaccess is forced to 3 (RTL-002), so its top bit never sets",
     "issue #147 (RTL-002) fixed"),

    ("sba-no-bus-error",
     r"^(sberror_valid(_[io])?|(sberror|sberror_[io])\[\d\]|sbcs_q\.sberror\[\d+\])$",
     "dm_sba raises sberror only on the sbaccess > 3 path (RTL-002) and dm_top "
     "has no bus-error input",
     "issue #147 (RTL-002) fixed, or bus-error reporting added to dm_sba"),

    ("keepalive-dead-code",
     r"^(keepalive_[odq]|dmcontrol_q\.(set|clr)keepalive)$",
     "setkeepalive/clrkeepalive are cleared before they are tested (RTL-005), "
     "so keepalive never changes",
     "issue #148 (RTL-005) fixed"),

    ("haltsum-undriven",
     r"^(haltsum[123]|halted|halted_flat[123])\[\d+\]$|^halted_reshaped[012]\[\d+\]\[\d+\]$",
     "with NrHarts = 1 the haltsum1-3 trees read a vector nothing drives "
     "(RTL-007), so they are X for the whole simulation",
     "RTL-007 fixed and a multi-hart build (with one hart they would be "
     "constant 0)"),

    # Only the padded slots nothing can write. dm_mem's halted/resuming
    # slots are indexed by the hart id written to it, so id 1 reaches them
    # (TC-DMC-009) -- they are deliberately not listed here.
    ("single-hart",
     r"^haltsum0\[([1-9]|[12]\d|3[01])\]$"
     r"|^(havereset_[dq]_aligned|resumeack_aligned|halted_aligned|resumereq_aligned"
     r"|haltreq_aligned|resumereq_wdata_aligned|halted_q_aligned|resuming_q_aligned)\[1\]$",
     "NrHarts = 1: haltsum0 has one hart bit, and these per-hart vectors are "
     "the hart inputs zero-extended to 2**HartSelLen = 2 entries, so the "
     "second entry is constant 0",
     "a multi-hart build"),

    # dm_mem's flag word: rdata[hartsel & 7] = {6'b0, resume, go}. hartsel is
    # one bit with one hart, so slots 2-7 are never addressed; the six pad
    # bits are constant; and hart 1's go/resume need halted_q_aligned[1] and
    # resumereq_aligned[1], both constant 0 (above).
    ("flag-word-constants",
     r"^rdata\[([2-7]\]\[\d|[01]\]\[[2-7]|1\]\[[01])\]$",
     "dm_mem builds the flag word as rdata[hartsel & 7] = {6'b0, resume, go}: "
     "the pad bits are constant, a one-bit hartsel never addresses slots 2-7, "
     "and hart 1's go/resume need slot-1 halted/resume state that is constant 0",
     "a multi-hart build", r"i_dm_mem$"),

    ("dmstatus-constants",
     r"^dmstatus\.(zero[01]\[\d+\]|impebreak|authbusy|hasresethaltreq|devtreevalid"
     r"|version\[\d+\])$",
     "fixed by dm_csrs: version 3 (1.0), no authentication, impebreak 0 with "
     "an 8-word Program Buffer, no devicetree, no halt-on-reset (RTL-004)",
     "a DM configured with those features"),

    ("dmcontrol-forced-zero",
     r"^dmcontrol_q\.(hartreset|ackhavereset|ackunavail|hasel|setresethaltreq"
     r"|clrresethaltreq)$",
     "dm_csrs forces these to 0 in dmcontrol_d every cycle: no per-hart reset, "
     "no hart array, no halt-on-reset, and the W1 bits act on the write rather "
     "than being stored",
     "a DM that implements hartreset, hasel or halt-on-reset"),

    ("abstractcs-constants",
     r"^abstractcs\.(zero[023]|progbufsize|datacount)\[\d+\]$",
     "fixed by parameters: progbufsize 8, datacount 2, reserved fields 0",
     "a build with other ProgBufSize/DataCount"),

    ("abstractauto-warl",
     r"^abstractauto_[dq]\.(zero0\[\d+\]|autoexecprogbuf\[(2[4-9]|3[01])\]"
     r"|autoexecdata\[([2-9]|1[01])\])$",
     "WARL: only 8 autoexecprogbuf and 2 autoexecdata bits exist; TC-DMC-005 "
     "writes all-ones and reads back 0x00ff0003",
     "a build with a larger Program Buffer or more data registers"),

    ("sbcs-constants",
     r"^sbcs_q\.(sbversion\[\d+\]|sbasize\[\d+\]|sbaccess(128|32|16|8))$",
     "fixed by dm_csrs for a 64-bit bus: sbversion 1, sbasize 64, and only "
     "sbaccess64 supported",
     "a build with another BusWidth"),

    ("dmcs2-not-implemented",
     r"^dmcs2_[dq]\.",
     "halt and resume groups are not implemented, so dm_csrs ignores dmcs2 "
     "writes and holds every field at 0",
     "a DM with halt/resume groups or external triggers"),

    ("shutdown-counter-range",
     r"^dmactive_shutdown_counter\[3\]$",
     "the counter is loaded with 5 and only counts down, so bit 3 never sets",
     "a longer dmactive shutdown window"),

    ("debug-rom-is-constant",
     r"^mem\[\d+\]\[\d+\]$",
     "debug_rom.sv's mem is a continuous assignment of constants; the words "
     "it serves are checked by TC-DMC-006 and their varying bits covered on "
     "rdata_o",
     "a writable ROM", r"i_debug_rom$"),

    # Only the bits dm_abstract_cmd_bits.py proves constant across every
    # program dm_mem can generate. A bit that can vary is never excluded,
    # however hard it is to reach.
    ("abstract-command-constant-bits",
     "^abstract_cmd\\[(" + "|".join(
         f"{slot}\\]\\[({'|'.join(str(b) for b in sorted(bits))})"
         for slot, bits in _ABSTRACT_CMD_CONSTANT.items() if bits) + ")\\]$",
     "constant in every program dm_mem.sv can generate for this build, by "
     "enumeration over all command shapes, aarsize values and regno classes "
     "(mk/dm_abstract_cmd_bits.py): slots 5-7 are '0, slot 1 is two fixed "
     "shifts, and the rest are fixed opcode/funct/register fields",
     "a DM that generates different abstract-command programs", r"i_dm_mem$"),

    ("debug-rom-constant-bits",
     r"^(rom_rdata|rdata_o)\[(0|1|7|41)\]$",
     "these bits hold the same value in all 19 debug ROM words, and TC-DMC-006 "
     "reads and checks every word",
     "a different debug ROM", r"(i_dm_mem|i_debug_rom)$"),
]


#: Instances that are in the report only for their DM-facing boundary. Anything
#: in them that is not on the keep list is out of the debug subsystem's scope
#: and is excluded by name, so the subsystem total never counts, or claims, the
#: rest of the SoC. This is scope, not unreachability, and it is stated as such
#: in the generated file.
#: (instance regex, what it is, signal keep regex, block/expression keep regex)
BOUNDARY = [
    (r"^tb_top_soc\.dut$",
     "ariane_testharness: only the DM's own connections -- the JTAG pins, the "
     "DMI request/response glue, ndmreset and its debug_req gating, and the DM "
     "bus signals -- are in the debug subsystem. The rest of the SoC harness "
     "(peripherals, memory, the AXI crossbar, RVFI/trace) is not.",
     r"^jtag_(TCK|TMS|TDI|TRSTn|TDO_data|TDO_driven)$"
     r"|^(debug_req_valid|debug_req_ready|debug_resp_valid|debug_resp_ready)$"
     r"|^(jtag_req_valid|jtag_resp_ready|jtag_resp_valid)$"
     r"|^(jtag_dmi_req|jtag_dmi_resp|debug_req|debug_resp)(\.|\[|$)"
     r"|^(ndmreset|ndmreset_n|debug_req_core|debug_req_core_ungtd|debug_enable)$"
     r"|^dmi_del_cnt_[dq]"
     r"|^dm_(slave|master)_|^dm_axi_m_(req|resp)",
     r"dmi_del_cnt|debug_req_core|ndmreset"),

    (r"^tb_top_soc\.dut\.i_ariane$",
     "the hart's debug boundary is its debug_req_i port; CVA6's internal debug "
     "logic (dcsr/dpc/dscratch, Debug Mode entry and exit, step, dret) is the "
     "processor's own coverage, not the debug subsystem's",
     r"^debug_req_i$",
     r"(?!)"),
]


def parse_all(report: Path):
    """Yield (instance, kind, id, name) for EVERY block, expression and signal
    in the boundary instances -- covered or not. The rule-based exclusions
    above work from holes; scoping has to work from everything."""
    for name, body in _sections(report):
        if not any(re.search(ipat, name) for ipat, *_ in BOUNDARY):
            continue
        sec = re.search(r"Block Detail Report.*?(?=Expression Detail|Toggle Detail|\Z)",
                        body, re.S)
        if sec:
            for _hit, idx, _line, _kind, _org, src in re.findall(
                    r"^(\d+)\s+(\d+)\s+(\d+)\s+(\S.*?)\s{2,}(\d+)\s+(.*)$",
                    sec.group(0), re.M):
                yield name, "block", idx, src.strip()
        sec = re.search(r"Expression Detail Report.*?(?=Toggle Detail|\Z)", body, re.S)
        if sec:
            for line in sec.group(0).splitlines():
                m = re.match(r"index: (\S+) grade: .* source: (.*)$", line)
                if m:
                    yield name, "expression", m.group(1), m.group(2).strip()
        sec = re.search(r"Toggle Detail Report.*?(?=Fsm Detail|\Z)", body, re.S)
        if sec:
            for _f, _r, _fa, sig in re.findall(r"^(\d)\s+(\d)\s+(\d)\s+(\S+)\s*$",
                                               sec.group(0), re.M):
                yield name, "toggle", re.sub(r"\[\d+\]$", "", sig), sig


def emit_boundary(report: Path) -> tuple[list[str], int, set]:
    """Exclusions that scope the boundary instances down to the DM-facing part."""
    out = ["", "# " + "=" * 74,
           "# Boundary scoping -- NOT unreachability. These instances are in the",
           "# report only for their connection to the DM; everything else in them",
           "# belongs to the processor or the rest of the SoC and is excluded by",
           "# name so the subsystem total neither counts nor claims it.",
           "# " + "=" * 74, ""]
    seen: set = set()
    total = 0
    for inst, kind, ident, name in parse_all(report):
        for ipat, what, sigpat, srcpat in BOUNDARY:
            if not re.search(ipat, inst):
                continue
            keep = re.search(sigpat, name) if kind == "toggle" else re.search(srcpat, name)
            if keep or (inst, kind, ident) in seen:
                continue
            seen.add((inst, kind, ident))
            total += 1
            arg = (f"-toggle {{{_imc_toggle_name(ident)}}}" if kind == "toggle"
                   else f"-{kind} {ident}")
            out.append(f'exclude -inst {{{inst}}} {arg} '
                       f'-comment {{boundary-scope: {what}}}')
    out.append("")
    return out, total, seen


#: FSM states and transitions this DUT cannot reach. Matched against
#: "<state>" or "<from> -> <to>" as parse_fsm yields them.
#: (rule name, instance regex, item regex, reason, what would make it reachable)
FSM_RULES = [
    ("dm-slave-single-beat-only", r"i_dm_axi2mem$", r"\bWRITE\b",
     "the WRITE state is the multi-beat write path; the hart's accesses to the "
     "DM region are single-beat, so a write goes IDLE/WAIT_WVALID -> SEND_B",
     "a master that issues burst writes to the DM region"),

    ("dm-master-single-request-only", r"i_dm_axi_master$",
     r"WAIT_LAST_W_READY_AW_READY|WAIT_AW_READY_BURST|WAIT_R_VALID_MULTIPLE",
     "burst states of this generic cache adapter; the DM's master is wired "
     "type_i = SINGLE_REQ",
     "a DM that issues bursts"),

    ("dm-master-no-amo", r"i_dm_axi_master$", r"WAIT_AMO_R_VALID",
     "the atomic path; amo_i is tied to AMO_NONE",
     "a DM that issues atomics"),

    ("dm-master-bus-never-backpressures", r"i_dm_axi_master$", r"WAIT_AW_READY\b",
     "TESTBENCH LIMIT: the crossbar has accepted the DM master's AW in the "
     "cycle it was offered in every run so far",
     "stimulus that congests the crossbar during an SBA access"),
]


def emit_fsm(report: Path) -> tuple[list[str], int, list]:
    """FSM exclusions, and the holes no rule claims."""
    out = ["", "# " + "=" * 74,
           "# FSM exclusions -- unreachable states and transitions.",
           "# " + "=" * 74, ""]
    matched: dict[str, list] = {r[0]: [] for r in FSM_RULES}
    holes = []
    for inst, fsm, kind, what in parse_fsm(report):
        for rule, ipat, wpat, _why, _when in FSM_RULES:
            if re.search(ipat, inst) and re.search(wpat, what):
                matched[rule].append((inst, fsm, kind, what))
                break
        else:
            holes.append((inst, kind, what))
    total = 0
    for rule, _i, _w, why, when in FSM_RULES:
        hits = matched[rule]
        out.append(f"# ---- {rule} ({len(hits)} item(s)) ----")
        out += [f"#   why       : {why}", f"#   reachable : {when}"]
        if not hits:
            out.append("#   NO LONGER MATCHES -- delete this rule.")
        for inst, fsm, kind, what in hits:
            total += 1
            arg = (f"-state {fsm}.{what}" if kind == "state"
                   else "-transition {}.{}".format(fsm, what.replace(" -> ", ".")))
            out.append(f'exclude -inst {{{inst}}} {arg} -comment {{{rule}: {why}}}')
        out.append("")
    return out, total, holes


def parse_toggles(report: Path):
    """Yield (instance, signal) for every signal bit that never toggled."""
    for name, body in _sections(report):
        sec = re.search(r"Toggle Detail Report.*?(?=Fsm Detail|\Z)", body, re.S)
        if not sec:
            continue
        for full, _rise, _fall, sig in re.findall(
                r"^(\d)\s+(\d)\s+(\d)\s+(\S+)\s*$", sec.group(0), re.M):
            if full == "0":
                yield name, sig


def _sections(report: Path):
    txt = report.read_text(encoding="utf-8", errors="replace")
    return zip(*[iter(re.split(r"^== (\S+)$", txt, flags=re.M)[1:])] * 2)


def parse_fsm(report: Path):
    """Yield (instance, fsm, 'state'|'transition', name) per unvisited FSM item."""
    for name, body in _sections(report):
        sec = re.search(r"Fsm Detail Report.*", body, re.S)
        if not sec:
            continue
        reg = re.search(r"^State register: (\S+)", sec.group(0), re.M)
        fsm = reg.group(1) if reg else "state_q"
        mode, prev = None, ""
        for line in sec.group(0).splitlines():
            if line.startswith("State Coverage"):
                mode = "state"
            elif line.startswith("Transition Coverage"):
                mode = "transition"
            elif line.startswith(("Reset States", "Arc Coverage")):
                mode = None
            elif mode == "state":
                m = re.fullmatch(r"(\w+)\s+([01]+)\s+(\d+)\s*", line)
                if m and m.group(3) == "0":
                    yield name, fsm, "state", m.group(1)
            elif mode == "transition":
                m = re.fullmatch(r"(\w+)?\s+(\w+)\s+(\d+)\s*", line)
                if m and m.group(2) not in ("N-State",):
                    prev = m.group(1) or prev
                    if m.group(3) == "0":
                        yield name, fsm, "transition", f"{prev} -> {m.group(2)}"


def parse(report: Path):
    """Yield (instance, block_index, source, kind, case_item) per uncovered block."""
    for name, body in _sections(report):
        sec = re.search(r"Block Detail Report.*?(?=Expression Detail|Toggle Detail|\Z)",
                        body, re.S)
        if not sec:
            continue
        case_item = ""
        for hit, idx, _line, kind, _org, src in re.findall(
                r"^(\d+)\s+(\d+)\s+(\d+)\s+(\S.*?)\s{2,}(\d+)\s+(.*)$", sec.group(0), re.M):
            if kind == "a case item of":
                case_item = src.strip()
            if hit == "0":
                yield name, idx, src.strip(), kind, case_item


def parse_exprs(report: Path):
    """Yield (instance, row_index, source, terms) per uncovered expression row."""
    for name, body in _sections(report):
        sec = re.search(r"Expression Detail Report.*?(?=Toggle Detail|\Z)", body, re.S)
        if not sec:
            continue
        source = ""
        for line in sec.group(0).splitlines():
            m = re.match(r"index: \S+ grade: .* source: (.*)$", line)
            if m:
                source = m.group(1).strip()
                continue
            cols = [c.strip() for c in line.split("|")]
            if len(cols) in (3, 4) and re.fullmatch(r"\d+\.\d+\.\d+", cols[0]) \
                    and cols[1] == "0":
                yield name, cols[0], source, " ".join(cols[-1].split())


def _imc_toggle_name(sig: str) -> str:
    """
    The name imc's `exclude -toggle` accepts for a report signal.

    The report prints a packed-struct field as `sbcs_q.sbversion[31]`, but imc
    names it `"sbcs_q.sbversion"[31]` -- quoted field path, bare index. The
    unquoted form is rejected with *W,NOMATCH, which does not fail the run:
    every struct-field exclusion was silently dropped that way before this.
    """
    m = re.fullmatch(r"(.+?)(\[\d+\])?", sig)
    base, idx = m.group(1), m.group(2) or ""
    return f'"{base}"{idx}' if "." in base else sig


def _rule_matches(rule, inst, src, kind, case_item) -> bool:
    _name, pat, _why, _when, *extra = rule
    f = extra[0] if extra else {}
    return (re.search(pat, src) is not None
            and re.search(f.get("inst", ""), inst) is not None
            and re.search(f.get("kind", ""), kind) is not None
            and re.search(f.get("case", ""), case_item) is not None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("report")
    ap.add_argument("--out", default="dm_exclusions.tcl")
    a = ap.parse_args()

    rows = list(parse(Path(a.report)))
    if not rows:
        return int(bool(sys.stderr.write(
            f"{a.report}: no uncovered blocks found -- wrong file, or nothing to exclude\n")))

    matched: dict[str, list] = {r[0]: [] for r in RULES}
    unmatched = []
    for inst, idx, src, kind, case_item in rows:
        for r in RULES:
            if _rule_matches(r, inst, src, kind, case_item):
                matched[r[0]].append((inst, idx, src))
                break
        else:
            unmatched.append((inst, idx, src))

    out = ["# " + "=" * 74,
           "# Debug Module code-coverage exclusions -- GENERATED, do not hand-edit.",
           "#   python3 mk/dm_cov_exclude.py <dm_code.rpt> --out <this file>",
           "#",
           "# Each exclusion states why the code is unreachable ON THIS DUT and what",
           "# would make it reachable again. Nothing is excluded for being hard.",
           "# " + "=" * 74, ""]
    total = 0
    for rule, _pat, why, when, *_ in RULES:
        hits = matched[rule]
        out.append(f"# ---- {rule} ({len(hits)} block(s)) ----")
        out += [f"#   why       : {why}", f"#   reachable : {when}"]
        if not hits:
            out.append("#   NO LONGER MATCHES -- the code is covered or gone; delete this rule.")
        for inst, idx, src in hits:
            total += 1
            out.append(f'exclude -inst {{{inst}}} -block {idx} '
                       f'-comment {{{rule}: {why}}}')
        out.append("")
    # ── expression exclusions ────────────────────────────────────────────
    ematched: dict[str, list] = {r[0]: [] for r in EXPR_RULES}
    eunmatched = []
    for inst, row, src, terms in parse_exprs(Path(a.report)):
        for rule, spat, tpat, _why, _when, ipat in EXPR_RULES:
            if re.search(ipat, inst) and re.search(spat, src) and re.search(tpat, terms):
                ematched[rule].append((inst, row))
                break
        else:
            eunmatched.append((inst, row, src, terms))
    out += ["", "# " + "=" * 74,
            "# Expression exclusions -- one row of one expression's truth table.",
            "# " + "=" * 74, ""]
    for rule, _s, _t, why, when, _i in EXPR_RULES:
        hits = ematched[rule]
        out.append(f"# ---- {rule} ({len(hits)} row(s)) ----")
        out += [f"#   why       : {why}", f"#   reachable : {when}"]
        if not hits:
            out.append("#   NO LONGER MATCHES -- delete this rule.")
        for inst, row in hits:
            total += 1
            out.append(f'exclude -inst {{{inst}}} -expression {row} '
                       f'-comment {{{rule}: {why}}}')
        out.append("")

    # ── toggle exclusions ────────────────────────────────────────────────
    tog = list(parse_toggles(Path(a.report)))
    tmatched: dict[str, list] = {r[0]: [] for r in TOGGLE_RULES}
    tunmatched = []
    for inst, sig in tog:
        for rule, pat, _why, _when, *ipat in TOGGLE_RULES:
            if re.search(pat, sig) and (not ipat or re.search(ipat[0], inst)):
                tmatched[rule].append((inst, sig))
                break
        else:
            tunmatched.append((inst, re.sub(r"\[\d+\]$", "", sig)))
    if tog:
        out += ["", "# " + "=" * 74,
                "# Toggle exclusions -- stated per signal or field, because a field a",
                "# parameter fixes is one fact about the DUT, not one per bit.",
                "# " + "=" * 74, ""]
        for rule, _pat, why, when, *_ in TOGGLE_RULES:
            hits = tmatched[rule]
            out.append(f"# ---- {rule} ({len(hits)} bit(s)) ----")
            out += [f"#   why       : {why}", f"#   reachable : {when}"]
            if not hits:
                out.append("#   NO LONGER MATCHES -- delete this rule.")
            for inst, sig in hits:
                total += 1
                out.append(f'exclude -inst {{{inst}}} -toggle {{{_imc_toggle_name(sig)}}} '
                           f'-comment {{{rule}: {why}}}')
            out.append("")

    flines, fcount, fsm_holes = emit_fsm(Path(a.report))
    out += flines
    total += fcount

    blines, bcount, bscoped = emit_boundary(Path(a.report))
    out += blines
    total += bcount

    Path(a.out).write_text("\n".join(out) + "\n", encoding="utf-8")

    print(f"wrote {a.out}: {total} exclusion(s) across "
          f"{sum(1 for r in RULES if matched[r[0]]) + sum(1 for r in EXPR_RULES if ematched[r[0]])} rule(s)")
    if eunmatched:
        print(f"\n{len(eunmatched)} uncovered expression row(s) NOT excluded -- real holes:")
        for inst, row, src, terms in eunmatched:
            print(f"  {inst.split('.')[-1]:<12} {row:<8} [{terms}]  {src[:56]}")
    if fsm_holes:
        print(f"\n{len(fsm_holes)} unvisited FSM state(s)/transition(s) -- real holes:")
        for inst, kind, what in fsm_holes:
            print(f"  {inst.split('.')[-1]:<16} {kind:<10} {what}")
    # Items the boundary rule excluded are out of scope and not holes. Items it
    # KEPT -- the DM's own bus and JTAG signals -- are in scope, so they stay.
    tunmatched = [(i, b) for i, b in tunmatched if (i, "toggle", b) not in bscoped]
    unmatched = [(i, x, src) for i, x, src in unmatched if (i, "block", x) not in bscoped]
    if tunmatched:
        import collections
        c = collections.Counter(b for _i, b in tunmatched)
        print(f"\n{len(tunmatched)} untoggled bit(s) NOT excluded -- real toggle "
              f"holes, top signal groups:")
        for base, n in c.most_common(12):
            print(f"  {base:<34} {n:>5} bits")
    if unmatched:
        print(f"\n{len(unmatched)} uncovered block(s) NOT excluded -- these are real "
              f"coverage holes, not unreachable code:")
        for inst, idx, src in unmatched[:40]:
            print(f"  {inst.split('.')[-1]:<12} block {idx:<4} {src[:64]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
