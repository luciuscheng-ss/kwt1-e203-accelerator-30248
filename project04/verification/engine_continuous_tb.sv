`timescale 1ns/1ps
module engine_continuous_tb;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,task_start=0;wire busy,done,fault;wire [31:0] cycles;
 wire c_cmd_valid,c_cmd_ready,c_rsp_ready;wire [31:0] c_cmd_addr;
 reg c_rsp_valid=0;reg [31:0] c_rsp_data=0;
 wire b_cmd_valid,b_cmd_ready,b_cmd_read,b_rsp_ready;wire [31:0] b_cmd_addr,b_cmd_wdata;wire [3:0] b_cmd_wmask;
 reg b_rsp_valid=0;integer ack_delay=0,cycle=0;
 wire [13:0] source_requests;wire [15:0] result_words;
 reg [31:0] sources[0:14*8168-1],matrix[0:14*12672-1],stored[0:12671];
 reg [32:0] gold_raw[0:14*25344-1];reg [13:0] gold_codes[0:14*25344-1];reg seen[0:12671];
 integer caseno=0,src=0,writes=0,acks=0,raw=0,quant=0,checks=0;
 kwt_norm_engine_narrow11_r5 dut(.clk(clk),.rst_n(rst_n),.task_start(task_start),.source_base(32'ha0000000),.result_base(32'ha0040000),
 .busy(busy),.done(done),.fault(fault),.cycles(cycles),.source_requests(source_requests),.result_words(result_words),
 .c_cmd_valid(c_cmd_valid),.c_cmd_ready(c_cmd_ready),.c_cmd_addr(c_cmd_addr),.c_rsp_valid(c_rsp_valid),.c_rsp_ready(c_rsp_ready),.c_rsp_data(c_rsp_data),.c_rsp_err(1'b0),
 .b_cmd_valid(b_cmd_valid),.b_cmd_ready(b_cmd_ready),.b_cmd_read(b_cmd_read),.b_cmd_addr(b_cmd_addr),.b_cmd_wdata(b_cmd_wdata),.b_cmd_wmask(b_cmd_wmask),.b_rsp_valid(b_rsp_valid),.b_rsp_ready(b_rsp_ready),.b_rsp_err(1'b0));
 assign c_cmd_ready=(!c_rsp_valid||c_rsp_ready)&&(cycle%11>1);
 assign b_cmd_ready=!b_rsp_valid&&ack_delay==0&&(cycle%13>3);
 always @(posedge clk)begin
  cycle=cycle+1;
  if(!rst_n)begin c_rsp_valid<=0;b_rsp_valid<=0;ack_delay<=0;end
  else begin
   if(c_rsp_valid&&c_rsp_ready)c_rsp_valid<=0;
   if(c_cmd_valid&&c_cmd_ready)begin
    if(src>=8168||c_cmd_addr!==32'ha0000000+4*src)$fatal(1,"Source read sequence");
    c_rsp_data<=sources[caseno*8168+src];c_rsp_valid<=1;src=src+1;
   end
   if(b_rsp_valid&&b_rsp_ready)begin b_rsp_valid<=0;acks=acks+1;end
   if(ack_delay>0)begin ack_delay<=ack_delay-1;if(ack_delay==1)b_rsp_valid<=1;end
   if(b_cmd_valid&&b_cmd_ready)begin
    if(b_cmd_read||b_cmd_wmask!=15||b_cmd_addr<32'ha0040000||b_cmd_addr>=32'ha004c600||b_cmd_addr[1:0]!=0)$fatal(1,"Output address/format");
    if(seen[(b_cmd_addr-32'ha0040000)>>2])$fatal(1,"Repeated output address");
    seen[(b_cmd_addr-32'ha0040000)>>2]=1;
    if(b_cmd_wdata!==matrix[caseno*12672+((b_cmd_addr-32'ha0040000)>>2)])$fatal(1,"Output matrix mismatch");
    stored[(b_cmd_addr-32'ha0040000)>>2]=b_cmd_wdata;writes=writes+1;ack_delay<=3;
   end
   if(dut.kernel_valid&&dut.quant_ready)begin
    if(dut.raw_even!==$signed(gold_raw[caseno*25344+raw])||dut.raw_odd!==$signed(gold_raw[caseno*25344+raw+1]))$fatal(1,"Continuous raw mismatch case=%0d index=%0d",caseno,raw);
    raw=raw+2;
   end
   if(dut.quant_valid&&dut.quant_out_ready)begin
    if(dut.quant_codes!=={gold_codes[caseno*25344+quant+1],gold_codes[caseno*25344+quant]})$fatal(1,"Continuous quant mismatch");quant=quant+2;
   end
   if(fault)$fatal(1,"Engine fault");
  end
 end
 initial begin
  $readmemh("source.hex",sources);$readmemh("raw.hex",gold_raw);$readmemh("codes.hex",gold_codes);$readmemh("matrix.hex",matrix);
  repeat(5)@(negedge clk);rst_n=1;
  // No global reset or SRAM clearing between any of the fourteen tasks.
  for(caseno=0;caseno<14;caseno=caseno+1)begin
   for(integer k=0;k<12672;k=k+1)seen[k]=0;
   src=0;writes=0;acks=0;raw=0;quant=0;
   @(negedge clk);task_start=1;@(negedge clk);task_start=0;
   wait(busy);wait(done);@(negedge clk);
   if(src!=8168||source_requests!=8168||writes!=12672||acks!=12672||result_words!=12672||raw!=25344||quant!=25344||busy)$fatal(1,"Continuous incomplete task");
   for(integer k=0;k<12672;k=k+1)if(!seen[k]||stored[k]!==matrix[caseno*12672+k])$fatal(1,"Continuous matrix readback");
   checks=checks+25344;$display("PASS CONTINUOUS TASK %0d RAW %0d QUANT %0d WORDS %0d",caseno,raw,quant,writes);
   repeat(8)@(negedge clk);
  end
  $display("PASS CONTINUOUS14 FULL ENGINE VALUES %0d",checks);$finish;
 end
 initial begin #200000000;$fatal(1,"Continuous engine timeout");end
endmodule
