`timescale 1ns/1ps
// X:8 SP1024x16 banks, four rows and two feature parities. AlphaX is
// computed from the same accepted load values, then written to two SP128x16.
module kwt_pair_x_store11(
 input wire clk,rst_n,task_start,input wire load_fire,input wire [10:0] load_quad,input wire [51:0] load_values,
 input wire mac_read,input wire [4:0] tile_row,input wire [4:0] feature_pair,
 output wire [103:0] x_pair,output reg x_valid,
 input wire alpha_read,input wire [6:0] alpha_row,output wire signed [31:0] alpha_data,output reg alpha_valid,
 output reg [24:0] rows_ready,output reg fault,output wire alpha_ready
);
 wire [4:0] write_tile=load_quad[10:6];wire [5:0] feature=load_quad[5:0];
 wire read_fire=mac_read&&!load_fire;
 reg [4:0] tile_delayed;
 reg signed [12:0] even_values[0:3];reg signed [30:0] alpha_acc[0:3];
 reg signed [30:0] queued_alpha[0:3];reg [4:0] queued_tile;reg [2:0] queue_remaining;reg [1:0] queue_at;
 wire alpha_write=queue_remaining!=0;
 assign alpha_ready=!alpha_write;
 wire [6:0] alpha_wa={queued_tile,2'd0}+{5'd0,queue_at};
 wire do_alpha_read=alpha_read&&!alpha_write;
 wire [31:0] alpha_q;wire [31:0] alpha_wd={{1{queued_alpha[queue_at][30]}},queued_alpha[queue_at]};
 assign alpha_data=alpha_q;
 genvar b;
 wire [95:0] store_q;
 reg [95:0] write_bits,write_mask;integer row;
 always @*begin
  write_bits=0;write_mask=0;
  for(row=0;row<4;row=row+1)if(write_tile*4+row<99)begin
   write_bits[(row*2+feature[0])*11+:11]=load_values[row*13+:11];
   write_mask[(row*2+feature[0])*11+:11]=11'h7ff;
  end
 end
 generate for(b=0;b<6;b=b+1)begin:x_banks
  kwt_sram_16_masked #(.DEPTH(1024)) mem(.clk(clk),.we(load_fire&&|write_mask[b*16+:16]),.wa({write_tile,feature[5:1]}),
   .wd(write_bits[b*16+:16]),.write_mask(write_mask[b*16+:16]),.re(read_fire),.ra({tile_row,feature_pair}),.rd(store_q[b*16+:16]));
 end
 for(b=0;b<8;b=b+1)begin:x_values
  wire [10:0] v=store_q[b*11+:11];
  assign x_pair[b*13+:13]=tile_delayed==24&&b>=6?13'd0:{{2{v[10]}},v};
 end
 for(b=0;b<2;b=b+1)begin:alpha_banks
  kwt_sram_16 #(.DEPTH(128)) mem(.clk(clk),.we(alpha_write&&alpha_wa<99),.wa(alpha_wa),.wd(alpha_wd[b*16+:16]),
   .re(do_alpha_read),.ra(alpha_row),.rd(alpha_q[b*16+:16]));
 end endgenerate
 integer r;reg signed [25:0] term;reg signed [30:0] next_alpha;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin queue_remaining<=0;queue_at<=0;queued_tile<=0;rows_ready<=0;fault<=0;x_valid<=0;alpha_valid<=0;tile_delayed<=0;end
  else begin
   x_valid<=read_fire;alpha_valid<=do_alpha_read;if(read_fire)tile_delayed<=tile_row;
   if(task_start)begin queue_remaining<=0;queue_at<=0;rows_ready<=0;fault<=0;x_valid<=0;alpha_valid<=0;end
   if(alpha_write)begin
    queue_remaining<=queue_remaining-1'b1;queue_at<=queue_at+1'b1;
    if(queue_remaining==1)rows_ready[queued_tile]<=1;
   end
   if(load_fire)begin
    if(load_quad>=1600)fault<=1;
    for(r=0;r<4;r=r+1)begin
     if(!feature[0])begin even_values[r]<=load_values[r*13+:13];if(feature==0)alpha_acc[r]<=0;end
     else begin
      term=$signed(even_values[r])*$signed(load_values[r*13+:13]);next_alpha=alpha_acc[r]+{{5{term[25]}},term};alpha_acc[r]<=next_alpha;
      if(feature==63)queued_alpha[r]<=next_alpha;
     end
    end
    if(feature==63)begin
     if(queue_remaining!=0)fault<=1;
     queued_tile<=write_tile;queue_remaining<=4;queue_at<=0;
    end
   end
  end
 end
endmodule

// 352-bit W pair:22 SP128x16 macros. Four88-bit load stripes use native
// per-bit masks at the crossing banks. Both buffers retain original addresses.
module kwt_pair_w_store11(
 input wire clk,rst_n,task_start,input wire load_fire,input wire load_buffer,input wire [6:0] load_unit,input wire [95:0] load_values,
 input wire mac_read,read_buffer,input wire [4:0] feature_pair,
 output wire [383:0] w_pair,output reg w_valid,output wire [511:0] alpha_w,
 output reg [1:0] buffer_ready
);
 wire read_fire=mac_read&&!load_fire;wire [4:0] load_pair=load_unit[6:2];wire [1:0] stripe=load_unit[1:0];
 wire [87:0] narrow_load;wire [351:0] store_q;reg [351:0] write_bits,write_mask;
 reg signed [26:0] alpha[0:31];genvar b,c;
 generate for(b=0;b<8;b=b+1)begin:load_narrow
  assign narrow_load[b*11+:11]=load_values[b*12+:11];
 end endgenerate
 always @*begin write_bits=0;write_mask=0;write_bits[stripe*88+:88]=narrow_load;write_mask[stripe*88+:88]={88{1'b1}};end
 generate for(b=0;b<22;b=b+1)begin:w_banks
  kwt_sram_16_masked #(.DEPTH(128)) mem(.clk(clk),.we(load_fire&&|write_mask[b*16+:16]),.wa({1'b0,load_buffer,load_pair}),
   .wd(write_bits[b*16+:16]),.write_mask(write_mask[b*16+:16]),.re(read_fire),.ra({1'b0,read_buffer,feature_pair}),.rd(store_q[b*16+:16]));
 end
 for(b=0;b<32;b=b+1)begin:w_expand
  wire [10:0] v=store_q[b*11+:11];assign w_pair[b*12+:12]={v[10],v};
 end
 for(c=0;c<16;c=c+1)begin:alpha_lanes
  wire signed [26:0] value=alpha[read_buffer*16+c];assign alpha_w[c*32+:32]={{5{value[26]}},value};
 end endgenerate
 integer j,ix;reg signed [21:0] term;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin w_valid<=0;buffer_ready<=0;end
  else begin
   w_valid<=read_fire;if(task_start)begin buffer_ready<=0;w_valid<=0;end
   if(load_fire)begin
    if(load_unit==0)buffer_ready[load_buffer]<=0;
    for(j=0;j<4;j=j+1)begin
     ix=load_buffer*16+stripe*4+j;
     term=$signed(load_values[j*24+:11])*$signed(load_values[j*24+12+:11]);
     alpha[ix]<=(load_pair==0?27'sd0:alpha[ix])+{{5{term[21]}},term};
    end
    if(load_unit==127)buffer_ready[load_buffer]<=1;
   end
  end
 end
endmodule
