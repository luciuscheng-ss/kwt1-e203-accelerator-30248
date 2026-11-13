`timescale 1ns/1ps
// Exact signed12 MAC plus four reused multiplier lanes for AlphaX/AlphaW.
// Correction inputs are hardware-maintained bias-AlphaW, selected for out_tile
// and held by the caller until that tile is consumed. No copied column context.
module kwt_kernel11_aux(
 input wire clk,rst_n,issue_valid,issue_first,issue_last,output wire issue_ready,
 input wire [95:0] x_pair,input wire [383:0] w_pair,input wire [115:0] alpha_x,
 input wire [527:0] correction,input wire [10:0] tile_id,
 input wire aux_valid,output wire aux_ready,input wire [95:0] aux_pairs,input wire [11:0] aux_tag,
 output wire aux_out_valid,output wire [103:0] aux_products,output wire [11:0] aux_out_tag,
 output reg out_valid,input wire out_ready,output reg [10:0] out_tile,
 input wire [5:0] out_index,output wire signed [32:0] out_raw,out_raw_next,output reg fault
);
 reg valid_sum,first_sum,last_sum,valid_product,first_product,last_product,aux_sum,aux_product;
 reg [11:0] tag_sum,tag_product;
 reg signed [11:0] sa[0:63],sb[0:63];reg signed [23:0] product[0:63];
 reg signed [28:0] acc[0:63],retired[0:63];
 reg [115:0] ax_pending,ax_retired;reg [10:0] tile_pending;
 wire step=!(valid_product&&last_product&&out_valid&&!out_ready);
 assign issue_ready=step;assign aux_ready=step&&!issue_valid;
 wire aux_accept=aux_valid&&aux_ready;
 wire sum_clk,small_sum_clk,product_clk,small_product_clk,acc_clk,retire_clk,context_clk;
 kwt_aux_gate11 gs(.clk(clk),.enable(step&&issue_valid),.gclk(sum_clk));
 kwt_aux_gate11 gsa(.clk(clk),.enable(step&&(issue_valid||aux_accept)),.gclk(small_sum_clk));
 kwt_aux_gate11 gp(.clk(clk),.enable(step&&valid_sum),.gclk(product_clk));
 kwt_aux_gate11 gpa(.clk(clk),.enable(step&&(valid_sum||aux_sum)),.gclk(small_product_clk));
 kwt_aux_gate11 ga(.clk(clk),.enable(step&&valid_product),.gclk(acc_clk));
 kwt_aux_gate11 gr(.clk(clk),.enable(step&&valid_product&&last_product),.gclk(retire_clk));
 kwt_aux_gate11 gc(.clk(clk),.enable(step&&issue_valid&&issue_last),.gclk(context_clk));
 genvar n;
 generate for(n=0;n<64;n=n+1)begin:lanes
  wire signed [10:0] xe=x_pair[(n/16)*24+:11],xo=x_pair[(n/16)*24+12+:11];
  wire signed [10:0] we=w_pair[(n%16)*24+:11],wo=w_pair[(n%16)*24+12+:11];
  wire signed [11:0] a=$signed({xe[10],xe})+$signed({wo[10],wo}),b=$signed({xo[10],xo})+$signed({we[10],we});
  wire signed [28:0] term={{5{product[n][23]}},product[n]};
  wire signed [28:0] completed=first_product?term:acc[n]+term;
  if(n<4)begin:shared
   wire signed [10:0] ae=aux_pairs[n*24+:11],ao=aux_pairs[n*24+12+:11];
   always @(posedge small_sum_clk)begin sa[n]<=aux_accept?$signed({ae[10],ae}):a;sb[n]<=aux_accept?$signed({ao[10],ao}):b;end
   always @(posedge small_product_clk)product[n]<=sa[n]*sb[n];
   assign aux_products[n*26+:26]={{2{product[n][23]}},product[n]};
  end else begin:ordinary
   always @(posedge sum_clk)begin sa[n]<=a;sb[n]<=b;end
   always @(posedge product_clk)product[n]<=sa[n]*sb[n];
  end
  always @(posedge acc_clk)acc[n]<=completed;
  always @(posedge retire_clk)retired[n]<=completed;
 end endgenerate
 wire signed [32:0] raw[0:1];
 generate for(n=0;n<2;n=n+1)begin:outputs
  wire [5:0] index=out_index+6'(n);
  wire signed [28:0] p=retired[index];wire signed [28:0] ax=ax_retired[index[5:4]*29+:29];
  wire signed [32:0] c=correction[index[3:0]*33+:33];
  assign raw[n]=$signed({{4{p[28]}},p})-$signed({{4{ax[28]}},ax})+c;
 end endgenerate
 assign out_raw=raw[0];assign out_raw_next=raw[1];
 assign aux_out_valid=step&&aux_product;assign aux_out_tag=tag_product;
 always @(posedge context_clk)begin ax_pending<=alpha_x;tile_pending<=tile_id;end
 always @(posedge retire_clk)ax_retired<=ax_pending;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   valid_sum<=0;valid_product<=0;first_sum<=0;last_sum<=0;first_product<=0;last_product<=0;
   aux_sum<=0;aux_product<=0;tag_sum<=0;tag_product<=0;out_valid<=0;out_tile<=0;fault<=0;
  end else begin
   if(step)begin
    valid_sum<=issue_valid;valid_product<=valid_sum;aux_sum<=aux_accept;aux_product<=aux_sum;
    if(issue_valid)begin first_sum<=issue_first;last_sum<=issue_last;end
    if(valid_sum)begin first_product<=first_sum;last_product<=last_sum;end
    if(aux_accept)tag_sum<=aux_tag;if(aux_sum)tag_product<=tag_sum;
   end
   if(out_valid&&out_ready)out_valid<=0;
   if(step&&valid_product&&last_product)begin out_valid<=1;out_tile<=tile_pending;end
  end
 end
endmodule
module kwt_aux_gate11(input wire clk,enable,output wire gclk);
`ifdef SYNTHESIS
 CLKLANAQV4_12TR40 physical_gate(.CK(clk),.E(enable),.TE(1'b0),.Q(gclk));
`elsif KWT_NATIVE_GATES
 // Native-model RTL verification keeps all non-synthesis assertions enabled.
 CLKLANAQV4_12TR40 physical_gate(.CK(clk),.E(enable),.TE(1'b0),.Q(gclk));
`else
 reg held;always_latch if(!clk)held<=enable;assign gclk=clk&&held;
`endif
endmodule
