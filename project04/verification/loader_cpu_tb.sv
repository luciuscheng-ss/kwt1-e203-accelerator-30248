`timescale 1ns/1fs
`include "dual_params.vh"
`include "cpu_params.vh"
module native_cpu_tb;
 reg clk=0,lfclk=0,rst_n=0;
 always #(10.0/3.0) clk=~clk;
 always #15258.7890625 lfclk=~lfclk;
 reg [31:0] gpio_a=0;wire [31:0] gpio_b,gpio_b_oe;
 e203_soc_top u_soc(
  .hfextclk(clk),.lfextclk(lfclk),
  .io_pads_aon_erst_n_i_ival(rst_n),
  .io_pads_dbgmode0_n_i_ival(1'b1),.io_pads_dbgmode1_n_i_ival(1'b1),.io_pads_dbgmode2_n_i_ival(1'b1),
  .io_pads_bootrom_n_i_ival(1'b0),.io_pads_aon_pmu_dwakeup_n_i_ival(1'b1),
  .io_pads_jtag_TCK_i_ival(1'b0),.io_pads_jtag_TMS_i_ival(1'b1),.io_pads_jtag_TDI_i_ival(1'b1),
  .io_pads_gpioA_i_ival(gpio_a),.io_pads_gpioB_i_ival(32'b0),
  .io_pads_gpioB_o_oval(gpio_b),.io_pads_gpioB_o_oe(gpio_b_oe),
  .io_pads_qspi0_dq_0_i_ival(1'b1),.io_pads_qspi0_dq_1_i_ival(1'b1),
  .io_pads_qspi0_dq_2_i_ival(1'b1),.io_pads_qspi0_dq_3_i_ival(1'b1)
 );
 localparam WORDS=8168;
 reg [63:0] firmware[0:`CPU_CODE_WORDS-1];reg [31:0] sources[0:`TEST_CASES*WORDS-1];
 reg [32:0] gold_raw[0:`TEST_CASES*25344-1];reg [13:0] gold_codes[0:`TEST_CASES*25344-1];
 reg [31:0] gold_words[0:`MATRIX_TOTAL-1],word_counts[0:`TEST_CASES-1];
 reg [11:0] boot_addr=0;reg [63:0] boot_data=0;
 reg [12:0] stage_addr=0;reg [31:0] stage_data=0;
 integer caseno=0,mode=0,offset=0,cycle=0,first_cycle=-1,last_ack=-1;
 reg matrix_seen[0:12671];
 integer raw_at=0,quant_at=0,out_at=0,ack_at=0,src_w=0,src_r=0,starts=0,staged=0;
 reg h_active=0,h_valid=0,h_ready=1;reg [31:0] h_addr=0,h_data=0;
 integer h_sent=0,h_acked=0,h_gap=0,h_delay=0,h_rsp_gap=0,h_rsp_cycle=0,cpu_wait_instructions=0,cpu_data_tcm_accesses=0,cpu_wfi_host_cycles=0;
 reg h_fire=0;
 reg measuring=0,finished=0;integer driver_submit_cycle=-1,driver_ack_cycle=-1;integer fd;string vcd_file;
 real window_start_ns=-1,window_end_ns=-1;
 always @(negedge clk)if(measuring&&ack_at==word_counts[caseno]&&window_end_ns<0)window_end_ns=$realtime;
 `include "native_cpu_bindings.svh"
 `define MAIN u_soc.u_e203_subsys_top.u_e203_subsys_main
 `define AI `MAIN.u_kwt_systembus
 `define CORE `MAIN.u_e203_cpu_top.u_e203_cpu.u_e203_core
 `define BIU `CORE.u_e203_biu
 `define CPU_RSP_QUIESCE `BIU.u_biu_icb_splt.i_icb_rsp_valid
 `define CPU_TOP `MAIN.u_e203_cpu_top
 `include "result_readback82.svh"
 `include "dump_scopes.svh"
 // Observe accepted transactions at every merge and the unchanged original split.
 icb_channel_audit #(.MAX_OUTS(8)) audit_dma_reads(.clk(clk),.rst_n(u_soc.kwt_sysmem_rst_n),.enable(measuring),
  .cmd_valid(`AI.source_buffer.m_cmd_valid),
  .cmd_ready(`AI.source_buffer.m_cmd_ready),
  .cmd_read(1'b1),
  .cmd_addr(`AI.source_buffer.m_cmd_addr),
  .cmd_wdata(32'd0),
  .cmd_wmask(4'd0),
  .rsp_valid(`AI.source_buffer.m_rsp_valid),
  .rsp_ready(`AI.source_buffer.m_rsp_ready),
  .rsp_rdata(`AI.source_buffer.m_rsp_data),
  .rsp_err(`AI.source_buffer.m_rsp_err));
 icb_channel_audit #(.MAX_OUTS(8)) audit_dma_writes(.clk(clk),.rst_n(u_soc.kwt_sysmem_rst_n),.enable(measuring),
  .cmd_valid(`AI.dma_arbiter.b_cmd_valid),
  .cmd_ready(`AI.dma_arbiter.b_cmd_ready),
  .cmd_read(`AI.dma_arbiter.b_cmd_read),
  .cmd_addr(`AI.dma_arbiter.b_cmd_addr),
  .cmd_wdata(`AI.dma_arbiter.b_cmd_wdata),
  .cmd_wmask(`AI.dma_arbiter.b_cmd_wmask),
  .rsp_valid(`AI.dma_arbiter.b_rsp_valid),
  .rsp_ready(`AI.dma_arbiter.b_rsp_ready),
  .rsp_rdata(`AI.dma_arbiter.b_rsp_rdata),
  .rsp_err(`AI.dma_arbiter.b_rsp_err));
 icb_channel_audit #(.MAX_OUTS(8)) audit_dma_merged(.clk(clk),.rst_n(u_soc.kwt_sysmem_rst_n),.enable(measuring),
  .cmd_valid(`AI.dma_arbiter.m_cmd_valid),
  .cmd_ready(`AI.dma_arbiter.m_cmd_ready),
  .cmd_read(`AI.dma_arbiter.m_cmd_read),
  .cmd_addr(`AI.dma_arbiter.m_cmd_addr),
  .cmd_wdata(`AI.dma_arbiter.m_cmd_wdata),
  .cmd_wmask(`AI.dma_arbiter.m_cmd_wmask),
  .rsp_valid(`AI.dma_arbiter.m_rsp_valid),
  .rsp_ready(`AI.dma_arbiter.m_rsp_ready),
  .rsp_rdata(`AI.dma_arbiter.m_rsp_rdata),
  .rsp_err(`AI.dma_arbiter.m_rsp_err));
 icb_channel_audit #(.MAX_OUTS(8)) audit_cpu_dma_merged(.clk(clk),.rst_n(u_soc.kwt_sysmem_rst_n),.enable(measuring),
  .cmd_valid(`AI.arbiter.m_cmd_valid),
  .cmd_ready(`AI.arbiter.m_cmd_ready),
  .cmd_read(`AI.arbiter.m_cmd_read),
  .cmd_addr(`AI.arbiter.m_cmd_addr),
  .cmd_wdata(`AI.arbiter.m_cmd_wdata),
  .cmd_wmask(`AI.arbiter.m_cmd_wmask),
  .rsp_valid(`AI.arbiter.m_rsp_valid),
  .rsp_ready(`AI.arbiter.m_rsp_ready),
  .rsp_rdata(`AI.arbiter.m_rsp_rdata),
  .rsp_err(`AI.arbiter.m_rsp_err));
 icb_channel_audit #(.MAX_OUTS(1)) audit_original_split(.clk(clk),.rst_n(u_soc.kwt_sysmem_rst_n),.enable(measuring),
  .cmd_valid(`MAIN.u_e203_subsys_mems.u_sirv_mem_fab.buf_icb_cmd_valid),
  .cmd_ready(`MAIN.u_e203_subsys_mems.u_sirv_mem_fab.buf_icb_cmd_ready),
  .cmd_read(`MAIN.u_e203_subsys_mems.u_sirv_mem_fab.buf_icb_cmd_read),
  .cmd_addr(`MAIN.u_e203_subsys_mems.u_sirv_mem_fab.buf_icb_cmd_addr),
  .cmd_wdata(`MAIN.u_e203_subsys_mems.u_sirv_mem_fab.buf_icb_cmd_wdata),
  .cmd_wmask(`MAIN.u_e203_subsys_mems.u_sirv_mem_fab.buf_icb_cmd_wmask),
  .rsp_valid(`MAIN.u_e203_subsys_mems.u_sirv_mem_fab.buf_icb_rsp_valid),
  .rsp_ready(`MAIN.u_e203_subsys_mems.u_sirv_mem_fab.buf_icb_rsp_ready),
  .rsp_rdata(`MAIN.u_e203_subsys_mems.u_sirv_mem_fab.buf_icb_rsp_rdata),
  .rsp_err(`MAIN.u_e203_subsys_mems.u_sirv_mem_fab.buf_icb_rsp_err));
 icb_channel_audit #(.MAX_OUTS(1)) audit_shared_port(.clk(clk),.rst_n(u_soc.kwt_sysmem_rst_n),.enable(measuring),
  .cmd_valid(u_soc.sysmem_icb_cmd_valid),
  .cmd_ready(u_soc.sysmem_icb_cmd_ready),
  .cmd_read(u_soc.sysmem_icb_cmd_read),
  .cmd_addr(u_soc.sysmem_icb_cmd_addr),
  .cmd_wdata(u_soc.sysmem_icb_cmd_wdata),
  .cmd_wmask(u_soc.sysmem_icb_cmd_wmask),
  .rsp_valid(u_soc.sysmem_icb_rsp_valid),
  .rsp_ready(u_soc.sysmem_icb_rsp_ready),
  .rsp_rdata(u_soc.sysmem_icb_rsp_rdata),
  .rsp_err(u_soc.sysmem_icb_rsp_err));

 icb_arbiter_owner_audit audit_owner_dma(.clk(clk),.rst_n(u_soc.kwt_sysmem_rst_n),.enable(measuring),
  .a_cmd_valid(`AI.dma_arbiter.a_cmd_valid),
  .a_cmd_ready(`AI.dma_arbiter.a_cmd_ready),
  .a_cmd_read(`AI.dma_arbiter.a_cmd_read),
  .a_cmd_addr(`AI.dma_arbiter.a_cmd_addr),
  .a_cmd_wdata(`AI.dma_arbiter.a_cmd_wdata),
  .a_cmd_wmask(`AI.dma_arbiter.a_cmd_wmask),
  .a_rsp_valid(`AI.dma_arbiter.a_rsp_valid),
  .a_rsp_ready(`AI.dma_arbiter.a_rsp_ready),
  .a_rsp_rdata(`AI.dma_arbiter.a_rsp_rdata),
  .a_rsp_err(`AI.dma_arbiter.a_rsp_err),
  .b_cmd_valid(`AI.dma_arbiter.b_cmd_valid),
  .b_cmd_ready(`AI.dma_arbiter.b_cmd_ready),
  .b_cmd_read(`AI.dma_arbiter.b_cmd_read),
  .b_cmd_addr(`AI.dma_arbiter.b_cmd_addr),
  .b_cmd_wdata(`AI.dma_arbiter.b_cmd_wdata),
  .b_cmd_wmask(`AI.dma_arbiter.b_cmd_wmask),
  .b_rsp_valid(`AI.dma_arbiter.b_rsp_valid),
  .b_rsp_ready(`AI.dma_arbiter.b_rsp_ready),
  .b_rsp_rdata(`AI.dma_arbiter.b_rsp_rdata),
  .b_rsp_err(`AI.dma_arbiter.b_rsp_err),
  .m_cmd_valid(`AI.dma_arbiter.m_cmd_valid),
  .m_cmd_ready(`AI.dma_arbiter.m_cmd_ready),
  .m_cmd_read(`AI.dma_arbiter.m_cmd_read),
  .m_cmd_addr(`AI.dma_arbiter.m_cmd_addr),
  .m_cmd_wdata(`AI.dma_arbiter.m_cmd_wdata),
  .m_cmd_wmask(`AI.dma_arbiter.m_cmd_wmask),
  .m_rsp_valid(`AI.dma_arbiter.m_rsp_valid),
  .m_rsp_ready(`AI.dma_arbiter.m_rsp_ready),
  .m_rsp_rdata(`AI.dma_arbiter.m_rsp_rdata),
  .m_rsp_err(`AI.dma_arbiter.m_rsp_err));
 icb_arbiter_owner_audit audit_owner_cpu_dma(.clk(clk),.rst_n(u_soc.kwt_sysmem_rst_n),.enable(measuring),
  .a_cmd_valid(`AI.arbiter.a_cmd_valid),
  .a_cmd_ready(`AI.arbiter.a_cmd_ready),
  .a_cmd_read(`AI.arbiter.a_cmd_read),
  .a_cmd_addr(`AI.arbiter.a_cmd_addr),
  .a_cmd_wdata(`AI.arbiter.a_cmd_wdata),
  .a_cmd_wmask(`AI.arbiter.a_cmd_wmask),
  .a_rsp_valid(`AI.arbiter.a_rsp_valid),
  .a_rsp_ready(`AI.arbiter.a_rsp_ready),
  .a_rsp_rdata(`AI.arbiter.a_rsp_rdata),
  .a_rsp_err(`AI.arbiter.a_rsp_err),
  .b_cmd_valid(`AI.arbiter.b_cmd_valid),
  .b_cmd_ready(`AI.arbiter.b_cmd_ready),
  .b_cmd_read(`AI.arbiter.b_cmd_read),
  .b_cmd_addr(`AI.arbiter.b_cmd_addr),
  .b_cmd_wdata(`AI.arbiter.b_cmd_wdata),
  .b_cmd_wmask(`AI.arbiter.b_cmd_wmask),
  .b_rsp_valid(`AI.arbiter.b_rsp_valid),
  .b_rsp_ready(`AI.arbiter.b_rsp_ready),
  .b_rsp_rdata(`AI.arbiter.b_rsp_rdata),
  .b_rsp_err(`AI.arbiter.b_rsp_err),
  .m_cmd_valid(`AI.arbiter.m_cmd_valid),
  .m_cmd_ready(`AI.arbiter.m_cmd_ready),
  .m_cmd_read(`AI.arbiter.m_cmd_read),
  .m_cmd_addr(`AI.arbiter.m_cmd_addr),
  .m_cmd_wdata(`AI.arbiter.m_cmd_wdata),
  .m_cmd_wmask(`AI.arbiter.m_cmd_wmask),
  .m_rsp_valid(`AI.arbiter.m_rsp_valid),
  .m_rsp_ready(`AI.arbiter.m_rsp_ready),
  .m_rsp_rdata(`AI.arbiter.m_rsp_rdata),
  .m_rsp_err(`AI.arbiter.m_rsp_err));
 // Testbench transaction agent at the original CPU MEM/SystemBus interface.
 // CPU enters architectural WFI before ownership; no response signal is masked.
 // Parameterized loader response backpressure; default0 is the nominal performance ingress.
 always @(negedge clk)begin
  if(h_active&&h_rsp_gap>0)begin
   if(h_rsp_cycle>=h_rsp_gap)begin h_ready=1;h_rsp_cycle=0;end
   else begin h_ready=0;h_rsp_cycle=h_rsp_cycle+1;end
  end else begin h_ready=1;h_rsp_cycle=0;end
 end
 integer cpu_mem_outstanding=0;
 always @(posedge clk)begin
  if(!rst_n)cpu_mem_outstanding=0;
  else begin
   case({`AI.u_cmd_valid&&`AI.u_cmd_ready,`AI.u_rsp_valid&&`AI.u_rsp_ready})
    2'b10:cpu_mem_outstanding=cpu_mem_outstanding+1;
    2'b01:cpu_mem_outstanding=cpu_mem_outstanding-1;
    default:begin end
   endcase
   if(cpu_mem_outstanding<0||cpu_mem_outstanding>16)$fatal(1,"CPU/MEM outstanding ledger");
  end
 end
 task seize_loading_boundary;begin
  if (`CPU_TOP.core_wfi!==1||`BIU.arbt_icb_cmd_valid!==0||`MAIN.mem_icb_cmd_valid!==0||cpu_mem_outstanding!=0||`AI.u_rsp_valid!==1'b0)
   $fatal(1,"Existing MEM boundary is not idle at loader ownership handoff");
  h_active=1;
  force `CPU_TOP.mem_icb_cmd_valid=h_valid;force `CPU_TOP.mem_icb_cmd_read=1'b0;
  force `CPU_TOP.mem_icb_cmd_addr=h_addr;force `CPU_TOP.mem_icb_cmd_wdata=h_data;force `CPU_TOP.mem_icb_cmd_wmask=4'hf;
  force `CPU_TOP.mem_icb_rsp_ready=h_ready;
  // Original response path remains live. Only the idle master outputs are driven.
 end endtask
 task release_loading_boundary;begin
  if(h_sent!=WORDS||h_acked!=WORDS||cpu_mem_outstanding!=0||`AI.u_rsp_valid!==1'b0)
   $fatal(1,"Loader ownership released with pending transaction");
  release `CPU_TOP.mem_icb_cmd_valid;release `CPU_TOP.mem_icb_cmd_read;release `CPU_TOP.mem_icb_cmd_addr;
  release `CPU_TOP.mem_icb_cmd_wdata;release `CPU_TOP.mem_icb_cmd_wmask;release `CPU_TOP.mem_icb_rsp_ready;
  h_active=0;
 end endtask
 always @(posedge `CORE.clk_core_ifu)if(h_active&&`CORE.ifu_o_valid&&`CORE.ifu_o_ready)begin
  cpu_wait_instructions=cpu_wait_instructions+1;$fatal(1,"CPU instruction executed while loader owns MEM interface");
 end
 always @(posedge clk)begin
  h_fire=0;
  if(measuring&&`DC.ram_cs!==0)begin cpu_data_tcm_accesses=cpu_data_tcm_accesses+1;$fatal(1,"Task data unexpectedly accessed DTCM");end
  if(h_active)begin
   if(`CPU_TOP.core_wfi!==1||`BIU.arbt_icb_cmd_valid!==0)$fatal(1,"CPU not quiescent during loading ownership");
   cpu_wfi_host_cycles=cpu_wfi_host_cycles+1;
   if(h_valid&&`AI.u_cmd_ready)begin
    if(h_sent>=WORDS||h_addr!==32'ha0000000+4*h_sent||h_data!==sources[caseno*WORDS+h_sent])$fatal(1,"Loader command sequence mismatch");
    h_sent=h_sent+1;h_fire=1;
   end
   if(`AI.u_rsp_valid&&h_ready)begin
    if(`AI.u_rsp_err||h_acked>=h_sent)$fatal(1,"Loader response error or unowned response");
    h_acked=h_acked+1;
   end
  end
 end
 always @(posedge clk)begin
  cycle=cycle+1;
  if(cycle>2500000)$fatal(1,"CPU SoC timeout ready=%b reset=%b sourceW=%0d sourceR=%0d raw=%0d start=%0d",gpio_b[0],`IC.rst_n,src_w,src_r,raw_at,starts);
  if(measuring&&cycle-first_cycle>200000)$fatal(1,"Cold watchdog sent=%0d ack=%0d source=%0d raw=%0d out=%0d wfi=%b",h_sent,h_acked,src_w,raw_at,ack_at,`CPU_TOP.core_wfi);
  if(measuring&&(cycle-first_cycle)%20000==0)begin $display("COLD_PROGRESS elapsed=%0d sent=%0d ack=%0d source=%0d raw=%0d output=%0d wfi=%b",cycle-first_cycle,h_sent,h_acked,src_w,raw_at,ack_at,`CPU_TOP.core_wfi);$fflush();end
  if(measuring)begin
   if(`MAIN.kwt_fault)$fatal(1,"CPU engine fault");
   if(u_soc.sysmem_icb_cmd_valid&&u_soc.sysmem_icb_cmd_ready&&u_soc.sysmem_icb_cmd_addr>=32'ha0000000&&u_soc.sysmem_icb_cmd_addr<32'ha0000000+4*WORDS)begin
    if(u_soc.sysmem_icb_cmd_read)src_r=src_r+1;
    else begin
     if(src_w>=WORDS||u_soc.sysmem_icb_cmd_addr!==32'ha0000000+4*src_w||u_soc.sysmem_icb_cmd_wdata!==sources[caseno*WORDS+src_w])$fatal(1,"CPU physical source write mismatch index=%0d",src_w);
     src_w=src_w+1;
    end
   end
   if(`AI.engine.kernel_valid&&`AI.engine.quant_ready)begin
    if(raw_at>=25344||`AI.engine.raw_even!==$signed(gold_raw[caseno*25344+raw_at])||`AI.engine.raw_odd!==$signed(gold_raw[caseno*25344+raw_at+1]))$fatal(1,"CPU native raw mismatch index=%0d",raw_at);
    raw_at=raw_at+2;
   end
   if(`AI.engine.quant_valid&&`AI.engine.quant_out_ready)begin
    if(quant_at>=25344||`AI.engine.quant_codes[13:0]!==gold_codes[caseno*25344+quant_at]||`AI.engine.quant_codes[27:14]!==gold_codes[caseno*25344+quant_at+1])$fatal(1,"CPU native quant mismatch index=%0d",quant_at);
    quant_at=quant_at+2;
   end
   if(`AI.b_cmd_valid&&`AI.b_cmd_ready)begin
    if(out_at>=12672||`AI.b_cmd_addr<32'ha0040000||`AI.b_cmd_addr>=32'ha004c600||`AI.b_cmd_addr[1:0]!=0)$fatal(1,"Fixed matrix address/count");
    if(matrix_seen[(`AI.b_cmd_addr-32'ha0040000)>>2])$fatal(1,"Duplicate matrix output address");
    matrix_seen[(`AI.b_cmd_addr-32'ha0040000)>>2]=1;
    if(`AI.b_cmd_wdata!==gold_words[offset+((`AI.b_cmd_addr-32'ha0040000)>>2)])$fatal(1,"CPU native full matrix mismatch address=%h",`AI.b_cmd_addr);
    out_at=out_at+1;
   end
   // Observe the real arbiter response handshake. Synthesis constant-folds
   // engine.b_rsp_ready and leaves that unused engine output undriven.
   if(`AI.dma_arbiter.b_rsp_valid&&`AI.dma_arbiter.b_rsp_ready)begin
    if(`AI.b_rsp_err)$fatal(1,"CPU native output error");ack_at=ack_at+1;last_ack=cycle;
    if(ack_at==word_counts[caseno])begin
     if(raw_at!=25344||quant_at!=25344||src_w!=WORDS||src_r!=(mode?0:WORDS)||out_at!=ack_at||h_sent!=WORDS||h_acked!=WORDS||cpu_data_tcm_accesses!=0)$fatal(1,"CPU native cold window incomplete");
     $display("CPU_LAST_OUTPUT_ACK case=%0d mode=%0d cycles=%0d loaderACK=%0d srcW=%0d srcR=%0d output=%0d raw=%0d quant=%0d",caseno,mode,last_ack-first_cycle+1,h_acked,src_w,src_r,out_at,raw_at,quant_at);$fflush();
    end
   end
   if(`MAIN.mem_icb_cmd_valid&&`MAIN.mem_icb_cmd_ready&&!`MAIN.mem_icb_cmd_read&&`MAIN.mem_icb_cmd_addr==32'ha0080000)begin
    if(`MAIN.mem_icb_cmd_wdata==2)$fatal(1,"CPU driver failure");
    if(`MAIN.mem_icb_cmd_wdata==1)starts=starts+1;
    if(`MAIN.mem_icb_cmd_wdata==0)begin
     if(starts!=1||ack_at!=word_counts[caseno]||`MAIN.kwt_busy||!`MAIN.kwt_done||gpio_b_oe!==32'hffffffff||gpio_b!==gold_words[offset+word_counts[caseno]-1])$fatal(1,"CPU driver completion incomplete");
     driver_submit_cycle=cycle;finished=1;
    end
   end
  end
 end
 initial begin
  if(!$value$plusargs("CASE=%d",caseno))caseno=0;
  if(!$value$plusargs("MODE=%d",mode))mode=0;
  if(!$value$plusargs("GAP=%d",h_gap))h_gap=0;
  if(!$value$plusargs("RSPGAP=%d",h_rsp_gap))h_rsp_gap=0;
  if(h_rsp_gap<0||h_rsp_gap>31)$fatal(1,"Invalid response backpressure");
  if(caseno<0||caseno>=`TEST_CASES||mode!=0||h_gap<0||h_gap>100)$fatal(1,"Invalid CPU case/mode");
  for(integer k=0;k<12672;k=k+1)matrix_seen[k]=0;
  $readmemh("cpu_copy_driver64.hex",firmware);$readmemh("source.hex",sources);$readmemh("raw.hex",gold_raw);$readmemh("codes.hex",gold_codes);$readmemh("matrix.hex",gold_words);$readmemh("word_counts.hex",word_counts);
  for(integer j=0;j<caseno;j=j+1)offset=offset+word_counts[j];
  if($value$plusargs("VCD=%s",vcd_file))begin $dumpfile(vcd_file);dump_current_scope();$dumpoff;end
  hold_all_tcm_clocks();
  @(negedge clk);begin_itcm_boot();
  for(integer j=0;j<`CPU_CODE_WORDS;j=j+1)begin boot_addr=j;boot_data=firmware[j];@(posedge clk);@(negedge clk);end
  hold_itcm_release_controls();
  repeat(20)@(negedge clk);rst_n=1;
  wait(`IC.rst_n===1'b1);
  repeat(2)begin @(negedge clk);check_itcm_idle();end
  release_itcm_clocks();release_dtcm_clocks();#0.02;check_itcm_clocks_low();check_dtcm_clocks_low();
  wait(gpio_b[0]===1'b1&&gpio_b_oe[0]===1'b1);
  $display("CPU_BOOT_READY cycle=%0d time_ns=%0.3f",cycle,$realtime);$fflush();
  // Both TCM clock/control overrides have ended before the cold window.
  @(negedge clk);measuring=1;first_cycle=cycle+1;window_start_ns=$realtime;
  if(vcd_file!="")$dumpon;
  @(posedge clk);#1.5;gpio_a=1|(mode<<2);
  wait(gpio_b===32'd3&&gpio_b_oe===32'hffffffff);
  wait(`CPU_TOP.core_wfi===1);
  repeat(2)@(negedge clk);
  if(mode&&(!`MAIN.kwt_busy||!`MAIN.kwt_stream_mode))$fatal(1,"Real CPU has not armed stream mode");
  if(!mode&&`MAIN.kwt_busy)$fatal(1,"Preload mode started too early");
  seize_loading_boundary();$display("LOADER_OWNERSHIP_BEGIN cycle=%0d wfi=%b",cycle,`CPU_TOP.core_wfi);$fflush();
  while(h_acked<WORDS)begin
   @(negedge clk);
   if(h_fire)h_delay=h_gap;
   if(h_sent==WORDS)h_valid=0;
   else if(h_delay>0)begin h_valid=0;h_delay=h_delay-1;end
   else begin h_valid=1;h_addr=32'ha0000000+4*h_sent;h_data=sources[caseno*WORDS+h_sent];end
  end
  h_valid=0;
  repeat(2)@(negedge clk);release_loading_boundary();
  if(cpu_wfi_host_cycles<100||cpu_wait_instructions!=0)$fatal(1,"WFI ownership proof incomplete");
  $display("LOADER_OWNERSHIP_END cycle=%0d ack=%0d idle=%0d",cycle,h_acked,cpu_wfi_host_cycles);$fflush();
  // Original platform TB uses the same PLIC external-IRQ net to stimulate CPU.
  force `CPU_TOP.ext_irq_a=1'b1;
  wait(`CPU_TOP.core_wfi===0);repeat(4)@(negedge clk);release `CPU_TOP.ext_irq_a;

  wait(finished);
  begin:drain_final_cpu_response
   integer tries;reg got_response;got_response=0;
   for(tries=0;tries<200;tries=tries+1)begin
    @(posedge clk);
    if(`MAIN.u_e203_cpu_top.mem_icb_rsp_valid&&`MAIN.u_e203_cpu_top.mem_icb_rsp_ready)begin
     if(`MAIN.u_e203_cpu_top.mem_icb_rsp_err)$fatal(1,"Final CPU completion response error");
     got_response=1;break;
    end
   end
   if(!got_response)$fatal(1,"Final CPU completion response timeout");
  end
  @(negedge clk);driver_ack_cycle=cycle;
  repeat(2)@(negedge clk);
  if(vcd_file!="")$dumpoff;
  measuring=0;for(integer k=0;k<12672;k=k+1)if(!matrix_seen[k])$fatal(1,"Missing matrix output word");physical_result_check();
  fd=$fopen("cpu_cycles.csv","w");$fdisplay(fd,"case,mode,cold_cycles,driver_return_cycles,TCM_task_data_words,source_writes,source_reads,output_writes,output_acks,raw_codes,quant_codes,window_start_ns,window_end_ns,physical_pin_readback_words,loader_commands,loader_responses,CPU_instruction_handshakes_while_loader,loader_gap,CPU_WFI_host_cycles,original_split_peak,shared_port_peak,dma_merge_peak,cpu_dma_merge_peak");
  $fdisplay(fd,"%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0.6f,%0.6f,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d,%0d",caseno,mode,last_ack-first_cycle+1,driver_ack_cycle-first_cycle+1,cpu_data_tcm_accesses,src_w,src_r,out_at,ack_at,raw_at,quant_at,window_start_ns,window_end_ns,physical_pin_readback_words,h_sent,h_acked,cpu_wait_instructions,h_gap,cpu_wfi_host_cycles,audit_original_split.peak,audit_shared_port.peak,audit_dma_merged.peak,audit_cpu_dma_merged.peak);$fclose(fd);
  $display("PASS scheduler CPU SystemBus loading sharedSRAM case=%0d mode=%0d raw=%0d quant=%0d outputs=%0d",caseno,mode,raw_at,quant_at,ack_at);$finish;
 end
endmodule

// Protocol observer only. It never drives, forces or changes a DUT signal.
module icb_channel_audit #(parameter integer MAX_OUTS=8)(
 input wire clk,rst_n,enable,cmd_valid,cmd_ready,cmd_read,
 input wire [31:0] cmd_addr,cmd_wdata,input wire [3:0] cmd_wmask,
 input wire rsp_valid,rsp_ready,input wire [31:0] rsp_rdata,input wire rsp_err
);
 integer outstanding=0,peak=0,head=0,tail=0,commands=0,responses=0;
 reg read_queue[0:MAX_OUTS];reg command_stalled=0,response_stalled=0;
 reg [68:0] held_command;reg [32:0] held_response;
 wire [68:0] command_payload={cmd_read,cmd_addr,cmd_read?32'd0:cmd_wdata,cmd_read?4'd0:cmd_wmask};
 wire response_is_read=(outstanding!=0)?read_queue[head]:cmd_read;
 wire [32:0] response_payload={rsp_err,response_is_read?rsp_rdata:32'd0};
 wire push=cmd_valid&&cmd_ready,pop=rsp_valid&&rsp_ready;
 always @(posedge clk)begin
  if(!rst_n)begin outstanding=0;peak=0;head=0;tail=0;commands=0;responses=0;command_stalled=0;response_stalled=0;end
  else if(enable)begin
   if($isunknown({cmd_valid,cmd_ready,rsp_valid,rsp_ready}))$fatal(1,"ICB unknown handshake %m");
   if(command_stalled&&(cmd_valid!==1'b1||command_payload!==held_command))$fatal(1,"ICB command changed under backpressure %m");
   if(response_stalled&&(rsp_valid!==1'b1||response_payload!==held_response))$fatal(1,"ICB response changed under backpressure %m");
   if(cmd_valid&&$isunknown(command_payload))$fatal(1,"ICB unknown meaningful command bits %m");
   if(rsp_valid&&$isunknown(response_payload))$fatal(1,"ICB unknown meaningful response bits %m");
   if(pop&&outstanding==0&&!push)$fatal(1,"ICB response without request %m");
   command_stalled=cmd_valid&&!cmd_ready;response_stalled=rsp_valid&&!rsp_ready;
   held_command=command_payload;held_response=response_payload;
   if(push)begin read_queue[tail]=cmd_read;tail=(tail+1)%(MAX_OUTS+1);commands=commands+1;end
   if(pop)begin head=(head+1)%(MAX_OUTS+1);responses=responses+1;end
   outstanding=outstanding+push-pop;
   if(outstanding<0||outstanding>MAX_OUTS)$fatal(1,"ICB downstream outstanding limit %m count=%0d",outstanding);
   if(outstanding>peak)peak=outstanding;
  end
 end
endmodule

module icb_arbiter_owner_audit(input wire clk,rst_n,enable,
 input wire a_cmd_valid,a_cmd_ready,a_cmd_read,
 input wire [31:0] a_cmd_addr,a_cmd_wdata,
 input wire [3:0] a_cmd_wmask,
 input wire a_rsp_valid,a_rsp_ready,a_rsp_err,
 input wire [31:0] a_rsp_rdata,
 input wire b_cmd_valid,b_cmd_ready,b_cmd_read,
 input wire [31:0] b_cmd_addr,b_cmd_wdata,
 input wire [3:0] b_cmd_wmask,
 input wire b_rsp_valid,b_rsp_ready,b_rsp_err,
 input wire [31:0] b_rsp_rdata,
 input wire m_cmd_valid,m_cmd_ready,m_cmd_read,
 input wire [31:0] m_cmd_addr,m_cmd_wdata,
 input wire [3:0] m_cmd_wmask,
 input wire m_rsp_valid,m_rsp_ready,m_rsp_err,
 input wire [31:0] m_rsp_rdata
);
 integer count=0,head=0,tail=0;reg owner[0:7],is_read[0:7];
 wire af=a_cmd_valid&&a_cmd_ready,bf=b_cmd_valid&&b_cmd_ready;
 wire mf=m_cmd_valid&&m_cmd_ready,rp=m_rsp_valid&&m_rsp_ready;
 wire [68:0] ap={a_cmd_read,a_cmd_addr,a_cmd_read?32'd0:a_cmd_wdata,a_cmd_read?4'd0:a_cmd_wmask};
 wire [68:0] bp={b_cmd_read,b_cmd_addr,b_cmd_read?32'd0:b_cmd_wdata,b_cmd_read?4'd0:b_cmd_wmask};
 wire [68:0] mp={m_cmd_read,m_cmd_addr,m_cmd_read?32'd0:m_cmd_wdata,m_cmd_read?4'd0:m_cmd_wmask};
 always @(posedge clk)begin
  if(!rst_n)begin count=0;head=0;tail=0;end
  else if(enable)begin
   if(af&&bf||mf!==(af||bf))$fatal(1,"Arbiter request grant mismatch %m");
   if(mf&&(mp!==(bf?bp:ap)))$fatal(1,"Arbiter accepted payload differs from owner %m");
   if(m_rsp_valid)begin
    if(count==0)$fatal(1,"Arbiter response has no prior owner %m");
    if(a_rsp_valid!==!owner[head]||b_rsp_valid!==owner[head])$fatal(1,"Arbiter response delivered to wrong owner %m");
    if(m_rsp_ready!==(owner[head]?b_rsp_ready:a_rsp_ready))$fatal(1,"Arbiter ignored response-owner backpressure %m");
    if(owner[head])begin
     if(b_rsp_err!==m_rsp_err||(is_read[head]&&b_rsp_rdata!==m_rsp_rdata))$fatal(1,"Arbiter B response payload %m");
    end else if(a_rsp_err!==m_rsp_err||(is_read[head]&&a_rsp_rdata!==m_rsp_rdata))$fatal(1,"Arbiter A response payload %m");
   end else if(a_rsp_valid||b_rsp_valid)$fatal(1,"Arbiter manufactured response %m");
   if(mf)begin owner[tail]=bf;is_read[tail]=m_cmd_read;tail=(tail+1)%8;end
   if(rp)head=(head+1)%8;
   count=count+mf-rp;
   if(count<0||count>8)$fatal(1,"Arbiter owner queue overflow %m");
  end
 end
endmodule
