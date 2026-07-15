/* Linker script for CVA6 bare-metal debug probe programs.
 * Places .text at CVA6's DRAM base (ariane_soc::DRAMBase = 0x8000_0000);
 * the bootrom jumps here after reset. */

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
