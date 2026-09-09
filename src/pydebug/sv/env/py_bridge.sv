// ══════════════════════════════════════════════════════════════════════════════
// Python Bridge — REUSABLE component for third-party integration
//
// Usage in any test:
//   python_bridge m_bridge;
//   m_bridge = python_bridge::type_id::create("m_bridge", this);
//   ...
//   m_bridge.serve(my_jtag_agent.sequencer);
//
// op=1 → DMI read  (2-phase JTAG DR shift)
// op=2 → DMI write (1-phase JTAG DR shift)
// op=3 → TAP reset
// op=4 → shutdown
// ══════════════════════════════════════════════════════════════════════════════

// ══════════════════════════════════════════════════════════════════════════════
// DPI imports — implemented in uvm_bridge.c
// ══════════════════════════════════════════════════════════════════════════════
import "DPI-C" function int  uvm_bridge_start();
import "DPI-C" function void uvm_bridge_stop();
import "DPI-C" function int  dpi_bridge_get_req(output int op, output int addr, output int unsigned data);
import "DPI-C" function void dpi_bridge_put_rsp(int unsigned data);
    // Text for an OP_LOG request. Valid only until the next get_req, which is
    // fine: it is read immediately, under the same handshake as a DMI op.
    import "DPI-C" function string dpi_bridge_get_text();

class python_bridge extends uvm_component;
    `uvm_component_utils(python_bridge)

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    // ── [DEBUG] register-name + key-field decode for issue debugging ───────
    // Distinct from the [BRIDGE] READ/WRITE lines above (which only show the
    // raw addr/data) — this exists so a log grep for "[DEBUG]" gives a
    // human-readable transaction timeline to correlate against a waveform
    // dump's $time, without having to mentally decode DMI addresses/fields.
    function string decode_addr_name(logic [6:0] addr);
        case (addr)
            dm_defines_pkg::DM_ADDR_DMCONTROL:  return "dmcontrol";
            dm_defines_pkg::DM_ADDR_DMSTATUS:   return "dmstatus";
            dm_defines_pkg::DM_ADDR_HARTINFO:   return "hartinfo";
            dm_defines_pkg::DM_ADDR_ABSTRACTCS: return "abstractcs";
            dm_defines_pkg::DM_ADDR_COMMAND:    return "command";
            dm_defines_pkg::DM_ADDR_DMCS2:      return "dmcs2";
            dm_defines_pkg::DM_ADDR_SBCS:       return "sbcs";
            dm_defines_pkg::DM_ADDR_HALTSUM0:   return "haltsum0";
            default: begin
                if (addr >= dm_defines_pkg::DM_ADDR_DATA0 && addr <= dm_defines_pkg::DM_ADDR_DATA11)
                    return "data";
                if (addr >= dm_defines_pkg::DM_ADDR_PROGBUF0 && addr <= dm_defines_pkg::DM_ADDR_PROGBUF15)
                    return "progbuf";
                return $sformatf("0x%02h", addr);
            end
        endcase
    endfunction

    // Opt-in per run with +DM_FIELD_TABLE. Cached rather than re-tested per
    // access: this runs on every DMI transaction.
    local bit field_table_en = 0;
    local bit field_table_checked = 0;

    function void debug_print(string dir, logic [6:0] addr, logic [31:0] data);
        string reg_name = decode_addr_name(addr);
        string extra = "";
        string table_str;

        if (!field_table_checked) begin
            field_table_en = $test$plusargs("DM_FIELD_TABLE");
            field_table_checked = 1;
        end

        if (reg_name == "abstractcs")
            extra = $sformatf(" (busy=%0b cmderr=%0d)", data[12], data[10:8]);
        `uvm_info("DMI_REG", $sformatf("DMI  %s %s (addr=0x%02h) data=0x%08h%s",
            dir, reg_name, addr, data, extra), UVM_LOW)

        // Full field breakdown, for when the hex word is not enough. Its own
        // plusarg rather than a verbosity level: raising verbosity to reach it
        // would also unleash the JTAG layer, which is usually not what you want
        // when the question is "which bit is set".
        if (field_table_en) begin
            table_str = dm_defines_pkg::dm_field_table(addr, data);
            if (table_str != "")
                `uvm_info("DMI_FIELDS",
                    $sformatf("%s = 0x%08h%s", reg_name, data, table_str), UVM_LOW)
        end
    endfunction

    task serve(uvm_sequencer #(jtag_txn_c) sqr);
        int rc;

        rc = uvm_bridge_start();
        if (rc != 0)
            `uvm_fatal("BRIDGE", "uvm_bridge_start() failed")
        `uvm_info("BRIDGE", "C bridge started — waiting for Python client", UVM_NONE)

        forever begin
            int op, addr;
            int unsigned data;

            if (dpi_bridge_get_req(op, addr, data)) begin
                case (op)
                    1: begin  // DMI Read
                        jtag_dmi_read_seq r_seq;
                        r_seq = jtag_dmi_read_seq::type_id::create("r_seq");
                        r_seq.addr = addr[6:0];
                        r_seq.start(sqr);
                        dpi_bridge_put_rsp(r_seq.rsp_data);
                        `uvm_info("DMI_REQ", $sformatf(
                            "DMI  READ  addr=0x%02h → data=0x%08h", addr, r_seq.rsp_data),
                            UVM_MEDIUM)
                        debug_print("READ ", addr[6:0], r_seq.rsp_data);
                    end
                    2: begin  // DMI Write
                        jtag_dmi_write_seq w_seq;
                        w_seq = jtag_dmi_write_seq::type_id::create("w_seq");
                        w_seq.addr = addr[6:0];
                        w_seq.data = data;
                        w_seq.start(sqr);
                        dpi_bridge_put_rsp(0);
                        `uvm_info("DMI_REQ", $sformatf(
                            "DMI  WRITE addr=0x%02h ← data=0x%08h", addr, data),
                            UVM_MEDIUM)
                        debug_print("WRITE", addr[6:0], data);
                    end
                    3: begin  // TAP Reset
                        jtag_tap_reset_seq rst_seq;
                        rst_seq = jtag_tap_reset_seq::type_id::create("rst_seq");
                        rst_seq.start(sqr);
                        dpi_bridge_put_rsp(0);
                        `uvm_info("BRIDGE", "TAP RESET", UVM_MEDIUM)
                    end
                    5: begin  // Python log record
                        // Printed here rather than by Python so it flows
                        // through the same report server as everything else:
                        // one writer, so the line is correctly ordered against
                        // the DMI traffic around it, carries the simulator's
                        // own $time, and cannot be torn in half by two
                        // processes writing one pipe. Verbosity comes from the
                        // Python side, mapped from its logging level.
                        `uvm_info("PY", dpi_bridge_get_text(), uvm_verbosity'(data))
                        dpi_bridge_put_rsp(0);
                    end
                    4: begin  // Shutdown
                        `uvm_info("BRIDGE",
                            "Shutdown requested by Python — exiting command loop",
                            UVM_NONE)
                        dpi_bridge_put_rsp(0);
                        uvm_bridge_stop();
                        return;
                    end
                    default: begin
                        `uvm_warning("BRIDGE",
                            $sformatf("Unknown op=%0d — ignoring", op))
                        dpi_bridge_put_rsp(0);
                    end
                endcase
            end else begin
                #1ns;
            end
        end
    endtask
endclass
