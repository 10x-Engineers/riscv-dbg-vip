# step_classes.S — one instruction of every class the step coverage bins.
#
# cg_step_external.cp_stepped_class needs a hart that actually executes each
# class while dcsr.step is set. A program of `li` instructions only ever fills
# the ordinary and compressed bins, which is why those two were the only ones
# closed before this existed.
#
# Every class is reachable by stepping straight through from _start, so the
# sequence does not have to know where anything lives -- it steps N times and
# the coverage model bins whatever retired. The labels are .globl anyway, so a
# sequence that wants to assert *which* class it stepped can resolve them.
#
# Deliberately NOT included: wrs.sto / wrs.nto. Zawrs is absent on this DUT, so
# they decode as illegal instructions and would fill the trapping bin while
# looking like stalling-instruction coverage.

        .section .text.start, "ax", @progbits
        .globl _start
        .globl main
        .globl cls_ordinary
        .globl cls_compressed
        .globl cls_branch_taken
        .globl cls_branch_ntaken
        .globl cls_load
        .globl cls_store
        .globl cls_wfi
        .globl cls_ecall
        .globl cls_trap_insn
        .globl loop_head

_start:
main:
        # A trap handler is needed before anything that can trap. mtvec is
        # WARL; direct mode (low bits 0) is what the handler below assumes.
        la      t0, trap_handler
        csrw    mtvec, t0

        # Somewhere safe to load from and store to. The linker puts us at
        # DRAMBase, so a word well past the code is mapped and unused.
        la      s0, scratch_area

# ── ordinary: a full-width instruction that is not a branch, load or CSR ──
cls_ordinary:
        # norvc, or the assembler compresses these into c.addi and the ordinary
        # bin never fills -- the compressed bin fills twice instead, which looks
        # like coverage rather than like a hole.
        .option push
        .option norvc
        addi    a0, a0, 1               # 4-byte ADDI -> ICLASS_ORDINARY
        xori    a1, a1, 0x55
        .option pop

# ── compressed: 2-byte encodings ─────────────────────────────────────────
cls_compressed:
        c.addi  a2, 1                   # 2-byte -> ICLASS_COMPRESSED
        c.addi  a3, 1

# ── load and store ───────────────────────────────────────────────────────
cls_store:
        li      t1, 0xA5A5
        sw      t1, 0(s0)               # STORE -> ICLASS_LOAD_STORE
cls_load:
        lw      t2, 0(s0)               # LOAD  -> ICLASS_LOAD_STORE

# ── branch, not taken: the condition is false so it falls through ────────
cls_branch_ntaken:
        li      t3, 1
        li      t4, 2
        beq     t3, t4, never_taken     # 1 == 2 is false -> ICLASS_BRANCH_NTAKEN

# ── branch, taken ────────────────────────────────────────────────────────
cls_branch_taken:
        beq     t3, t3, taken_target    # always true -> ICLASS_BRANCH_TAKEN
        nop                             # skipped; reaching it means the branch
                                        # was mispredicted as not-taken
taken_target:
        addi    a4, a4, 1

# ── privilege change: ecall traps to the handler, mret returns ───────────
# ecall is FU_CSR/ECALL -> ICLASS_PRIV_CHANGE, and the trap it raises also
# exercises the trapping class on the following entry.
cls_ecall:
        ecall

# ── an instruction that traps for its own reason, not by request ─────────
# A load from address 0 faults: nothing is mapped there. This fills the
# trapping bin from a data access rather than from ecall, which is a
# different path through the commit stage.
cls_trap_insn:
        li      t5, 0
        lw      t6, 0(t5)               # -> exception -> ICLASS_TRAPPING

# ── wfi: the stalling instruction ────────────────────────────────────────
# Stepped, the spec requires this be treated as a nop. Halted into, the spec
# requires the hart leave the stalled state and complete it. Two different
# RTL paths, and this single instruction serves both tests.
cls_wfi:
        wfi

