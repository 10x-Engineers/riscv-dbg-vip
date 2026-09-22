// ══════════════════════════════════════════════════════════════════════════════
// Scoreboard — checks DMI status from the JTAG monitor's analysis port
// ══════════════════════════════════════════════════════════════════════════════
class debug_scoreboard extends uvm_scoreboard;
    `uvm_component_utils(debug_scoreboard)

    uvm_analysis_imp #(jtag_txn_c, debug_scoreboard) analysis_export;
    int unsigned total_checked;
    int unsigned total_errors;
    //: DMI "busy" responses seen, split by what the transaction was. Counted
    //: rather than errored: busy is flow control, not a failure (#6.1.5 -- the
    //: debugger clears dmistat and retries), and jtag_dmi_read_seq does retry.
    //: A write is different only because jtag_dmi_write_seq does NOT retry, so
    //: a busy write is an operation that did not happen and nothing noticed.
    int unsigned total_busy_read;
    int unsigned total_busy_write;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        analysis_export = new("analysis_export", this);
    endfunction

    function void write(jtag_txn_c item);
        total_checked++;
        if (item.dmi_status == 2'b11 && dmi_busy_expected) begin
            `uvm_info("SCB", $sformatf("[tx#%0d] provoked DMI busy on %s",
                       total_checked, item.convert2string()), UVM_MEDIUM)
        end else if (item.dmi_status == 2'b11) begin
            // Busy is the DTM telling the debugger to slow down, not a fault:
            // #6.1.5 says the operation did not happen and the debugger
            // retries after clearing dmistat. Erroring on it aborted any
            // scenario that legitimately kept the DM busy -- on Ibex, whose
            // DM answers faster than the JTAG link, the abstract-command
            // cases provoke it as a matter of course.
            if (item.dmi_op == 2'b10) begin
                total_busy_write++;
                // jtag_dmi_write_seq does not retry (see its own note), so
                // this write was dropped and no caller will notice.
                `uvm_warning("SCB", $sformatf(
                    "DMI busy on a WRITE, which is not retried, so the write did not happen: %s",
                    item.convert2string()))
            end else begin
                total_busy_read++;
                `uvm_info("SCB", $sformatf("[tx#%0d] DMI busy (retried) on %s",
                           total_checked, item.convert2string()), UVM_MEDIUM)
            end
        end else if (item.dmi_status == 2'b10) begin
            total_errors++;
            `uvm_error("SCB", $sformatf("DMI error status=%02b on %s",
                        item.dmi_status, item.convert2string()))
        end else begin
            `uvm_info("SCB", $sformatf("[tx#%0d] %s ✓", total_checked,
                       item.convert2string()), UVM_HIGH)
        end
    endfunction

    function void report_phase(uvm_phase phase);
        `uvm_info("SCB", $sformatf(
                  "Checked=%0d Errors=%0d BusyRead=%0d BusyWrite=%0d",
                  total_checked, total_errors,
                  total_busy_read, total_busy_write), UVM_NONE)
    endfunction
endclass