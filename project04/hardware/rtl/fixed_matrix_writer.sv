`timescale 1ns/1ps
// Fixed row-major 99x256 signed16 matrix. No compression or differential code.
// Input order: sixteen column groups,99rows,8 adjacent pairs per row.
module kwt_fixed_matrix_writer(
 input wire clk,rst_n,
 input wire in_valid,output wire in_ready,
 input wire signed [13:0] in_even,in_odd,input wire in_frame_end,
 output reg out_valid,input wire out_ready,
 output reg [31:0] out_data,output reg [13:0] out_word_index,
 output reg out_last,output reg fault
);
 reg [6:0] row;
 reg [3:0] group_id;
 reg [2:0] pair_column;
 reg complete;
 wire end_group=row==98&&pair_column==7;
 wire accept=in_valid&&in_ready;
 assign in_ready=(!out_valid||out_ready)&&!complete;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   row<=0;group_id<=0;pair_column<=0;complete<=0;
   out_valid<=0;out_data<=0;out_word_index<=0;out_last<=0;fault<=0;
  end else begin
   if(out_valid&&out_ready)out_valid<=0;
   if(accept)begin
    out_valid<=1;
    out_data<={{2{in_odd[13]}},in_odd,{2{in_even[13]}},in_even};
    out_word_index<={row,group_id,pair_column};
    out_last<=end_group;
    if(in_frame_end!=end_group)fault<=1;
    if(pair_column==7)begin
     pair_column<=0;
     if(row==98)begin
      row<=0;
      if(group_id==15)complete<=1;else group_id<=group_id+1'b1;
     end else row<=row+1'b1;
    end else pair_column<=pair_column+1'b1;
   end
  end
 end
endmodule
