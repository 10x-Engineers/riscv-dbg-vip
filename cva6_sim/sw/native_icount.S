# native_icount.S -- NATIVE-OP3: native single-step with an icount trigger.
#
# Sdtrig icount, action=0: the trigger fires after `count` instructions have run
# in an enabled mode, as a breakpoint exception, with `tval` written 0. The
# breakpoint is taken just before the next instruction, so mepc is the
# instruction after the last one counted. As it fires, `pending` is cleared.
#
# U-mode is the counted mode and the breakpoint goes to M -- the native-debug
# arrangement Sdtrig describes (a monitor in M stepping U code), with no
# re-entrancy question.
#
#   case 1: count=1 -> fires after u_a1, mepc = u_a2
#   case 2: count=2 -> fires after u_b2, mepc = u_b3
#   case 3: m-, s- and u-bits clear, count=1 -> never fires; U reaches its ecall

#include "native_common.h"

        NATIVE_START
native_main:
# ── case 1: count = 1 ───────────────────────────────────────────────────────
        li      t0, 0
        csrw    CSR_TSELECT, t0
        li      t0, TYPE_ICOUNT | IC_COUNT(1) | IC_U
        csrw    CSR_TDATA1, t0
        csrr    t1, CSR_TDATA1
        CHECK_EQ(0x10, t1, TYPE_ICOUNT | IC_COUNT(1) | IC_U)
        ON_M_TRAP(case1_trap)
        MRET_TO(u_a1, PRV_U)

case1_trap:
        LOAD(t1, m_cause)
        CHECK_EQ(0x11, t1, CAUSE_BREAKPOINT)
        LOAD(t1, m_epc)
        CHECK_SYM(0x12, t1, u_a2)
        LOAD(t1, m_tval)
        CHECK_EQ(0x13, t1, 0)
        LOAD(t1, m_status)
        srli    t1, t1, 11
        andi    t1, t1, 3
        CHECK_EQ(0x14, t1, PRV_U)           # the trap came from U
        csrr    t1, CSR_TDATA1
        li      t2, IC_PENDING
        and     t1, t1, t2
        CHECK_EQ(0x15, t1, 0)               # pending cleared as it fired
        li      t0, TYPE_ICOUNT | IC_COUNT(2) | IC_U
        csrw    CSR_TDATA1, t0
        ON_M_TRAP(case2_trap)
        MRET_TO(u_b1, PRV_U)

case2_trap:
        LOAD(t1, m_cause)
        CHECK_EQ(0x21, t1, CAUSE_BREAKPOINT)
        LOAD(t1, m_epc)
        CHECK_SYM(0x22, t1, u_b3)
        LOAD(t1, m_tval)
        CHECK_EQ(0x23, t1, 0)
        # case 3: no mode bits -> no trigger
        DISABLE_TRIGGER(0, TYPE_ICOUNT | IC_COUNT(1))
        ON_M_TRAP(case3_trap)
        MRET_TO(u_c1, PRV_U)

case3_trap:
        LOAD(t1, m_cause)
        CHECK_EQ(0x31, t1, CAUSE_ECALL_U)   # ran to the ecall untouched
        LOAD(t1, m_epc)
        CHECK_SYM(0x32, t1, u_ecall)
        LOAD(t1, m_count)
        CHECK_EQ(0x33, t1, 3)

# ── case 4: the same step, counted in S ─────────────────────────────────────
        li      t0, TYPE_ICOUNT | IC_COUNT(1) | IC_S
        csrw    CSR_TDATA1, t0
        ON_M_TRAP(case4_trap)
        MRET_TO(s_d1, PRV_S)

case4_trap:
        LOAD(t1, m_cause)
        CHECK_EQ(0x41, t1, CAUSE_BREAKPOINT)
        LOAD(t1, m_epc)
        CHECK_SYM(0x42, t1, s_d2)
        LOAD(t1, m_tval)
        CHECK_EQ(0x43, t1, 0)
        DISABLE_TRIGGER(0, TYPE_ICOUNT | IC_COUNT(1))
        j       native_pass

# ── U-mode code ──────────────────────────────────────────────────────────────
u_a1:   addi    s1, s1, 1
u_a2:   addi    s1, s1, 1
        j       u_a2                        # never reached: case 1 traps first

u_b1:   addi    s2, s2, 1
u_b2:   addi    s2, s2, 1
u_b3:   addi    s2, s2, 1
        j       u_b3

u_c1:   addi    s3, s3, 1
        addi    s3, s3, 1
u_ecall:
        ecall

# ── S-mode code, for the S pass ──────────────────────────────────────────────
s_d1:   addi    s4, s4, 1
s_d2:   addi    s4, s4, 1
        j       s_d2

        NATIVE_END
