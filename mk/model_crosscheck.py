#!/usr/bin/env python3
"""
model_crosscheck.py -- replay a simulation's reference-model trace through the
Python model and compare the two models prediction by prediction.

dm_ref_model.sv (the checker's model) and pydebug.model.predictor.DMPredictor
describe the same Debug Module. Porting one from the other by inspection says
nothing about whether they still agree, so with +DM_MODEL_TRACE the SV model
records every input it receives and, at every read the checker examines, what
it predicted. This script feeds the same inputs, in the same order, to the
Python model and compares at each read:

  - whether each model claims the address (has_model),
  - the bits each claims (predict_mask),
  - the predicted value over those bits.

It also scores both models against the RTL value the read returned, so the
report shows that the two reach the same verdict on the DUT, not only on each
other. Exit status is 1 if the models disagree anywhere.

dmstatus is compared twice. Before each dmstatus comparison the checker copies
the RTL's halted/running/resumeack into the model (they reach the DM with a
latency an untimed model cannot know), so after that sync those bits agree by
construction. The "R" record, taken before the sync, is the one that tests
the models' run-control logic against each other; its RTL column counts
latency as well as real differences. The "V" record, after the sync, is the
comparison the checker actually made.

    python3 mk/model_crosscheck.py cva6_sim/sim_outputs/coverage/*.model_trace
    python3 mk/model_crosscheck.py --report out/model_crosscheck.md <traces...>
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from pydebug.model.dut_config import load_dut_config  # noqa: E402
from pydebug.model.predictor import DMPredictor  # noqa: E402

#: DMI register names, for the report (spec #3.14).
NAMES = {
    0x04: "data0", 0x10: "dmcontrol", 0x11: "dmstatus", 0x12: "hartinfo",
    0x14: "hawindowsel", 0x16: "abstractcs", 0x17: "command",
    0x18: "abstractauto", 0x1D: "nextdm", 0x38: "sbcs", 0x3C: "sbdata0",
    0x40: "haltsum0",
}


@dataclass
class Tally:
    reads: int = 0          # reads the checker examined
    claimed: int = 0        # of those, reads both models claimed
    agree: int = 0          # claimed reads where both predicted the same bits
    sv_vs_rtl: int = 0      # claimed reads where the SV model disagrees with the RTL
    py_vs_rtl: int = 0      # the same, for the Python model


@dataclass
class Result:
    trace: Path
    tallies: dict = field(default_factory=lambda: defaultdict(Tally))
    divergences: list = field(default_factory=list)
    inputs: int = 0


def _config_path(note: str, trace: Path) -> Path:
    """The trace records the path the simulator used, relative to its run
    directory. Resolve it the way the simulator did, or by file name."""
    raw = Path(note)
    for base in (Path.cwd(), ROOT / "cva6_sim", ROOT / "ibex_sim", trace.parent):
        cand = raw if raw.is_absolute() else base / raw
        if cand.is_file():
            return cand.resolve()
    by_name = ROOT / "src" / "pydebug" / "dut_configs" / raw.name
    if by_name.is_file():
        return by_name
    raise FileNotFoundError(f"{trace}: DUT config {note!r} not found")


def replay(trace: Path) -> Result:
    res = Result(trace)
    model = DMPredictor()
    for lineno, line in enumerate(trace.read_text().splitlines(), 1):
        tok = line.split()
        if not tok:
            continue
        kind, args = tok[0], tok[1:]
        if kind == "C":
            cfg = load_dut_config(_config_path(" ".join(args), trace))
            model.set_config(cfg.declared_config(num_harts=1))
            continue
        res.inputs += 1
        if kind == "B":
            model.set_observed_cmdbusy(args[0] == "1")
        elif kind == "W":
            model.on_write(int(args[0], 16), int(args[1], 16))
        elif kind == "S":
            model.sync_observed_hart_signals(int(args[0], 16))
        elif kind == "O":
            model.observe_sbdata0_read()
        elif kind in ("R", "V"):
            res.inputs -= 1
            addr, rtl = int(args[0], 16), int(args[1], 16)
            sv_has, sv_mask, sv_pred = args[2] == "1", int(args[3], 16), int(args[4], 16)
            py_has, py_mask, py_pred = model.has_model(addr), model.predict_mask(addr), model.predict(addr)
            t = res.tallies[(addr, kind)]
            t.reads += 1
            why = []
            if sv_has != py_has:
                why.append(f"has_model sv={int(sv_has)} py={int(py_has)}")
            elif sv_has:
                if sv_mask != py_mask:
                    why.append(f"mask sv={sv_mask:08x} py={py_mask:08x}")
                elif (sv_pred & sv_mask) != (py_pred & py_mask):
                    why.append(f"prediction sv={sv_pred & sv_mask:08x} "
                               f"py={py_pred & py_mask:08x} (bits {(sv_pred ^ py_pred) & sv_mask:08x})")
                else:
                    t.agree += 1
                t.claimed += 1
                t.sv_vs_rtl += int((sv_pred & sv_mask) != (rtl & sv_mask))
                t.py_vs_rtl += int((py_pred & py_mask) != (rtl & py_mask))
            if why:
                res.divergences.append((lineno, (addr, kind), "; ".join(why)))
        else:
            raise ValueError(f"{trace}:{lineno}: unknown record {line!r}")
    return res


def _name(key) -> str:
    addr, kind = key if isinstance(key, tuple) else (key, "R")
    name = NAMES.get(addr, f"0x{addr:02x}")
    if addr == 0x11:
        name += " (after hart-signal sync: the checker's verdict)" if kind == "V" \
            else " (before hart-signal sync: run-control logic)"
    return name


def render(results: list) -> str:
    total = defaultdict(Tally)
    for r in results:
        for a, t in r.tallies.items():
            for k in vars(t):
                setattr(total[a], k, getattr(total[a], k) + getattr(t, k))
    diverged = sum(len(r.divergences) for r in results)
    out = [
        "# Reference-model cross-check: dm_ref_model.sv vs DMPredictor",
        "",
        f"{len(results)} trace(s), {sum(r.inputs for r in results)} model inputs replayed, "
        f"{sum(t.reads for k, t in total.items() if k[1] == 'R')} reads compared "
        f"(plus {sum(t.reads for k, t in total.items() if k[1] == 'V')} dmstatus reads after the "
        f"hart-signal sync). "
        f"**{'The models agree on every read.' if not diverged else f'{diverged} divergence(s).'}**",
        "",
        "| Register | Reads | Both claim | Same prediction | SV ≠ RTL | Python ≠ RTL |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for a in sorted(total):
        t = total[a]
        out.append(f"| `{_name(a)}` | {t.reads} | {t.claimed} | {t.agree} | {t.sv_vs_rtl} | {t.py_vs_rtl} |")
    out += ["", "| Trace | Inputs | Reads | Divergences |", "|---|---:|---:|---:|"]
    for r in results:
        out.append(f"| `{r.trace.name}` | {r.inputs} | "
                   f"{sum(t.reads for k, t in r.tallies.items() if k[1] == 'R')} | {len(r.divergences)} |")
    if diverged:
        out += ["", "## Divergences", ""]
        for r in results:
            for lineno, addr, why in r.divergences[:50]:
                out.append(f"- `{r.trace.name}:{lineno}` `{_name(addr)}`: {why}")
    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("traces", nargs="+", type=Path)
    ap.add_argument("--report", type=Path, help="also write the markdown report here")
    a = ap.parse_args()
    results = [replay(t) for t in a.traces]
    text = render(results)
    print(text, end="")
    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(text)
    return int(any(r.divergences for r in results))


if __name__ == "__main__":
    sys.exit(main())
