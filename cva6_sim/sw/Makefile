# Build bare-metal RV64 debug-probe test programs for CVA6 SoC simulation.
#
#   make                  — build all .S files into ELFs
#   make halt_probe.elf   — build just one
#   make clean            — remove build artifacts

RISCV_PREFIX ?= /home/jk/Documents/riscv/bin/riscv64-unknown-elf-
CC      = $(RISCV_PREFIX)gcc
LD      = $(RISCV_PREFIX)ld
OBJDUMP = $(RISCV_PREFIX)objdump

SRCS ?= $(wildcard *.S)
ELFS  = $(SRCS:.S=.elf)

ASFLAGS = -march=rv64imafdc -mabi=lp64d
LDFLAGS = -T link.ld -nostdlib -static

.PHONY: all clean disasm

all: $(ELFS)

%.elf: %.o link.ld
	$(LD) $(LDFLAGS) -o $@ $<
	@echo "Built $@"

%.o: %.S
	$(CC) $(ASFLAGS) -c -o $@ $<

clean:
	rm -f *.o *.elf

disasm: $(ELFS)
	@for f in $(ELFS); do echo "=== $$f ==="; $(OBJDUMP) -d $$f; done
