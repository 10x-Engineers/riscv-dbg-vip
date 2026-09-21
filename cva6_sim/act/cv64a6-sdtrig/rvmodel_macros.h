// rvmodel_macros.h -- riscv-arch-test (ACT4) DUT macros for the riscv-dbg-vip
// CVA6 build (ariane_testharness, cv64a6_imafdc_sv39 + Sdtrig).
// Derived from config/cores/cvw/cvw-rv64gc/rvmodel_macros.h: the ariane SoC
// has the same CLINT/PLIC/UART addresses. Changes: no console, and an access
// fault address outside the ariane map.
#ifndef _RVMODEL_MACROS_H
#define _RVMODEL_MACROS_H

// Reference-model (signature) builds include sail_macros.h, which needs these
// two addresses. ACT4 passes them only when Sail is the reference model; with
// Spike (needed here: Sail has no Sdtrig) nothing defines them and every
// signature build stops with #error. Spike's CLINT is at 0x0200_0000, as Sail's
// default is; the interrupt-generator address is unused by the Sdtrig tests.
#ifndef RVTEST_SELFCHECK
  #ifndef SAIL_CLINT_BASE_ADDRESS
    #define SAIL_CLINT_BASE_ADDRESS 0x02000000
  #endif
  #ifndef SAIL_SIMPLE_INTERRUPT_GENERATOR_BASE_ADDRESS
    #define SAIL_SIMPLE_INTERRUPT_GENERATOR_BASE_ADDRESS 0x0C000000
  #endif
#endif

#define RVMODEL_DATA_SECTION \
        .pushsection .tohost,"aw",@progbits;                \
        .balign 8; .global tohost; tohost: .dword 0;         \
        .balign 8; .global fromhost; fromhost: .dword 0;     \
        .popsection;

#define STANDARD_SM_SUPPORTED

##### STARTUP #####

# Perform boot operations. Can be empty or left undefined unless needed for
# DUT-specific behavior such as turning on a memory controller or
# initializing custom state.
//#define RVMODEL_BOOT

// Custom RVMODEL_BOOT_TO_MMODE overrides default RVTEST_BOOT_TO_MMODE
// if defined.  For most DUTs, the default should work and this macro
// should not be defined.  If no M-mode or CSRs are implemented, define this
// macro as blank to bypass the boot process.  If a nonconforming
// M-mode is implemented, define this macro to set up the necessary
// state in a fashion similar to RVTEST_BOOT_TO_MMODE.
//#define RVMODEL_BOOT_TO_MMODE

##### TERMINATION #####

# Terminate test with a pass indication.
# When the test is run in simulation, this should end the simulation.
#define RVMODEL_HALT_PASS  \
  li x1, 1                ;\
  la t0, tohost           ;\
  write_tohost_pass:      ;\
    sw x1, 0(t0)          ;\
    sw x0, 4(t0)          ;\
  self_loop_pass:         ;\
    j self_loop_pass      ;\

# Terminate test with a fail indication.
# When the test is run in simulation, this should end the simulation.
#define RVMODEL_HALT_FAIL \
  li x1, 3                ;\
  la t0, tohost           ;\
  write_tohost_fail:      ;\
    sw x1, 0(t0)          ;\
    sw x0, 4(t0)          ;\
  self_loop_fail:         ;\
    j self_loop_fail      ;\

##### IO #####

# No console. The testbench does not capture the UART, and pass/fail is read
# from tohost by the debugger (pydebug run_elf scenario), so printing would
# only cost simulation time.
#define RVMODEL_IO_INIT(_R1, _R2, _R3)
#define RVMODEL_IO_WRITE_STR(_R1, _R2, _R3, _STR_PTR)

##### Access Fault #####

# 0x0 is the Debug Module in the ariane SoC map; 0x5000_0000 is decoded by no
# peripheral (ariane_soc_pkg.sv), so the AXI crossbar answers with an error.
#define RVMODEL_ACCESS_FAULT_ADDRESS 0x50000000

##### Interrupt Latency #####

#define RVMODEL_INTERRUPT_LATENCY 10

##### Machine Timer #####

// Wally's mtime advances one tick per core clock, and the code between arming
// mtimecmp and reaching the lower privilege mode (three CLINT stores plus
// RVTEST_GOTO_LOWER_MODE) can take well over 100 cycles on a pipelined core
// with caches.  With a delay of 100 the timer interrupt fires while still in
// M-mode with MIE=1, so the trap records MPP=M instead of MPP=U/S.
#define RVMODEL_TIMER_INT_SOON_DELAY 10000

