// ══════════════════════════════════════════════════════════════════════════════
// dm_reg_decode.sv — field-level decode of Debug Module registers.
//
// Produces a table showing which field holds which value, for the moments when
// a hex word is not enough:
//
//   dmstatus = 0x00800383
//     field             bits     value
//     ------------------------------------------------------
//     version           [3:0]    0x3     (1.0)
//     authenticated     [7]      1
//     anyhalted         [8]      1
//     allhalted         [9]      1
//     ...
//
// Off by default and deliberately so -- a table per DMI access is several
// hundred lines a run, which buries everything else. Enable per run with
// +DM_FIELD_TABLE. Field layouts follow the RISC-V Debug Specification v1.0.
// ══════════════════════════════════════════════════════════════════════════════

// One row. `hi`/`lo` are the bit range; a single-bit field prints as [n].
function automatic string dm_fld(string name, int hi, int lo,
                                 logic [31:0] data, string note = "");
    logic [31:0] val = (data >> lo) & ((32'h1 << (hi - lo + 1)) - 1);
    string bits = (hi == lo) ? $sformatf("[%0d]", lo) : $sformatf("[%0d:%0d]", hi, lo);
    return $sformatf("    %-18s %-8s 0x%0h%s\n",
                     name, bits, val, (note != "") ? {"     (", note, ")"} : "");
endfunction

function automatic string dm_cmderr_str(logic [2:0] e);
    case (e)
        3'd0: return "none";
        3'd1: return "busy";
        3'd2: return "not supported";
        3'd3: return "exception";
        3'd4: return "halt/resume";
        3'd5: return "bus";
        3'd7: return "other";
        default: return "reserved";
    endcase
endfunction

function automatic string dm_version_str(logic [3:0] v);
    case (v)
        4'd0: return "none";
        4'd1: return "0.11";
        4'd2: return "0.13";
        4'd3: return "1.0";
        default: return "unknown";
    endcase
endfunction

// Returns "" for a register with no decode, so callers can skip printing.
function automatic string dm_field_table(logic [6:0] addr, logic [31:0] data);
    string s = "";

    case (addr)
        7'h10: begin  // dmcontrol
            s = {s, dm_fld("haltreq",          31, 31, data)};
            s = {s, dm_fld("resumereq",        30, 30, data)};
            s = {s, dm_fld("hartreset",        29, 29, data)};
            s = {s, dm_fld("ackhavereset",     28, 28, data)};
            s = {s, dm_fld("ackunavail",       27, 27, data)};
            s = {s, dm_fld("hasel",            26, 26, data)};
            s = {s, dm_fld("hartsello",        25, 16, data)};
            s = {s, dm_fld("hartselhi",        15,  6, data)};
            s = {s, dm_fld("setkeepalive",      5,  5, data)};
            s = {s, dm_fld("clrkeepalive",      4,  4, data)};
            s = {s, dm_fld("setresethaltreq",   3,  3, data)};
            s = {s, dm_fld("clrresethaltreq",   2,  2, data)};
            s = {s, dm_fld("ndmreset",          1,  1, data)};
            s = {s, dm_fld("dmactive",          0,  0, data)};
        end

        7'h11: begin  // dmstatus
            s = {s, dm_fld("ndmresetpending",  24, 24, data)};
            s = {s, dm_fld("stickyunavail",    23, 23, data)};
            s = {s, dm_fld("impebreak",        22, 22, data)};
            s = {s, dm_fld("allhavereset",     19, 19, data)};
            s = {s, dm_fld("anyhavereset",     18, 18, data)};
            s = {s, dm_fld("allresumeack",     17, 17, data)};
            s = {s, dm_fld("anyresumeack",     16, 16, data)};
            s = {s, dm_fld("allnonexistent",   15, 15, data)};
            s = {s, dm_fld("anynonexistent",   14, 14, data)};
            s = {s, dm_fld("allunavail",       13, 13, data)};
            s = {s, dm_fld("anyunavail",       12, 12, data)};
            s = {s, dm_fld("allrunning",       11, 11, data)};
            s = {s, dm_fld("anyrunning",       10, 10, data)};
            s = {s, dm_fld("allhalted",         9,  9, data)};
            s = {s, dm_fld("anyhalted",         8,  8, data)};
            s = {s, dm_fld("authenticated",     7,  7, data)};
            s = {s, dm_fld("authbusy",          6,  6, data)};
            s = {s, dm_fld("hasresethaltreq",   5,  5, data)};
            s = {s, dm_fld("confstrptrvalid",   4,  4, data)};
            s = {s, dm_fld("version",           3,  0, data, dm_version_str(data[3:0]))};
        end

        7'h12: begin  // hartinfo
            s = {s, dm_fld("nscratch",         23, 20, data)};
            s = {s, dm_fld("dataaccess",       16, 16, data)};
            s = {s, dm_fld("datasize",         15, 12, data)};
            s = {s, dm_fld("dataaddr",         11,  0, data)};
        end

        7'h16: begin  // abstractcs
            s = {s, dm_fld("progbufsize",      28, 24, data)};
            s = {s, dm_fld("busy",             12, 12, data)};
            s = {s, dm_fld("relaxedpriv",      11, 11, data)};
            s = {s, dm_fld("cmderr",           10,  8, data, dm_cmderr_str(data[10:8]))};
            s = {s, dm_fld("datacount",         3,  0, data)};
        end

        7'h17: begin  // command
            s = {s, dm_fld("cmdtype",          31, 24, data,
                           (data[31:24] == 0) ? "AccessRegister" :
                           (data[31:24] == 1) ? "QuickAccess"    :
                           (data[31:24] == 2) ? "AccessMemory"   : "reserved")};
            if (data[31:24] == 0) begin   // AccessRegister layout
                s = {s, dm_fld("aarsize",          22, 20, data,
                               $sformatf("%0d-bit", 8 << data[22:20]))};
                s = {s, dm_fld("aarpostincrement", 19, 19, data)};
                s = {s, dm_fld("postexec",         18, 18, data)};
                s = {s, dm_fld("transfer",         17, 17, data)};
                s = {s, dm_fld("write",            16, 16, data)};
                s = {s, dm_fld("regno",            15,  0, data,
                               (data[15:12] == 4'h1) ? "GPR" :
                               (data[15:12] == 4'h0) ? "CSR" : "")};
            end else begin
                s = {s, dm_fld("control",          23,  0, data)};
            end
        end

        7'h18: begin  // abstractauto
            s = {s, dm_fld("autoexecprogbuf",  31, 16, data)};
            s = {s, dm_fld("autoexecdata",     11,  0, data)};
        end

        7'h38: begin  // sbcs
            s = {s, dm_fld("sbversion",        31, 29, data)};
            s = {s, dm_fld("sbbusyerror",      22, 22, data)};
            s = {s, dm_fld("sbbusy",           21, 21, data)};
            s = {s, dm_fld("sbreadonaddr",     20, 20, data)};
            s = {s, dm_fld("sbaccess",         19, 17, data)};
            s = {s, dm_fld("sbautoincrement",  16, 16, data)};
            s = {s, dm_fld("sbreadondata",     15, 15, data)};
            s = {s, dm_fld("sberror",          14, 12, data)};
            s = {s, dm_fld("sbasize",          11,  5, data)};
            s = {s, dm_fld("sbaccess128",       4,  4, data)};
            s = {s, dm_fld("sbaccess64",        3,  3, data)};
            s = {s, dm_fld("sbaccess32",        2,  2, data)};
            s = {s, dm_fld("sbaccess16",        1,  1, data)};
            s = {s, dm_fld("sbaccess8",         0,  0, data)};
        end

        default: return "";   // data0-11, progbuf, haltsum: no fields to name
    endcase

    return {"\n    field              bits     value\n",
            "    ------------------------------------------------------\n", s};
endfunction