# ── loop back, so the hart is always executing something worth stepping ──
# A `j .` spin gives one instruction to step forever, where the PC never
# advances and no register changes. Looping the whole body means a halt lands
# on a known instruction and every class stays reachable on the next pass.
loop_head:
        addi    a5, a5, 1
        j       main

# ── an ebreak the debugger can jump to on purpose ─────────────────────────
# cg_debug_entry.cp_cause.ebreak needs a hart that executes `ebreak` in its own
# program with dcsr.ebreakm set, which is a different entry path from haltreq
# and cannot be reached by any DMI write. Parked out of the normal flow so it
# only executes when a sequence sets dpc to it deliberately; the spin after it
# keeps the hart somewhere harmless if debug entry does not happen.
        .globl cls_ebreak
        .globl ebreak_park
cls_ebreak:
        ebreak
ebreak_park:
        j       ebreak_park

# ── a fixed address for an execute trigger to match ───────────────────────
# cg_debug_entry.cp_cause.trigger needs a trigger to fire, which needs a known
# instruction address to arm tdata2 against.
#
# The debugger resumes at trigger_lead, one instruction BEFORE the target, so
# the trigger fires on an instruction the hart reaches by executing rather than
# on the first instruction after resume.
        .globl trigger_lead
        .globl cls_trigger_target
        .globl trigger_park
trigger_lead:
        addi    a5, a5, 1
cls_trigger_target:
        addi    a4, a4, 1
trigger_park:
        j       trigger_park

never_taken:
        # Only reached if a not-taken branch was taken. Park loudly rather
        # than falling through into the trap handler.
        j       never_taken

# ── a loop to single-step through, at any privilege ──────────────────────
# cg_step_external crosses each instruction class with stepie, a pending
# interrupt, the privilege level and the length of a run of consecutive
# steps. The main flow above only ever runs in M and is interrupted by
# haltreq, so the debugger instead points dpc here, sets dcsr.prv, and steps
# round this loop as many times as a bin needs. Every instruction is 4 bytes
# (norvc) because the trap handler resumes at mepc + 4. s0 must point at
# scratch_area; the debugger sets it before stepping.
        .globl step_loop
        .globl cls_sret
        .option push
        .option norvc
step_loop:
        wfi                             # WFI -- a nop while stepping; in U an illegal instruction
        li      t3, 1
        li      t4, 2
        beq     t3, t4, never_taken     # BRANCH_NTAKEN
        lw      t2, 0(s0)               # LOAD_STORE
        .word   0                       # an illegal instruction -> TRAPPING
        ecall                           # an exception too -> TRAPPING
        beq     t3, t3, step_loop       # BRANCH_TAKEN

# An xRET that is legal below M: stepped in S, this is PRIV_CHANGE at S (mret
# only runs in the handler, in M; in U every xRET is illegal).
#
# sepc is deliberately NOT the next instruction: a step over the sret must
# land on step_loop, and a DUT that lands on pc+4 instead (RTL-011) is then
# distinguishable. The jump after the sret is reached only in that case.
cls_sret:
        la      t0, step_loop
        csrw    sepc, t0
        li      t0, 0x100
        csrs    sstatus, t0             # SPP = S, so sret stays in S
sret_insn:
        sret                            # PRIV_CHANGE
sret_fallthrough:
        j       step_loop
        .option pop

# ── trap handler ─────────────────────────────────────────────────────────
# Skips the faulting instruction and returns. mepc points at the instruction
# that trapped; advancing by 4 resumes after it. Every trap the loops above
# raise comes from a 4-byte instruction, so a fixed +4 is correct here and
# would not be in a handler meant for general use. (A trap from cls_ebreak's
# 2-byte ebreak resumes 4 bytes on, at trigger_lead, which is harmless.)
        .align 2
trap_handler:
        csrr    t0, mepc
        addi    t0, t0, 4
        csrw    mepc, t0
handler_mret:
        mret                            # -> ICLASS_PRIV_CHANGE
handler_end:

        .section .data
        .align 3
scratch_area:
        .dword 0
        .dword 0
