# step_stall_probe.S — a loop with a stalling instruction, to be single-stepped.
#
# Sdext, "Step Bit In Dcsr": "If the instruction being stepped over would
# normally stall the hart, then instead the instruction is treated as a `nop`.
# This includes `wfi`, `wrs.sto`, and `wrs.nto`."
#
# Without that rule a debugger deadlocks itself: during a step dcsr.stepie=0
# masks the interrupts that would wake a wfi, and the debugger must not assert
# haltreq, because re-halting unaided is the property under test.
#
# wfi_insn is .globl so the test can resolve its address from the symbol table
# instead of carrying a hardcoded constant. Edit this file, run `make`, and the
# test picks up the new address by itself.
#
# Only wfi is exercised: wrs.sto and wrs.nto are Zawrs, which this DUT does not
# implement, so they would decode as illegal instructions and test the trap
# handler rather than the step rule.

        .section .text.start, "ax", @progbits
        .globl _start
        .globl main
        .globl stall_loop
        .globl wfi_insn

_start:
main:
        li      x1,  1
        li      x2,  2
        li      x3,  3

stall_loop:
        addi    x1, x1, 1       # before: an ordinary step, the control
wfi_insn:
        wfi                     # the instruction under test
        addi    x2, x2, 1       # after: reached only if the wfi completed
        j       stall_loop
