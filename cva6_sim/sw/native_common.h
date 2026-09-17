// native_common.h -- shared scaffolding for the native-debug (Sdtrig action=0)
// programs, native_*.S.
//
// Each program checks itself and finishes the way riscv-arch-test programs do:
// it writes 1 (pass) or 3 (fail) to `tohost` and loops, so the pydebug run_elf
// scenario reports it without knowing anything about the program. On a failure
// `native_fail` holds {check id, actual, expected}; run_elf prints it.
//
// Trap handling is hook-based: the M- and S-mode handlers snapshot the trap
// CSRs, count the trap, and jump to whatever the program stored in m_hook /
// s_hook for the trap it expects next. A trap with no hook set fails the test,
// so an unexpected trap can never be silently skipped.
//
// Everything is 4-byte (norvc) so "the next instruction" is always +4.

#ifndef NATIVE_COMMON_H
#define NATIVE_COMMON_H

#define CSR_TSELECT   0x7a0
#define CSR_TDATA1    0x7a1
#define CSR_TDATA2    0x7a2
#define CSR_DCSR      0x7b0
#define CSR_DPC       0x7b1
#define CSR_DSCRATCH0 0x7b2
#define CSR_DSCRATCH1 0x7b3

// tdata1 types (Sdtrig), at [63:60] on RV64.
#define TYPE_ICOUNT    (3 << 60)
#define TYPE_ITRIGGER  (4 << 60)
#define TYPE_ETRIGGER  (5 << 60)
#define TYPE_MCONTROL6 (6 << 60)

// mcontrol6 fields.
#define MC6_HIT0      (1 << 22)
#define MC6_M         (1 << 6)
#define MC6_S         (1 << 4)
#define MC6_U         (1 << 3)
#define MC6_EXECUTE   (1 << 2)

// icount fields.
#define IC_HIT        (1 << 24)
#define IC_COUNT(n)   ((n) << 10)
#define IC_COUNT_MASK (0x3fff << 10)
#define IC_M          (1 << 9)
#define IC_PENDING    (1 << 8)
#define IC_S          (1 << 7)
#define IC_U          (1 << 6)

// itrigger / etrigger fields: hit at XLEN-6; m/s/u = trap taken FROM that mode.
#define IE_HIT        (1 << 58)
#define IE_M          (1 << 9)
#define IE_S          (1 << 7)
#define IE_U          (1 << 6)

#define CAUSE_ILLEGAL    2
#define CAUSE_BREAKPOINT 3
#define CAUSE_ECALL_U    8
#define CAUSE_ECALL_S    9
#define CAUSE_ECALL_M    11
#define INTR_SSI         ((1 << 63) | 1)

#define MSTATUS_SIE    (1 << 1)
#define MSTATUS_MIE    (1 << 3)
#define MSTATUS_MPIE   (1 << 7)
#define MSTATUS_MPP    (3 << 11)
#define MSTATUS_MPP_S  (1 << 11)
#define PRV_U 0
#define PRV_S 1
#define PRV_M 3

// Disable trigger n. NOT by writing tdata1=0: CVA6 ignores that on RV64
// (RTL-013). A trigger of the same type with every mode bit clear cannot match.
#define DISABLE_TRIGGER(n, type)    \
        li      t0, n;              \
        csrw    CSR_TSELECT, t0;    \
        li      t0, type;           \
        csrw    CSR_TDATA1, t0

// Fail with check id `id`, actual value in `reg`, expected `val`, unless equal.
#define CHECK_EQ(id, reg, val)      \
        li      t6, val;            \
        beq     reg, t6, 1f;        \
        mv      a1, reg;            \
        mv      a2, t6;             \
        li      a0, id;             \
        j       native_fail_now;    \
1:

// As CHECK_EQ, against the address of label `sym`.
#define CHECK_SYM(id, reg, sym)     \
        la      t6, sym;            \
        beq     reg, t6, 1f;        \
        mv      a1, reg;            \
        mv      a2, t6;             \
        li      a0, id;             \
        j       native_fail_now;    \
1:

