// dbg_axi_txn.sv — one completed AXI burst, as observed on the bus.
//
// Parameterised on the same widths as the interface it came from, so a 32-bit
// SoC does not carry 64-bit fields and a wider one is not truncated.
class dbg_axi_txn #(
    parameter int unsigned ADDR_W = 64,
    parameter int unsigned DATA_W = 64,
    parameter int unsigned ID_W   = 4
) extends uvm_sequence_item;

    localparam int unsigned STRB_W = DATA_W / 8;

    typedef enum bit { AXI_READ, AXI_WRITE } dir_e;

    dir_e              dir;
    bit [ADDR_W-1:0]   addr;
    bit [7:0]          len;      // AxLEN: beats - 1
    bit [2:0]          size;     // AxSIZE: log2(bytes per beat)
    bit [1:0]          burst;
    bit [ID_W-1:0]     id;
    bit [DATA_W-1:0]   data[$];  // one entry per beat
    bit [STRB_W-1:0]   strb[$];  // write only
    bit [1:0]          resp;
    string             region;   // optional name from dbg_axi_cfg
    time               t_start;
    time               t_end;

    `uvm_object_param_utils(dbg_axi_txn #(ADDR_W, DATA_W, ID_W))

    function new(string name = "dbg_axi_txn");
        super.new(name);
    endfunction

    static function string resp_str(bit [1:0] r);
        case (r)
            2'b00: return "OKAY";
            2'b01: return "EXOKAY";
            2'b10: return "SLVERR";
            2'b11: return "DECERR";
        endcase
    endfunction

    // Single-beat bursts dominate debug traffic, so those stay on one line and
    // only a real burst spills into a beat list -- a 16-beat refill should not
    // cost 16 log lines.
    virtual function string convert2string();
        string s;
        s = $sformatf("%-5s addr=0x%0h%s size=%0dB id=%0d resp=%s",
                      (dir == AXI_WRITE) ? "WRITE" : "READ",
                      addr,
                      (region != "") ? $sformatf(" (%s)", region) : "",
                      1 << size, id, resp_str(resp));
        if (len == 0) begin
            if (data.size() > 0) s = {s, $sformatf(" data=0x%0h", data[0])};
            if (dir == AXI_WRITE && strb.size() > 0)
                s = {s, $sformatf(" strb=0x%0h", strb[0])};
        end else begin
            s = {s, $sformatf(" len=%0d beats", len + 1)};
            foreach (data[i]) begin
                s = {s, $sformatf("\n      [%0d] 0x%0h", i, data[i])};
                if (dir == AXI_WRITE && i < strb.size())
                    s = {s, $sformatf(" strb=0x%0h", strb[i])};
            end
        end
        return s;
    endfunction

endclass
