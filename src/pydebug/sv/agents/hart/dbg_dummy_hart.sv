// ─────────────────────────────────────────────────────────────────────────────
// dbg_dummy_hart.sv — a hart, as far as the Debug Module can tell.
//
// The DM does not have a "this hart is halted" input. A hart tells the DM what
// it is doing by *executing the debug ROM*, which comes down to three accesses
// on the DM's own memory slave (dm_mem.sv:77-83, :244-258):
//
//   write HaltedAddr   (0x100), wdata = hart id   "I am halted"
//   read  FlagsBase    (0x400 + id), bit0=go, bit1=resume
//   write ResumingAddr (0x108), wdata = hart id   "I am running again"
//
// That is the whole contract, and none of it requires a processor. This module
// performs exactly those accesses in response to `debug_req_i`, so a DM
// configured with NrHarts>1 sees a second, third, ... hart halt and resume on
// request — which is what makes `dmstatus`'s all*/any* pairs able to differ,
// `haltsum0` have more than one interesting bit, and the hart array mask
// (`hasel`, `hawindow`) mean something.
//
// It is deliberately NOT a core model. It never fetches an instruction, never
// executes an abstract command, and never touches the data registers: it
// stands in for the run-control handshake and nothing else. A test that needs
// a real hart's register file must use a real core (cva6_sim, ibex_sim); a
// test that needs *several* harts to halt and resume together uses these.
//
// Wiring: the DM's memory slave is a simple req/we/addr/be/wdata port, and the
// real system already drives it (through axi2mem on CVA6). `dbg_hart_arbiter`
// muxes this module's accesses onto that port, giving the dummy harts priority
// only while they have a request outstanding — they are idle the rest of the
// time, so the debugger's own accesses are unaffected.
// ─────────────────────────────────────────────────────────────────────────────

module dbg_dummy_hart #(
    // This hart's index, as the debugger selects it in dmcontrol.hartsel.
    parameter int unsigned HartId = 1,
    parameter int unsigned BusWidth = 64,
    // Cycles between polls of the flags word while halted. Nothing depends on
    // the value; it exists so a waveform is readable and the DM's slave port
    // is not saturated by one idle hart.
    parameter int unsigned PollPeriod = 8
) (
    input  logic                  clk_i,
    input  logic                  rst_ni,
    //: From dm_top.debug_req_o[HartId].
    input  logic                  debug_req_i,

    //: Request onto the DM's memory slave (see dbg_hart_arbiter).
    output logic                  req_o,
    output logic                  we_o,
    output logic [BusWidth-1:0]   addr_o,
    output logic [BusWidth-1:0]   wdata_o,
    output logic [BusWidth/8-1:0] be_o,
    //: Granted this cycle by the arbiter; the read result arrives next cycle.
    input  logic                  gnt_i,
    input  logic [BusWidth-1:0]   rdata_i,

    //: Observable state, for the testbench and for assertions. Not connected
    //: to the DM: the DM learns the same thing from the accesses above.
    output logic                  halted_o
);

    // dm_mem.sv's own localparams. Repeated rather than imported because they
    // are local to that module; a mismatch would show up immediately as a hart
    // that never reports halted.
    localparam logic [11:0] HaltedAddr   = 12'h100;
    localparam logic [11:0] GoingAddr    = 12'h104;
    localparam logic [11:0] ResumingAddr = 12'h108;
    localparam logic [11:0] FlagsBaseAddr = 12'h400;

    typedef enum logic [2:0] {
        RUNNING,      // not in debug mode; waiting for debug_req
        REPORT_HALT,  // writing HaltedAddr
        HALTED,       // in debug mode; polling the flags word
        POLL_WAIT,    // flags read issued, result due next cycle
        REPORT_RESUME // writing ResumingAddr
    } state_e;

    state_e state_q, state_d;
    logic [$clog2(PollPeriod+1)-1:0] poll_q;
    logic resume_seen;

    //: Flags word for THIS hart. dm_mem returns {6'b0, resume, go} in the byte
    //: lane matching hartsel, and only while this hart is the selected one --
    //: which is correct: a hart is told to resume through its own flag.
    assign resume_seen = rdata_i[(HartId % 8) * 8 + 1];

    assign halted_o = (state_q inside {HALTED, POLL_WAIT, REPORT_RESUME});

    always_comb begin
        state_d = state_q;
        req_o   = 1'b0;
        we_o    = 1'b0;
        addr_o  = '0;
        wdata_o = '0;
        be_o    = '0;

        unique case (state_q)
            RUNNING: begin
                if (debug_req_i) state_d = REPORT_HALT;
            end

            // "I am halted." wdata carries the hart id, which is how dm_mem
            // knows which hart's halted bit to set (wdata_hartsel).
            REPORT_HALT: begin
                req_o   = 1'b1;
                we_o    = 1'b1;
                addr_o  = BusWidth'(HaltedAddr);
                wdata_o = BusWidth'(HartId);
                be_o    = '1;
                if (gnt_i) state_d = HALTED;
            end

            // Poll this hart's flags for the resume request. A real hart does
            // this from the debug ROM's park loop.
            HALTED: begin
                if (poll_q == '0) begin
                    req_o  = 1'b1;
                    we_o   = 1'b0;
                    addr_o = BusWidth'(FlagsBaseAddr + HartId);
                    be_o   = '1;
                    if (gnt_i) state_d = POLL_WAIT;
                end
            end

            POLL_WAIT: state_d = resume_seen ? REPORT_RESUME : HALTED;

            // "I am running again." dm_mem clears halted and sets resuming,
            // which is what dmstatus.allresumeack reports.
            REPORT_RESUME: begin
                req_o   = 1'b1;
                we_o    = 1'b1;
                addr_o  = BusWidth'(ResumingAddr);
                wdata_o = BusWidth'(HartId);
                be_o    = '1;
                // A halt request can arrive again immediately; going back to
                // RUNNING re-arms on debug_req rather than latching it.
                if (gnt_i) state_d = RUNNING;
            end

            default: state_d = RUNNING;
        endcase
    end

    always_ff @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) begin
            state_q <= RUNNING;
            poll_q  <= '0;
        end else begin
            state_q <= state_d;
            // Free-running divider; only consulted in HALTED.
            poll_q  <= (poll_q == PollPeriod[$bits(poll_q)-1:0]) ? '0 : poll_q + 1'b1;
        end
    end

    // A hart that reports halted while its debug request was never asserted
    // would make dmstatus lie in the DM's favour, which is exactly the kind of
    // testbench bug that looks like a passing test.
    `ifndef VERILATOR
    assert property (@(posedge clk_i) disable iff (!rst_ni)
        (state_q == REPORT_HALT) |-> $past(debug_req_i))
        else $error("dbg_dummy_hart[%0d]: reported halted without a debug request", HartId);
    `endif

endmodule
