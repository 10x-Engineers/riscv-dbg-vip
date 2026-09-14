# priv_irq.S — run in M, S and U, with a timer interrupt left pending.
#
# Three coverpoints need this and cannot be filled from an M-mode-only program:
#
#   cg_debug_entry.cp_prv            entry privilege seen as U, S and M
#   cg_step_external.cp_prv_at_step  same, at the moment of a step
#   cg_step_external.cp_stepie_irq   the {stepie, irq_pending} 2x2, which needs
#                                    an interrupt that is genuinely pending
#
# The interrupt is the CLINT timer: mtimecmp is armed close to mtime so MTIP
# asserts and then STAYS asserted, because nothing ever services it. A
# permanently-pending interrupt is what the stepie cross needs; a self-clearing
# one is only pending for the few cycles nobody is looking.
#
# mstatus.MIE is left CLEAR throughout. mie.MTIE is set so MTIP shows up in
# (mip & mie), which is what the coverage samples, while the global enable stays
# off so the hart does not actually take the trap and leave the privilege under
# test. A pending interrupt is the point, not a taken one.
#
# Keeping MIE clear takes more than never setting it: `mret` restores
# mstatus.MIE from mstatus.MPIE. Leaving MPIE set with MTIP pending means every
# mret re-enables interrupts and the timer fires again immediately. An earlier
# version did exactly that and spun in the handler forever -- 90 single-steps
# never reached the program body and every privilege bin but M stayed empty.
# So MPIE is cleared before each mret below.
#
# The dispatcher is a state counter in s1, not mcause decoding. An earlier
# version routed on mcause and an unexpected trap fell into a generic
# "skip the instruction and return" path, which re-entered the same trap
# forever -- 90 single-steps never left the handler and every privilege bin
# stayed empty except M. A counter cannot do that: every trap advances the
# state, so the worst case is visiting a state early, not looping in one.

        .equ CLINT_MTIMECMP, 0x02004000
        .equ CLINT_MTIME,    0x0200BFF8

        .equ MSTATUS_MPP,    0x1800      # MPP field mask
        .equ MSTATUS_MPP_S,  0x0800      # MPP = 01 (S)
        .equ MSTATUS_MPP_M,  0x1800      # MPP = 11 (M)
        .equ MIE_MTIE,       0x0080
        .equ MSTATUS_MPIE,   0x0080      # mstatus.MPIE, bit 7

        .section .text.start, "ax", @progbits
        .globl _start
        .globl main
        .globl m_mode_work
        .globl s_mode_work
        .globl u_mode_work
        .globl arm_timer

_start:
main:
        la      t0, trap_handler
        csrw    mtvec, t0
        # Every trap goes to M, so the handler below is the only one that runs
        # and S/U code cannot vector somewhere unmapped.
        csrw    medeleg, zero
        csrw    mideleg, zero
        li      s1, 0                   # dispatcher state

# ── Arm the timer so MTIP asserts and stays asserted ─────────────────────
arm_timer:
        li      t0, CLINT_MTIME
        ld      t1, 0(t0)
        addi    t1, t1, 128
        li      t2, CLINT_MTIMECMP
        sd      t1, 0(t2)
        li      t0, MIE_MTIE
        csrs    mie, t0

# ── M-mode body ──────────────────────────────────────────────────────────
# Several instructions so a step has a reasonable chance of landing here, and
# a mix of widths so the ordinary and compressed class bins fill in M too.
m_mode_work:
        addi    a0, a0, 1
        c.addi  a1, 1
        addi    a0, a0, 1
        c.addi  a1, 1
        nop
        nop

# ── Drop to S ────────────────────────────────────────────────────────────
        li      s1, 1                   # next trap means "came from S"
        la      t0, s_mode_work
        csrw    mepc, t0
        li      t1, MSTATUS_MPP
        csrc    mstatus, t1             # MPP = 00
        li      t1, MSTATUS_MPP_S
        csrs    mstatus, t1             # MPP = 01 (S)
        li      t1, MSTATUS_MPIE
        csrc    mstatus, t1             # MPIE = 0, so mret leaves MIE = 0
        mret

s_mode_work:
        addi    a2, a2, 1
        c.addi  a3, 1
        addi    a2, a2, 1
        c.addi  a3, 1
        nop
        nop
        ecall                           # -> handler, state 1

# ── Drop to U (entered from the handler) ─────────────────────────────────
to_u_mode:
        li      s1, 2                   # next trap means "came from U"
        la      t0, u_mode_work
        csrw    mepc, t0
        li      t1, MSTATUS_MPP
        csrc    mstatus, t1             # MPP = 00 (U)
        li      t1, MSTATUS_MPIE
        csrc    mstatus, t1             # MPIE = 0
        mret

u_mode_work:
        addi    a4, a4, 1
        c.addi  a5, 1
        addi    a4, a4, 1
        c.addi  a5, 1
        nop
        nop
        ecall                           # -> handler, state 2

loop_head:
        addi    a6, a6, 1
        li      s1, 0
        j       arm_timer

# ── Trap handler, always M ───────────────────────────────────────────────
# Dispatch on s1, never on mcause. Whatever the trap was, the state says where
# to go next, so an unexpected trap costs one wasted pass rather than wedging
# the program. MPP is set to M explicitly before every return, because the
# trap may have arrived from S or U and mret returns to whatever MPP holds.
        .align 2
trap_handler:
        li      t1, MSTATUS_MPP_M
        csrs    mstatus, t1             # return to M whatever we came from
        li      t1, MSTATUS_MPIE
        csrc    mstatus, t1             # MPIE = 0, or mret re-enables the timer

        li      t0, 1
        beq     s1, t0, h_from_s
        li      t0, 2
        beq     s1, t0, h_from_u

        # State 0 or anything unexpected: restart the cycle. Skipping the
        # faulting instruction is deliberately NOT done here -- that is the
        # path that looped forever.
        la      t0, loop_head
        csrw    mepc, t0
        mret

h_from_s:
        la      t0, to_u_mode
        csrw    mepc, t0
        mret

h_from_u:
        la      t0, loop_head
        csrw    mepc, t0
        mret
