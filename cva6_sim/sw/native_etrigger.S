# native_etrigger.S -- NATIVE-OP2: an exception trigger (etrigger), action=0.
#
# Sdtrig etrigger: when an exception whose cause bit is set in tdata2 is taken
# from an enabled mode, the trigger fires "after the trap occurs, just before
# the first instruction of the trap handler", as a breakpoint exception with
# tval written 0. Both re-entrancy options make that moot for traps handled in
# M-mode, so the case under test is the one Sdtrig describes for native debug:
# the exception is delegated to S (medeleg[2]=1), breakpoints are not
# (medeleg[3]=0), so the breakpoint goes from the S handler's entry to M.
#
#   case 1 (negative): trigger enabled for exceptions taken from U only; an
#                      illegal instruction in S traps to S with no breakpoint.
#   case 2: trigger enabled for S; the same illegal instruction traps to S and
#           then, before the S handler runs, to M with mcause=3, mepc=stvec,
#           mtval=0 and MPP=S. scause/sepc of the original trap are intact.

#include "native_common.h"

        NATIVE_START
native_main:
        li      t0, 1 << CAUSE_ILLEGAL
        csrw    medeleg, t0                     # illegal -> S; breakpoint stays in M
        li      t0, 0
        csrw    CSR_TSELECT, t0
        li      t0, 1 << CAUSE_ILLEGAL
        csrw    CSR_TDATA2, t0
        csrr    t1, CSR_TDATA2
        CHECK_EQ(0x10, t1, 1 << CAUSE_ILLEGAL)  # the cause is supported

# ── case 1: enabled for U only -> the S-mode exception does not fire it ─────
        li      t0, TYPE_ETRIGGER | IE_U
        csrw    CSR_TDATA1, t0
        ON_M_TRAP(case1_ecall)
        MRET_TO(s_case1, PRV_S)

s_case1:
        ON_S_TRAP(case1_s_trap)
s_case1_ill:
        .word   0                               # illegal instruction, taken in S
        ecall                                   # -> M
case1_s_trap:
        LOAD(t1, s_cause)
        CHECK_EQ(0x11, t1, CAUSE_ILLEGAL)
        LOAD(t1, s_epc)
        CHECK_SYM(0x12, t1, s_case1_ill)
        addi    t1, t1, 4
        csrw    sepc, t1
        sret

case1_ecall:
        LOAD(t1, m_cause)
        CHECK_EQ(0x13, t1, CAUSE_ECALL_S)       # no breakpoint came first
        LOAD(t1, m_count)
        CHECK_EQ(0x14, t1, 1)

# ── case 2: enabled for S -> breakpoint to M at the S handler's entry ──────
        li      t0, TYPE_ETRIGGER | IE_S
        csrw    CSR_TDATA1, t0
        ON_M_TRAP(case2_bp)
        MRET_TO(s_case2, PRV_S)

s_case2:
        ON_S_TRAP(case2_s_trap)
s_case2_ill:
        .word   0
        ecall

case2_bp:
        LOAD(t1, m_cause)
        CHECK_EQ(0x21, t1, CAUSE_BREAKPOINT)
        LOAD(t1, m_epc)
        CHECK_SYM(0x22, t1, s_handler)          # before the handler's first instruction
        LOAD(t1, m_tval)
        CHECK_EQ(0x23, t1, 0)
        LOAD(t1, m_status)
        srli    t1, t1, 11
        andi    t1, t1, 3
        CHECK_EQ(0x24, t1, PRV_S)
        csrr    t1, scause
        CHECK_EQ(0x25, t1, CAUSE_ILLEGAL)       # the original trap is intact
        csrr    t1, sepc
        CHECK_SYM(0x26, t1, s_case2_ill)
        csrr    t1, CSR_TDATA1
        li      t2, IE_HIT
        and     t1, t1, t2
        CHECK_EQ(0x27, t1, IE_HIT)              # hit set as it fired
        DISABLE_TRIGGER(0, TYPE_ETRIGGER)
        ON_M_TRAP(case2_ecall)
        LOAD(t1, m_epc)
        csrw    mepc, t1                        # back into the S handler
        mret

case2_s_trap:
        LOAD(t1, s_cause)
        CHECK_EQ(0x28, t1, CAUSE_ILLEGAL)
        LOAD(t1, s_epc)
        CHECK_SYM(0x29, t1, s_case2_ill)
        addi    t1, t1, 4
        csrw    sepc, t1
        sret

case2_ecall:
        LOAD(t1, m_cause)
        CHECK_EQ(0x2A, t1, CAUSE_ECALL_S)
        LOAD(t1, m_count)
        CHECK_EQ(0x2B, t1, 3)                   # ecall, breakpoint, ecall
        j       native_pass

        NATIVE_END
