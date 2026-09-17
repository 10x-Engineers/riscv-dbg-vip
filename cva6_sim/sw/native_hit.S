# native_hit.S -- NATIVE-OP5: telling triggers apart by their hit bits.
#
# mcause=3 says only that some trigger fired. A native monitor finds which one
# from the hit bits (mcontrol6 hit0/hit1, {hit1,hit0}=01 for a trigger that
# fired before its instruction). Two U-mode execute triggers on two
# instructions; each breakpoint must set the hit bits of the trigger that fired
# and of no other, and `tval` must be the matched address (the faulting virtual
# address of an instruction address breakpoint).
#
#   trigger 0 -> u_first, trigger 1 -> u_second; U runs u_first then u_second.

#include "native_common.h"

#define MC6_HIT_BITS ((1 << 25) | (1 << 22))
#define MC6_U_EXEC   (TYPE_MCONTROL6 | MC6_U | MC6_EXECUTE)

        NATIVE_START
native_main:
        li      t0, 0
        csrw    CSR_TSELECT, t0
        la      t0, u_first
        csrw    CSR_TDATA2, t0
        li      t0, MC6_U_EXEC
        csrw    CSR_TDATA1, t0
        li      t0, 1
        csrw    CSR_TSELECT, t0
        la      t0, u_second
        csrw    CSR_TDATA2, t0
        li      t0, MC6_U_EXEC
        csrw    CSR_TDATA1, t0
        csrr    t1, CSR_TDATA1
        CHECK_EQ(0x10, t1, MC6_U_EXEC)          # trigger 1 exists and took the config
        ON_M_TRAP(first_bp)
        MRET_TO(u_first, PRV_U)

first_bp:
        LOAD(t1, m_cause)
        CHECK_EQ(0x11, t1, CAUSE_BREAKPOINT)
        LOAD(t1, m_epc)
        CHECK_SYM(0x12, t1, u_first)            # before the instruction
        LOAD(t1, m_tval)
        CHECK_SYM(0x13, t1, u_first)
        li      t0, 0
        csrw    CSR_TSELECT, t0
        csrr    t1, CSR_TDATA1
        li      t2, MC6_HIT_BITS
        and     t1, t1, t2
        CHECK_EQ(0x14, t1, 1 << 22)             # trigger 0: hit0 (fired before)
        DISABLE_TRIGGER(0, TYPE_MCONTROL6)      # so u_first can run; also clears hit
        li      t0, 1
        csrw    CSR_TSELECT, t0
        csrr    t1, CSR_TDATA1
        li      t2, MC6_HIT_BITS
        and     t1, t1, t2
        CHECK_EQ(0x15, t1, 0)                   # trigger 1: not hit
        ON_M_TRAP(second_bp)
        LOAD(t1, m_epc)
        csrw    mepc, t1
        mret                                    # MPP is still U

second_bp:
        LOAD(t1, m_cause)
        CHECK_EQ(0x21, t1, CAUSE_BREAKPOINT)
        LOAD(t1, m_epc)
        CHECK_SYM(0x22, t1, u_second)
        LOAD(t1, m_tval)
        CHECK_SYM(0x23, t1, u_second)
        li      t0, 1
        csrw    CSR_TSELECT, t0
        csrr    t1, CSR_TDATA1
        li      t2, MC6_HIT_BITS
        and     t1, t1, t2
        CHECK_EQ(0x24, t1, 1 << 22)             # trigger 1: hit0
        li      t0, 0
        csrw    CSR_TSELECT, t0
        csrr    t1, CSR_TDATA1
        li      t2, MC6_HIT_BITS
        and     t1, t1, t2
        CHECK_EQ(0x25, t1, 0)                   # trigger 0 (disabled): not hit again
        DISABLE_TRIGGER(1, TYPE_MCONTROL6)
        ON_M_TRAP(done)
        LOAD(t1, m_epc)
        csrw    mepc, t1
        mret

done:
        LOAD(t1, m_cause)
        CHECK_EQ(0x31, t1, CAUSE_ECALL_U)
        LOAD(t1, m_count)
        CHECK_EQ(0x32, t1, 3)
        j       native_pass

# ── U-mode code ──────────────────────────────────────────────────────────────
u_first:
        addi    s1, s1, 1
        addi    s1, s1, 1
u_second:
        addi    s1, s1, 1
        ecall

        NATIVE_END
