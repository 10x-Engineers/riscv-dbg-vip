/* Linker script for running debug-probe test programs on real Ibex
 * Demo System hardware (Arty A7) via OpenOCD load_image.
 *
 * Unlike link.ld (used for simulation, linked at CVA6's 0x80000000 so
 * tb_top_ibex.sv's address-translation hack can remap it), this links
 * directly at Ibex's real boot address: MEM_START (0x00100000) + 0x80,
 * matching sw/common/link.ld's _entry_point convention and
 * ibex_demo_system.sv's boot_addr_i(32'h00100000). No translation hack
 * exists on real hardware, so the ELF must already be linked correctly. */

OUTPUT_ARCH("riscv")
ENTRY(_start)

MEMORY
{
    ram (rwx) : ORIGIN = 0x00100080, LENGTH = 0x1DF80 /* 124 KiB - 0x80 */
}

SECTIONS
{
    .text : {
        *(.text.start)
        *(.text*)
    } > ram

    .rodata : {
        *(.rodata*)
    } > ram

    .data : {
        *(.data*)
    } > ram

    .bss : {
        *(.bss*)
        *(COMMON)
    } > ram

    /DISCARD/ : {
        *(.comment)
        *(.note*)
        *(.eh_frame*)
    }
}
