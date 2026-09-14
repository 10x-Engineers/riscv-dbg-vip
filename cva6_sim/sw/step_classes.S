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

never_taken:
        # Only reached if a not-taken branch was taken. Park loudly rather
        # than falling through into the trap handler.
        j       never_taken

# ── trap handler ─────────────────────────────────────────────────────────
# Skips the faulting instruction and returns. mepc points at the instruction
# that trapped; advancing by 4 resumes after it. Both traps raised above come
# from 4-byte instructions, so a fixed +4 is correct here and would not be in
# a handler meant for general use.
        .align 2
trap_handler:
        csrr    t0, mepc
        addi    t0, t0, 4
        csrw    mepc, t0
        mret                            # -> ICLASS_PRIV_CHANGE

        .section .data
        .align 3
scratch_area:
        .dword 0
        .dword 0
