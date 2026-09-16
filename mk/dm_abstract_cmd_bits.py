#!/usr/bin/env python3
"""
dm_abstract_cmd_bits.py -- which bits of dm_mem's abstract_cmd can ever vary.

dm_mem.sv builds each abstract command's program into abstract_cmd[7:0]
(p_abstract_cmd_rom) from cmdtype, aarsize, transfer, write, postexec,
aarpostincrement and regno. This is a transcription of that block and of the
dm_pkg.sv encoders it calls, for this build's parameters (HasSndScratch=1,
LoadBaseAddr=x10, MaxAar=4), enumerated over every command shape, every
aarsize and every regno class. A bit that holds one value across all of them
is constant by construction, which is the only basis on which
dm_cov_exclude.py excludes an abstract_cmd toggle.

If dm_mem.sv's generator changes, this transcription must change with it.

    python3 mk/dm_abstract_cmd_bits.py out/dm_code.rpt   # compare with a report
"""

import re, sys
def load(sz,d,b,o): return (o<<20)|(b<<15)|(sz<<12)|(d<<7)|0x03
def store(sz,s,b,o): return ((o>>5)<<25)|(s<<20)|(b<<15)|(sz<<12)|((o&0x1f)<<7)|0x23
def fload(sz,d,b,o): return (o<<20)|(b<<15)|(sz<<12)|(d<<7)|0x07
def fstore(sz,s,b,o): return ((o>>5)<<25)|(s<<20)|(b<<15)|(sz<<12)|((o&0x1f)<<7)|0x27
def csrw(c,r): return (c<<20)|(r<<15)|(1<<12)|0x73
def csrr(c,d): return (c<<20)|(2<<12)|(d<<7)|0x73
def auipc(rd,imm): return (rd<<7)|0x17   # imm=0
def srli(rd,rs,sh): return (sh<<20)|(rs<<15)|(5<<12)|(rd<<7)|0x13
def slli(rd,rs,sh): return (sh<<20)|(rs<<15)|(1<<12)|(rd<<7)|0x13
EBREAK, NOP, ILLEGAL = 0x00100073, 0x13, 0
DS0, DS1, LB, DA = 0x7b2, 0x7b3, 10, 0x380
def w(lo,hi): return (hi<<32)|lo
def programs():
    regnos = set()
    for top in (0, 1, 2, 3):                         # regno[15:14]
        for b12 in (0, 1):
            for b5 in (0, 1):
                for low5 in range(32):
                    for mid in (0, 0x7c0, 0x1c0, 0x440):   # other regno[11:6] patterns
                        regnos.add((top<<14)|(b12<<12)|(b5<<5)|low5|(mid & ~0x20 & 0xfc0))
    regnos |= {1<<k for k in range(16)} | {0xfff, 0x0}
    for cmdtype in (0, 1):
        for size in range(8):
            for transfer in (0,1):
                for write in (0,1):
                    for postexec in (0,1):
                        for postinc in (0,1):
                            for regno in regnos:
                                yield gen(cmdtype,size,transfer,write,postexec,postinc,regno)
def gen(cmdtype,size,transfer,write,postexec,postinc,regno):
    s = [0]*8
    s[0] = w(ILLEGAL, auipc(10,0)); s[1] = w(srli(10,10,12), slli(10,10,12))
    s[2] = w(NOP,NOP); s[3] = w(NOP,NOP); s[4] = w(csrr(DS1,10), EBREAK)
    uns = False
    lo = lambda i: s[i] & 0xffffffff; hi = lambda i: s[i] >> 32
    def setlo(i,v): s[i] = (hi(i)<<32)|v
    def sethi(i,v): s[i] = (v<<32)|lo(i)
    if cmdtype == 0:
        r12, r5, r4 = (regno>>12)&1, (regno>>5)&1, regno&0x1f
        if size < 4 and transfer and write:
            setlo(0, csrw(DS1,10))
            if regno>>14: setlo(0, EBREAK); uns = True
            elif r12 and not r5 and r4 == 10:
                setlo(2, csrw(DS0,8)); sethi(2, load(size,8,LB,DA))
                setlo(3, csrw(DS1,8)); sethi(3, csrr(DS0,8))
            elif r12:
                setlo(2, (fload if r5 else load)(size,r4,LB,DA))
            else:
                setlo(2, csrw(DS0,8)); sethi(2, load(size,8,LB,DA))
                setlo(3, csrw(regno&0xfff,8)); sethi(3, csrr(DS0,8))
        elif size < 4 and transfer and not write:
            setlo(0, csrw(DS1,LB))
            if regno>>14: setlo(0, EBREAK); uns = True
            elif r12 and not r5 and r4 == 10:
                setlo(2, csrw(DS0,8)); sethi(2, csrr(DS1,8))
                setlo(3, store(size,8,LB,DA)); sethi(3, csrr(DS0,8))
            elif r12:
                setlo(2, (fstore if r5 else store)(size,r4,LB,DA))
            else:
                setlo(2, csrw(DS0,8)); sethi(2, csrr(regno&0xfff,8))
                setlo(3, store(size,8,LB,DA)); sethi(3, csrr(DS0,8))
        elif size >= 4 or postinc:
            setlo(0, EBREAK); uns = True
        if postexec and not uns: sethi(4, NOP)
    else:
        setlo(0, EBREAK)
    return s
def constant_bits():
    """{slot: set of bit positions no generated program changes}."""
    seen = [set() for _ in range(8)]
    for p in programs():
        for i in range(8):
            seen[i].add(p[i])
    const = {}
    for i in range(8):
        ones, zeros = ~0, ~0
        for v in seen[i]:
            ones &= v
            zeros &= ~v
        const[i] = {b for b in range(64) if (ones >> b) & 1 or (zeros >> b) & 1}
    return const


if __name__ == "__main__":
    const = constant_bits()
    # uncovered bits from the report
    rep = open(sys.argv[1]).read()
    sec = rep[rep.index("== tb_top_soc.dut.i_dm_top.i_dm_mem\n"):]
    sec = sec[:sec.index("\n== ", 5)] if "\n== " in sec[5:] else sec
    unc = re.findall(r"^0\s+\d\s+\d\s+abstract_cmd\[(\d)\]\[(\d+)\]", sec, re.M)
    reach = [(int(a),int(b)) for a,b in unc if int(b) not in const[int(a)]]
    print("uncovered:", len(unc), " constant-by-construction:", len(unc)-len(reach))
    print("REACHABLE but uncovered:", reach)
    for i in range(8): print(i, "variable bits:", sorted(set(range(64))-const[i]))
