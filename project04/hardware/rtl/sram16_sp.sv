`timescale 1ns/1ps
// Physical single-port wrapper. All callers arbitrate read/write before here.
// Preserve the previous read result when native Q becomes X on disable/write.
module kwt_sram_16 # (parameter integer DEPTH=1024,AW=$clog2(DEPTH))(
 input wire clk,we,input wire [AW-1:0] wa,input wire [15:0] wd,
 input wire re,input wire [AW-1:0] ra,output wire [15:0] rd
);
 wire [15:0] q;wire [AW-1:0] address=we?wa:ra;
 reg read_live;reg [15:0] held;
 always @(posedge clk)begin read_live<=re&&!we;if(read_live)held<=q;end
 assign rd=read_live?q:held;
 generate if(DEPTH==1024)begin:bank1024
  RAMSP1024X16 macro(.Q(q),.CLK(clk),.CEN(!(we||re)),.GWEN(!we),.WEN(16'd0),.A(address),.D(wd),.EMA(3'b010),.EMAW(2'b00),.RET1N(1'b1));
 end else if(DEPTH==128)begin:bank128
  RAMSP128X16 macro(.Q(q),.CLK(clk),.CEN(!(we||re)),.GWEN(!we),.WEN(16'd0),.A(address),.D(wd),.EMA(3'b010),.EMAW(2'b00),.RET1N(1'b1));
 end endgenerate
`ifndef SYNTHESIS
 initial if(DEPTH!=1024&&DEPTH!=128)$fatal(1,"Unsupported physical SRAM shape");
 always @(posedge clk)if(we&&re)$fatal(1,"Physical single-port collision");
`endif
endmodule