// Load a saved trap value into `reg`.
#define LOAD(reg, sym)              \
        la      reg, sym;           \
        ld      reg, 0(reg)

// Set the hook the next M/S trap jumps to.
#define ON_M_TRAP(label)            \
        la      t0, label;          \
        la      t1, m_hook;         \
        sd      t0, 0(t1)
#define ON_S_TRAP(label)            \
        la      t0, label;          \
        la      t1, s_hook;         \
        sd      t0, 0(t1)

// mret to `target` in privilege `prv`, with MPIE cleared (so M interrupts stay
// disabled after the return).
#define MRET_TO(target, prv)        \
        li      t0, MSTATUS_MPP | MSTATUS_MPIE; \
        csrc    mstatus, t0;        \
        li      t0, (prv) << 11;    \
        csrs    mstatus, t0;        \
        la      t0, target;         \
        csrw    mepc, t0;           \
        mret

// ── program skeleton ───────────────────────────────────────────────────────
.macro NATIVE_START
        .option norvc
        .section .text.start
        .globl _start
_start:
        la      sp, native_stack_top
        la      t0, m_handler
        csrw    mtvec, t0
        la      t0, s_handler
        csrw    stvec, t0
        // PMP entry 0: all memory, RWX, so S and U can run.
        li      t0, -1
        csrw    pmpaddr0, t0
        li      t0, 0x1f
        csrw    pmpcfg0, t0
        csrw    medeleg, zero
        csrw    mideleg, zero
        csrw    mie, zero
        csrw    satp, zero
        j       native_main
.endm

.macro NATIVE_END
native_pass:
        li      t0, 1
        la      t1, tohost
        sd      t0, 0(t1)
native_pass_loop:
        j       native_pass_loop

native_fail_now:
        la      t1, native_fail
        sd      a0, 0(t1)
        sd      a1, 8(t1)
        sd      a2, 16(t1)
        li      t0, 3
        la      t1, tohost
        sd      t0, 0(t1)
native_fail_loop:
        j       native_fail_loop

        .align 2
m_handler:
        csrr    t0, mcause
        la      t1, m_cause
        sd      t0, 0(t1)
        csrr    t0, mepc
        sd      t0, 8(t1)
        csrr    t0, mtval
        sd      t0, 16(t1)
        csrr    t0, mstatus
        sd      t0, 24(t1)
        ld      t0, 32(t1)
        addi    t0, t0, 1
        sd      t0, 32(t1)
        la      t1, m_hook
        ld      t0, 0(t1)
        sd      zero, 0(t1)              // one hook per trap
        beqz    t0, m_unexpected
        jr      t0
m_unexpected:
        li      a0, 0xE0                 // unexpected M trap: actual=mcause, expected=mepc
        LOAD(a1, m_cause)
        LOAD(a2, m_epc)
        j       native_fail_now

        .align 2
s_handler:
        csrr    t0, scause
        la      t1, s_cause
        sd      t0, 0(t1)
        csrr    t0, sepc
        sd      t0, 8(t1)
        csrr    t0, stval
        sd      t0, 16(t1)
        ld      t0, 24(t1)
        addi    t0, t0, 1
        sd      t0, 24(t1)
        la      t1, s_hook
        ld      t0, 0(t1)
        sd      zero, 0(t1)
        beqz    t0, s_unexpected
        jr      t0
s_unexpected:
        li      a0, 0xE1                 // unexpected S trap: actual=scause, expected=sepc
        LOAD(a1, s_cause)
        LOAD(a2, s_epc)
        j       native_fail_now

        .section .data
        .align 3
        .globl tohost
tohost:         .dword 0
        .globl fromhost
fromhost:       .dword 0
        .globl native_fail
native_fail:    .dword 0, 0, 0
m_hook:         .dword 0
s_hook:         .dword 0
m_cause:        .dword 0
m_epc:          .dword 0
m_tval:         .dword 0
m_status:       .dword 0
m_count:        .dword 0
s_cause:        .dword 0
s_epc:          .dword 0
s_tval:         .dword 0
s_count:        .dword 0
        .section .bss
        .align 3
        .space 4096
native_stack_top:
.endm

#endif
