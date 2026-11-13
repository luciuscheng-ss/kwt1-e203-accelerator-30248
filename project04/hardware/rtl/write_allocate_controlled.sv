`timescale 1ns/1ps
// Ordered SystemBus adapter. Every accepted upstream command is forwarded to
// the original SRAM controller. Source data becomes readable only after the
// matching successful downstream write response. No SRAM macro data-pin tap.
module kwt_write_allocate_controlled #(
 parameter integer WORDS=9064,DEPTH=4,TAGS=2,RESP_DEPTH=0
)(
 input wire clk,rst_n,arm,disarm,input wire [31:0] source_base,
 input wire u_cmd_valid,output wire u_cmd_ready,input wire u_cmd_read,
 input wire [31:0] u_cmd_addr,u_cmd_wdata,input wire [3:0] u_cmd_wmask,
 output wire u_rsp_valid,input wire u_rsp_ready,output wire [31:0] u_rsp_rdata,output wire u_rsp_err,
 output wire m_cmd_valid,input wire m_cmd_ready,output wire m_cmd_read,
 output wire [31:0] m_cmd_addr,m_cmd_wdata,output wire [3:0] m_cmd_wmask,
 input wire m_rsp_valid,output wire m_rsp_ready,input wire [31:0] m_rsp_rdata,input wire m_rsp_err,
 input wire c_cmd_valid,output wire c_cmd_ready,input wire [31:0] c_cmd_addr,
 output reg c_rsp_valid,input wire c_rsp_ready,output reg [31:0] c_rsp_data,output reg c_rsp_err,
 output reg fault,output reg [13:0] source_writes,source_acks,source_reads
);
 localparam integer DW=$clog2(DEPTH),TW=$clog2(TAGS);
 reg [31:0] data[0:DEPTH-1];reg tag[0:TAGS-1];
 reg [DW-1:0] put_at,get_at;reg [TW-1:0] tag_head,tag_tail;reg [TW:0] tag_count;
 reg armed;reg [31:0] base;
 wire source_write=armed&&!u_cmd_read&&u_cmd_addr>=base&&u_cmd_addr<base+4*WORDS;
 wire legal=source_write&&u_cmd_addr==base+4*source_writes&&u_cmd_wmask==15&&source_writes<WORDS;
 wire response_pop=m_rsp_valid&&m_rsp_ready;
 wire tag_space=tag_count<TAGS||response_pop;
 wire source_space=source_writes-source_reads<DEPTH;
 wire forward_ok=tag_space&&(!source_write||source_space);
 assign m_cmd_valid=u_cmd_valid&&forward_ok;
 assign u_cmd_ready=m_cmd_ready&&forward_ok;
 assign m_cmd_read=u_cmd_read;assign m_cmd_addr=u_cmd_addr;assign m_cmd_wdata=u_cmd_wdata;assign m_cmd_wmask=u_cmd_wmask;
 // The optional response FIFO releases the shared bus after the SRAM's real
 // response, even when the original CPU/loader cannot consume its response.
 // It remains finite, ordered and backpressured; no response is discarded.
 generate if(RESP_DEPTH==0)begin:direct_response
  assign u_rsp_valid=m_rsp_valid;assign m_rsp_ready=u_rsp_ready;
  assign u_rsp_rdata=m_rsp_rdata;assign u_rsp_err=m_rsp_err;
 end else begin:buffered_response
  localparam integer RW=$clog2(RESP_DEPTH);
  reg [32:0] records[0:RESP_DEPTH-1];reg [RW-1:0] head,tail;reg [RW:0] used;
  assign u_rsp_valid=used!=0;assign {u_rsp_err,u_rsp_rdata}=records[head];
  wire pop=u_rsp_valid&&u_rsp_ready;
  assign m_rsp_ready=used<RESP_DEPTH||pop;
  wire push=m_rsp_valid&&m_rsp_ready;
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin head<=0;tail<=0;used<=0;end
   else begin
    if(push)begin records[tail]<={m_rsp_err,m_rsp_rdata};tail<=tail+1'b1;end
    if(pop)head<=head+1'b1;
    case({push,pop})2'b10:used<=used+1'b1;2'b01:used<=used-1'b1;default:begin end endcase
   end
  end
`ifndef SYNTHESIS
  initial if(RESP_DEPTH<2||(RESP_DEPTH&(RESP_DEPTH-1)))$fatal(1,"Bad response FIFO geometry");
  always @(posedge clk)if(rst_n&&used>RESP_DEPTH)$fatal(1,"Source response FIFO overflow");
`endif
 end endgenerate
 wire command_push=m_cmd_valid&&m_cmd_ready;
 wire available=armed&&!fault&&source_reads<source_acks;
 assign c_cmd_ready=!arm&&(!c_rsp_valid||c_rsp_ready)&&available;
 wire cache_pop=c_cmd_valid&&c_cmd_ready;
 wire address_ok=c_cmd_addr==base+4*source_reads;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   put_at<=0;get_at<=0;tag_head<=0;tag_tail<=0;tag_count<=0;
   source_writes<=0;source_acks<=0;source_reads<=0;armed<=0;base<=0;fault<=0;
   c_rsp_valid<=0;c_rsp_data<=0;c_rsp_err<=0;
  end else begin
   if(disarm)begin
    if(source_writes!=source_reads||source_writes!=source_acks||c_rsp_valid)fault<=1;
    else begin armed<=0;fault<=0;end
   end
   if(arm)begin
    if(source_writes!=source_reads||source_writes!=source_acks||c_rsp_valid||command_push)fault<=1;
    else begin
     put_at<=0;get_at<=0;source_writes<=0;source_acks<=0;source_reads<=0;fault<=0;base<=source_base;armed<=1;
    end
   end
   if(c_rsp_valid&&c_rsp_ready)c_rsp_valid<=0;
   if(cache_pop)begin
    c_rsp_valid<=1;c_rsp_data<=data[get_at];c_rsp_err<=!address_ok;
    if(!address_ok)fault<=1;
    get_at<=get_at+1'b1;source_reads<=source_reads+1'b1;
   end
   case({command_push,response_pop})2'b10:tag_count<=tag_count+1'b1;2'b01:tag_count<=tag_count-1'b1;default:begin end endcase
   if(command_push)begin
    tag[tag_tail]<=legal;tag_tail<=tag_tail+1'b1;
    if(source_write&&!legal)fault<=1;
    if(legal)begin data[put_at]<=u_cmd_wdata;put_at<=put_at+1'b1;source_writes<=source_writes+1'b1;end
   end
   if(response_pop)begin
    tag_head<=tag_head+1'b1;
    if(tag_count==0)fault<=1;
    else if(tag[tag_head])begin
     if(m_rsp_err)fault<=1;
     else source_acks<=source_acks+1'b1;
    end
   end
  end
 end
`ifndef SYNTHESIS
 initial if(DEPTH<2||(DEPTH&(DEPTH-1))||TAGS<2||(TAGS&(TAGS-1))||WORDS>16383)$fatal(1,"Bad cache geometry");
 always @(posedge clk)if(rst_n)begin
  if(response_pop&&tag_count==0)$fatal(1,"Write allocation response without accepted command");
  if(command_push&&tag_count==TAGS&&!response_pop)$fatal(1,"Tag overflow");
  if(source_reads>source_acks||source_acks>source_writes||source_writes-source_reads>DEPTH)$fatal(1,"Bad cache credits");
  if(arm&&disarm)$fatal(1,"Conflicting cache mode commands");
  if(arm&&command_push&&source_write)$fatal(1,"Arm overlaps source command");
 end
`endif
endmodule
