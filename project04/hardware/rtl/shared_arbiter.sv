`timescale 1ns/1ps
// Candidate two-master merger at the existing SystemBus SysMem destination.
// The original bus stays upstream of port0's write-allocation adapter; port1
// is the accelerator's ordinary bus master. No SRAM macro pins are exposed.
// One ordered slave response per accepted command, latency >= one cycle.
// Reset must also reset both masters and the slave (no transactions retained).
module kwt_shared_arbiter # (parameter integer TAGS=2)(
 input wire clk,rst_n,
 input wire a_cmd_valid,output wire a_cmd_ready,input wire a_cmd_read,
 input wire [31:0] a_cmd_addr,a_cmd_wdata,input wire [3:0] a_cmd_wmask,
 output wire a_rsp_valid,input wire a_rsp_ready,output wire [31:0] a_rsp_rdata,output wire a_rsp_err,
 input wire b_cmd_valid,output wire b_cmd_ready,input wire b_cmd_read,
 input wire [31:0] b_cmd_addr,b_cmd_wdata,input wire [3:0] b_cmd_wmask,
 output wire b_rsp_valid,input wire b_rsp_ready,output wire [31:0] b_rsp_rdata,output wire b_rsp_err,
 output wire m_cmd_valid,input wire m_cmd_ready,output wire m_cmd_read,
 output wire [31:0] m_cmd_addr,m_cmd_wdata,output wire [3:0] m_cmd_wmask,
 input wire m_rsp_valid,output wire m_rsp_ready,input wire [31:0] m_rsp_rdata,input wire m_rsp_err
);
 localparam integer TW=$clog2(TAGS);
 reg owner[0:TAGS-1];reg [TW-1:0] head,tail;reg [TW:0] count;
 reg prefer_b,locked,locked_b;
 wire responding=count!=0;
 wire response_b=owner[head];
 assign a_rsp_valid=m_rsp_valid&&responding&&!response_b;
 assign b_rsp_valid=m_rsp_valid&&responding&&response_b;
 assign m_rsp_ready=responding&&(response_b?b_rsp_ready:a_rsp_ready);
 assign a_rsp_rdata=m_rsp_rdata;assign b_rsp_rdata=m_rsp_rdata;
 assign a_rsp_err=m_rsp_err;assign b_rsp_err=m_rsp_err;
 wire pop=m_rsp_valid&&m_rsp_ready;
 wire space=count<TAGS;
 wire select_b=locked?locked_b:(!a_cmd_valid||(b_cmd_valid&&prefer_b));
 wire selected_valid=select_b?b_cmd_valid:a_cmd_valid;
 assign m_cmd_valid=selected_valid&&space;
 assign a_cmd_ready=m_cmd_ready&&space&&!select_b;
 assign b_cmd_ready=m_cmd_ready&&space&&select_b;
 assign m_cmd_read=select_b?b_cmd_read:a_cmd_read;
 assign m_cmd_addr=select_b?b_cmd_addr:a_cmd_addr;
 assign m_cmd_wdata=select_b?b_cmd_wdata:a_cmd_wdata;
 assign m_cmd_wmask=select_b?b_cmd_wmask:a_cmd_wmask;
 wire push=m_cmd_valid&&m_cmd_ready;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin head<=0;tail<=0;count<=0;prefer_b<=0;locked<=0;locked_b<=0;end
  else begin
   if(m_cmd_valid&&!m_cmd_ready)begin locked<=1;locked_b<=select_b;end
   if(push)begin owner[tail]<=select_b;tail<=tail+1'b1;prefer_b<=!select_b;locked<=0;end
   if(pop)head<=head+1'b1;
   case({push,pop})2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;default:begin end endcase
  end
 end
`ifndef SYNTHESIS
 initial if(TAGS<2||(TAGS&(TAGS-1)))$fatal(1,"Bad arbiter tag geometry");
 always @(posedge clk)if(rst_n)begin
  if(m_rsp_valid&&count==0)$fatal(1,"Slave response has no accepted owner");
  if(count>TAGS)$fatal(1,"Arbiter owner overflow");
  if(push&&count==TAGS&&!pop)$fatal(1,"Arbiter owner overwrite");
  if(a_cmd_valid&&a_cmd_ready&&b_cmd_valid&&b_cmd_ready)$fatal(1,"Two grants on one bus");
 end
`endif
endmodule
