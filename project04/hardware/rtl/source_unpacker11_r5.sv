`timescale 1ns/1ps
// Lossless decoder for norm_codec.py. Each of16 groups carries16 biases,
// 16 M4/R6 fields and128 96-bit W stripes. Only group0 carries1600 X quads.
module kwt_source_unpacker11_r5(
 input wire clk,rst_n,word_valid,output wire word_ready,input wire [31:0] word_data,
 output wire field_valid,input wire field_ready,output reg [1:0] kind,
 output reg [3:0] group_id,output reg [10:0] field_index,output wire [95:0] field_data,
 output reg done
);
 reg [127:0] bits;reg [7:0] count;
 wire [7:0] needed=kind==0?8'd32:kind==1?8'd10:kind==2?8'd88:8'd55;
 assign field_valid=!done&&count>=needed;
 wire [95:0] w_expanded;wire [59:0] x_expanded;
 genvar c;
 generate for(c=0;c<8;c=c+1)begin:w_expand
  assign w_expanded[c*12+:12]={bits[c*11+10],bits[c*11+:11]};
 end
 for(c=0;c<5;c=c+1)begin:x_expand
  assign x_expanded[c*12+:12]={bits[c*11+10],bits[c*11+:11]};
 end endgenerate
 assign field_data=kind==2?w_expanded:kind==3?{36'd0,x_expanded}:bits[95:0];
 wire take=field_valid&&field_ready;
 wire [7:0] left_count=count-(take?needed:8'd0);
 wire [127:0] left_bits=take?(bits>>needed):bits;
 assign word_ready=!done&&left_count<=96;
 wire push=word_valid&&word_ready;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin bits<=0;count<=0;kind<=0;group_id<=0;field_index<=0;done<=0;end
  else begin
   if(take||push)begin bits<=left_bits|(push?({96'd0,word_data}<<left_count):128'd0);count<=left_count+(push?8'd32:8'd0);end
   if(take)begin
    field_index<=field_index+1'b1;
    if(kind<2&&field_index==15)begin kind<=kind+1'b1;field_index<=0;end
    if(kind==2&&field_index==127)begin
     field_index<=0;
     if(group_id==0)kind<=3;
     else if(group_id==15)done<=1;
     else begin kind<=0;group_id<=group_id+1'b1;end
    end
    if(kind==3&&field_index==1279)begin kind<=0;field_index<=0;group_id<=1;end
   end
  end
 end
`ifndef SYNTHESIS
 always @(posedge clk)if(rst_n&&count>128)$fatal(1,"Source bit reservoir overflow");
`endif
endmodule
