// ─────────────────────────────────────────────────────────────────────────────
// dbg_hart_arbiter.sv — put several dummy harts on the DM's one memory slave.
//
// `dm_top`'s slave port is a single simple memory interface: one request per
// cycle, the read data arriving the cycle after. Real harts reach it through
// the SoC's interconnect, which arbitrates between them. `dbg_dummy_hart` has
// no interconnect behind it, so this does the same job in the testbench: pick
// one requesting hart per cycle, drive its request onto the slave port, and
// hand the grant (and, a cycle later, the read data) back to that hart alone.
//
// Round-robin rather than fixed priority, and the distinction matters: a fixed
// priority would let hart 0 starve hart 1 while both poll their flags word,
// and the halt-group and hart-array tests are precisely the ones where several
// harts are meant to be doing the same thing at the same time.
// ─────────────────────────────────────────────────────────────────────────────

module dbg_hart_arbiter #(
    parameter int unsigned NrHarts  = 2,
    parameter int unsigned BusWidth = 32
) (
    input  logic clk_i,
    input  logic rst_ni,

    //: One set per hart, from dbg_dummy_hart.
    input  logic [NrHarts-1:0]                  req_i,
    input  logic [NrHarts-1:0]                  we_i,
    input  logic [NrHarts-1:0][BusWidth-1:0]    addr_i,
    input  logic [NrHarts-1:0][BusWidth-1:0]    wdata_i,
    input  logic [NrHarts-1:0][BusWidth/8-1:0]  be_i,
    output logic [NrHarts-1:0]                  gnt_o,
    output logic [NrHarts-1:0][BusWidth-1:0]    rdata_o,

    //: To dm_top's memory slave.
    output logic                  slave_req_o,
    output logic                  slave_we_o,
    output logic [BusWidth-1:0]   slave_addr_o,
    output logic [BusWidth-1:0]   slave_wdata_o,
    output logic [BusWidth/8-1:0] slave_be_o,
    input  logic [BusWidth-1:0]   slave_rdata_i
);

    localparam int unsigned IdxWidth = (NrHarts > 1) ? $clog2(NrHarts) : 1;

    logic [IdxWidth-1:0] rotate_q, winner;
    logic                any_req;
    //: Which hart the slave is answering this cycle -- the read data it
    //: returns belongs to the request granted on the PREVIOUS one.
    logic [NrHarts-1:0]  granted_q;

    // Round-robin: start from the hart after the last winner and take the
    // first one asking.
    always_comb begin
        winner  = rotate_q;
        any_req = 1'b0;
        for (int unsigned i = 0; i < NrHarts; i++) begin
            automatic int unsigned cand = (rotate_q + i) % NrHarts;
            if (!any_req && req_i[cand]) begin
                winner  = IdxWidth'(cand);
                any_req = 1'b1;
            end
        end
    end

    always_comb begin
        gnt_o         = '0;
        slave_req_o   = any_req;
        slave_we_o    = any_req ? we_i[winner]    : 1'b0;
        slave_addr_o  = any_req ? addr_i[winner]  : '0;
        slave_wdata_o = any_req ? wdata_i[winner] : '0;
        slave_be_o    = any_req ? be_i[winner]    : '0;
        if (any_req) gnt_o[winner] = 1'b1;
    end

    // The slave answers a read one cycle later, so the data goes to whoever
    // was granted then -- not to whoever happens to be asking now.
    always_comb begin
        rdata_o = '0;
        for (int unsigned i = 0; i < NrHarts; i++) begin
            rdata_o[i] = granted_q[i] ? slave_rdata_i : '0;
        end
    end

    always_ff @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            rotate_q  <= '0;
            granted_q <= '0;
        end else begin
            granted_q <= gnt_o;
            if (any_req) begin
                rotate_q <= (winner == IdxWidth'(NrHarts - 1)) ? '0
                                                               : winner + 1'b1;
            end
        end
    end

    `ifndef VERILATOR
    // At most one hart on the slave per cycle: the port cannot carry two, and
    // a bug here would look like a hart's access landing at another's address.
    assert property (@(posedge clk_i) disable iff (!rst_ni) $onehot0(gnt_o))
        else $error("dbg_hart_arbiter: %0d harts granted in one cycle", $countones(gnt_o));
    `endif

endmodule
