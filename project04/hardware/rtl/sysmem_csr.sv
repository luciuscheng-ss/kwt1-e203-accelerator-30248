`timescale 1ns/1ps
// Original SysMem downstream endpoint: CSR plus an unchanged ordinary memory
// bus, which connects only to the restored512KiB shared SRAM at SoC level.
module kwt_sysmem_csr(
 input wire clk,rst_n,
 input wire cmd_valid,output wire cmd_ready,input wire cmd_read,
 input wire [31:0] cmd_addr,cmd_wdata,input wire [3:0] cmd_wmask,
 output wire rsp_valid,input wire rsp_ready,output wire [31:0] rsp_rdata,output wire rsp_err,
 output wire m_cmd_valid,input wire m_cmd_ready,output wire m_cmd_read,
 output wire [31:0] m_cmd_addr,m_cmd_wdata,output wire [3:0] m_cmd_wmask,
 input wire m_rsp_valid,output wire m_rsp_ready,input wire [31:0] m_rsp_rdata,input wire m_rsp_err,
 output reg task_start,stream_mode,output reg [31:0] source_base,result_base,
 input wire busy,done,fault,input wire [31:0] cycles,
 input wire [13:0] source_requests,source_writes,source_acks,source_reads,input wire [15:0] result_words
);
 wire selected=cmd_addr[31:12]==20'ha0080;
 reg csr_valid,csr_err;reg [31:0] csr_data;
 assign rsp_valid=csr_valid||m_rsp_valid;
 assign rsp_err=csr_valid?csr_err:m_rsp_err;
 assign rsp_rdata=csr_valid?csr_data:m_rsp_rdata;
 assign m_rsp_ready=rsp_ready&&!csr_valid;
 assign m_cmd_valid=cmd_valid&&!selected&&(!csr_valid||rsp_ready);
 assign m_cmd_read=cmd_read;assign m_cmd_addr=cmd_addr;assign m_cmd_wdata=cmd_wdata;assign m_cmd_wmask=cmd_wmask;
 wire csr_ready=(!csr_valid||rsp_ready)&&(!m_rsp_valid||m_rsp_ready);
 assign cmd_ready=selected?csr_ready:((!csr_valid||rsp_ready)&&m_cmd_ready);
 wire take=cmd_valid&&cmd_ready&&selected;
 wire active=busy||task_start;
 wire bad_control=|(cmd_wdata&{{8{cmd_wmask[3]}},{8{cmd_wmask[2]}},{8{cmd_wmask[1]}},{8{cmd_wmask[0]}}}&32'hfffffffe);
 wire [32:0] source_end={1'b0,source_base}+33'd32672;
 wire [32:0] result_end={1'b0,result_base}+33'd50688;
 wire bounds_ok=source_base[1:0]==0&&result_base[1:0]==0&&source_base>=32'ha0000000&&result_base>=32'ha0000000&&source_end<=33'h0a0080000&&result_end<=33'h0a0080000&&(source_end<={1'b0,result_base}||result_end<={1'b0,source_base});
 reg [31:0] read_value;reg address_valid;
 always @*begin
  address_valid=cmd_addr[1:0]==0;read_value=0;
  case(cmd_addr[11:0])
   12'h000:read_value=0;
   12'h004:read_value=source_base;
   12'h008:read_value=result_base;
   12'h00c:read_value={29'd0,fault,done&&!active,active};
   12'h010:read_value=cycles;
   12'h014:read_value={18'd0,source_requests};
   12'h018:read_value={16'd0,result_words};
   12'h01c:read_value={18'd0,source_writes};
   12'h020:read_value={18'd0,source_acks};
   12'h024:read_value={18'd0,source_reads};
   12'h028:read_value=32'h0b0b0d16;
   12'h02c:read_value={31'd0,stream_mode};
   default:address_valid=0;
  endcase
 end
 integer lane;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin task_start<=0;stream_mode<=0;source_base<=32'ha0000000;result_base<=32'ha0040000;csr_valid<=0;csr_err<=0;csr_data<=0;end
  else begin
   task_start<=0;
   if(csr_valid&&rsp_ready)csr_valid<=0;
   if(take)begin
    csr_valid<=1;csr_err<=!address_valid;csr_data<=cmd_read?read_value:32'd0;
    if(!cmd_read&&address_valid)begin
     case(cmd_addr[11:0])
      12'h000:begin
       if(bad_control)csr_err<=1;
       else if(cmd_wmask[0]&&cmd_wdata[0])begin
        if(active||!bounds_ok)csr_err<=1;else task_start<=1;
       end
      end
      12'h004:begin
       if(active)csr_err<=1;
       else for(lane=0;lane<4;lane=lane+1)if(cmd_wmask[lane])source_base[lane*8+:8]<=cmd_wdata[lane*8+:8];
      end
      12'h008:begin
       if(active)csr_err<=1;
       else for(lane=0;lane<4;lane=lane+1)if(cmd_wmask[lane])result_base[lane*8+:8]<=cmd_wdata[lane*8+:8];
      end
      12'h02c:begin
       if(active||bad_control||(cmd_wmask[0]&&cmd_wdata[0]))csr_err<=1;
       stream_mode<=0;
      end
      default:csr_err<=1;
     endcase
    end
   end
  end
 end
`ifndef SYNTHESIS
 always @(posedge clk)if(rst_n)begin
  if(csr_valid&&m_rsp_valid)$fatal(1,"CSR/SRAM response ordering collision");
  if(task_start&&!bounds_ok)$fatal(1,"DMA source/result outside shared SRAM");
 end
`endif
endmodule
