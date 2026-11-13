`timescale 1ns/1ps
// Candidate restoration of the diagram's512KiB SysMem slave. Its status as
// the fixed platform SRAM is pending framework/loader review. Macro ports
// are only driven here; accelerators see the ordinary32-bit bus interface.
module kwt_shared_sram512 # (parameter [31:0] BASE=32'ha0000000)(
 input wire clk,rst_n,input wire cmd_valid,output wire cmd_ready,
 input wire cmd_read,input wire [31:0] cmd_addr,cmd_wdata,input wire [3:0] cmd_wmask,
 output reg rsp_valid,input wire rsp_ready,output wire [31:0] rsp_rdata,output reg rsp_err
);
 wire in_range=cmd_addr>=BASE&&cmd_addr<BASE+32'h80000&&cmd_addr[1:0]==0;
 wire [18:0] offset=cmd_addr-BASE;
 wire fire=cmd_valid&&cmd_ready;
 assign cmd_ready=!rsp_valid||rsp_ready;
 reg [3:0] read_bank;reg read_live,response_read;reg [31:0] held;
 wire [31:0] q[0:15];wire [31:0] selected=q[read_bank];
 assign rsp_rdata=response_read?(read_live?selected:held):32'd0;
 genvar bank;
 generate for(bank=0;bank<16;bank=bank+1)begin:banks
  wire enabled=fire&&in_range&&offset[18:15]==bank;
  wire [31:0] mask_n=~{{8{cmd_wmask[3]}},{8{cmd_wmask[2]}},{8{cmd_wmask[1]}},{8{cmd_wmask[0]}}};
  RAMSP8KX32 macro(.Q(q[bank]),.CLK(clk),.CEN(!enabled),.GWEN(cmd_read),.WEN(mask_n),
   .A(offset[14:2]),.D(cmd_wdata),.EMA(3'b010),.EMAW(2'b00),.RET1N(1'b1));
 end endgenerate
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin rsp_valid<=0;rsp_err<=0;read_live<=0;response_read<=0;read_bank<=0;end
  else begin
   if(read_live)held<=selected;
   read_live<=fire&&in_range&&cmd_read;
   if(rsp_valid&&rsp_ready)rsp_valid<=0;
   if(fire)begin
    rsp_valid<=1;rsp_err<=!in_range;response_read<=in_range&&cmd_read;
    if(in_range&&cmd_read)read_bank<=offset[18:15];
   end
  end
 end
endmodule
