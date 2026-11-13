`timescale 1ns/1ps
module fixed_matrix_writer_tb;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,in_valid=0,out_ready=0,active=0;
 wire in_ready,out_valid,out_last,fault;
 reg signed [13:0] in_even=0,in_odd=0;reg in_frame_end=0;
 wire [31:0] out_data;wire [13:0] out_word_index;
 kwt_fixed_matrix_writer dut(.*);
 reg [13:0] codes[0:14*25344-1];
 reg [31:0] golden[0:14*12672-1],stored[0:12671];
 reg seen[0:12671];
 integer caseno=0,input_pairs=0,outputs=0,cycle=0,group_ends=0,total_checks=0;
 reg stalled=0;reg [46:0] previous_payload;
 always @(negedge clk)begin
  if(active)begin
   out_ready=(cycle%13>3)&&(cycle%37<29);
   if(!in_valid||in_ready)in_valid=input_pairs<12672&&(cycle%7!=0);
   in_even=codes[caseno*25344+input_pairs*2];
   in_odd=codes[caseno*25344+input_pairs*2+1];
   in_frame_end=(input_pairs%792)==791;
  end else begin in_valid=0;out_ready=0;end
 end
 always @(posedge clk)begin
  cycle=cycle+1;
  if(rst_n&&active)begin
   if(fault)$fatal(1,"Formatter fault");
   if(stalled&&(!out_valid||{out_word_index,out_last,out_data}!==previous_payload))$fatal(1,"Output changed under backpressure");
   stalled=out_valid&&!out_ready;previous_payload={out_word_index,out_last,out_data};
   if(in_valid&&in_ready)input_pairs=input_pairs+1;
   if(out_valid&&out_ready)begin
    if(out_word_index>=12672||seen[out_word_index])$fatal(1,"Duplicate/out-of-bounds matrix word");
    if(out_data!==golden[caseno*12672+out_word_index])$fatal(1,"Physical matrix data mismatch case=%0d word=%0d",caseno,out_word_index);
    if(out_last!==((outputs%792)==791))$fatal(1,"Group end mismatch");
    seen[out_word_index]=1;stored[out_word_index]=out_data;
    outputs=outputs+1;total_checks=total_checks+1;if(out_last)group_ends=group_ends+1;
   end
  end else stalled=0;
 end
 initial begin
  $readmemh("codes.hex",codes);$readmemh("matrix.hex",golden);
  for(caseno=0;caseno<14;caseno=caseno+1)begin
   active=0;rst_n=0;repeat(3)@(negedge clk);
   for(integer i=0;i<12672;i=i+1)begin seen[i]=0;stored[i]=32'hdeadbeef;end
   input_pairs=0;outputs=0;group_ends=0;rst_n=1;@(posedge clk);active=1;
   wait(outputs==12672);@(negedge clk);active=0;
   if(input_pairs!=12672||group_ends!=16||fault)$fatal(1,"Incomplete matrix");
   for(integer i=0;i<12672;i=i+1)if(!seen[i]||stored[i]!==golden[caseno*12672+i])$fatal(1,"Matrix hole/readback mismatch");
   $display("PASS FIXED16 MATRIX CASE %0d WORDS %0d",caseno,outputs);
  end
  $display("PASS FIXED16 ALL14 WORD CHECKS %0d VALUES %0d",total_checks,total_checks*2);$finish;
 end
 initial begin #100000000;$fatal(1,"Formatter timeout");end
endmodule
