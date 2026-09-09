# Minimal RV64 bare-metal spin program for CVA6 debug bring-up.
# Fills x1-x31 with known values, then loops forever at main_end so a
# debugger can halt, read GPRs/PC, and resume against real RTL.

        .section .text.start, "ax", @progbits
        .globl _start
        .globl main
        .globl main_end

_start:
main:
        li      x1,  1
        li      x2,  2
        li      x3,  3
        li      x4,  4
        li      x5,  5
        li      x6,  6
        li      x7,  7
        li      x8,  8
        li      x9,  9
        li      x10, 10
        li      x11, 11
        li      x12, 12
        li      x13, 13
        li      x14, 14
        li      x15, 15
        li      x16, 16
        li      x17, 17
        li      x18, 18
        li      x19, 19
        li      x20, 20
        li      x21, 21
        li      x22, 22
        li      x23, 23
        li      x24, 24
        li      x25, 25
        li      x26, 26
        li      x27, 27
        li      x28, 28
        li      x29, 29
        li      x30, 30
        li      x31, 31

# Loop the whole register-write sequence rather than spinning on a single
# instruction. The debugger halts a *running* hart, so the program has to stay
# busy doing something worth stepping through: a `j .` spin gave one
# instruction to step -- the jump itself -- where the PC does not advance and
# no register changes.
#
# Looping back to main means the hart is always somewhere in these 31 writes,
# so a halt lands on a known instruction, a single step advances the PC by one
# of them, and every GPR still holds its documented constant because each
# iteration rewrites it.
        j       main