#define RVMODEL_MTIME_ADDRESS  0x0200BFF8  /* Address of mtime CSR */

#define RVMODEL_MTIMECMP_ADDRESS 0x02004000 /* Address of mtimecmp CSR */

##### Machine Interrupts #####

#define CLINT_BASE_ADDRESS 0x02000000
#define RVMODEL_MSIP_ADDRESS (CLINT_BASE_ADDRESS + 0x0)


#define PLIC_BASE_ADDRESS    0x0c000000
#define PLIC_ENABLE_ADDRESS  0x0c002000
#define PLIC_THRESH_ADDRESS  0x0c200000
#define PLIC_CLAIM_ADDRESS   0x0c200004
#define PLIC_SENABLE_ADDRESS 0x0c002080   /* For S mode */
#define PLIC_STHRESH_ADDRESS 0x0c201000
#define PLIC_SCLAIM_ADDRESS  0x0c201004

#define NS16550_BASE_ADDRESS 0x10000000
#define UART_INT_SRC         10

#define RVMODEL_SET_MEXT_INT(_R1, _R2)          \
  li _R1, 7;                                     \
  li _R2, PLIC_BASE_ADDRESS;                     \
  sw _R1, (4*UART_INT_SRC)(_R2);                 \
  li _R1, (1 << UART_INT_SRC);                   \
  li _R2, PLIC_ENABLE_ADDRESS;                   \
  sw _R1, 0(_R2);                                \
  li _R2, PLIC_THRESH_ADDRESS;                   \
  sw zero, 0(_R2);                               \
  li _R1, 0x02;                                  \
  li _R2, NS16550_BASE_ADDRESS;                  \
  sb _R1, 1(_R2);

#define RVMODEL_CLR_MEXT_INT(_R1, _R2)          \
  li _R2, NS16550_BASE_ADDRESS;                  \
  sb zero, 1(_R2);                               \
  li _R2, PLIC_CLAIM_ADDRESS;                    \
  lw _R1, 0(_R2);                                 \
  sw _R1, 0(_R2);                               \
  li _R2, PLIC_ENABLE_ADDRESS;  /* Since SEXT and MEXT interrupt contexts share the same source, PLIC must be disabled for MEXT context so that it can properly trigger SEXT */\
  sw zero, 0(_R2);

##### Supervisor Interrupts #####

#define CVW_SSIP_ADDRESS (CLINT_BASE_ADDRESS + 0xC000)

#define RVMODEL_SET_SEXT_INT(_R1, _R2)          \
  li _R1, 7;                                     \
  li _R2, PLIC_BASE_ADDRESS;                     \
  sw _R1, (4*UART_INT_SRC)(_R2);                 \
  li _R1, (1 << UART_INT_SRC);                   \
  li _R2, PLIC_SENABLE_ADDRESS;                   \
  sw _R1, 0(_R2);                                \
  li _R2, PLIC_STHRESH_ADDRESS;                   \
  sw zero, 0(_R2);                               \
  li _R1, 0x02;                                  \
  li _R2, NS16550_BASE_ADDRESS;                  \
  sb _R1, 1(_R2);

#define RVMODEL_CLR_SEXT_INT(_R1, _R2)          \
  li _R2, NS16550_BASE_ADDRESS;                  \
  sb zero, 1(_R2);                               \
  li _R2, PLIC_SCLAIM_ADDRESS;                    \
  lw _R1, 0(_R2);                               \
  sw _R1, 0(_R2); \
  li _R2, PLIC_SENABLE_ADDRESS;  /* Disable the S-context UART enable that SET_SEXT turned on, so a later MEXT test does not also raise SEIP via the shared source */\
  sw zero, 0(_R2);

#define RVMODEL_SET_SSW_INT(_R1, _R2) \
  li _R1, 1; \
  li _R2, CVW_SSIP_ADDRESS; \
  sw _R1, 0(_R2);

#define RVMODEL_CLR_SSW_INT(_R1, _R2) \
  li _R2, CVW_SSIP_ADDRESS; \
  sw zero, 0(_R2);

#endif // _RVMODEL_MACROS_H
