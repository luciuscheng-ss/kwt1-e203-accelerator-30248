`timescale 1ns/1ps
// Exact M4/R6 sign/magnitude requantization. Four elastic stages separate
// absolute-value carry propagation, multiply and shift/round/saturation.
module kwt_scaled_quantize2 #(parameter integer OUTPUT_BITS=14)(
 input wire clk,rst_n,in_valid,output wire in_ready,input wire [65:0] in_raw,
 input wire [7:0] in_mult,input wire [11:0] in_shift,input wire in_frame_end,
 output wire out_valid,input wire out_ready,output wire [27:0] out_codes,output wire out_frame_end,output reg fault
);
 reg v0,v1,v2,v3;
 wire r3=!v3||out_ready,r2=!v2||r3,r1=!v1||r2,r0=!v0||r1;
 assign in_ready=r0;assign out_valid=v3;
 reg [65:0] raw0;reg [7:0] mult0,mult1;reg [11:0] shift0,shift1,shift2;
 reg end0,end1,end2,end3;reg [1:0] sign1,sign2;
 reg [32:0] magnitude1[0:1];reg [36:0] product2[0:1];reg [27:0] codes3;
 wire c0,c1,c2,c3;
 kwt_quant_gate g0(.clk(clk),.enable(r0&&in_valid),.gclk(c0));
 kwt_quant_gate g1(.clk(clk),.enable(r1&&v0),.gclk(c1));
 kwt_quant_gate g2(.clk(clk),.enable(r2&&v1),.gclk(c2));
 kwt_quant_gate g3(.clk(clk),.enable(r3&&v2),.gclk(c3));
 always @(posedge c0)begin raw0<=in_raw;mult0<=in_mult;shift0<=in_shift;end0<=in_frame_end;end
 always @(posedge c1)begin mult1<=mult0;shift1<=shift0;end1<=end0;end
 always @(posedge c2)begin sign2<=sign1;shift2<=shift1;end2<=end1;end
 always @(posedge c3)end3<=end2;
 genvar n;
 generate for(n=0;n<2;n=n+1)begin:lanes
  wire [32:0] raw=raw0[n*33+:33];
  always @(posedge c1)begin magnitude1[n]<=raw[32]?(~raw+33'd1):raw;sign1[n]<=raw[32];end
  always @(posedge c2)product2[n]<=magnitude1[n]*mult1[n*4+:4];
  wire [5:0] shift=shift2[n*6+:6];
  wire [37:0] shifted={product2[n],1'b0}>>shift;
  wire [14:0] rounded_low={1'b0,shifted[14:1]}+shifted[0];
  localparam [13:0] LIMIT=(1<<(OUTPUT_BITS-1))-1;
  wire [13:0] clipped=(|shifted[37:15])||rounded_low>{1'b0,LIMIT}?LIMIT:rounded_low[13:0];
  always @(posedge c3)codes3[n*14+:14]<=sign2[n]?-clipped:clipped;
 end endgenerate
 assign out_codes=codes3;assign out_frame_end=end3;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin v0<=0;v1<=0;v2<=0;v3<=0;fault<=0;end
  else begin
   if(r0)v0<=in_valid;if(r1)v1<=v0;if(r2)v2<=v1;if(r3)v3<=v2;
   if(in_valid&&in_ready&&(in_mult[3:0]==0||in_mult[7:4]==0||in_shift[5:0]>38||in_shift[11:6]>38))fault<=1;
  end
 end
endmodule
module kwt_quant_gate(input wire clk,enable,output wire gclk);
`ifdef SYNTHESIS
 CLKLANAQV4_12TR40 physical_gate(.CK(clk),.E(enable),.TE(1'b0),.Q(gclk));
`elsif KWT_NATIVE_GATES
 CLKLANAQV4_12TR40 physical_gate(.CK(clk),.E(enable),.TE(1'b0),.Q(gclk));
`else
 reg held;always_latch if(!clk)held<=enable;assign gclk=clk&&held;
`endif
endmodule
