# RISC-V Debug — Flow Diagrams

Companion sketches to `riscv_debug_testplan.md` and `VERIFICATION_STRATEGY.md`. Kept as a living document — update alongside those two as TC-IDs and gap-matrix content get added, rather than treating this as a one-off snapshot.

## Foundational features (apply across all five use cases)

A handful of CAT2 features are foundational rather than tied to one specific use case — every debug session needs them regardless of *why* you're debugging. Shown once here rather than repeated in each use-case diagram below.

```mermaid
flowchart LR
    DTM["JTAG Debug Transport Module (Ch.6)\nunderlies every operation below"]
    DTM --> F1["Discover DM/implementation info\n(dmstatus.version, confstrptr*, hartinfo)"]
    DTM --> F2["Halt / resume individual hart\n(dmcontrol.haltreq/resumereq)\n✅ TC-RC-001..006"]
    DTM --> F3["Report hart halt status\n(dmstatus, haltsum0-3)"]
    DTM --> F4["Authentication / DM locking\n(authenticated, authbusy, authdata)"]
    F2 --> RC1["TC-RC-001..002\nhalt request / re-halt no-op"]
    F2 --> RC2["TC-RC-003..005\nresume request / running no-op / haltreq priority"]
    F2 --> RC3["TC-RC-006\nresponse latency"]
```

## Use case 1 — Accessing hardware with no working CPU (External debug)

```mermaid
flowchart LR
    U1["Accessing hardware on a\nhardware platform without\na working CPU"]
    U1 --> C1["Abstract GPR read/write\n(Ch.3 op 4, Required)"]
    U1 --> C2["Direct System Bus Access\n(Ch.3 op 11, Optional)"]
    C1 --> M1["Access Register cmdtype=0,\ndata0-11 (#3.7.1.1, #3.14.14)"]
    C2 --> M2["sbcs, sbaddress0-3, sbdata0-3\n(#3.10, #3.14.22-30)"]
```

## Use case 2 — Bootstrapping before any executable code path (External debug)

```mermaid
flowchart LR
    U2["Bootstrapping a hardware\nplatform before there is any\nexecutable code path"]
    U2 --> C3["Reset signal / debug from\nfirst instruction (Ch.3 op 5, Required)\n✅ TC-RST-001..005"]
    U2 --> C4["Halt-on-reset\n(Ch.3 op 6, Optional)\n✅ TC-HOR-001..005"]
    C3 --> M3["dmcontrol.ndmreset/hartreset,\ndmstatus.*havereset (#3.2, #3.14.2)"]
    C4 --> M4["dmstatus.hasresethaltreq,\ndmcontrol.set/clrresethaltreq (#3.5, #3.14.1-2)"]
    M3 --> RST1["TC-RST-001..002\nndmreset / hartreset"]
    M3 --> RST2["TC-RST-003..004\nhavereset / ackhavereset"]
    M3 --> RST3["TC-RST-005\nrestricted DMI during reset (negative)"]
    M4 --> HOR1["TC-HOR-001\ndiscover support (gate)"]
    M4 --> HOR2["TC-HOR-002..003\nset/clrresethaltreq"]
    M4 --> HOR3["TC-HOR-004..005\nper-hart independence /\nillegal simultaneous writes (negative)"]
```

## Use case 3 — Debugging low-level software with no OS (External debug)

```mermaid
flowchart LR
    U3["Debugging low-level software\nin the absence of an OS\nor other software"]
    U3 --> C5["Abstract access to\nnon-GPR registers (CSRs)\n(Ch.3 op 7, Optional)"]
    U3 --> C6["Program Buffer\n(Ch.3 op 8, Optional)"]
    U3 --> C7["Memory access from\nhart's point of view\n(Ch.3 op 10, Optional)"]
    U3 --> C8["Hardware single-step\n(#1.5 feature 8)"]
    C5 --> M5["Access Register on CSR regnos\n(#3.7.1.1, Table 4)"]
    C6 --> M6["progbuf0-15, postexec\n(#3.8, #3.14.15)"]
    C7 --> M7["Access Memory cmdtype=2\n(#3.7.1.3)"]
    C8 --> M8["dcsr.step (#4.5),\nicount trigger alternative"]
```

## Use case 4 — Debugging issues in the OS itself (External or native debug)

```mermaid
flowchart LR
    U4["Debugging issues\nin the OS itself"]
    U4 --> C5b["Abstract access to\nnon-GPR registers (CSRs)"]
    U4 --> C9["Multi-hart halt/resume/reset\n(hart array mask)\n(Ch.3 op 9, Optional)"]
    U4 --> C10["Hart grouping — halt group\n(Ch.3 op 12, Optional)"]
    C5b --> M5b["Access Register on CSR regnos\n(#3.7.1.1, Table 4)"]
    C9 --> M9["hasel, hawindowsel/hawindow\n(#3.3.2, #3.14.4-5)"]
    C10 --> M10["dmcs2.grouptype/group/\nhgselect/hgwrite (#3.6, #3.14.17)"]
```

