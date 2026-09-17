# native_reentrancy.S -- NATIVE-OP4: an action=0 trigger inside a trap handler.
#
# Sdtrig "Native Triggers": a trigger with action=0 that fires in the mode that
# handles its breakpoint re-enters the handler and overwrites mcause/mepc.
# Harts supporting action=0 SHOULD prevent that one of two ways:
#   1. no action=0 trigger matches or fires in M-mode while mstatus.MIE=0, or
#   2. tcontrol.mte/mpte is implemented and medeleg[3] is hard-wired to 0.
# CVA6 implements no tcontrol (the CSR traps), so it must be option 1.
#
#   case 1 (control): an M-mode execute trigger on m_target, reached from M
#                     with MIE=1 -> fires; mepc = m_target.
#   case 2: the same trigger on h_target, an instruction inside the M trap
#           handler (MIE=0 there, as for every trap) -> must NOT fire.
#   case 3: tcontrol (0x7a5) is absent -> illegal instruction, which is why
#           option 1 is the one that applies.

#include "native_common.h"

#define CSR_TCONTROL 0x7a5
#define MC6_M_EXEC   (TYPE_MCONTROL6 | MC6_M | MC6_EXECUTE)

        NATIVE_START
native_main:
# ── case 3: no tcontrol ─────────────────────────────────────────────────────
        ON_M_TRAP(no_tcontrol)
tcontrol_read:
        csrr    t1, CSR_TCONTROL
        li      a0, 0x30                        # read succeeded: tcontrol exists
        mv      a1, t1
        li      a2, 0
        j       native_fail_now
no_tcontrol:
        LOAD(t1, m_cause)
        CHECK_EQ(0x31, t1, CAUSE_ILLEGAL)
        LOAD(t1, m_epc)
        CHECK_SYM(0x32, t1, tcontrol_read)

# ── case 1: MIE=1 in M -> the trigger fires ─────────────────────────────────
        li      t0, 0
        csrw    CSR_TSELECT, t0
        la      t0, m_target
        csrw    CSR_TDATA2, t0
        li      t0, MC6_M_EXEC
        csrw    CSR_TDATA1, t0
        ON_M_TRAP(case1_bp)
        csrsi   mstatus, MSTATUS_MIE            # mie=0, so no interrupt can be taken
m_target:
        addi    s1, s1, 1
        li      a0, 0x10                        # fell through: the control did not fire
        li      a1, 0
        li      a2, 1
        j       native_fail_now

case1_bp:
        LOAD(t1, m_cause)
        CHECK_EQ(0x11, t1, CAUSE_BREAKPOINT)
        LOAD(t1, m_epc)
        CHECK_SYM(0x12, t1, m_target)
        csrci   mstatus, MSTATUS_MIE            # MIE is already 0 in the handler; keep it so

# ── case 2: MIE=0 in the handler -> the trigger must not fire ──────────────
        la      t0, h_target
        csrw    CSR_TDATA2, t0                  # trigger 0 is still armed (mcontrol6, m, execute)
        ON_M_TRAP(case2_bp)                     # only reached if it (wrongly) fires
h_target:
        addi    s2, s2, 1                       # executed in the handler, MIE=0
        LOAD(t1, m_count)
        CHECK_EQ(0x21, t1, 2)                   # tcontrol trap + case 1; nothing new
        DISABLE_TRIGGER(0, TYPE_MCONTROL6)
        j       native_pass

case2_bp:
        li      a0, 0x22                        # fired with MIE=0: re-entered the handler
        LOAD(a1, m_epc)
        la      a2, h_target
        j       native_fail_now

        NATIVE_END
