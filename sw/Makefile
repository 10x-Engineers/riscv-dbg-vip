# ──────────────────────────────────────────────────────────────────────────────
# Makefile — Build bare-metal RV64 test programs for CVA6 SoC simulation
#
# Usage:
#   make                    — build all .S files into ELFs
#   make infinite_loop.elf  — build just one
#   make clean              — remove all build artifacts
#   make disasm             — show disassembly of all ELFs
# ──────────────────────────────────────────────────────────────────────────────

# ── Toolchain ─────────────────────────────────────────────────────────────────
RISCV_PREFIX ?= /home/jk/Documents/riscv/bin/riscv64-unknown-elf-
CC      = $(RISCV_PREFIX)gcc
AS      = $(RISCV_PREFIX)as
LD      = $(RISCV_PREFIX)ld
OBJDUMP = $(RISCV_PREFIX)objdump
OBJCOPY = $(RISCV_PREFIX)objcopy

# ── Sources ───────────────────────────────────────────────────────────────────
SRCS ?= $(wildcard *.S)
ELFS  = $(SRCS:.S=.elf)

# ── Flags ─────────────────────────────────────────────────────────────────────
ASFLAGS  = -march=rv64imafdc -mabi=lp64d
LDFLAGS  = -T link.ld -nostdlib -static

# ── Targets ───────────────────────────────────────────────────────────────────
.PHONY: all clean disasm

all: $(ELFS)

%.elf: %.o link.ld
	$(LD) $(LDFLAGS) -o $@ $<
	@echo "✅ Built $@"
	@$(OBJDUMP) -d $@ | head -40

%.o: %.S
	$(CC) $(ASFLAGS) -c -o $@ $<

clean:
	rm -f *.o *.elf

disasm: $(ELFS)
	@for f in $(ELFS); do \
		echo "═══ $$f ═══"; \
		$(OBJDUMP) -d $$f; \
	done
