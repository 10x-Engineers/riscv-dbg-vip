// dbg_axi_cfg.sv — runtime configuration for one AXI tap.
//
// Bus widths are elaboration-time and live as parameters on the interface and
// the monitor. Everything that can vary per run without recompiling lives
// here, so one SoC can tap several buses with different naming, filtering and
// address annotation from the same compiled kit.
class dbg_axi_cfg extends uvm_object;

    // Names the tap in every log line. With more than one bus tapped, this is
    // the only thing telling them apart.
    string bus_name = "axi";

    // Some taps are inherently one-directional (an instruction port is never
    // written). Switching the unused half off keeps a thread from watching a
    // channel that never handshakes.
    bit monitor_writes = 1;
    bit monitor_reads  = 1;

    // Verbosity for transaction lines. UVM_MEDIUM prints under the default
    // +UVM_VERBOSITY; raise to UVM_HIGH for a bus that is noisy but
    // occasionally interesting.
    uvm_verbosity log_level = UVM_MEDIUM;

    // Only report transactions inside [addr_lo, addr_hi]. Defaults span
    // everything. Useful to reduce a shared interconnect tap to just the
    // window you care about -- e.g. the debug module's own address range.
    bit [63:0] addr_lo = 64'h0;
    bit [63:0] addr_hi = 64'hFFFF_FFFF_FFFF_FFFF;

    // Optional address annotation: region_name[addr] prints alongside the
    // address, so a log reads `addr=0x104 (GoingAddr)` instead of a bare
    // number. Populate from the SoC's own memory map in the tb.
    string region_name[bit [63:0]];

    // Named address ranges, for regions where naming every word is pointless:
    // a debug ROM fetch is interesting as "DebugROM", not as 0x838. Checked
    // after the exact map, so a specific register inside a named range still
    // wins.
    typedef struct {
        bit [63:0] lo;
        bit [63:0] hi;
        string     name;
    } region_range_t;

    region_range_t region_ranges[$];

    `uvm_object_utils(dbg_axi_cfg)

    function new(string name = "dbg_axi_cfg");
        super.new(name);
    endfunction

    // Address is matched after masking to the region granule, so a named
    // 4-byte register still matches when the bus issues a wider aligned beat.
    virtual function string annotate(bit [63:0] addr);
        if (region_name.exists(addr))          return region_name[addr];
        if (region_name.exists(addr & ~64'h3)) return region_name[addr & ~64'h3];
        if (region_name.exists(addr & ~64'h7)) return region_name[addr & ~64'h7];
        // Fall back to a named range, with the offset so consecutive fetches
        // are still distinguishable: DebugROM+0x38.
        foreach (region_ranges[i]) begin
            if (addr >= region_ranges[i].lo && addr <= region_ranges[i].hi) begin
                if (addr == region_ranges[i].lo) return region_ranges[i].name;
                return $sformatf("%s+0x%0h", region_ranges[i].name, addr - region_ranges[i].lo);
            end
        end
        return "";
    endfunction

    virtual function bit in_window(bit [63:0] addr);
        return (addr >= addr_lo) && (addr <= addr_hi);
    endfunction

endclass
