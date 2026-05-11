`timescale 1ns/1ps

module jtag_bitbang #(
    parameter int PORT = 9824
) (
    input  logic clk_i,
    input  logic rst_ni,
    input  logic enable_i,   // only init+tick when high

    // JTAG pins
    output logic tck_o,
    output logic tms_o,
    output logic tdi_o,
    output logic trstn_o,
    input  logic tdo_i,
    
    // Status
    output logic quit_o
);

    import "DPI-C" function int  rbs_init(input int port);
    import "DPI-C" function void rbs_tick(
        output byte tck,
        output byte tms,
        output byte tdi,
        output byte trstn,
        input  byte tdo
    );
    import "DPI-C" function byte rbs_done();

    byte tck_c, tms_c, tdi_c, trstn_c, tdo_c;
    logic initialized;

    initial begin
        tck_o   = 1'b0;
        tms_o   = 1'b0;
        tdi_o   = 1'b0;
        trstn_o = 1'b0;
        quit_o  = 1'b0;
        initialized = 1'b0;
    end

    always @(posedge clk_i) begin
        if (~rst_ni) begin
            tck_o   <= 1'b0;
            tms_o   <= 1'b0;
            tdi_o   <= 1'b0;
            trstn_o <= 1'b0;
            quit_o  <= 1'b0;
        end else if (enable_i) begin
            if (!initialized) begin
                if (rbs_init(PORT) == 0)
                    $fatal(1, "Failed to init JTAG remote bitbang on port %0d", PORT);
                initialized <= 1'b1;
            end else begin
                tdo_c = {7'h0, tdo_i};
                rbs_tick(tck_c, tms_c, tdi_c, trstn_c, tdo_c);
                tck_o   <= tck_c[0];
                tms_o   <= tms_c[0];
                tdi_o   <= tdi_c[0];
                trstn_o <= trstn_c[0];
                quit_o  <= rbs_done()[0];
            end
        end
    end

endmodule
