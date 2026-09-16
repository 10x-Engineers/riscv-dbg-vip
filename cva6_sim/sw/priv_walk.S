# priv_walk.S — cycle M -> S -> U -> M, and nothing else.
#
# Fills cg_debug_entry.cp_prv and cg_step_external.cp_prv_at_step, which an
# M-mode-only program cannot reach.
#
# Deliberately minimal. An earlier version armed a CLINT timer in the same
# program to also fill the {stepie, irq_pending} cross, and spent far longer in
# M setting that up than it did in S and U combined -- a halt landed in M ~85%
# of the time. Worse, any fault in that setup returned into the same fault and
# the hart spun in the trap handler, so 40 single-steps covered five
# instructions. Two behaviours, two programs: the interrupt cross belongs in its
# own test where a failure means one thing.
#
# Everything here is an addi, a nop, or the minimum CSR work to change
# privilege. No memory access at all, so there is nothing to fault on.

        .equ MSTATUS_MPP,    0x1800      # MPP field
        .equ MSTATUS_MPP_S,  0x0800      # MPP = 01 (S)
        .equ MSTATUS_MPP_M,  0x1800      # MPP = 11 (M)

        .section .text.start, "ax", @progbits
        .globl _start
        .globl main
        .globl m_block
        .globl s_block
        .globl u_block

_start:
main:
        la      t0, trap_handler
        csrw    mtvec, t0
        csrw    medeleg, zero           # every trap to M
        csrw    mideleg, zero

# ── M ────────────────────────────────────────────────────────────────────
# Kept short on purpose: M already gets the whole trap handler and both mret
# setups, so it does not need a long body to be well represented.
m_block:
        addi    a0, a0, 1
        addi    a0, a0, 1
        nop
        nop

# ── M -> S ───────────────────────────────────────────────────────────────
        la      t0, s_block
        csrw    mepc, t0
        li      t1, MSTATUS_MPP
        csrc    mstatus, t1             # MPP = 00
        li      t1, MSTATUS_MPP_S
        csrs    mstatus, t1             # MPP = 01 (S)
        mret

# ── S ────────────────────────────────────────────────────────────────────
# Long, so a halt or a short step walk lands here often. 24 instructions of
# pure arithmetic: nothing that can trap, so the only way out is the ecall.
s_block:
        addi    a2, a2, 1
        addi    a2, a2, 1
        addi    a2, a2, 1
        addi    a2, a2, 1
        addi    a2, a2, 1
        addi    a2, a2, 1
        addi    a2, a2, 1
        addi    a2, a2, 1
        nop
        nop
        nop
        nop
        addi    a3, a3, 1
        addi    a3, a3, 1
        addi    a3, a3, 1
        addi    a3, a3, 1
        addi    a3, a3, 1
        addi    a3, a3, 1
        addi    a3, a3, 1
        addi    a3, a3, 1
        nop
        nop
        nop
        ecall                           # -> handler, s1 says "next is U"

# ── M -> U (entered from the handler) ────────────────────────────────────
to_u:
        la      t0, u_block
        csrw    mepc, t0
        li      t1, MSTATUS_MPP
        csrc    mstatus, t1             # MPP = 00 (U)
        mret

# ── U ────────────────────────────────────────────────────────────────────
u_block:
        addi    a4, a4, 1
        addi    a4, a4, 1
        addi    a4, a4, 1
        addi    a4, a4, 1
        addi    a4, a4, 1
        addi    a4, a4, 1
        addi    a4, a4, 1
        addi    a4, a4, 1
        nop
        nop
        nop
        nop
        addi    a5, a5, 1
        addi    a5, a5, 1
        addi    a5, a5, 1
        addi    a5, a5, 1
        addi    a5, a5, 1
        addi    a5, a5, 1
        addi    a5, a5, 1
        addi    a5, a5, 1
        nop
        nop
        nop
        ecall                           # -> handler, back to the top

# ── Trap handler, always entered in M ────────────────────────────────────
# Alternates between "go to U" and "go back to the top" using s1, so the cycle
# runs forever without ever needing to decode mcause. Whatever the trap was,
# the state says where to go next, so an unexpected trap costs one pass of the
# cycle rather than repeating itself forever -- which is what a generic
# "skip the faulting instruction and return" fallback does.
        .align 2
trap_handler:
        li      t1, MSTATUS_MPP_M
        csrs    mstatus, t1             # return to M whatever we came from

        li      t0, 1
        beq     s1, t0, go_u

        # s1 != 1: the trap came from U (or this is the first pass). Restart.
        li      s1, 1
        la      t0, main
        csrw    mepc, t0
        mret

go_u:
        li      s1, 0
        la      t0, to_u
        csrw    mepc, t0
        mret
