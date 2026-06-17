// Copyright lowRISC contributors.
// Licensed under the Apache License, Version 2.0, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0

// Abstract prim wrapper for prim_ram_2p.
// Stop-gap shim for simulation without FuseSoC prim generation.

module prim_ram_2p import prim_ram_2p_pkg::*;

#(
  parameter  int Width           = 32,
  parameter  int Depth           = 128,
  parameter  int DataBitsPerMask = 1,
  parameter      MemInitFile     = "",

  localparam int Aw              = $clog2(Depth)
) (
  input clk_a_i,
  input clk_b_i,

  input                    a_req_i,
  input                    a_write_i,
  input        [Aw-1:0]    a_addr_i,
  input        [Width-1:0] a_wdata_i,
  input  logic [Width-1:0] a_wmask_i,
  output logic [Width-1:0] a_rdata_o,

  input                    b_req_i,
  input                    b_write_i,
  input        [Aw-1:0]    b_addr_i,
  input        [Width-1:0] b_wdata_i,
  input  logic [Width-1:0] b_wmask_i,
  output logic [Width-1:0] b_rdata_o,

  input ram_2p_cfg_t       cfg_i
);

  if (1) begin : gen_generic
    prim_generic_ram_2p #(
      .Depth(Depth),
      .Width(Width),
      .DataBitsPerMask(DataBitsPerMask),
      .MemInitFile(MemInitFile)
    ) u_impl_generic (
      .*
    );
  end

endmodule
