# native_dbgcsr.S -- NATIVE-OP7: the Debug Mode CSRs are not reachable natively.
#
# Sdext: dcsr, dpc, dscratch0 and dscratch1 are only accessible from Debug
# Mode. From M-mode (the most privileged native mode), reading or writing any
# of them must raise an illegal instruction exception, and must not change it.
#
# Each access traps to the M handler, whose hook checks mcause=2 and the
# faulting address and carries straight on with the next access (still in M,
# never returning). A CSR access that does not trap falls through into a
# failure.

#include "native_common.h"

// `op a, b` must raise an illegal-instruction trap at that address.
#define EXPECT_ILLEGAL(name, id, op, a, b)      \
        ON_M_TRAP(name##_trap);                 \
name##_at:                                      \
        op      a, b;                           \
        li      a0, id + 0x40;                  \
        li      a1, 0;                          \
        li      a2, 1;                          \
        j       native_fail_now;                \
name##_trap:                                    \
        LOAD(t1, m_cause);                      \
        CHECK_EQ(id, t1, CAUSE_ILLEGAL);        \
        LOAD(t1, m_epc);                        \
        CHECK_SYM(id + 0x80, t1, name##_at)

        NATIVE_START
native_main:
        EXPECT_ILLEGAL(rd_dcsr,  0x1, csrr, t2, CSR_DCSR)
        EXPECT_ILLEGAL(rd_dpc,   0x2, csrr, t2, CSR_DPC)
        EXPECT_ILLEGAL(rd_dscr0, 0x3, csrr, t2, CSR_DSCRATCH0)
        EXPECT_ILLEGAL(rd_dscr1, 0x4, csrr, t2, CSR_DSCRATCH1)
        EXPECT_ILLEGAL(wr_dpc,   0x5, csrw, CSR_DPC, zero)
        EXPECT_ILLEGAL(wr_dscr0, 0x6, csrw, CSR_DSCRATCH0, zero)
        EXPECT_ILLEGAL(wr_dcsr,  0x7, csrw, CSR_DCSR, zero)
        LOAD(t1, m_count)
        CHECK_EQ(0x10, t1, 7)
        j       native_pass

        NATIVE_END
