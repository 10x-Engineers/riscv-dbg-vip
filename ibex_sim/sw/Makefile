# Build bare-metal RV64 debug-probe test programs for CVA6 SoC simulation.
#
#   make                  — build all .S files into ELFs
#   make halt_probe.elf   — build just one
#   make clean            — remove build artifacts

# Default to whichever riscv64 bare-metal gcc is on PATH rather than one
# machine's install directory; RISCV_PREFIX=<prefix> still overrides.
RISCV_GCC    := $(shell command -v riscv64-unknown-elf-gcc 2>/dev/null)
RISCV_PREFIX ?= $(patsubst %gcc,%,$(RISCV_GCC))
ifeq ($(strip $(RISCV_PREFIX)),)
$(error no riscv64-unknown-elf-gcc on PATH -- install one or pass RISCV_PREFIX=/path/to/riscv64-unknown-elf-)
endif
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
