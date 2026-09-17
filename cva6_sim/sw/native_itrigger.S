# native_itrigger.S -- NATIVE-OP2: an interrupt trigger (itrigger), action=0.
#
# Sdtrig itrigger: when an interrupt whose code bit is set in tdata2 is taken
# from an enabled mode, the trigger fires just before the first instruction of
# the handler, as a breakpoint exception with tval written 0. As for etrigger,
# the testable native case is an interrupt delegated to S with breakpoints kept
# in M: the supervisor software interrupt (code 1), delegated with mideleg[1],
# raised by M through mip.SSIP, and taken from U (S-level interrupts are always
# enabled while in U).
#
#   case 1 (negative): trigger enabled for interrupts taken from S only; the
#                      interrupt taken from U reaches the S handler directly.
#   case 2: trigger enabled for U; the interrupt is taken to S and then, before
#           the S handler runs, the breakpoint goes to M with mcause=3,
#           mepc=stvec, mtval=0, MPP=S; scause/sepc of the interrupt intact.

#include "native_common.h"

#define SSIP (1 << 1)

        NATIVE_START
native_main:
        li      t0, SSIP
        csrw    mideleg, t0                     # SSI -> S
        csrs    mie, t0                         # sie.SSIE
        li      t0, 0
        csrw    CSR_TSELECT, t0
        li      t0, SSIP
        csrw    CSR_TDATA2, t0
        csrr    t1, CSR_TDATA2
        CHECK_EQ(0x10, t1, SSIP)                # the interrupt code is supported

# ── case 1: enabled for S only -> an interrupt from U does not fire it ──────
        li      t0, TYPE_ITRIGGER | IE_S
        csrw    CSR_TDATA1, t0
        ON_S_TRAP(case1_s_trap)
        li      t0, SSIP
        csrs    mip, t0                         # raise SSI; taken once in U
        MRET_TO(u_wait1, PRV_U)

u_wait1:
        j       u_wait1

case1_s_trap:
        LOAD(t1, s_cause)
        CHECK_EQ(0x11, t1, INTR_SSI)
        LOAD(t1, s_epc)
        CHECK_SYM(0x12, t1, u_wait1)
        li      t0, SSIP
        csrc    sip, t0                         # S clears its own SSIP
        la      t0, u_done1
        csrw    sepc, t0
        sret
u_done1:
        ON_M_TRAP(case1_ecall)                  # (writes .data from U: PMP is open)
        ecall

case1_ecall:
        LOAD(t1, m_cause)
        CHECK_EQ(0x13, t1, CAUSE_ECALL_U)
        LOAD(t1, m_count)
        CHECK_EQ(0x14, t1, 1)                   # no breakpoint before the ecall

# ── case 2: enabled for U -> breakpoint to M at the S handler's entry ──────
        li      t0, TYPE_ITRIGGER | IE_U
        csrw    CSR_TDATA1, t0
        ON_M_TRAP(case2_bp)
        ON_S_TRAP(case2_s_trap)
        li      t0, SSIP
        csrs    mip, t0
        MRET_TO(u_wait2, PRV_U)

u_wait2:
        j       u_wait2

case2_bp:
        LOAD(t1, m_cause)
        CHECK_EQ(0x21, t1, CAUSE_BREAKPOINT)
        LOAD(t1, m_epc)
        CHECK_SYM(0x22, t1, s_handler)
        LOAD(t1, m_tval)
        CHECK_EQ(0x23, t1, 0)
        LOAD(t1, m_status)
        srli    t1, t1, 11
        andi    t1, t1, 3
        CHECK_EQ(0x24, t1, PRV_S)
        csrr    t1, scause
        CHECK_EQ(0x25, t1, INTR_SSI)
        csrr    t1, sepc
        CHECK_SYM(0x26, t1, u_wait2)
        csrr    t1, CSR_TDATA1
        li      t2, IE_HIT
        and     t1, t1, t2
        CHECK_EQ(0x27, t1, IE_HIT)
        DISABLE_TRIGGER(0, TYPE_ITRIGGER)
        LOAD(t1, m_epc)
        csrw    mepc, t1                        # back into the S handler
        mret

case2_s_trap:
        LOAD(t1, s_cause)
        CHECK_EQ(0x28, t1, INTR_SSI)
        li      t0, SSIP
        csrc    sip, t0
        la      t0, u_done2
        csrw    sepc, t0
        sret
u_done2:
        ON_M_TRAP(case2_ecall)
        ecall

case2_ecall:
        LOAD(t1, m_cause)
        CHECK_EQ(0x29, t1, CAUSE_ECALL_U)
        LOAD(t1, m_count)
        CHECK_EQ(0x2A, t1, 3)                   # ecall, breakpoint, ecall
        j       native_pass

        NATIVE_END
