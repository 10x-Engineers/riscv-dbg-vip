/* ──────────────────────────────────────────────────────────────────────────
 * link.ld — Linker script for CVA6 bare-metal test programs
 *
 * Places .text at 0x8000_0000 (CVA6 DRAM base, ariane_soc::DRAMBase).
 * The bootrom jumps here after reset.
 * ────────────────────────────────────────────────────────────────────────── */

OUTPUT_ARCH("riscv")
ENTRY(_start)

MEMORY
{
    DRAM (rwx) : ORIGIN = 0x80000000, LENGTH = 64M
}

SECTIONS
{
    .text : {
        *(.text.start)
        *(.text*)
    } > DRAM

    .rodata : {
        *(.rodata*)
    } > DRAM

    .data : {
        *(.data*)
    } > DRAM

    .bss : {
        *(.bss*)
        *(COMMON)
    } > DRAM

    /DISCARD/ : {
        *(.comment)
        *(.note*)
        *(.eh_frame*)
    }
}
