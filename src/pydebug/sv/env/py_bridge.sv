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

class python_bridge extends uvm_component;
    `uvm_component_utils(python_bridge)

    function new(string name, uvm_component parent);
        super.new(name, parent);
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
                        `uvm_info("BRIDGE", $sformatf(
                            "READ  addr=0x%02h → data=0x%08h", addr, r_seq.rsp_data),
                            UVM_MEDIUM)
                    end
                    2: begin  // DMI Write
                        jtag_dmi_write_seq w_seq;
                        w_seq = jtag_dmi_write_seq::type_id::create("w_seq");
                        w_seq.addr = addr[6:0];
                        w_seq.data = data;
                        w_seq.start(sqr);
                        dpi_bridge_put_rsp(0);
                        `uvm_info("BRIDGE", $sformatf(
                            "WRITE addr=0x%02h ← data=0x%08h", addr, data),
                            UVM_MEDIUM)
                    end
                    3: begin  // TAP Reset
                        jtag_tap_reset_seq rst_seq;
                        rst_seq = jtag_tap_reset_seq::type_id::create("rst_seq");
                        rst_seq.start(sqr);
                        dpi_bridge_put_rsp(0);
                        `uvm_info("BRIDGE", "TAP RESET", UVM_MEDIUM)
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
