`timescale 1ns/1ps
// Lossless16-code row blocks: 4-bit tag plus either uniform-width zigzag
// row differences (tags0..13), or16 raw signed14 codes (tag15). A frame
// contains whole rows and is padded only once, at its final32-bit word.
module kwt_block_packer(
 input wire clk,rst_n,input wire in_valid,output wire in_ready,
 input wire signed [13:0] in_even,in_odd,input wire in_frame_end,
 output wire out_valid,input wire out_ready,output wire [31:0] out_data,
 output wire out_last,output reg fault
);
 reg signed [13:0] previous[0:15];reg [13:0] raw_codes[0:31];reg [14:0] residual[0:31];
 reg [3:0] widths[0:1];reg [1:0] full,ends;
 reg write_bank,read_bank,first_row,frame_blocked,flush;
 reg [2:0] write_pair,read_pair;reg [3:0] row_width;
 reg [95:0] reservoir;reg [6:0] count;
 function automatic [3:0] bit_width(input [14:0] value);
  integer k;begin bit_width=0;for(k=0;k<15;k=k+1)if(value[k])bit_width=k+1;end
 endfunction
 wire [3:0] wi0={write_pair,1'b0},wi1={write_pair,1'b1};
 wire signed [14:0] old0=first_row?15'sd0:$signed({previous[wi0][13],previous[wi0]});
 wire signed [14:0] old1=first_row?15'sd0:$signed({previous[wi1][13],previous[wi1]});
 wire signed [14:0] delta0=$signed({in_even[13],in_even})-old0,delta1=$signed({in_odd[13],in_odd})-old1;
 wire [14:0] z0=delta0[14]?((~delta0)<<1)|15'd1:delta0<<1;
 wire [14:0] z1=delta1[14]?((~delta1)<<1)|15'd1:delta1<<1;
 wire [3:0] b0=bit_width(z0),b1=bit_width(z1);
 wire [3:0] pair_width=b0>b1?b0:b1;
 wire [3:0] final_width=pair_width>row_width?pair_width:row_width;
 assign in_ready=!full[write_bank]&&!frame_blocked&&!fault;
 wire take=in_valid&&in_ready;
 assign out_valid=count>=32||(flush&&count!=0);
 assign out_data=reservoir[31:0];assign out_last=flush&&count<=32&&count!=0;
 wire drain=out_valid&&out_ready;
 wire [6:0] after_count=drain?(count>=32?count-7'd32:7'd0):count;
 wire [95:0] after_bits=drain?reservoir>>32:reservoir;
 wire serialize=full[read_bank]&&!flush&&after_count<=31&&!fault;
 wire raw_mode=widths[read_bank]>=14;
 wire [3:0] width=raw_mode?4'd14:widths[read_bank];
 wire [4:0] ri0={read_bank,read_pair,1'b0},ri1={read_bank,read_pair,1'b1};
 wire [14:0] v0=raw_mode?{1'b0,raw_codes[ri0]}:residual[ri0];
 wire [14:0] v1=raw_mode?{1'b0,raw_codes[ri1]}:residual[ri1];
 wire [31:0] mask=(32'd1<<width)-1;
 wire [31:0] pair_token=({17'd0,v0}&mask)|(({17'd0,v1}&mask)<<width);
 wire [31:0] token=read_pair==0?(pair_token<<4)|(raw_mode?32'd15:{28'd0,width}):pair_token;
 wire [5:0] token_bits={1'b0,width,1'b0}+(read_pair==0?6'd4:6'd0);
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   full<=0;ends<=0;write_bank<=0;read_bank<=0;first_row<=1;frame_blocked<=0;flush<=0;
   write_pair<=0;read_pair<=0;row_width<=0;reservoir<=0;count<=0;fault<=0;
  end else begin
   if(drain||serialize)begin
    reservoir<=after_bits|(serialize?({64'd0,token}<<after_count):96'd0);
    count<=after_count+(serialize?token_bits:6'd0);
   end
   if(take)begin
    previous[wi0]<=in_even;previous[wi1]<=in_odd;
    raw_codes[{write_bank,wi0}]<=in_even;raw_codes[{write_bank,wi1}]<=in_odd;
    residual[{write_bank,wi0}]<=z0;residual[{write_bank,wi1}]<=z1;
    if(in_frame_end&&write_pair!=7)fault<=1;
    if(write_pair==7)begin
     full[write_bank]<=1;ends[write_bank]<=in_frame_end;widths[write_bank]<=final_width;
     write_bank<=!write_bank;write_pair<=0;row_width<=0;first_row<=0;
     if(in_frame_end)frame_blocked<=1;
    end else begin write_pair<=write_pair+1'b1;row_width<=final_width;end
   end
   if(serialize)begin
    if(read_pair==7)begin
     full[read_bank]<=0;read_bank<=!read_bank;read_pair<=0;
     if(ends[read_bank])flush<=1;
    end else read_pair<=read_pair+1'b1;
   end
   if(drain&&out_last)begin
    full<=0;ends<=0;write_bank<=0;read_bank<=0;first_row<=1;frame_blocked<=0;flush<=0;
    write_pair<=0;read_pair<=0;row_width<=0;reservoir<=0;count<=0;
   end
  end
 end
`ifndef SYNTHESIS
 always @(posedge clk)if(rst_n)begin
  if(count>63)$fatal(1,"Output reservoir overflow");
  if(serialize&&widths[read_bank]==14)begin end //14 selects documented raw fallback.
 end
`endif
endmodule
