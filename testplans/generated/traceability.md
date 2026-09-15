# Traceability — Debug v1.0

| Obligation | Modality | Requirement | Rows |
|---|---|---|---|
| OB-0016C84C | MAY | Second, it may improve performance when accessing memory. | TC-SBA-028 |
| OB-0100569D | CONDITIONAL | If an abstract command does not complete in the expected time and appears to be hung, the debugger can try to  | TC-AC-001 |
| OB-01315BF7 | SHOULD | No other mechanism should exist that may result in resetting the Debug Module after power up. | TC-TRIG-152 |
| OB-017981C2 | SHOULD | When an implementation supports data value triggers (select=1), it is recommended that those triggers support  | TC-TRIG-065 |
| OB-01DC3821 | SHOULD | In addition hardware should ignore writes to mcontrol6 that set dmode to 1 if the previous trigger has both dm | TC-TRIG-093 |
| OB-02126F63 | CONDITIONAL | While ndmreset or any external reset is asserted, the only supported DM operations are reading/writing dmcontr | TC-RST-001 |
| OB-02213F12 | CONDITIONAL | When mret is executed, mte is set to the value of mpte. | TC-TRIG-118 |
| OB-02698A9C | MUST | An implementation must support the value of 0, but all other values are optional. | TC-TRIG-094 |
| OB-0273DDE1 | MUST | JTAG TAPs used as a DTM must have an IR of at least 5 bits. | TC-DTM-001 |
| OB-03F99DF4 | MUST | For the purposes of debug triggers, two classes of cache operations must match as stores: Cache operations tha | TC-TRIG-020 |
| OB-04805E69 | CONDITIONAL | If groups aren’t implemented, then this entire field is 0. | TC-RC-009 |
| OB-0499428E | CONDITIONAL | If the breakpoint trap does not go to a higher privilege mode, this will lose CSR information for the original | TC-TRIG-033 |
| OB-057E5897 | CONDITIONAL | While this field is set, no more system bus accesses can be initiated by the Debug Module. | TC-SBA-011 |
| OB-05B47EDA | CONDITIONAL | If the debugger executes a program that doesn’t terminate with an ebreak instruction, the hart will remain in  | TC-PB-004 |
| OB-05D1BDB8 | SHOULD | In general this should only be used when the Debugger has reason to expect that the outstanding DMI transactio | TC-DTM-022 |
| OB-0623EC9D | MUST | This is a behavior that debug users must be aware of. | TC-DCSR-001 |
| OB-06A5C122 | CONDITIONAL | If the trigger is disabled, then this register can be written with any value supported by any of the trigger t | TC-TRIG-126 |
| OB-06C64E07 | CONDITIONAL | If either of the bits is not implemented, the unimplemented bits will be read-only 0. 0 (false): The trigger d | TC-TRIG-095 |
| OB-07399E10 | SHOULD | Writes to this bit should be ignored while an abstract command is executing. | TC-TRIG-153, TC-TRIG-154, TC-TRIG-155, TC-TRIG-156, TC-TRIG-157 |
| OB-07AAC19F | MUST | If the failure is that the requested register does not exist in the hart, cmderr must be set to 3 (exception). | TC-AC-016 |
| OB-08232C1C | MAY | All control transfer instructions may act as illegal instructions if their destination is outside the Program  | TC-DCSR-035 |
| OB-08418D43 | CONDITIONAL | If more than one of the above events occur during a single instruction execution, the trigger still only match | TC-TRIG-044 |
| OB-08BE3BCD | CONDITIONAL | If the bit is not implemented, it is always 0 and writing it has no effect. | TC-TRIG-045 |
| OB-091C0ADE | SHOULD_NOT | The user should not access dcsr directly, because doing so might interfere with the debugger. | TC-GEN-005 |
| OB-09F6CC19 | CONDITIONAL | If the A extension is supported, then triggers on loads/stores treat them as follows: lr instructions are load | TC-TRIG-014 |
| OB-0A06EFC6 | MUST | If a register is accessible, then reads of aarsize less than or equal to the register’s actual size must be su | TC-AC-017 |
| OB-0B121B4E | CONDITIONAL | If DXLEN >= 64, then this register provides access to the low bits of each field defined in textra64. | TC-TRIG-130 |
| OB-0B567414 | UNSPECIFIED | It is undefined whether the increment happens when transfer is 0. postexec 0 (disabled): No effect. | TC-AC-018 |
| OB-0BE457D5 | CONDITIONAL | When confstrptrvalid is set, reading this register returns bits 63:32 of the configuration structure pointer. | TC-DIS-007 |
| OB-0C163BA1 | MAY | First, an implementation may allow some abstract commands to execute without halting the hart. | TC-GEN-007 |
| OB-0C42DDA8 | MUST | If the halt signal (driven by the hart’s halt request bit in the Debug Module) or hasresethaltreq are asserted | TC-GEN-003 |
| OB-0C4BDCDC | SHOULD | Debuggers should use other mechanisms to debug these cases, such as patching the handler or setting a breakpoi | TC-TRIG-145 |
| OB-0C6D659A | CONDITIONAL | If the H extension is not supported, the only legal values are 0 and 4. | TC-TRIG-131 |
| OB-0C7BEBF9 | UNSPECIFIED | This operation leaves the values in address and data UNSPECIFIED. 1 (read): Read from address. | TC-DMI-007 |
| OB-0DC5D424 | MAY | In implementations that support match mode 1 (NAPOT), not all NAPOT ranges may be supported. | TC-TRIG-096 |
| OB-0DE691B9 | MAY | Writes of values greater than or equal to the number of supported triggers may result in a different value in  | TC-TRIG-140 |
| OB-0E658809 | CONDITIONAL | When a hart halts: cause is updated. prv and v are set to reflect current privilege mode and virtualization mo | TC-RC-001 |
| OB-0EEA3282 | CONDITIONAL | When an external trigger that’s a member of the resume group fires: All the harts in that group that are halte | TC-HG-005 |
| OB-0F3427A3 | SHOULD_NOT | NMI Non-Maskable Interrupt. physical address address that is directly usable on the system bus. recommended fe | _(uncovered)_ |
| OB-1019002E | MAY | Commands may fail because a hart is not halted, not running, unavailable, or because they encounter an error d | TC-AC-002 |
| OB-107E0AB3 | MAY | DMs that support all necessary functionality using abstract commands only may choose to omit the Program Buffe | TC-PB-005 |
| OB-10D251F5 | UNSPECIFIED | It is undefined when exactly such a chain fires. | TC-TRIG-066 |
| OB-1132158B | SHOULD | When an implementation supports address triggers (select=0), it is recommended that those triggers support eve | TC-TRIG-097 |
| OB-117BA64A | UNSPECIFIED | Allowing dpc to become UNSPECIFIED upon Program Buffer execution allows for direct implementations that don’t  | TC-DCSR-023 |
| OB-11DBEB47 | MUST | This variant must be supported, and is the only supported one if progbufsize is 0. 1 (enabled): Execute the pr | TC-AC-019 |
| OB-12247C16 | CONDITIONAL | If halt groups are not implemented, then group will always be 0 when grouptype is 0. | TC-RC-010 |
| OB-12820A89 | CONDITIONAL | If sbasize is less than 33, then this register is not present. | TC-SBA-005 |
| OB-128AD42B | MUST | This register must be implemented if hcontext is implemented, and is optional otherwise. | TC-TRIG-061 |
| OB-135336B9 | MAY | Since some bits in the hart array mask register may be constant 0, some bits in this register may be constant  | TC-HS-007 |
| OB-1666B3BD | CONDITIONAL | When confstrptrvalid is set, reading this register returns bits 127:96 of the configuration structure pointer. | TC-DIS-009 |
| OB-1698F3A3 | CONDITIONAL | If the instruction performed multiple memory accesses, all of them have been completed. | TC-TRIG-098 |
| OB-173862A8 | MUST | This process must be repeated until op returns 0. | TC-DMI-002 |
| OB-1853C145 | CONDITIONAL | When this operation succeeds, address contains the address that was read from, and data contains the value tha | TC-DMI-008 |
| OB-19247AC3 | CONDITIONAL | If the bit is not implemented, it is always 0 and writing it has no effect. | TC-TRIG-034 |
| OB-1A54AF66 | MAY | An implementation may detect an upcoming failure early, and fail the overall command before it reaches the ste | TC-AM-001 |
| OB-1A650D65 | MAY | Pins whose functionality isn’t needed may be left unconnected. | TC-DTM-005 |
| OB-1AAC7474 | MUST | If the IR actually has more than 5 bits, then the encodings in Table 1 should be extended with 0’s in their mo | TC-DTM-002 |
| OB-1BC5D4F2 | MUST | In that case it must be advertised as conforming to "RISC-V Debug Specification, with custom DTM." If the JTAG | TC-DTM-019 |
| OB-1BEE603C | MAY | An implementation may be able to optimize the storage required, depending on the widest addresses it supports. | TC-TRIG-025 |
| OB-1C54EC01 | SHOULD | To help users out, debuggers should detect when a single step restarted an instruction, and then step again. | TC-SSTEP-006 |
| OB-1C8CD92F | MAY | Hardware may only support a subset of interrupts for this trigger. | TC-TRIG-053 |
| OB-1D4ECB8E | CONDITIONAL | If sbasize is 0, then this register is not present. | TC-SBA-001 |
| OB-1ED3D947 | MAY | Implementations that wish to limit the maximum length of a trigger chain (eg. to meet timing requirements) may | TC-TRIG-099 |
| OB-1F89A3BD | MUST | Debuggers must avoid the latter case by checking chain on the previous trigger if they’re writing mcontrol. | TC-TRIG-067 |
| OB-1FD807EA | MUST | If this is not implemented, then the hart must enter Debug Mode and ignore the breakpoint exception. | TC-TRIG-008 |
| OB-20BDED99 | CONDITIONAL | When executing code due to an abstract command, the hart stays in Debug Mode and the following apply: All impl | TC-DCSR-036 |
| OB-20CBEE7D | CONDITIONAL | If sbautoincrement is set and the read was successful, increment sbaddress. | TC-SBA-016 |
| OB-21432296 | CONDITIONAL | If control is transferred to a trap handler while executing the instruction, then Debug Mode is re-entered imm | TC-SSTEP-001 |
| OB-2189F35B | MAY | Implementations may also change the group of a minimal set of unselected harts in the same way, if that is nec | TC-RC-011 |
| OB-22F8CCE2 | CONDITIONAL | When a hart resumes: pc changes to the value stored in dpc. | TC-RC-004 |
| OB-235FC342 | MAY | The hart behaves exactly as in the running case, except that interrupts may be disabled (depending on stepie)  | TC-SSTEP-015 |
| OB-2393302C | MUST | Other bits must be hard-wired to 0. | TC-AC-033 |
| OB-23BDABB0 | MAY | For invalid instruction fetch addresses and load and store effective addresses, the compare value may be chang | TC-TRIG-022 |
| OB-25C68870 | MAY | Field Description Access Reset hawindowsel The high bits of this field may be tied to 0, depending on how larg | TC-HS-008 |
| OB-264C72EE | SHOULD | This signal should only be used to support legacy components that rely on this functionality. nTRST_PD Test re | TC-DTM-006 |
| OB-266A72BB | MUST_NOT | A debugger must not write to this register unless hartinfo explicitly mentions it (the Debug Module may use th | TC-DCSR-034 |
| OB-27CAFF80 | CONDITIONAL | If the trigger is disabled, then this register can be written with any value supported by any of the trigger t | TC-TRIG-128 |
| OB-2A19CE5B | MAY | A higher level debugger may choose to automate this. | TC-DCSR-002 |
| OB-2B0490C7 | CONDITIONAL | While this field is non-zero, no more system bus accesses can be initiated by the Debug Module. | TC-SBA-012 |
| OB-2B14D073 | MUST | If virtual addresses are less than XLEN bits wide, they are sign-extended. tdata2 must be implemented with eno | TC-TRIG-026 |
| OB-2BBF0054 | CONDITIONAL | If neither of these features exist, then single step is doable, but tricky to get right. | TC-SSTEP-007 |
| OB-2BC5A5AF | CONDITIONAL | When a design progresses from simulation to hardware implementation, a user’s control and understanding of the | TC-GEN-027 |
| OB-2C7135A4 | CONDITIONAL | When any hart in a resume group resumes: All the other harts in that group that are halted will quickly resume | TC-HG-006 |
| OB-2CC037E5 | MUST | In order to let the debugger discover all harts, they must show up as unavailable even if there is no chance o | TC-HS-001 |
| OB-2D73E1EE | MUST | When the DM is reset, all harts must be placed in the lowest-numbered halt and resume groups that they can be  | TC-HG-007 |
| OB-2D7FF24A | MAY | The System Bus Access block may support 8-, 16-, 32-, 64-, and 128-bit accesses. | TC-SBA-029 |
| OB-2DAF5030 | MUST | Debug Modules must implement this command and must support read and write access to all GPRs when the selected | TC-AC-020 |
| OB-2DC1C314 | CONDITIONAL | If the bus manager is busy then accesses set sbbusyerror, and don’t do anything else. | TC-SBA-026 |
| OB-2E8AAD38 | SHOULD | To place the Debug Module into a known state, a debugger should write 0 to dmactive, poll until dmactive is ob | TC-TRIG-158 |
| OB-2F1A125F | MAY | While all harts have stoptime=1 and are in Debug Mode, mtime is allowed to stop incrementing. | TC-DCSR-006 |
| OB-2F449452 | CONDITIONAL | When this is the case REQ_OP can be set to 1 for a read or 2 for a write request. | TC-GEN-019 |
| OB-2F51C0F3 | MUST | Example: Every DM must support the Access Register command, but might not support accessing CSRs. | TC-AC-003 |
| OB-2F8D0289 | MUST | The still-in-progress status is sticky to accommodate debuggers that batch together a number of scans, which m | TC-DMI-009 |
| OB-30495D6E | SHOULD | This signal should only be used to support legacy components that rely on this functionality. | TC-DTM-007 |
| OB-309768D3 | CONDITIONAL | If hardware ties mprven to 0 then the external debugger is expected to simulate all the effects of MPRV, inclu | TC-DCSR-037 |
| OB-3136B540 | MUST | If there was an exception, it’s left to the debugger to know what must have caused it. | TC-AC-040 |
| OB-3144B345 | SHOULD | When it is set, it suggests that the hardware should attempt to keep the hart available for the debugger, e.g. | TC-TRIG-159 |
| OB-32A61DFD | CONDITIONAL | If this register is included, the debugger can do more with the Program Buffer by writing programs which expli | TC-DIS-014 |
| OB-32D66181 | SHOULD | In addition hardware should ignore writes to mcontrol that set dmode to 1 if the previous trigger has both dmo | TC-TRIG-068 |
| OB-333EB526 | SHOULD | The debugger should perform this extra step when the PC doesn’t change during a regular step. | TC-SSTEP-008 |
| OB-33C53BBA | SHOULD | E.g. a vector load should be treated as if it performed multiple loads of size SEW (selected element width), a | TC-TRIG-018 |
| OB-3482D902 | MUST | Writing 0 to this register must result in a trigger that is disabled. | TC-TRIG-121 |
| OB-3598F677 | SHOULD | Debuggers should consider this when setting such breakpoints on, for example, memory-mapped I/O addresses. | TC-TRIG-069 |
| OB-364C1261 | MAY | Registers that may be updated as part of execution before the exception are allowed to be updated. | TC-DCSR-038 |
| OB-36576034 | UNSPECIFIED | Almost all instructions that change the privilege mode have UNSPECIFIED behavior. | TC-DCSR-039 |
| OB-36C3D0F5 | MUST | If the command takes arguments, the debugger must write them to the data registers before writing to command. | TC-AC-004 |
| OB-36EEBE64 | MAY | System designers may choose to add additional hardware debug support, but this specification defines a standar | TC-GEN-028 |
| OB-374E382F | CONDITIONAL | When a debugger writes 1 to resumereq, each selected hart’s resume ack bit is cleared and each selected, halte | TC-RC-019 |
| OB-376EA57A | MUST | If there is another mechanism to reset the DM, this mechanism must also reset all the harts accessible to the  | TC-RST-002 |
| OB-3857257F | SHOULD | On systems that have buses wider than 32 bits, a debugger should access sbdata0 after accessing the other sbda | TC-SBA-017 |
| OB-387C8D06 | MUST | The others must be written 0. | TC-TRIG-160 |
| OB-3910CF96 | CONDITIONAL | If stoptime is 0 then time continues to update. | TC-DCSR-040 |
| OB-3966132C | CONDITIONAL | If the bus manager is busy then accesses set sbbusyerror, and don’t do anything else. | TC-SBA-027 |
| OB-39E5E336 | CONDITIONAL | If the read succeeded and sbautoincrement is set, increment sbaddress. | TC-SBA-002 |
| OB-3A5A1CDE | CONDITIONAL | If it was necessary to clear ndmreset, this might have the following side effects: haltreq is cleared, potenti | TC-DIS-001 |
| OB-3A6DC444 | MUST_NOT | While an abstract command is executing (busy in abstractcs is high), a debugger must not change `hartsel`, and | TC-AC-005 |
| OB-3B16A732 | CONDITIONAL | When ebreak is executed (indicating the end of the Program Buffer code) the hart returns to its park loop. | TC-AC-043 |
| OB-3BB9820E | MAY | It may also be possible for the debugger to read from the program buffer through these registers. | TC-PB-001 |
| OB-3C2F3C6F | MUST | If halt is requested while wrs.sto or wrs.nto is executing, then the hart must leave the stalled state, comple | TC-GEN-002 |
| OB-3C49DBE0 | CONDITIONAL | If desired, debuggers can use a trigger’s mode filtering bits to restrict the matching to modes where it consi | TC-TRIG-132 |
| OB-3CE2B935 | MUST | An implementation must support the value of 0, but all other values are optional. | TC-TRIG-070 |
| OB-3CE8C55D | CONDITIONAL | If a debugger sees this status, it needs to give the target more TCK edges between Update-DR and Capture-DR. | TC-DMI-010 |
| OB-3FFC5310 | CONDITIONAL | If any of these operations fail, cmderr is set and none of the remaining steps are executed. | TC-AC-021 |
| OB-40588DFB | MAY | If the hart is using address translation this may be different from the physical address. | _(uncovered)_ |
| OB-40C96667 | CONDITIONAL | When select=1 and access size is N, this is further reduced, and comparisons only look at the lower N bits of  | TC-TRIG-071 |
| OB-40CE5B27 | CONDITIONAL | If an exception is encountered, the hart jumps to an address within the Debug Module. | TC-AC-044 |
| OB-40D7929B | CONDITIONAL | When the next most significant bit of this field is 1, it causes bits 15:8 to be ignored in the comparison, wh | TC-TRIG-133 |
| OB-40E5C5BF | SHOULD | It should almost never be necessary to scan IR, avoiding a big part of the inefficiency in typical JTAG use. | TC-DMI-003 |
| OB-411DA6FF | MUST_NOT | The PMP must not disallow fetches, loads, or stores in the address range associated with the Debug Module when | TC-AC-045 |
| OB-417BBC79 | UNSPECIFIED | How Debug Mode is implemented is not specified here. | TC-DCSR-041 |
| OB-41B6439E | MUST | If halt is requested while wfi is executing, then the hart must leave the stalled state, completing this instr | TC-GEN-001 |
| OB-41CC6045 | SHOULD | All DM registers should read 0, while writes should be ignored, with the following mandatory exceptions: authe | TC-AUTH-001 |
| OB-4268BEC1 | MUST | An implementation which does not implement the hart array mask register must tie this field to 0. | TC-TRIG-161 |
| OB-428E3BA1 | CONDITIONAL | If there is no translation then it will be the same. xepc The exception program counter CSR (e.g. mepc) that i | _(uncovered)_ |
| OB-44126EA0 | CONDITIONAL | When count is greater than 1 and the trigger matches, then count is decremented by 1. | TC-TRIG-046 |
| OB-442235EA | MUST | In the latter case, hit of the trigger whose action is 0 must still be set, giving a debugger an opportunity t | TC-TRIG-009 |
| OB-4463B604 | MUST_NOT | When authenticated is clear, the DM must not interact with the rest of the hardware platform, nor expose detai | TC-AUTH-002 |
| OB-447B9D84 | CONDITIONAL | If the trigger is mcontrol and timing is 0 or if the trigger is mcontrol6 and hit1 is 0, this corresponds to t | TC-DCSR-024 |
| OB-44B48B91 | CONDITIONAL | If there are additional DMs on this DMI, the base address of the next DM in the DMI address space is given in  | TC-DMI-001 |
| OB-458FEB4A | CONDITIONAL | If executing or fetching the instruction causes a trigger to fire with action=1, Debug Mode is re-entered imme | TC-SSTEP-002 |
| OB-45A50BE4 | MUST | It must be at least 0 and at most 20. | TC-TRIG-162 |
| OB-46F168A6 | MUST | If the debugger writes a compressed instruction into the Program Buffer, it must be placed into the lower 16 b | TC-PB-006 |
| OB-488DD661 | SHOULD | Debuggers should read back this field after writing to confirm they are using a hart group that is supported. | TC-RC-012 |
| OB-49511D4C | MAY | Abstract memory accesses act as if they are performed by the hart, although the actual implementation may diff | TC-GEN-016 |
| OB-497CE61E | CONDITIONAL | If stopcount is 0 then counters continue. | TC-DCSR-042 |
| OB-4A63EC3E | MUST | All debug modules must support selecting a single hart. | TC-GEN-008 |
| OB-4ABB0B8F | CONDITIONAL | If the Ssdbltrp extension is implemented and the new privilege mode is U, VS, or VU, then sstatus.SDT is set t | TC-RC-005 |
| OB-4B3A25CB | CONDITIONAL | If sberror is 0, sbbusyerror is 0, and sbreadonaddr is set then writes to this register start the following: S | TC-SBA-003 |
| OB-4C89EE63 | MUST | When halt or resume is requested, a hart must respond in less than one second, unless it is unavailable. (How  | TC-RC-020 |
| OB-4C8C3B9D | MUST | ELP Expected landing pad state, define by the Zicfilp extension. essential feature An essential feature must b | _(uncovered)_ |
| OB-4D3A997B | MAY | Custom extensions may also support instructions that are wider than XLEN. | TC-TRIG-100 |
| OB-4D7C060E | CONDITIONAL | If a debugger sees this status, there might be additional information in errinfo. 3 (busy): A DMI operation wa | TC-DMI-011 |
| OB-4D7EB531 | CONDITIONAL | If the hart halts for some other reason (e.g. breakpoint), the command sets cmderr to ``halt/resume'' and does | TC-QA-001 |
| OB-4DABD08C | MAY | If an abstract command is started while the selected hart is unavailable or if a hart becomes unavailable whil | TC-AC-006 |
| OB-4DEC4559 | SHOULD_NOT | Debuggers should not terminate a chain with a trigger with a different type. | TC-TRIG-072 |
| OB-4E06FCE7 | MAY | This bit can be used to just execute the Program Buffer without having to worry about placing valid values int | TC-AC-022 |
| OB-4E491BF3 | CONDITIONAL | While the reset is on-going, harts are either in the running state, indicating it’s possible to perform some a | TC-RST-003 |
| OB-4EBB9AFF | MAY | KEY This pin may be cut on the male and plugged on the female header to ensure the header is always plugged in | TC-DTM-008 |
| OB-4EFDFF24 | MUST | A debugger must still check dmistat when necessary. 0: It is not necessary to enter Run-Test/Idle at all. 1: E | TC-DTM-023 |
| OB-505C0BEA | CONDITIONAL | If this register is written while an abstract command is executing then the write is ignored and cmderr become | TC-AC-034 |
| OB-50A5BF54 | MUST_NOT | While this bit is 1, the debugger must not change which harts are selected. | TC-TRIG-163 |
| OB-512F79E4 | SHOULD | The Debug Module’s own state and registers should only be reset at power-up and while dmactive in dmcontrol is | TC-RST-004 |
| OB-5153C8AA | MAY | Pins whose functionality isn’t needed may be left unconnected. | TC-DTM-017 |
| OB-51D2FA20 | CONDITIONAL | If textra32 or textra64 are implemented for this trigger, it only matches when the conditions set there are sa | TC-TRIG-101 |
| OB-52E51B4F | MUST | For address matches without a mask, tdata2 must be able to hold all valid addresses in all supported translati | TC-TRIG-027 |
| OB-54813EE5 | MAY | There may be multiple DTMs in a single hardware platform. | TC-DTM-020 |
| OB-54FE9A68 | SHOULD | Debuggers should only write values to tdata2 such that M + maskmax ≥ XLEN and M > 0, otherwise it’s undefined  | TC-TRIG-073 |
| OB-55353F21 | MAY | The reset itself may also take an arbitrarily long time. | TC-RST-005 |
| OB-5581CFB4 | CONDITIONAL | If physical addresses are less than XLEN bits wide, they are zero-extended. | TC-TRIG-028 |
| OB-55B5756E | CONDITIONAL | If the debugger starts a new command while busy is set, cmderr becomes 1 (busy), the currently executing comma | TC-AC-007 |
| OB-573DC225 | MUST | The set of accessible triggers must start at 0, and be contiguous. | TC-TRIG-141 |
| OB-57452DA5 | CONDITIONAL | If textra32 or textra64 are implemented for this trigger, it only matches when the conditions set there are sa | TC-TRIG-035 |
| OB-57F58162 | SHOULD | This is similar to a type 2 trigger, but provides additional functionality and should be used instead of type  | TC-TRIG-122 |
| OB-5806ECD8 | CONDITIONAL | If the trigger fires with action=0 then zero is written to the tval CSR on the breakpoint trap. | TC-TRIG-047 |
| OB-584D4C25 | MAY | It may be supported with different options set, but it will not be supported at a later time when the hart or  | TC-AC-036 |
| OB-59621783 | MAY | Any accesses to the module may fail. | TC-TRIG-164 |
| OB-5A152AE4 | CONDITIONAL | When confstrptrvalid is set, reading this register returns bits 95:64 of the configuration structure pointer. | TC-DIS-008 |
| OB-5B68FD10 | CONDITIONAL | When a robust OS is running on a core, software can handle many debugging tasks. | TC-GEN-029 |
| OB-5C7970C0 | MAY | A target may relay the TCK signal here once it has processed it, allowing a debugger to adjust its TCK frequen | TC-DTM-009 |
| OB-5D9818BC | UNSPECIFIED | If more than one of these triggers has action=0 then tval is updated in accordance with one of them, but which | TC-TRIG-010 |
| OB-5E1F7B80 | CONDITIONAL | If the bit is not implemented, it is always 0 and writing it has no effect. | TC-TRIG-054 |
| OB-5F2CFA19 | MUST | For use in single step, icount must match for traps where the instruction will not be reexecuted after the han | TC-TRIG-048 |
| OB-5F5F139D | SHOULD | If the Access Register abstract command supports reading dpc while the hart is running, then the value read sh | TC-DCSR-025 |
| OB-5FFE2228 | CONDITIONAL | If textra32 or textra64 are implemented for this trigger, it only matches when the conditions set there are sa | TC-TRIG-055 |
| OB-60831DD0 | SHOULD | Accesses to this memory should be uncached to avoid side effects from debugging operations. | TC-AC-046 |
| OB-6095E42F | CONDITIONAL | When read this field returns 0. | _(uncovered)_ |
| OB-60AFAED8 | MAY | When this value is written, the DM may ignore any other bits written to `dmcontrol` in the same write. 1 (acti | TC-TRIG-165 |
| OB-62CDF75E | MAY | Custom extensions may also support instructions that are wider than XLEN. | TC-TRIG-074 |
| OB-634284F6 | MAY | While the spec allows for 20 `hartsel` bits, an implementation may choose to implement fewer than that. | TC-TRIG-166 |
| OB-637C9969 | SHOULD_NOT | Debuggers should not terminate a chain with a trigger with a different type. | TC-TRIG-102 |
| OB-63A2C8AF | CONDITIONAL | If multiple mcontrol triggers are chained then the faulting virtual address is the address which caused any of | TC-TRIG-075 |
| OB-641C3117 | CONDITIONAL | While the uncertain mechanism exists to deal with these situations, it can lead to an unusable number of false | TC-TRIG-103 |
| OB-64F52203 | MAY | A debugger may write any value. | _(uncovered)_ |
| OB-65B84BD6 | MAY | If etrigger/itrigger is set to trigger on exception/interrupt X and if X is delegated to mode Y then the trigg | TC-TRIG-146 |
| OB-65EAE27E | UNSPECIFIED | Writes to sbcs while sbbusy is high result in undefined behavior. | TC-SBA-013 |
| OB-664DCB83 | CONDITIONAL | When leaving Debug Mode, time will reflect the latest value of mtime again. | TC-DCSR-007 |
| OB-66712737 | UNSPECIFIED | Accessing authdata results in unspecified behavior. authbusy only becomes set in immediate response to an acce | TC-DIS-010 |
| OB-675A96C8 | CONDITIONAL | If there is a failure, the interface ensures that no commands execute after the failing one. | TC-AC-008 |
| OB-676C626B | CONDITIONAL | If the write succeeded and sbautoincrement is set, increment sbaddress. | TC-SBA-018 |
| OB-687501FB | MAY | An instruction may cause an exception into a more privileged mode where the trigger is not enabled. | TC-SSTEP-009 |
| OB-6888F4EE | MUST | Debuggers must avoid the latter case by checking chain on the previous trigger if they’re writing mcontrol6. | TC-TRIG-104 |
| OB-6941FBAA | MAY | This may cancel outstanding halt requests for those harts. | TC-TRIG-167 |
| OB-69647D83 | CONDITIONAL | If either sberror or sbbusyerror isn’t 0 then accesses do nothing. | TC-SBA-019 |
| OB-6969F74F | MAY | Debug Modules may implement a Hart Array Mask register to allow selecting multiple harts at once. | TC-HS-010 |
| OB-69C228E5 | CONDITIONAL | When transfer is set, the DM populates these words with lw <gpr>, 0x400(zero) or sw <gpr>, 0x400(zero). 64- an | TC-AC-047 |
| OB-69E787E6 | MUST | The busy condition must be cleared by writing dmireset in dtmcs, and then the second scan scan must be perform | TC-DMI-004 |
| OB-69EADA5F | MUST | When the TAP is reset, IR must default to 00001, selecting the IDCODE instruction. | TC-DTM-003 |
| OB-69FD1205 | MAY | All control transfer instructions may act as illegal instructions if their destination is in the Program Buffe | TC-DCSR-043 |
| OB-6AC00D11 | CONDITIONAL | If cmderr is non-zero, writes to this register are ignored. cmderr inhibits starting a new command to accommod | TC-AC-039 |
| OB-6BD0BBD1 | UNSPECIFIED | The result of other writes is undefined. | _(uncovered)_ |
| OB-6BF0589C | MAY | This trigger may fire on up to XLEN of the Exception Codes defined in mcause (described in the Privileged Spec | TC-TRIG-036 |
| OB-6CD8999A | MAY | The reservation registered by an lr instruction on a memory address may be lost when entering Debug Mode or wh | TC-DCSR-003 |
| OB-6D10A122 | MAY | Debuggers may assume that a hardware platform has no harts with indexes higher than the first nonexistent one. | TC-HS-002 |
| OB-6D4B3094 | MAY | For example, vector load/store instructions which raise exceptions may partially update the destination regist | TC-DCSR-044 |
| OB-6D94A52F | CONDITIONAL | If sbasize is less than 65, then this register is not present. | TC-SBA-007 |
| OB-6E4A7155 | CONDITIONAL | If textra32 or textra64 are implemented for this trigger, it only matches when the conditions set there are sa | TC-TRIG-049 |
| OB-6E938BEE | CONDITIONAL | Once a hart’s reset is complete, havereset becomes set. | TC-RST-006 |
| OB-6F0BB28B | CONDITIONAL | If an exception is encountered during execution of the Program Buffer, no more instructions are executed, the  | TC-PB-007 |
| OB-6F7EAA7A | MAY | Hardware may implement the bit fully writable, in which case the debugger has a little more control. | TC-TRIG-076 |
| OB-6FA6FEB5 | MUST | On single-hart cores cycle should be stopped, but on multi-hart cores it must keep incrementing. | TC-DCSR-008 |
| OB-6FCBFC58 | SHOULD | This field should be tied to 0 when S-mode is not supported. | TC-TRIG-134, TC-TRIG-135 |
| OB-6FE51F06 | SHOULD | When an external trigger that’s a member of the halt group fires: All the harts in the halt group that are run | TC-HG-008 |
| OB-71273439 | MUST | To enumerate all the harts, a debugger must first determine HARTSELLEN by writing all ones to `hartsel` (assum | TC-HS-013 |
| OB-713437CA | CONDITIONAL | When the debugger reads this field, it means the following: 0 (success): The previous operation completed succ | TC-DMI-012 |
| OB-713A614B | CONDITIONAL | If dataaccess is 1: Address of RAM where the data registers are shadowed. | TC-DIS-015 |
| OB-72667843 | CONDITIONAL | If medeleg [3]=1 and hedeleg [3]=1 then it prevents triggers with action=0 from matching or firing while in VS | TC-TRIG-147 |
| OB-7268188E | SHOULD_NOT | These should not be implemented and aren’t further documented here. 2 (mcontrol): The trigger is an address/da | TC-TRIG-123 |
| OB-72E1861A | CONDITIONAL | If the command fails, no assumptions can be made about the contents of these registers. | TC-GEN-012 |
| OB-730B372D | MUST | If it is implemented, mcontext must also be implemented. | TC-TRIG-041 |
| OB-7387CD43 | SHOULD | Technically backwards incompatible, but unlikely to be noticeable: stopcount only applies to hart-local counte | TC-GEN-021 |
| OB-7429F88E | SHOULD | The signal should reset every part of the hardware platform, including every hart, except for the DM and any l | TC-TRIG-168 |
| OB-75E8DBC5 | MAY | Hardware may support none or just a few TM external trigger inputs (starting with TM external trigger input 0  | TC-HG-001 |
| OB-76553A0D | CONDITIONAL | If this feature is supported, multiple harts can be halted, resumed, and reset simultaneously. | TC-HS-011 |
| OB-765F059B | UNSPECIFIED | This operation leaves the values in address and data UNSPECIFIED. 3 (reserved): Reserved. | TC-DMI-013 |
| OB-7695BA34 | MUST | Hardware must return 0 when those fields are read, and ignore the value written to them. | TC-GEN-024 |
| OB-76B6FD7E | CONDITIONAL | When any trap into M-mode is taken, mte is set to 0. | TC-TRIG-119 |
| OB-772A3799 | MAY | Additional DTMs may be added in future versions of this specification. | TC-DTM-021 |
| OB-779B3232 | CONDITIONAL | If medeleg [3]=1 then it prevents triggers with action=0 from matching or firing while in S-mode and while SIE | TC-TRIG-148 |
| OB-77AB89C4 | MUST | A typical debugger will not know enough about the hardware platform to know what’s going to happen, and must a | TC-AC-041 |
| OB-77CBC2C2 | CONDITIONAL | When the trigger matches, it fires after the trap occurs, just before the first instruction of the trap handle | TC-TRIG-056 |
| OB-7804001D | SHOULD | JTAG Refers to work done by IEEE’s Joint Test Action Group, described in IEEE 1149.1. legacy feature A legacy  | _(uncovered)_ |
| OB-78B09A4C | MAY | On any given write, a debugger may only write 1 to at most one of the following bits: resumereq, hartreset, ac | TC-TRIG-169 |
| OB-78D05CBF | MUST | progbuf0 through progbuf15 must provide write access to the optional program buffer. | TC-PB-002 |
| OB-79B338B8 | SHOULD | Asserting reset should reset any RISC-V cores as well as any other peripherals on the PCB. | TC-DTM-010 |
| OB-7AECBFE5 | SHOULD | In later operations the debugger should allow for more time between Update-DR and Capture-DR. | TC-DMI-005 |
| OB-7C245867 | MAY | W1 - hasel Selects the definition of currently selected harts. 0 (single): There is a single currently selecte | TC-TRIG-170 |
| OB-7C25B377 | MAY | Executing the Program Buffer may cause the value of dpc to become UNSPECIFIED. | TC-DCSR-026 |
| OB-7DCFCB55 | SHOULD | A debugger which wishes to use the hart array mask register feature should set this bit and read back to see i | TC-TRIG-171 |
| OB-7E09022C | SHOULD | It is recommended that if one register in a group is accessible, then all registers in that group are accessib | TC-AC-023 |
| OB-7FACBC59 | UNSPECIFIED | If an instruction matches this trigger and the instruction performs multiple memory accesses, it is UNSPECIFIE | TC-TRIG-077 |
| OB-801BF5E9 | MAY | The DM external triggers available to add to halt groups may be the same as or distinct from the DM external t | TC-RC-013 |
| OB-80D43B2B | CONDITIONAL | When any trap into M-mode is taken, mpte is set to the value of mte. | TC-TRIG-120 |
| OB-80DC4913 | CONDITIONAL | When the halt request bit is set, the Debug Module raises a special interrupt to the selected harts. | TC-AC-048 |
| OB-811A6EBE | CONDITIONAL | If this results in an illegal instruction exception, then there are no triggers implemented. | TC-TRIG-003 |
| OB-820B57A9 | MAY | Third, it may provide access to devices that a hart does not have access to. | TC-SBA-030 |
| OB-82610EE4 | CONDITIONAL | When authbusy is clear, the debugger can communicate with the authentication module by reading or writing this | TC-AUTH-005 |
| OB-82F9818A | SHOULD | Debug software should implement them, but hardware can skip this section. | TC-GEN-006 |
| OB-83F72B6A | MAY | The optional custom0 through custom15 registers may be used for non-standard features. | TC-GEN-011 |
| OB-84D439AC | CONDITIONAL | If the instruction that is executed causes the PC to change to an address where an instruction fetch causes an | TC-SSTEP-003 |
| OB-8698F4F0 | MAY | Commands may be supported with some options set, but not with other options set. | TC-AC-009 |
| OB-86F2FD32 | CONDITIONAL | If this is combined with load and select=1 then a memory access will be performed (including any side effects  | TC-TRIG-078 |
| OB-88014B55 | CONDITIONAL | If a value is unsupported, the implementation converts the value to one that is supported. | _(uncovered)_ |
| OB-881C3791 | MUST | When any hart in the group halts, they all halt. (Optional) Respond to external triggers by halting each hart  | TC-GEN-009 |
| OB-88264FCA | SHOULD_NOT | The hardware should not rely on this debugger behavior, but should enforce it by ignoring writes to these bits | TC-AC-010 |
| OB-88FF7056 | MUST | If this command supports memory accesses while the hart is running, it must also support memory accesses while | TC-AM-002 |
| OB-891C5A28 | SHOULD | Otherwise, if the hart was initially running it will execute normally (running state) and if the hart was init | TC-RST-007 |
| OB-894F5BEF | CONDITIONAL | If XLEN is less than DXLEN, writes to this register are sign-extended. | TC-TRIG-127 |
| OB-895941E6 | MAY | For instance a series of scans may write a Debug Program and execute it. | TC-DMI-014 |
| OB-89715BB2 | SHOULD_NOT | It should not reset the debug logic. | TC-DTM-011 |
| OB-89717419 | SHOULD | It is recommended that there are additional compare values for the other accessed virtual addresses. (E.g. on  | TC-TRIG-079 |
| OB-8A224D0A | SHOULD | If the Access Register abstract command supports writing dpc while the hart is running, then the executing pro | TC-DCSR-027 |
| OB-8A4EBAA6 | CONDITIONAL | When triggers are chained, the priority is the lowest priority of the triggers in the chain. | TC-TRIG-011 |
| OB-8A95398D | MAY | It may be tied to either 0 or 1. | TC-DCSR-009 |
| OB-8B59ED72 | MAY | This optional register may be implemented only if the H extension is implemented. | TC-TRIG-042 |
| OB-8BBB0165 | MAY | An implementation may either ignore the signal altogether when it cannot fire (dropping the trigger event) or  | TC-HG-002 |
| OB-8BDD4DD9 | MUST_NOT | Writes to one tdata register must not modify the contents of other tdata registers, nor the configuration of a | TC-TRIG-029 |
| OB-8C432E52 | MUST | Software must only write 0 to those fields, and ignore their value while reading. | TC-GEN-025 |
| OB-8C5B1904 | MAY | An implementation may support an implicit ebreak that is executed when a hart runs off the end of the Program  | TC-PB-008 |
| OB-8C7C97F1 | CONDITIONAL | When set to 1, each selected hart will halt upon the next deassertion of its reset. | TC-TRIG-172 |
| OB-8CC4C274 | MAY | This means that there may be no forward progress if Debug Mode is entered between lr and sc pairs. | TC-DCSR-004 |
| OB-8D06AC44 | CONDITIONAL | If an exception occurs, cmderr is set to ``exception,'' the Program Buffer execution ends, and the hart is hal | TC-QA-002 |
| OB-8D727FC3 | CONDITIONAL | If the instruction being stepped over would normally stall the hart, then instead the instruction is treated a | TC-SSTEP-004 |
| OB-8DD1659F | SHOULD | In addition, it is recommended that there are additional compare values for the other accessed virtual address | TC-TRIG-105 |
| OB-8DEE01F2 | CONDITIONAL | When count is 0 it stays at 0 until explicitly written. | TC-TRIG-050 |
| OB-8DF53D9D | CONDITIONAL | Once allresumeack is set, the debugger knows the selected harts have resumed. | TC-GEN-017 |
| OB-8ECFAB58 | CONDITIONAL | If the bus manager is busy then accesses set sbbusyerror, and don’t do anything else. | TC-SBA-020 |
| OB-8EDEE401 | MUST | If a command returns results, the Debug Module must ensure they are placed in the data registers before busy i | TC-AC-011 |
| OB-8F42D686 | MAY | Hardware platforms with very large number of harts may permanently disable some during manufacturing, leaving  | TC-HS-003 |
| OB-8FD1FA4F | MAY | All operations are executed with machine mode privilege, except that additional Debug Mode CSRs are accessible | TC-DCSR-045 |
| OB-900643C1 | MAY | An implementation may tie any number of upper bits in this field to 0. | TC-TRIG-062 |
| OB-9074ADA2 | MAY | The Program Buffer may be implemented as RAM which is accessible to the hart. | TC-PB-009 |
| OB-90A1E417 | MUST | If that caused an exception, the debugger must read tdata1 to discover the type. (If type is 0, this trigger d | TC-TRIG-004 |
| OB-90E3569C | CONDITIONAL | If hardware implements mpte and mte, then stepping through non-trap code which doesn’t allow for nested interr | TC-SSTEP-010 |
| OB-91F031CC | CONDITIONAL | When the system bus manager is busy, writes to this register will set sbbusyerror and don’t do anything else. | TC-SBA-004 |
| OB-927ACB75 | CONDITIONAL | When a hart comes out of reset and haltreq or resethaltreq are set, the hart will immediately enter Debug Mode | TC-RST-008 |
| OB-92A6C8BF | MUST | Multiple State Change Instructions. xepc or dpc (depending on action) must be set to the virtual address of th | TC-TRIG-106 |
| OB-934D84D3 | MUST | Otherwise, this must be an address that can be used to access the configuration structure from the hart with I | TC-DIS-003 |
| OB-934DD1FC | SHOULD | If tdata2 can hold any invalid addresses, then writes of an invalid address that can not be represented as-is  | TC-TRIG-023 |
| OB-93B92434 | MUST_NOT | If hardware automatically prevents action=0 triggers from matching when entering a trap handler as described i | TC-SSTEP-011 |
| OB-93CCD089 | MAY | An access may only fail if the hart, running M-mode code, might encounter that same failure when it attempts t | TC-AM-003 |
| OB-94557B58 | CONDITIONAL | If step is set when a hart resumes then it will single step, regardless of the reason for resuming. | TC-SSTEP-005 |
| OB-94F5A044 | MUST_NOT | A debugger must not write to sbcs until it reads sbbusy as 0. | TC-SBA-014 |
| OB-95214F7D | CONDITIONAL | If sbaccess64 and sbaccess128 are 0, then this register is not present. | TC-SBA-024 |
| OB-954248D0 | CONDITIONAL | If so, the debugger has more flexibility in what it can do with the program buffer. | TC-PB-010 |
| OB-9678E673 | SHOULD | Hardware should enforce this by ignoring changes to `hartsel` while busy is set. | TC-TRIG-173 |
| OB-96A4A892 | CONDITIONAL | If reading is not supported, then all reads return 0. progbufsize indicates how many progbuf registers are imp | TC-PB-003 |
| OB-97334823 | UNSPECIFIED | If the destination register of any load or AMO is zero then it is UNSPECIFIED whether a data load trigger will | TC-TRIG-015 |
| OB-979715B3 | SHOULD | A shrouded connector should be used to prevent the cable from being plugged in incorrectly. | TC-DTM-012 |
| OB-98097CE3 | CONDITIONAL | When 1 is written and hgselect is 1, the DM will change the group of the DM external trigger selected by dmext | TC-RC-014 |
| OB-985839B9 | MUST_NOT | The exact address is an implementation detail that a debugger must not rely on. | TC-AC-049 |
| OB-98C38078 | MAY | E.g. on a hardware platform with 48 harts only bit 0 of this field may actually be writable. | TC-HS-009 |
| OB-99DCB478 | MUST | Because chain affects the next trigger, hardware must zero it in writes to mcontrol that set dmode to 0 if the | TC-TRIG-080 |
| OB-99F62644 | CONDITIONAL | When confstrptrvalid is set, reading this register returns bits 31:0 of the configuration structure pointer. | TC-DIS-004 |
| OB-9A3DE48A | CONDITIONAL | If XLEN is 32, then it is not possible to set a trigger for interrupts with Exception Code larger than 31. | TC-TRIG-057 |
| OB-9A89C487 | SHOULD | If it is not present it should read all-zero. | TC-DIS-016 |
| OB-9AA78A6E | MUST | Because chain affects the next trigger, hardware must zero it in writes to mcontrol6 that set dmode to 0 if th | TC-TRIG-107 |
| OB-9B06478A | MAY | Debug Modules may optionally implement this command and may support read and write access to memory locations  | TC-AM-004 |
| OB-9B1EC118 | MUST | This means that a debugger must always read back values it writes to tdata registers, unless it already knows  | TC-TRIG-030 |
| OB-9D5EA091 | CONDITIONAL | While these programs are executed, the hart does not leave Debug Mode (see Sdext.adoc#debugmode). | TC-PB-011 |
| OB-9DAFE72E | CONDITIONAL | If transfer is not set, the DM populates these instructions as nop’s. | TC-AC-050 |
| OB-9E69165C | MAY | Debug Modules may optionally support accessing other registers, or accessing registers when the hart is runnin | TC-AC-024 |
| OB-9EBAAE8B | MUST | The DM must respond to a request from the DTM when RSP_READY is high. | TC-GEN-020 |
| OB-9EBF2B70 | MAY | To accommodate various implementations, execute, load, and store address/data triggers may fire at whatever po | TC-TRIG-081 |
| OB-9F36F03C | CONDITIONAL | If it is 1 then time will not update. | TC-DCSR-046 |
| OB-A01C0FEE | SHOULD | If this trigger supports multiple types, then the hardware should disable it by changing type to 15. | TC-TRIG-124 |
| OB-A0A86388 | UNSPECIFIED | The reset value is either a constant or "Preset." The latter means it is an implementation-specific legal valu | TC-GEN-026 |
| OB-A0ED4DE3 | CONDITIONAL | When the system bus manager is busy, writes to this register will set sbbusyerror and don’t do anything else. | TC-SBA-009 |
| OB-A2378959 | UNSPECIFIED | The value of the remaining bits of arg0 are UNSPECIFIED. 1 (memory): Copy data from the low bits of arg0 into  | TC-AM-005 |
| OB-A28E8B3F | CONDITIONAL | If the bit is 1 then the hart is selected. | TC-HS-012 |
| OB-A2A3A8FA | MAY | Harts may report 3 for this cause instead. 7 (other): The hart halted for a reason other than the ones mention | TC-DCSR-010 |
| OB-A343AEA1 | CONDITIONAL | If write is set and transfer is set, then copy data from the arg0 region of data into the register specified b | TC-AC-025 |
| OB-A3468DC8 | MUST | For data load triggers, debuggers must first attempt to set the breakpoint with timing of 1. | TC-TRIG-082 |
| OB-A398E5DE | MAY | To protect intellectual property it may be desirable to lock access to the Debug Module. | TC-AUTH-003 |
| OB-A431FA7B | MAY | Hardware may support only a subset of exceptions. | TC-TRIG-037 |
| OB-A43F9589 | MUST | If there are no DM external triggers, this field must be tied to 0. | TC-RC-015 |
| OB-A49F0FED | MAY | To accommodate various implementations, execute, load, and store address/data triggers may fire at whatever po | TC-TRIG-108 |
| OB-A5194D4F | MAY | An implementation may report ``Other'' (7) for any error condition. 0 (none): There was no bus error. 1 (timeo | TC-SBA-015 |
| OB-A560EA93 | MUST | If this register is implemented then bits corresponding to implemented progbuf and data registers must be writ | TC-AC-035 |
| OB-A6B5A53C | SHOULD | A debugger should discover HARTSELLEN by writing all ones to `hartsel` (assuming the maximum size) and reading | TC-TRIG-174 |
| OB-A7559BE4 | CONDITIONAL | If confstrptrvalid is 0, then the confstrptr registers hold identifier information which is not further specif | TC-DIS-005 |
| OB-A780F203 | MAY | Since an NMI can indicate a hardware error condition, reliable debugging may no longer be possible once this b | TC-DCSR-011 |
| OB-A7C3DDB5 | MUST | Code that restores CSR context of triggers that might be configured to fire in the current privilege mode must | TC-TRIG-031 |
| OB-A8D1452C | CONDITIONAL | If the bit is not implemented, it is always 0 and writing it has no effect. | TC-TRIG-083 |
| OB-A989500A | UNSPECIFIED | Whether data store triggers match on AMOs is UNSPECIFIED. | TC-TRIG-016 |
| OB-A9E0D915 | MAY | If the encoding written is not supported or the debugger is not allowed to change to it, the hart may change t | TC-DCSR-012 |
| OB-AA0F5B7A | MAY | If one of the writes fails but the execution continues, then the Debug Program may hang or have other unexpect | TC-DMI-015 |
| OB-AA3E9B6B | MUST | See custom, and custom0 through custom15. #406 Reserve trigger type values for non-standard use. #417 Add nmi  | TC-GEN-022 |
| OB-AA5FF870 | CONDITIONAL | If the H extension is implemented, it’s recommended to implement 7 bits on RV32 and 14 bits on RV64. | TC-TRIG-063 |
| OB-AA652C80 | MUST | Since triggers can be used both by Debug Mode and M-mode, the external debugger must restore this register if  | TC-TRIG-142 |
| OB-AAB99703 | MAY | Harts may be unavailable for a variety of reasons including being reset, temporarily powered down, and not bei | TC-HS-004 |
| OB-AC404D1B | MAY | Implementations may pay attention to this bit to further aid debugging, for example by preventing the Debug Mo | TC-TRIG-175 |
| OB-AC832F1C | MAY | Any number of upper bits of mhvalue and svalue may be tied to 0. mhselect and sselect may only support 0 (igno | TC-TRIG-136 |
| OB-ACDAE456 | CONDITIONAL | If a non-existent trigger value is written here, the hardware will change it to a valid one or 0 if no DM exte | TC-RC-016 |
| OB-AE674FDB | SHOULD | All the other harts in the halt group that are running will quickly halt. cause for those harts should be set  | TC-HG-009 |
| OB-AE7B5FB7 | CONDITIONAL | When mprven, the external debugger can set MPRV and MPP appropriately to have hardware perform memory accesses | TC-DCSR-047 |
| OB-AEDFF545 | UNSPECIFIED | The address and data reported in the following Capture-DR are undefined. | TC-DMI-016 |
| OB-AFA85424 | CONDITIONAL | When pending is set, the trigger fires just before any further instructions are executed in a mode where the t | TC-TRIG-051 |
| OB-AFE39A9C | CONDITIONAL | If action=0, the standard CSRs are updated for taking the breakpoint trap, and zero is written to the relevant | TC-TRIG-058 |
| OB-B08205DE | SHOULD | The Core Debug Registers ([debreg]) should be accessible if abstract CSR access is implemented. | TC-AC-026 |
| OB-B082EA41 | MAY | data0 through data11 are registers that may be read or changed by abstract commands. datacount indicates how m | TC-GEN-013 |
| OB-B10553EA | CONDITIONAL | If sbasize is less than 97, then this register is not present. | TC-SBA-010 |
| OB-B10A0637 | MUST | After changing the value of this bit, the debugger must poll dmcontrol until dmactive has taken the requested  | TC-TRIG-176 |
| OB-B237B93F | MAY | Writing less than the full register may be supported, but what happens to the high bits in that case is UNSPEC | TC-AC-027 |
| OB-B2AA28A5 | CONDITIONAL | If resume groups are not implemented, then grouptype will remain 0 even after 1 is written there. | TC-RC-017 |
| OB-B341DF22 | CONDITIONAL | When the system bus manager is busy, writes to this register will set sbbusyerror and don’t do anything else. | TC-SBA-008 |
| OB-B3B5EA02 | UNSPECIFIED | The behavior of other accesses is undefined. | TC-RST-009 |
| OB-B4F931A6 | CONDITIONAL | When cetrig is 1, resuming from Debug Mode following an entry due to a critical error will result in an immedi | TC-DCSR-013 |
| OB-B52071A0 | UNSPECIFIED | Incrementing past the highest supported value causes regno to become UNSPECIFIED. | TC-AC-028 |
| OB-B54F3500 | MAY | The debugger may resume with cetrig set to 0 to allow the platform defined actions on critical-error signal to | TC-DCSR-014 |
| OB-B5A0374F | SHOULD | The MIPI-10 connector should provide plenty of signals for all modern hardware. | TC-DTM-013 |
| OB-B6DC9B48 | CONDITIONAL | If the debugger requests to read a CSR in that case, the command will return "not supported". | TC-AC-012 |
| OB-B7C020E6 | MAY | In these cases such a trigger may cause a breakpoint exception while already in a trap handler. | TC-TRIG-149 |
| OB-B82496D0 | MAY | Implementations that wish to limit the maximum length of a trigger chain (eg. to meet timing requirements) may | TC-TRIG-084 |
| OB-B845B423 | MUST | Exactly what is affected by this reset is implementation dependent, but it must be possible to debug programs  | TC-RST-010 |
| OB-B8651EBD | SHOULD | When an implementation supports data value triggers (select=1), it is recommended that those triggers support  | TC-TRIG-109 |
| OB-B86DB63F | SHOULD | When read the returned value should be 0. | _(uncovered)_ |
| OB-B8A26943 | MUST | When harts have been reset, they must set a sticky havereset state bit. | TC-RST-011 |
| OB-B8A95BEA | MUST | WARL 0 timing 0 (before): The action for this trigger will be taken just before the instruction that triggered | TC-TRIG-085 |
| OB-B8D6518D | MUST | Other harts in the halt group that are halted but have started the process of resuming must also quickly becom | TC-HG-010, TC-HG-011 |
| OB-B91C10EF | CONDITIONAL | When hgselect is 1, contains the group of the DM external trigger selected by dmexttrigger. | TC-RC-018 |
| OB-B932B7D6 | MAY | Each trigger may support a variety of features. | TC-TRIG-005 |
| OB-B94D3BEB | CONDITIONAL | When a hart’s halt-on-reset request bit is set, the hart will immediately enter debug mode on the next deasser | TC-RC-021 |
| OB-B9A3E98D | MUST | Debuggers that want to disable interrupts while stepping must disable them by changing mstatus, and specially  | TC-TRIG-001 |
| OB-B9D6932F | MUST | Table 1. action encoding Value Description 0 Raise a breakpoint exception. (Used when software wants to use th | TC-TRIG-006 |
| OB-BA42D32B | CONDITIONAL | If it is not 1 then NAPOT matching is not supported. | TC-TRIG-110 |
| OB-BA502A14 | UNSPECIFIED | The details of the latter are implementation-specific. 0 (full checks): Full permission checks apply. 1 (relax | TC-AC-037 |
| OB-BACE5E9D | CONDITIONAL | If the bus manager is busy then accesses set sbbusyerror, and don’t do anything else. | TC-SBA-025 |
| OB-BB0D78DF | CONDITIONAL | When any hart in a halt group halts: That hart halts normally, with cause reflecting the original cause of the | TC-HG-012 |
| OB-BB705A10 | SHOULD | Harts that are in the process of halting should complete that process and stay halted. | TC-HG-013, TC-HG-014 |
| OB-BC0EA380 | CONDITIONAL | When select=1 and access size is N, this is further reduced, and comparisons only look at the lower N bits of  | TC-TRIG-111 |
| OB-BC2186F3 | MUST | This must be 1 when progbufsize is 1. | TC-DIS-011 |
| OB-BC3EEA7F | CONDITIONAL | When they resume execution, they will execute the same instruction once more. | TC-TRIG-143 |
| OB-BC4993CF | MUST | To avoid an infinite loop if the exception handler does not address the cause of the exception, the debugger m | TC-SSTEP-012 |
| OB-BC7D4ECD | SHOULD | When clearing this bit, debuggers should also set the action field (whose location depends on type) to somethi | TC-TRIG-125 |
| OB-BD3D2338 | MUST | A debugger must read back tdata2 after writing it to confirm the requested functionality is actually supported | TC-TRIG-059 |
| OB-BD58176C | MUST | Bits 6:0 must be bits 6:0 of the designer/manufacturer’s Identification Code as assigned by JEDEC Standard JEP | TC-DTM-026 |
| OB-BE5AAD05 | CONDITIONAL | If textra32 or textra64 are implemented for this trigger, it only matches when the conditions set there are sa | TC-TRIG-086 |
| OB-BE895C5E | MUST | If progbufsize is 1 then the following apply: impebreak must be 1. | TC-PB-012 |
| OB-C00B3FF2 | CONDITIONAL | When an exception occurs while executing the Program Buffer, command becomes set. | TC-AC-042 |
| OB-C0D042EA | CONDITIONAL | If that doesn’t clear busy, then it can try resetting the Debug Module (using dmactive). | TC-AC-013 |
| OB-C0E3DB5B | SHOULD | When an implementation supports address triggers (select=0), it is recommended that those triggers support eve | TC-TRIG-087 |
| OB-C112BA4F | MAY | Instructions that depend on the value of the PC (e.g. auipc) may act as illegal instructions. | TC-DCSR-048 |
| OB-C20B338E | SHOULD | Implementations should implement priorities as shown in the table. | TC-DCSR-015 |
| OB-C2D3D7FB | SHOULD | This pin is optional but strongly encouraged. nRESET should never be connected to the TAP reset, otherwise the | TC-DTM-014 |
| OB-C32A3527 | CONDITIONAL | If XLEN is less than DXLEN, writes to this register are sign-extended. | TC-TRIG-129 |
| OB-C35B2B26 | CONDITIONAL | If Smstateen is implemented, then accessibility of in HS-Mode is controlled by mstateenzero[57]. | TC-TRIG-043 |
| OB-C432B15B | MUST | Since there are at most 12 data registers, the value in this register must be 12 or smaller. | TC-DIS-017 |
| OB-C501790D | CONDITIONAL | If the breakpoint trap does not go to a higher privilege mode, this will lose CSR information for the original | TC-TRIG-060 |
| OB-C5807841 | MAY | Possibilities may include writing to special memory-mapped locations, or executing special instructions via th | TC-SBA-031 |
| OB-C5923002 | MUST | These bits must be set regardless of the cause of the reset. | TC-RST-012 |
| OB-C632BA74 | CONDITIONAL | If the Zicfilp extension is enabled at the new privilege mode, the current ELP state is changed to that specif | TC-RC-006 |
| OB-C7143C1D | MUST | Writing this register while an abstract command is executing causes cmderr to become 1 (busy) once the command | TC-AC-038 |
| OB-C71E58C5 | UNSPECIFIED | If the DM is reset while a hart is halted, it is UNSPECIFIED whether that hart resumes. | TC-RC-022 |
| OB-C7DF8E9B | CONDITIONAL | If the trigger fires with action=0 then zero is written to the tval CSR on the breakpoint trap. | TC-HG-003 |
| OB-C82CFCE2 | MUST | Unimplemented instructions must select the BYPASS register. | TC-DTM-004 |
| OB-C860E223 | MAY | The actual reset may start as soon as the bit is asserted, but may start an arbitrarily long time after the bi | TC-RST-013 |
| OB-C87DB74D | CONDITIONAL | When a debugger writes 1 to haltreq, each selected hart’s halt request bit is set. | TC-RC-023 |
| OB-C89C1926 | MAY | A debugger may write dpc to change where the hart resumes. | TC-DCSR-028 |
| OB-C9753D1E | MAY | The signal may be used bi-directional to drive or sense the target reset signal. | TC-DTM-015 |
| OB-C9AD34AA | CONDITIONAL | When the trigger matches, it fires after the trap occurs, just before the first instruction of the trap handle | TC-TRIG-038 |
| OB-C9F7A1E5 | MAY | During this time, the DM may ignore any register writes. 0 (inactive): The module’s state, including authentic | TC-TRIG-177 |
| OB-CA052A69 | MUST | It should be taken before the next instruction is retired, but it is better to implement triggers imprecisely  | TC-TRIG-088 |
| OB-CBBF5EB9 | MUST | Alternatively, it may state that partial execution is not allowed, implying that a mid-execution trigger must  | TC-TRIG-144 |
| OB-CCDDA3DE | SHOULD | The Trigger Module should match such accesses as if they all happened individually. | TC-TRIG-019 |
| OB-CE90F8DD | CONDITIONAL | If the H extension is not implemented, it’s recommended to implement 6 bits on RV32 and 13 bits on RV64 (as vi | TC-TRIG-064 |
| OB-CE92313B | MAY | Harts may be unavailable while reset is asserted, and some time after reset is deasserted. | TC-HS-005 |
| OB-CFF92650 | MUST | In particular, dpc must be able to hold all valid virtual addresses and the writability of the low bits depend | TC-DCSR-029 |
| OB-D006BECC | MUST | Systems that only support M-Mode can use icount as well, but count must be able to count several instructions  | TC-TRIG-002 |
| OB-D1081042 | SHOULD | When there are multiple reasons to enter Debug Mode in a single cycle, hardware should set cause to the cause  | TC-DCSR-016 |
| OB-D166808B | SHOULD | That means harts might become available or unavailable at any time, although these events should be rare in ha | TC-HS-006 |
| OB-D33286E8 | CONDITIONAL | If the new privilege mode is less privileged than M-mode, MPRV in mstatus is cleared. | TC-RC-007 |
| OB-D4554185 | SHOULD | If a design does need legacy JTAG signals, then the MIPI-20 connector should be used. | TC-DTM-016 |
| OB-D636CFDD | MAY | Debug Modules on systems without address translation (i.e. virtual addresses equal physical) may optionally al | TC-AM-006 |
| OB-D6A08D5A | CONDITIONAL | Once they are set, they will not clear until the debugger acknowledges them using ackunavail. | TC-DIS-012 |
| OB-D6E5BD74 | MAY | An implementation may tie any number of high bits in this field to 0. | TC-TRIG-117 |
| OB-D898401F | MUST | Implementing this trigger as described here requires that version is 1 or higher, which in turn means tinfo mu | TC-TRIG-112 |
| OB-D9BC6E5C | MUST | On components that don’t implement authentication, this bit must be preset as 1. | TC-DIS-013 |
| OB-DAC9C9EE | MUST | If that is the case, it must be possible to read/write dpc using an abstract command with postexec not set. | TC-DCSR-030 |
| OB-DAEC5018 | SHOULD | If the current instruction can be partially executed and should be restarted to complete, then the relevant st | TC-RC-002 |
| OB-DB14A7D2 | MUST | If the operation didn’t complete in time, op will be 3 and the value in data must be ignored. | TC-DMI-006 |
| OB-DB29A6E2 | CONDITIONAL | If action=0, the standard CSRs are updated for taking the breakpoint trap, and zero is written to the relevant | TC-TRIG-039 |
| OB-DBC18B0D | SHOULD | For these reasons it is recommended to tie mprven to 1. | TC-DCSR-049 |
| OB-DC9F205D | MAY | The debugger may request specific timings as described in timing. | TC-TRIG-089 |
| OB-DD6EE835 | SHOULD | This value should be supported. 1 (interrupts enabled): Interrupts (including NMI) are enabled during single s | TC-DCSR-017 |
| OB-DD957B93 | CONDITIONAL | If dmactive is 0 or ndmreset is 1: Write dmcontrol, preserving hartreset, hasel, hartsello, and hartselhi from | TC-DIS-002 |
| OB-DDD43814 | CONDITIONAL | When resuming, the hart’s PC is updated to the virtual address stored in dpc. | TC-DCSR-031 |
| OB-DE0342C3 | SHOULD | This operation should never affect DMI busy or error status. | TC-DMI-017 |
| OB-DE0E1893 | MUST | Field Description cmdtype This is 2 to indicate Access Memory Command. aamvirtual An implementation does not h | TC-AM-007 |
| OB-DE3C95F0 | SHOULD | W1 - idle This is a hint to the debugger of the minimum number of cycles a debugger should spend in Run-Test/I | TC-DTM-024 |
| OB-DED87815 | SHOULD | If the Zicfilp extension is implemented, pelp is set to the current ELP state and ELP is set to NO_LP_EXPECTED | TC-RC-003 |
| OB-DF177553 | MUST | WARL 0 hit If this bit is implemented then it must become set when this trigger fires and may become set when  | TC-TRIG-090 |
| OB-DF94CEB9 | UNSPECIFIED | It is UNSPECIFIED whether failing sc instructions are stores or not. | TC-TRIG-017 |
| OB-DFAFCCCE | CONDITIONAL | When a user is single stepping through such code, they will have to step twice to get past the restarted instr | TC-SSTEP-013 |
| OB-DFC7E0AC | MAY | Field Description Access Reset errinfo This optional field may provide additional detail about an error that o | TC-DTM-025 |
| OB-DFD65C76 | MUST_NOT | The debugger must not change the value of this bit while the hart is running. | TC-DCSR-018, TC-DCSR-019 |
| OB-E0FCE46E | CONDITIONAL | If the currently selected trigger doesn’t exist, this field contains 1. | TC-TRIG-138 |
| OB-E13BBA70 | MAY | If a debugger writes an unsupported configuration, the register will read back a value that is supported (whic | TC-TRIG-032 |
| OB-E14C5C30 | MUST | This variant must be supported. 1 (enabled): After a successful register access, regno is incremented. | TC-AC-029 |
| OB-E205A8B9 | CONDITIONAL | If postexec is set, execution continues to the debugger-controlled Program Buffer, otherwise the DM causes an  | TC-AC-051 |
| OB-E2067229 | CONDITIONAL | When a step is required, the OS or debug stub writes count=1, action=0, m=0 before returning control to the lo | TC-SSTEP-014 |
| OB-E421E9E5 | SHOULD | Harts that support triggers with action=0 should implement one of the following two solutions to solve the pro | TC-TRIG-150 |
| OB-E4613D8E | MAY | Implementations may hard wire this bit to 0. | TC-DCSR-020 |
| OB-E4BE0A83 | SHOULD_NOT | Implementations where it’s not possible to unlock the DM by using authdata should not implement that register. | TC-AUTH-004 |
| OB-E4C7F69B | MUST_NOT | If they have a breakpoint set between a lr and sc pair, or are stepping through such code, the sc may never su | TC-DCSR-005 |
| OB-E4E58F04 | MAY | A debugger can access memory from a hart’s point of view using a Program Buffer or the Abstract Access Memory  | TC-SBA-032 |
| OB-E5C9DC7C | CONDITIONAL | When a running hart, or a hart just coming out of reset, sees its halt request bit high, it responds by haltin | TC-RC-024 |
| OB-E61FF669 | UNSPECIFIED | It is undefined when exactly such a chain fires. | TC-TRIG-113 |
| OB-E6A338DF | SHOULD | That means to implement the suggestions in Table 4, both timings should be supported on load address triggers  | TC-TRIG-091 |
| OB-E7002892 | CONDITIONAL | If the Program Buffer executed without an exception, then resume the hart. | TC-QA-003 |
| OB-E70E4574 | CONDITIONAL | When XLEN=32 some of the bits can be accessed through textra32. | TC-TRIG-137 |
| OB-E745032F | MUST | The debugger must attempt to save dpc between halting and executing a Program Buffer, and then restore dpc bef | TC-DCSR-032 |
| OB-E7FCEE52 | CONDITIONAL | When the system bus manager is busy, writes to this register will set sbbusyerror and don’t do anything else. | TC-SBA-006 |
| OB-E8221643 | SHOULD | When implementing cJTAG access to a JTAG DTM, the MIPI 10-pin Narrow JTAG connector should be used. | TC-DTM-018 |
| OB-E843D8C4 | MUST | Suggested Trigger Timings Match Type Suggested Trigger Timing Execute Address Before Execute Instruction Befor | TC-TRIG-114 |
| OB-E8964912 | MAY | This optional register may be used for non-standard features. | TC-GEN-010 |
| OB-E9456F4D | MAY | If aarpostincrement and transfer are set, increment regno. regno may also be incremented if aarpostincrement i | TC-AC-030 |
| OB-E9BB65A9 | CONDITIONAL | If this feature is not implemented, the bit always stays 0, so after writing 1 the debugger can read the regis | TC-TRIG-178 |
| OB-E9D6A299 | MUST_NOT | A debugger must not write to this register unless hartinfo explicitly mentions it (the Debug Module may use th | TC-DCSR-033 |
| OB-EA02F0C0 | MAY | An implementation may detect an upcoming failure early, and fail the overall command before it reaches the ste | TC-AC-031 |
| OB-EAD61D48 | SHOULD | Debuggers should use resumereq to explicitly resume harts before clearing dmactive and disconnecting. | TC-RC-025 |
| OB-EB4F728A | MUST | Implementations must implement one of the following options. | TC-TRIG-021 |
| OB-EB9DDE05 | MUST | If aarsize specifies a size larger than the register’s actual size, then the access must fail. | TC-AC-032 |
| OB-EBE53751 | CONDITIONAL | If supported by the hart and desired by the debugger, triggers will often be programmed to have m=0 so that wh | TC-TRIG-151 |
| OB-EC50056B | CONDITIONAL | When dret is executed, pc is restored from dpc and normal execution resumes at the privilege set by prv and v, | TC-AC-052 |
| OB-ECF4D772 | MUST | The debugger must write to clrresethaltreq to clear it. | TC-TRIG-179 |
| OB-EE104FDE | MUST | A debugger must read back tdata2 after writing it to confirm the requested functionality is actually supported | TC-TRIG-040 |
| OB-EECB6BC2 | CONDITIONAL | If the bit is set, then that type is supported by the currently selected trigger. | TC-TRIG-139 |
| OB-EFA20AFE | MAY | If the width of the read access is less than the width of sbdata, the contents of the remaining high bits may  | TC-SBA-021 |
| OB-EFD4A7B9 | CONDITIONAL | If aampostincrement is set, increment arg1. | TC-AM-008 |
| OB-EFF04B65 | SHOULD | First, the debugger should restore any registers that it has overwritten. | TC-GEN-018 |
| OB-F0AB699A | MAY | Abstract memory accesses act as if they are performed by the hart, although the actual implementation may diff | TC-GEN-015 |
| OB-F0C212AA | CONDITIONAL | When taking this jump, pc is saved to dpc and cause is updated in dcsr. | TC-AC-053 |
| OB-F2150C32 | CONDITIONAL | If a trigger with timing of 0 matches, it is implementation-dependent whether that prevents a trigger with tim | TC-TRIG-092 |
| OB-F2586FCE | MUST_NOT | Debuggers must not change `hartsel` while an abstract command is executing. | TC-TRIG-180 |
| OB-F287152E | MUST | Since tdata1 is WARL, hardware must prevent it from containing dmode=0 and action=1. | TC-TRIG-007 |
| OB-F29C40A3 | CONDITIONAL | If hasresethaltreq is 0, this field is not implemented. | TC-TRIG-181 |
| OB-F416713B | CONDITIONAL | If multiple mcontrol6 triggers are chained then the faulting virtual address is the address which caused any o | TC-TRIG-115 |
| OB-F4A656CF | MAY | Depending on the implementation, the debugger may be able to perform some abstract commands even when the sele | TC-AC-014 |
| OB-F4F62B81 | MUST | When system bus access is implemented, this must be an address that can be used with the System Bus Access mod | TC-DIS-006 |
| OB-F50B7C68 | CONDITIONAL | If any of these operations fail, cmderr is set and none of the remaining steps are executed. | TC-AM-009 |
| OB-F61B8B4B | MAY | For every hart, the Debug Module tracks 4 conceptual bits of state: halt request, resume ack, halt-on-reset re | TC-RC-026 |
| OB-F6C94C6E | MUST | If a command has unsupported options set or if bits that are defined as 0 aren’t 0, then the DM must set cmder | TC-AC-015 |
| OB-F7FAC044 | CONDITIONAL | If this table contradicts the table in the Privileged Spec, then the latter takes precedence. | TC-TRIG-012 |
| OB-F823F66C | CONDITIONAL | When a debugger wants to set a trigger, it writes the desired configuration, and then reads back to see if tha | TC-TRIG-183 |
| OB-F85DDCA8 | MUST | In that case it must be possible to discover the groups by using dmcs2 even if it’s not possible to change the | TC-HG-015 |
| OB-F8CA9178 | MAY | An implementation may hardwire this bit to 0 or 1. | TC-DCSR-021, TC-DCSR-022 |
| OB-F8CC43C7 | MUST | If one such instruction acts as an illegal instruction, all such instructions must act as illegal instructions | TC-DCSR-050, TC-DCSR-051 |
| OB-F92A60E7 | CONDITIONAL | If sbreadondata is set: Perform a system bus read from the address contained in sbaddress, placing the result  | TC-SBA-022 |
| OB-F9B0D91E | CONDITIONAL | If there is more than one DM accessible on this DMI, this register contains the base address of the next one i | TC-GEN-014 |
| OB-F9D15BA0 | MAY | Hardware may take an arbitrarily long time to complete activation or deactivation and will indicate completion | TC-TRIG-182 |
| OB-FA15770A | CONDITIONAL | If all of the sbaccess bits in sbcs are 0, then this register is not present. | TC-SBA-023 |
| OB-FA5F4F78 | CONDITIONAL | If one of these triggers has the "enter Debug Mode" action (1) and another trigger has the "raise a breakpoint | TC-TRIG-013 |
| OB-FA75264B | SHOULD | Depending on how many harts exist, the process should start at one of the lower haltsum registers. | TC-RC-027 |
| OB-FAECE020 | CONDITIONAL | If dataaccess is 1: Number of 32-bit words in the memory map dedicated to shadowing the data registers. | TC-DIS-018 |
| OB-FBD55F90 | MUST | The debugger can write whatever program it likes (including jumps out of the Program Buffer), but the program  | TC-PB-013 |
| OB-FC557430 | MUST | The supported Core Debug Registers must be implemented for each hart that can be debugged. | TC-GEN-004 |
| OB-FD764B83 | CONDITIONAL | If the bit is not implemented, it is always 0 and writing it has no effect. | TC-HG-004 |
| OB-FD888007 | CONDITIONAL | When count is 1 and the trigger matches, then pending becomes set. | TC-TRIG-052 |
| OB-FE2974F0 | CONDITIONAL | If it is 1 then counters are stopped. | TC-DCSR-052 |
| OB-FE32BA11 | MAY | In addition, an implementation may choose to inhibit all trigger matching against invalid addresses, especiall | TC-TRIG-024 |
| OB-FE6F2704 | CONDITIONAL | If the Smdbltrp extension is implemented and the new privilege mode is not M, then the MDT bit is set to 0. | TC-RC-008 |
| OB-FE9F0537 | UNSPECIFIED | M is XLEN-1 minus the index of the least-significant bit containing 0 in tdata2. tdata2 is WARL and if bits ma | TC-TRIG-116 |
| OB-FEA5186F | CONDITIONAL | When the Zicfilp extension is implemented, the ELP state is NO_LP_EXPECTED and is not updated by any instructi | TC-DCSR-053 |
| OB-FF62EF3E | MAY | In this case an implementation may reset more harts than just the ones that are selected. | TC-RST-014 |
| OB-FF80860E | MAY | It may not be possible to read the contents of the Program Buffer using the progbuf registers. #731 tcontrol f | TC-GEN-023 |
