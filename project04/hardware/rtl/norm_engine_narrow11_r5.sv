`timescale 1ns/1ps
// First complete-path candidate: use the tested8+26 SP stores and dedicated
// hardware Alpha generators. Deliberately retain this simple reference before
// considering multiplier sharing/packed Alpha storage as score tradeoffs.
// Prefetch the next four hardware AlphaX values while the current tile MACs.
// Extra context registers trade a little area for fewer scheduling bubbles.
// No data results/Alpha values arrive from software. Source is8168 bus words.
module kwt_norm_engine_narrow11_r5 #(parameter integer OUTPUT_BITS=13)(
 input wire clk,rst_n,task_start,input wire [31:0] source_base,result_base,
 output reg busy,done,fault,output reg [31:0] cycles,
 output wire c_cmd_valid,input wire c_cmd_ready,output wire [31:0] c_cmd_addr,
 input wire c_rsp_valid,output wire c_rsp_ready,input wire [31:0] c_rsp_data,input wire c_rsp_err,
 output wire b_cmd_valid,input wire b_cmd_ready,output wire b_cmd_read,
 output wire [31:0] b_cmd_addr,b_cmd_wdata,output wire [3:0] b_cmd_wmask,
 input wire b_rsp_valid,output wire b_rsp_ready,input wire b_rsp_err,
 output reg [13:0] source_requests,output reg [15:0] result_words
);
 reg reset_task;wire local_rst_n=rst_n&&!reset_task;
 reg [31:0] src_base,out_base;
 wire running=busy&&!reset_task&&!task_start;
 assign c_cmd_valid=running&&source_requests<8168;
 assign c_cmd_addr=src_base+{16'd0,source_requests,2'd0};
 wire word_ready,field_valid,field_ready,source_done;
 wire [1:0] kind;wire [3:0] load_group;wire [10:0] field_index;wire [95:0] field_data;
 assign c_rsp_ready=running&&word_ready;
 kwt_source_unpacker11_r5 decoder(.clk(clk),.rst_n(local_rst_n),.word_valid(c_rsp_valid&&running),.word_ready(word_ready),.word_data(c_rsp_data),
  .field_valid(field_valid),.field_ready(field_ready),.kind(kind),.group_id(load_group),.field_index(field_index),.field_data(field_data),.done(source_done));
 // Queue only source weights, and use otherwise idle SP cycles for writes.
 reg [103:0] wq[0:3];reg [1:0] wqh,wqt;reg [2:0] wqcount;
 wire wload;wire wq_space=wqcount<4||wload;
 reg [1:0] buffer_free;reg signed [31:0] bias[0:31];reg [9:0] scale[0:31];
 assign field_ready=running&&(kind!=0||field_index!=0||buffer_free[load_group[0]])&&(kind!=2||wq_space);
 wire field_take=field_valid&&field_ready;
 wire xload=field_take&&kind==3,wq_push=field_take&&kind==2;
 wire [64:0] xload_values;
 genvar z;
 generate for(z=0;z<5;z=z+1)begin:expand_x
  assign xload_values[z*13+:13]={field_data[z*12+11],field_data[z*12+:12]};
 end endgenerate
 localparam [2:0] S_WAIT=0,S_ALPHA=1,S_MAC=2,S_DRAIN=3,S_GROUP=4,S_FINISH=5,S_NEXT=6;
 reg [2:0] state;reg [3:0] mac_group;reg [4:0] tile_row,read_feature;
 reg alpha_active,alpha_target_next,next_alpha_valid;reg [4:0] alpha_target_tile;reg [144:0] next_alpha;
 reg [2:0] alpha_requested,alpha_received;reg [2:0] alpha_return_index;reg [144:0] alpha_x;
 wire [24:0] rows_ready;wire [1:0] weights_ready;
 wire xvalid,wvalid,alpha_valid,alpha_ready,x_fault;wire signed [31:0] alpha_data;
 wire [129:0] xp;wire [383:0] wp;wire [511:0] alpha_w;
 wire alpha_pad=running&&alpha_active&&rows_ready[alpha_target_tile]&&alpha_target_tile==19&&alpha_requested==4;
 wire alpha_read=running&&alpha_active&&rows_ready[alpha_target_tile]&&alpha_requested<5&&!alpha_pad;
 wire alpha_fire=alpha_read&&alpha_ready;
 wire [6:0] alpha_row=alpha_target_tile*7'd5+{4'd0,alpha_requested};
 wire memory_read;
 kwt_pair_x_store11_r5 xs(.clk(clk),.rst_n(local_rst_n),.task_start(1'b0),.load_fire(xload),.load_quad(field_index),.load_values(xload_values),
  .mac_read(memory_read),.tile_row(tile_row),.feature_pair(read_feature),.x_pair(xp),.x_valid(xvalid),
  .alpha_read(alpha_read),.alpha_row(alpha_row),.alpha_data(alpha_data),.alpha_valid(alpha_valid),.alpha_ready(alpha_ready),.rows_ready(rows_ready),.fault(x_fault));
 kwt_pair_w_store11 ws(.clk(clk),.rst_n(local_rst_n),.task_start(1'b0),.load_fire(wload),.load_buffer(wq[wqh][103]),.load_unit(wq[wqh][102:96]),.load_values(wq[wqh][95:0]),
  .mac_read(memory_read),.read_buffer(mac_group[0]),.feature_pair(read_feature),.w_pair(wp),.w_valid(wvalid),.alpha_w(alpha_w),.buffer_ready(weights_ready));
 // Two elastic records reserve space for a synchronous SRAM read already in
 // flight when the kernel withdraws ready. Never overwrite an unconsumed pair.
 reg [119:0] fx[0:1];reg [383:0] fw[0:1];reg ff[0:1],fl[0:1];reg [10:0] ft[0:1];
 reg fh,fp;reg [1:0] fcount;reg first_delayed,last_delayed;reg [10:0] tile_delayed;
 wire issue_valid=fcount!=0;wire issue_ready;wire issue_pop=issue_valid&&issue_ready;
 wire [2:0] reserved={1'b0,fcount}+{2'd0,xvalid}-(issue_pop?3'd1:3'd0);
 assign wload=running&&wqcount!=0&&(state!=S_MAC||reserved>=2);
 assign memory_read=running&&state==S_MAC&&!xload&&!wload&&reserved<2;
 wire [527:0] correction;
 generate for(z=0;z<16;z=z+1)begin:column_correction
  wire signed [31:0] b=bias[{mac_group[0],4'(z)}];wire signed [31:0] aw=alpha_w[z*32+:32];
  assign correction[z*33+:33]=$signed({b[31],b})-$signed({aw[31],aw});
 end endgenerate
 wire kernel_valid,kernel_ready,kernel_fault;wire [10:0] kernel_tile;
 reg [6:0] raw_index;wire signed [32:0] raw_even,raw_odd;
 kwt_kernel11_r5 kernel(.clk(clk),.rst_n(local_rst_n),.issue_valid(issue_valid),.issue_ready(issue_ready),.issue_first(ff[fh]),.issue_last(fl[fh]),
  .x_pair(fx[fh]),.w_pair(fw[fh]),.alpha_x(alpha_x),.correction(correction),.tile_id(ft[fh]),
  .aux_valid(1'b0),.aux_ready(),.aux_pairs(96'd0),.aux_tag(12'd0),.aux_out_valid(),.aux_products(),.aux_out_tag(),
  .out_valid(kernel_valid),.out_ready(kernel_ready),.out_tile(kernel_tile),.out_index(raw_index),.out_raw(raw_even),.out_raw_next(raw_odd),.fault(kernel_fault));
 wire quant_ready,quant_valid,quant_out_ready,quant_end,quant_fault;wire [27:0] quant_codes;
 wire raw_last_pair=raw_index==(kernel_tile[4:0]==19?7'd62:7'd78);
 wire raw_frame_end=kernel_tile[4:0]==19&&raw_last_pair;
 wire raw_take=kernel_valid&&quant_ready;
 assign kernel_ready=raw_take&&raw_last_pair;
 wire [4:0] scale_index={mac_group[0],raw_index[3:0]};
 wire [9:0] scale_even=scale[scale_index],scale_odd=scale[scale_index+5'd1];
 kwt_scaled_quantize2 #(.OUTPUT_BITS(OUTPUT_BITS)) quant(.clk(clk),.rst_n(local_rst_n),.in_valid(kernel_valid),.in_ready(quant_ready),.in_raw({raw_odd,raw_even}),
  .in_mult({scale_odd[3:0],scale_even[3:0]}),.in_shift({scale_odd[9:4],scale_even[9:4]}),.in_frame_end(raw_frame_end),
  .out_valid(quant_valid),.out_ready(quant_out_ready),.out_codes(quant_codes),.out_frame_end(quant_end),.fault(quant_fault));
 wire matrix_valid,matrix_ready,matrix_last,matrix_fault;
 wire [31:0] matrix_data;wire [13:0] matrix_word_index;
 kwt_fixed_matrix_writer writer(.clk(clk),.rst_n(local_rst_n),
  .in_valid(quant_valid),.in_ready(quant_out_ready),.in_even(quant_codes[13:0]),.in_odd(quant_codes[27:14]),.in_frame_end(quant_end),
  .out_valid(matrix_valid),.out_ready(matrix_ready),.out_data(matrix_data),.out_word_index(matrix_word_index),.out_last(matrix_last),.fault(matrix_fault));
 assign b_cmd_valid=running&&matrix_valid;assign matrix_ready=running&&b_cmd_ready;
 assign b_cmd_read=1'b0;assign b_cmd_wmask=4'b1111;
 assign b_cmd_addr=out_base+{16'd0,matrix_word_index,2'd0};assign b_cmd_wdata=matrix_data;
 assign b_rsp_ready=1'b1;
 wire write_fire=b_cmd_valid&&b_cmd_ready,response_fire=b_rsp_valid&&b_rsp_ready;
 reg [3:0] pending_writes;reg [3:0] frames_sent;reg final_sent;
 integer n;wire [2:0] alpha_increment={2'd0,alpha_valid}+{2'd0,alpha_pad};
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   reset_task<=0;busy<=0;done<=0;fault<=0;cycles<=0;source_requests<=0;result_words<=0;src_base<=0;out_base<=0;
   state<=S_WAIT;mac_group<=0;tile_row<=0;read_feature<=0;alpha_active<=0;alpha_target_next<=0;next_alpha_valid<=0;alpha_target_tile<=0;alpha_requested<=0;alpha_received<=0;alpha_return_index<=0;
   fh<=0;fp<=0;fcount<=0;first_delayed<=0;last_delayed<=0;tile_delayed<=0;raw_index<=0;
   pending_writes<=0;frames_sent<=0;final_sent<=0;buffer_free<=3;wqh<=0;wqt<=0;wqcount<=0;
  end else begin
   reset_task<=0;
   if(task_start)begin
    if(busy)fault<=1;
    else begin busy<=1;done<=0;reset_task<=1;src_base<=source_base;out_base<=result_base;end
   end
   if(reset_task)begin
    fault<=0;cycles<=0;source_requests<=0;result_words<=0;state<=S_WAIT;mac_group<=0;tile_row<=0;read_feature<=0;
    alpha_active<=0;alpha_target_next<=0;next_alpha_valid<=0;alpha_target_tile<=0;alpha_requested<=0;alpha_received<=0;alpha_return_index<=0;fh<=0;fp<=0;fcount<=0;
    first_delayed<=0;last_delayed<=0;tile_delayed<=0;raw_index<=0;pending_writes<=0;frames_sent<=0;final_sent<=0;buffer_free<=3;wqh<=0;wqt<=0;wqcount<=0;
   end else if(running)begin
    cycles<=cycles+1'b1;
    if(wq_push)begin wq[wqt]<={load_group[0],field_index[6:0],field_data};wqt<=wqt+1'b1;end
    if(wload)wqh<=wqh+1'b1;
    case({wq_push,wload})2'b10:wqcount<=wqcount+1'b1;2'b01:wqcount<=wqcount-1'b1;default:begin end endcase
    if(c_cmd_valid&&c_cmd_ready)source_requests<=source_requests+1'b1;
    if(c_rsp_valid&&c_rsp_ready&&c_rsp_err)fault<=1;
    if(field_take&&kind==0)begin
     bias[{load_group[0],field_index[3:0]}]<=field_data[31:0];
     if(field_index==0)buffer_free[load_group[0]]<=0;
    end
    if(field_take&&kind==1)begin
     scale[{load_group[0],field_index[3:0]}]<=field_data[9:0];
     if(field_data[3:0]==0||field_data[9:4]>38)fault<=1;
    end
    if(xload&&field_index>=1216&&field_data[59:48]!=0)fault<=1;
    if(memory_read)begin
     first_delayed<=read_feature==0;last_delayed<=read_feature==31;tile_delayed<={2'd0,mac_group,tile_row};
     if(read_feature==31)state<=S_DRAIN;else read_feature<=read_feature+1'b1;
    end
    if(xvalid&&wvalid)begin
     for(n=0;n<10;n=n+1)fx[fp][n*12+:12]<=xp[n*13+:12];
     fw[fp]<=wp;ff[fp]<=first_delayed;fl[fp]<=last_delayed;ft[fp]<=tile_delayed;fp<=!fp;
    end
    if(issue_pop)begin
     fh<=!fh;
     if(fl[fh])begin
      if(tile_row==19)state<=S_GROUP;
      else begin state<=S_NEXT;tile_row<=tile_row+1'b1;end
     end
    end
    case({xvalid&&wvalid,issue_pop})2'b10:fcount<=fcount+1'b1;2'b01:fcount<=fcount-1'b1;default:begin end endcase
    if(state==S_WAIT&&rows_ready[tile_row]&&weights_ready[mac_group[0]])begin
     state<=S_ALPHA;alpha_active<=1;alpha_target_next<=0;alpha_target_tile<=tile_row;alpha_requested<=0;alpha_received<=0;
    end
    if(alpha_fire)begin alpha_return_index<=alpha_requested[2:0];alpha_requested<=alpha_requested+1'b1;end
    if(alpha_valid)begin
     if(alpha_target_next)next_alpha[alpha_return_index*29+:29]<=alpha_data[28:0];
     else alpha_x[alpha_return_index*29+:29]<=alpha_data[28:0];
    end
    if(alpha_pad)begin
     if(alpha_target_next)next_alpha[4*29+:29]<=0;else alpha_x[4*29+:29]<=0;
     alpha_requested<=5;
    end
    if(alpha_active&&alpha_increment!=0)begin
     alpha_received<=alpha_received+alpha_increment;
     if(alpha_received+alpha_increment==5)begin
      if(alpha_target_next)begin alpha_active<=0;next_alpha_valid<=1;end
      else begin
       state<=S_MAC;read_feature<=0;alpha_target_next<=1;alpha_target_tile<=tile_row==19?5'd0:tile_row+1'b1;
       alpha_requested<=0;alpha_received<=0;alpha_active<=!(mac_group==15&&tile_row==19);next_alpha_valid<=0;
      end
     end
    end
    if(state==S_NEXT&&next_alpha_valid&&alpha_target_tile==tile_row&&rows_ready[tile_row]&&weights_ready[mac_group[0]])begin
     alpha_x<=next_alpha;state<=S_MAC;read_feature<=0;next_alpha_valid<=0;
     alpha_target_next<=1;alpha_target_tile<=tile_row==19?5'd0:tile_row+1'b1;
     alpha_requested<=0;alpha_received<=0;alpha_active<=!(mac_group==15&&tile_row==19);
    end
    if(raw_take)begin
     if(raw_last_pair)raw_index<=0;else raw_index<=raw_index+7'd2;
     if(raw_frame_end)begin
      buffer_free[mac_group[0]]<=1;
      if(mac_group==15)state<=S_FINISH;
      else begin mac_group<=mac_group+1'b1;tile_row<=0;state<=S_NEXT;end
     end
    end
    if(write_fire)begin
     result_words<=result_words+1'b1;
     if(matrix_last)begin if(frames_sent==15)final_sent<=1;else frames_sent<=frames_sent+1'b1;end
    end
    case({write_fire,response_fire})2'b10:pending_writes<=pending_writes+1'b1;2'b01:pending_writes<=pending_writes-1'b1;default:begin end endcase
    if(response_fire&&b_rsp_err)fault<=1;
    if(x_fault||kernel_fault||quant_fault||matrix_fault)fault<=1;
    if(final_sent&&pending_writes==0)begin busy<=0;done<=1;end
   end
  end
 end
`ifndef SYNTHESIS
 always @(posedge clk)if(running)begin
  if(wqcount>4)$fatal(1,"R5 W queue overflow");
  if(done&&wqcount!=0)$fatal(1,"R5 incomplete W drain");
  if(xvalid!==wvalid)$fatal(1,"Mismatched X/W read pipelines");
  if(xvalid&&fcount==2&&!issue_pop)$fatal(1,"SRAM pair FIFO overwrite");
  if(fcount>2)$fatal(1,"SRAM pair FIFO overflow");
  if(response_fire&&pending_writes==0)$fatal(1,"Output response without command");
  if(kernel_valid&&kernel_tile[8:5]!=mac_group)$fatal(1,"Column correction context replaced too early");
  if(raw_take&&raw_frame_end&&state!=S_GROUP)$fatal(1,"Group context released before input complete");
  if(done&&(!source_done||source_requests!=8168||result_words!=12672))$fatal(1,"Task completed before full source decoding");
 end
`endif
endmodule