## Use case 5 — Debugging processes running on an OS (Native or external debug)

```mermaid
flowchart LR
    U5["Debugging processes\nrunning on an OS"]
    U5 --> C9b["Multi-hart halt/resume/reset"]
    U5 --> C8b["Hardware single-step"]
    U5 --> C11["External trigger halt response\n(Ch.3 op 13, Optional)"]
    U5 --> C12["External trigger resume\nsignaling (Ch.3 op 14, Optional)"]
    U5 --> C13["Hart-side Trigger Module —\nhalt on match (native debug,\nFig.1 box + #1.5 feature 16)"]
    C9b --> M9b["hasel, hawindowsel/hawindow"]
    C8b --> M8b["dcsr.step, icount trigger"]
    C11 --> M11["dmcs2.dmexttrigger +\nhalt-group notification (#3.6, #3.14.17)"]
    C12 --> M12["dmcs2 resume-group\nnotification (#3.6, #3.14.17)"]
    C13 --> M13["Ch.5 Sdtrig in full: tselect,\ntdata1-3, mcontrol/mcontrol6,\nicount, itrigger, etrigger, tmexttrigger"]
```

## Stimulus Architecture

The same stimulus code runs against two different backends — this is the mechanism behind the cross-platform verification level and the whole `pydebug` portability claim. Only the boxes below "Transport (abstract)" differ between simulation and emulation; everything above it is identical Python.

```mermaid
flowchart TB
    RUN["run.py / CLI (pydebug run)"]
    SEQ["Sequence module\n(e.g. halt_sequence.py:\nbuild_halt_sequence)"]
    SESSION["DebugSession / StepResult\n(orchestration, pass/fail per step)"]
    DM["RISCVDebug / DMI\n(dm.read/write, riscv_dm.py)"]
    TRANSPORT["DebugTransport (abstract)\nread/write"]
    RUN --> SEQ --> SESSION --> DM --> TRANSPORT

    TRANSPORT --> UVMT["UVMTransport\n(Unix/TCP socket)"]
    TRANSPORT --> OCDT["OpenOCDTransport\n(TCP port 6666, TCL)"]

    UVMT --> BRIDGE["C Bridge (DPI-C)"]
    OCDT --> OCDSRV["OpenOCD server"]

    BRIDGE --> UVMTEST["UVM Test\n(rv_dbg_base_test)"]
    OCDSRV --> BOARD["Target board\n(Arty A7 / Genesys2)"]

    UVMTEST --> AGENT["JTAG/DMI Agent\n(driver/monitor/sequencer,\ntestbench-agnostic, sv/agents/jtag/)"]
    BOARD --> AGENT

    AGENT --> DMI["DMI bus"]
    DMI --> DUT["DUT\n(Ibex / CVA6 / future SoC)"]
```

Simulation uses the left branch (`UVMTransport` → DPI-C bridge → UVM test); emulation uses the right branch (`OpenOCDTransport` → OpenOCD server → real board) — same `RISCVDebug`/`DMI` calls, same sequence module, same `DebugSession` orchestration above the transport line. Post-silicon bring-up is the same right branch again, just pointed at silicon instead of an FPGA.

## Verification levels pipeline

From `riscv-debug-verif-strategy`'s six levels, in dependency order, each annotated with which platforms apply. Cross-platform is a modifier that applies to every other level, not a separate stage in the pipeline — shown as a lane crossing the whole diagram rather than a box in the sequence.

```mermaid
flowchart LR
    subgraph Simulation only
        L1["1. Protocol/interface\n(JTAG DTM, IDCODE, TAP)"]
        L2["2. Register/DMI\n(field-level, model-checked)"]
        L3["3. Functional/scenario\n(halt, read, resume, step)"]
        L4["4. System/integration\n(real SW running, interrupts,\nmulti-hart)"]
    end
    subgraph Simulation + Emulation + Post-silicon
        L5["5. Cross-platform\n(same stimulus, transport swapped)"]
    end
    subgraph All platforms, lowest priority to start
        L6["6. Stress/negative/\ncompliance-edge"]
    end
    L1 --> L2 --> L3 --> L4 --> L5 --> L6
```

**CAT1 anchoring** (why each level exists, not just what it checks):

- Levels 1–2 (protocol, register) → anchor "Accessing hardware with no working CPU" and "Bootstrapping before any executable code path" — both use cases are unreachable if the transport/register layer doesn't work first.
- Level 3 (functional) → "Debugging low-level software with no OS" and "Debugging issues in the OS itself."
- Level 4 (system) → "Debugging issues in the OS itself" and "Debugging processes running on an OS."
- Level 5 (cross-platform) → orthogonal to CAT1; applies to every use case and every other level. This is this project's specific differentiator (see `INTEGRATION_GUIDE.md`'s three-level table) — a result proven only in simulation is not yet proven portable.
- Level 6 (stress/negative) → backs the Authentication/DM-locking CAT2 row specifically (#3.12's IP-protection intent), plus the general P0 "must-pass" claims across every other row.
