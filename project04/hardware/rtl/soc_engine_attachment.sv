`timescale 1ns/1ps
// SystemBus master attachment only. CPU enters u_*; f_* enters the original
// e203_subsys_mems. There are no TCM data ports and no new host loading port.
module kwt_soc_engine_attachment(
 input wire clk,rst_n,task_start,stream_mode,input wire [31:0] source_base,result_base,
 input wire u_cmd_valid,output wire u_cmd_ready,input wire u_cmd_read,
 input wire [31:0] u_cmd_addr,u_cmd_wdata,input wire [3:0] u_cmd_wmask,
 output wire u_rsp_valid,input wire u_rsp_ready,output wire [31:0] u_rsp_rdata,output wire u_rsp_err,
 output wire f_cmd_valid,input wire f_cmd_ready,output wire f_cmd_read,
 output wire [31:0] f_cmd_addr,f_cmd_wdata,output wire [3:0] f_cmd_wmask,
 input wire f_rsp_valid,output wire f_rsp_ready,input wire [31:0] f_rsp_rdata,input wire f_rsp_err,
 output wire busy,done,fault,output wire [31:0] cycles,
 output wire [13:0] source_requests,source_writes,source_acks,source_reads,output wire [15:0] result_words
);
 wire c_cmd_valid,c_cmd_ready,c_rsp_valid,c_rsp_ready,c_rsp_err;wire [31:0] c_cmd_addr,c_rsp_data;
 wire physical_read_valid,physical_read_ready,physical_rsp_valid,physical_rsp_ready,physical_rsp_err;
 wire [31:0] physical_read_addr,physical_rsp_data;
 wire b_cmd_valid,b_cmd_ready,b_cmd_read,b_rsp_valid,b_rsp_ready,b_rsp_err;
 wire [31:0] b_cmd_addr,b_cmd_wdata,b_rsp_rdata;wire [3:0] b_cmd_wmask;
 wire a_cmd_valid,a_cmd_ready,a_cmd_read,a_rsp_valid,a_rsp_ready,a_rsp_err;
 wire [31:0] a_cmd_addr,a_cmd_wdata,a_rsp_rdata;wire [3:0] a_cmd_wmask;
 wire engine_fault;assign fault=engine_fault||stream_mode;
 assign source_writes=14'd0;assign source_acks=14'd0;assign source_reads=14'd0;
 assign a_cmd_valid=u_cmd_valid;assign u_cmd_ready=a_cmd_ready;
 assign a_cmd_read=u_cmd_read;assign a_cmd_addr=u_cmd_addr;assign a_cmd_wdata=u_cmd_wdata;assign a_cmd_wmask=u_cmd_wmask;
 assign u_rsp_valid=a_rsp_valid;assign a_rsp_ready=u_rsp_ready;
 assign u_rsp_rdata=a_rsp_rdata;assign u_rsp_err=a_rsp_err;
 kwt_norm_engine_narrow11_r5 engine(.clk(clk),.rst_n(rst_n),.task_start(task_start),.source_base(source_base),.result_base(result_base),
  .busy(busy),.done(done),.fault(engine_fault),.cycles(cycles),.source_requests(source_requests),.result_words(result_words),
  .c_cmd_valid(c_cmd_valid),.c_cmd_ready(c_cmd_ready),.c_cmd_addr(c_cmd_addr),.c_rsp_valid(c_rsp_valid),.c_rsp_ready(c_rsp_ready),.c_rsp_data(c_rsp_data),.c_rsp_err(c_rsp_err),
  .b_cmd_valid(b_cmd_valid),.b_cmd_ready(b_cmd_ready),.b_cmd_read(b_cmd_read),.b_cmd_addr(b_cmd_addr),.b_cmd_wdata(b_cmd_wdata),.b_cmd_wmask(b_cmd_wmask),.b_rsp_valid(b_rsp_valid),.b_rsp_ready(b_rsp_ready),.b_rsp_err(b_rsp_err));
 wire d_cmd_valid,d_cmd_ready,d_cmd_read,d_rsp_valid,d_rsp_ready,d_rsp_err;
 wire [31:0] d_cmd_addr,d_cmd_wdata,d_rsp_rdata;wire [3:0] d_cmd_wmask;
 // Every source word is read from shared SRAM after CPU START.
 kwt_source_read_buffer #(.DEPTH(8)) source_buffer(.clk(clk),.rst_n(rst_n),
  .e_cmd_valid(c_cmd_valid),.e_cmd_ready(c_cmd_ready),.e_cmd_addr(c_cmd_addr),
  .e_rsp_valid(c_rsp_valid),.e_rsp_ready(c_rsp_ready),.e_rsp_data(c_rsp_data),.e_rsp_err(c_rsp_err),
  .m_cmd_valid(physical_read_valid),.m_cmd_ready(physical_read_ready),.m_cmd_addr(physical_read_addr),
  .m_rsp_valid(physical_rsp_valid),.m_rsp_ready(physical_rsp_ready),.m_rsp_data(physical_rsp_data),.m_rsp_err(physical_rsp_err));
 kwt_shared_arbiter #(.TAGS(8)) dma_arbiter(.clk(clk),.rst_n(rst_n),
  .a_cmd_valid(physical_read_valid),.a_cmd_ready(physical_read_ready),.a_cmd_read(1'b1),.a_cmd_addr(physical_read_addr),.a_cmd_wdata(32'd0),.a_cmd_wmask(4'd0),
  .a_rsp_valid(physical_rsp_valid),.a_rsp_ready(physical_rsp_ready),.a_rsp_rdata(physical_rsp_data),.a_rsp_err(physical_rsp_err),
  .b_cmd_valid(b_cmd_valid),.b_cmd_ready(b_cmd_ready),.b_cmd_read(b_cmd_read),.b_cmd_addr(b_cmd_addr),.b_cmd_wdata(b_cmd_wdata),.b_cmd_wmask(b_cmd_wmask),
  .b_rsp_valid(b_rsp_valid),.b_rsp_ready(b_rsp_ready),.b_rsp_rdata(b_rsp_rdata),.b_rsp_err(b_rsp_err),
  .m_cmd_valid(d_cmd_valid),.m_cmd_ready(d_cmd_ready),.m_cmd_read(d_cmd_read),.m_cmd_addr(d_cmd_addr),.m_cmd_wdata(d_cmd_wdata),.m_cmd_wmask(d_cmd_wmask),
  .m_rsp_valid(d_rsp_valid),.m_rsp_ready(d_rsp_ready),.m_rsp_rdata(d_rsp_rdata),.m_rsp_err(d_rsp_err));
 kwt_shared_arbiter #(.TAGS(8)) arbiter(.m_cmd_valid(f_cmd_valid),.m_cmd_ready(f_cmd_ready),.m_cmd_read(f_cmd_read),
  .m_cmd_addr(f_cmd_addr),.m_cmd_wdata(f_cmd_wdata),.m_cmd_wmask(f_cmd_wmask),
  .m_rsp_valid(f_rsp_valid),.m_rsp_ready(f_rsp_ready),.m_rsp_rdata(f_rsp_rdata),.m_rsp_err(f_rsp_err),
  .b_cmd_valid(d_cmd_valid),.b_cmd_ready(d_cmd_ready),.b_cmd_read(d_cmd_read),.b_cmd_addr(d_cmd_addr),.b_cmd_wdata(d_cmd_wdata),.b_cmd_wmask(d_cmd_wmask),
  .b_rsp_valid(d_rsp_valid),.b_rsp_ready(d_rsp_ready),.b_rsp_rdata(d_rsp_rdata),.b_rsp_err(d_rsp_err),.*);
endmodule
