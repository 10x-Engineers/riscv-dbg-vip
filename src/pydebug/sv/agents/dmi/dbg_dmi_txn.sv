// dbg_dmi_txn.sv — one DMI bus request, and the response that followed it.
class dbg_dmi_txn extends uvm_sequence_item;

    bit [6:0]  addr;
    bit [1:0]  op;
    bit [31:0] wdata;
    bit [31:0] rdata;
    bit [1:0]  status;
    bit        has_resp;
    time       t_req;
    time       t_resp;

    `uvm_object_utils(dbg_dmi_txn)

    function new(string name = "dbg_dmi_txn");
        super.new(name);
    endfunction

    static function string op_str(bit [1:0] o);
        case (o)
            2'd0: return "NOP";
            2'd1: return "READ";
            2'd2: return "WRITE";
            default: return "RSVD";
        endcase
    endfunction

    virtual function string convert2string();
        string s = $sformatf("%-5s addr=0x%02h", op_str(op), addr);
        if (op == 2'd2) s = {s, $sformatf(" wdata=0x%08h", wdata)};
        if (has_resp)   s = {s, $sformatf(" -> rdata=0x%08h status=%0d", rdata, status)};
        return s;
    endfunction

endclass
