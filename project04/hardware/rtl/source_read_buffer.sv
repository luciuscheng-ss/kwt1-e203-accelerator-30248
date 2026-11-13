`timescale 1ns/1ps
// Reserve enough response slots before issuing reads. Decoder backpressure
// cannot leave a source read blocking result-write ACKs on the shared bus.
module kwt_source_read_buffer #(parameter integer DEPTH=8)(
 input wire clk,rst_n,
 input wire e_cmd_valid,output wire e_cmd_ready,input wire [31:0] e_cmd_addr,
 output wire e_rsp_valid,input wire e_rsp_ready,output wire [31:0] e_rsp_data,output wire e_rsp_err,
 output wire m_cmd_valid,input wire m_cmd_ready,output wire [31:0] m_cmd_addr,
 input wire m_rsp_valid,output wire m_rsp_ready,input wire [31:0] m_rsp_data,input wire m_rsp_err
);
 localparam integer W=$clog2(DEPTH);
 reg [32:0] data[0:DEPTH-1];reg [W-1:0] head,tail;reg [W:0] used,reserved;
 assign e_rsp_valid=used!=0;assign {e_rsp_err,e_rsp_data}=data[head];
 wire pop=e_rsp_valid&&e_rsp_ready;
 wire credit=reserved<DEPTH;
 assign m_cmd_valid=e_cmd_valid&&credit;assign e_cmd_ready=m_cmd_ready&&credit;assign m_cmd_addr=e_cmd_addr;
 wire issue=m_cmd_valid&&m_cmd_ready;
 assign m_rsp_ready=used<DEPTH;
 wire push=m_rsp_valid&&m_rsp_ready;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin head<=0;tail<=0;used<=0;reserved<=0;end
  else begin
   if(push)begin data[tail]<={m_rsp_err,m_rsp_data};tail<=tail+1'b1;end
   if(pop)head<=head+1'b1;
   case({push,pop})2'b10:used<=used+1'b1;2'b01:used<=used-1'b1;default:begin end endcase
   case({issue,pop})2'b10:reserved<=reserved+1'b1;2'b01:reserved<=reserved-1'b1;default:begin end endcase
  end
 end
`ifndef SYNTHESIS
 initial if(DEPTH<2||(DEPTH&(DEPTH-1)))$fatal(1,"Bad source read-buffer geometry");
 always @(posedge clk)if(rst_n)begin
  if(used>reserved||reserved>DEPTH)$fatal(1,"Read response reservation overflow");
  if(push&&reserved==used&&!issue)$fatal(1,"Source read response without outstanding read");
 end
`endif
endmodule
