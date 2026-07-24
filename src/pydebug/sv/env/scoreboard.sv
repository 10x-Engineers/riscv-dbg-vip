// ══════════════════════════════════════════════════════════════════════════════
// Scoreboard — checks DMI status from the JTAG monitor's analysis port
// ══════════════════════════════════════════════════════════════════════════════
class debug_scoreboard extends uvm_scoreboard;
    `uvm_component_utils(debug_scoreboard)

    uvm_analysis_imp #(jtag_txn_c, debug_scoreboard) analysis_export;
    int unsigned total_checked;
    int unsigned total_errors;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        analysis_export = new("analysis_export", this);
    endfunction

    function void write(jtag_txn_c item);
        total_checked++;
        if (item.dmi_status == 2'b10 || item.dmi_status == 2'b11) begin
            total_errors++;
            `uvm_error("SCB", $sformatf("DMI error status=%02b on %s",
                        item.dmi_status, item.convert2string()))
        end else begin
            `uvm_info("SCB", $sformatf("[tx#%0d] %s ✓", total_checked,
                       item.convert2string()), UVM_HIGH)
        end
    endfunction

    function void report_phase(uvm_phase phase);
        `uvm_info("SCB", $sformatf("Checked=%0d Errors=%0d",
                  total_checked, total_errors), UVM_NONE)
    endfunction
endclass