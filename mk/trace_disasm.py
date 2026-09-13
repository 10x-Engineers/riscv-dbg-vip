#!/usr/bin/env python3
"""
trace_disasm.py — rewrite CVA6's instruction trace with correct disassembly.

CVA6's instr_tracer prints rd, rs1 and the immediate from the scoreboard entry
(sbe.rd / sbe.rs1 / sbe.result), which carries junk in this build: every
destination prints as x0, immediates arrive with garbage in their upper bits
(0x1800000001d where 0x1d is correct), and the PC column is stale or contains
literal X/Z. The raw encoding column, passed separately, is correct.

So this reads the encodings and disassembles them with objdump, which needs no
trust in anything the tracer computed. Output keeps the trace's own time, cycle
and privilege columns -- those are fine -- and replaces the rest.

Usage: trace_disasm.py <trace_hart_0.log> <out.log> [objdump]
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# "   2795ns    266 M 000...  0 00100413 li  x0, a2, 164926..."
#    time       cyc  priv  pc  ?  encoding  <mangled disassembly>
LINE = re.compile(
    r"^\s*(?P<time>\d+)ns\s+(?P<cyc>\d+)\s+(?P<priv>[MSUD])\s+\S+\s+\S+\s+"
    r"(?P<enc>[0-9a-fA-F]{8})\b"
)


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    objdump = sys.argv[3] if len(sys.argv) > 3 else "riscv64-unknown-elf-objdump"

    if not src.is_file():
        return 0   # nothing to do; a missing trace is not an error

    rows, blob = [], bytearray()
    for line in src.read_text(errors="replace").splitlines():
        m = LINE.match(line)
        if not m:
            continue
        enc = int(m.group("enc"), 16)
        # Compressed when the low two bits are not 0b11 (RISC-V ISA 16-bit form).
        # Emit exactly the instruction's length so objdump stays in step.
        width = 2 if (enc & 0x3) != 0x3 else 4
        blob += (enc & 0xFFFF).to_bytes(2, "little") if width == 2 \
            else enc.to_bytes(4, "little")
        rows.append((m.group("time"), m.group("cyc"), m.group("priv"), enc, width))

    if not rows:
        return 0

    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as fh:
        fh.write(blob)
        binpath = fh.name
    try:
        out = subprocess.run(
            [objdump, "-D", "-b", "binary", "-m", "riscv:rv64", binpath],
            capture_output=True, text=True, check=False)
    except FileNotFoundError:
        print(f"{objdump} not found; leaving trace unprocessed", file=sys.stderr)
        return 0
    finally:
        Path(binpath).unlink(missing_ok=True)

    # objdump lines look like:  "   0:\t00100413          \taddi\ts0,zero,1"
    disasm = {}
    for line in out.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and parts[0].strip().rstrip(":").strip():
            try:
                off = int(parts[0].strip().rstrip(":"), 16)
            except ValueError:
                continue
            disasm[off] = "\t".join(parts[2:]).strip()

    with dst.open("w") as f:
        f.write("# Disassembly regenerated from the encoding column by objdump.\n"
                "# CVA6's tracer prints rd/rs1/immediate from the scoreboard entry,\n"
                "# which is corrupt in this build; only the encoding is trustworthy.\n"
                "# Columns: time, cycle, privilege (D = Debug Mode), encoding, instruction.\n")
        off = 0
        for t, cyc, priv, enc, width in rows:
            text = disasm.get(off, "(undecoded)")
            f.write(f"{t:>10}ns {cyc:>8} {priv}  {enc:08x}  {text}\n")
            off += width
    return 0


if __name__ == "__main__":
    sys.exit(main())
