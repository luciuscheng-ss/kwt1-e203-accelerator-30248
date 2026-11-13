`timescale 1ns/1fs
`default_nettype none
module uart_equivalence_tb;
 reg clk=0;
 always #3.333333 clk=~clk;
 reg reset_n=1;
 reg [11:0] addr=0;
 reg [31:0] wdata=0;
 reg write=0,sel=0,enable=0,loopback=0;
 wire [31:0] old_read,new_read;
 wire old_ready,new_ready,old_err,new_err,old_tx,new_tx,old_irq,new_irq;
 wire old_rx=loopback ? old_tx : 1'b1;
 wire new_rx=loopback ? new_tx : 1'b1;
 integer cycles=0,checks=0,enqueues=0,full_rejects=0,thr_writes=0,dlab_writes=0;
 integer reads=0,writes=0,consecutive=0,reset_events=0,invalid_differences=0;
 integer tx_edges=0,irq_edges=0,rx_reads=0;
 reg old_tx_last=1,old_irq_last=0;
 reg last_access=0;
 integer last_access_cycle=-100;
 reg [31:0] captured;
 integer i;

 apb_uart_original u_old(.CLK(clk),.RSTN(reset_n),.PADDR(addr),.PWDATA(wdata),.PWRITE(write),
  .PSEL(sel),.PENABLE(enable),.PRDATA(old_read),.PREADY(old_ready),.PSLVERR(old_err),
  .rx_i(old_rx),.tx_o(old_tx),.event_o(old_irq));
 apb_uart_sv u_new(.CLK(clk),.RSTN(reset_n),.PADDR(addr),.PWDATA(wdata),.PWRITE(write),
  .PSEL(sel),.PENABLE(enable),.PRDATA(new_read),.PREADY(new_ready),.PSLVERR(new_err),
  .rx_i(new_rx),.tx_o(new_tx),.event_o(new_irq));

 always @(negedge reset_n) reset_events=reset_events+1;
 always @(posedge clk) begin
  cycles=cycles+1;
  if(cycles>100000) $fatal(1,"UART_EQ watchdog");
  if(reset_n && reset_events>0) begin
   // The only data consumer samples at this edge, before FIFO NBA updates.
   if((^{u_old.fifo_tx_valid,u_new.fifo_tx_valid,u_old.uart_tx_fifo_i.full,u_new.uart_tx_fifo_i.full})===1'bx)
    $fatal(1,"UART_EQ unknown enqueue control");
   if(u_old.fifo_tx_valid!==u_new.fifo_tx_valid || u_old.uart_tx_fifo_i.full!==u_new.uart_tx_fifo_i.full)
    $fatal(1,"UART_EQ enqueue control mismatch");
   if(u_old.fifo_tx_valid !== (sel && enable && write && addr[4:2]==0 && !u_old.regs_q[31]))
    $fatal(1,"UART_EQ valid differs from actual THR/DLAB decode");
   if(u_old.fifo_tx_valid && !u_old.uart_tx_fifo_i.full) begin
    if((^u_old.fifo_tx_data)===1'bx || (^u_new.fifo_tx_data)===1'bx ||
       u_old.fifo_tx_data!==u_new.fifo_tx_data || u_new.fifo_tx_data!==wdata[7:0])
     $fatal(1,"UART_EQ effective enqueue payload mismatch");
    enqueues=enqueues+1;
   end
   if(u_old.fifo_tx_valid && u_old.uart_tx_fifo_i.full) full_rejects=full_rejects+1;
   if(sel && enable) begin
    if((^{old_read,new_read,old_ready,new_ready,old_err,new_err,old_tx,new_tx,old_irq,new_irq})===1'bx ||
       {old_read,old_ready,old_err,old_tx,old_irq}!=={new_read,new_ready,new_err,new_tx,new_irq})
     $fatal(1,"UART_EQ external mismatch at APB sampling edge");
    if(last_access_cycle==cycles-2) consecutive=consecutive+1;
    last_access_cycle=cycles;
    if(write) begin
     writes=writes+1;
     if(addr[4:2]==0 && !u_old.regs_q[31]) thr_writes=thr_writes+1;
     if((addr[4:2]==0 || addr[4:2]==1) && u_old.regs_q[31]) dlab_writes=dlab_writes+1;
    end else begin
     reads=reads+1;
     if(addr[4:2]==0 && !u_old.regs_q[31]) rx_reads=rx_reads+1;
    end
   end
  end
  #1;
  if(reset_events>0) begin
   if((^{old_read,new_read,old_ready,new_ready,old_err,new_err,old_tx,new_tx,old_irq,new_irq})===1'bx)
    $fatal(1,"UART_EQ external X after reset");
   if({old_read,old_ready,old_err,old_tx,old_irq}!=={new_read,new_ready,new_err,new_tx,new_irq})
    $fatal(1,"UART_EQ external mismatch cycle=%0d",cycles);
   if(old_ready!==1'b1 || old_err!==1'b0) $fatal(1,"UART_EQ original APB response contract differs");
   if(u_new.fifo_tx_data!==wdata[7:0]) $fatal(1,"UART_EQ fixed combinational default does not follow PWDATA");
   if(!u_old.fifo_tx_valid && u_old.fifo_tx_data!==u_new.fifo_tx_data) invalid_differences=invalid_differences+1;
   if(old_tx!=old_tx_last) tx_edges=tx_edges+1;
   if(old_irq!=old_irq_last) irq_edges=irq_edges+1;
   old_tx_last=old_tx;old_irq_last=old_irq;
   checks=checks+1;
  end
 end

 task automatic transfer(input reg wr,input reg[2:0] regno,input reg[31:0] data);
  begin
   @(negedge clk);sel=1;enable=0;write=wr;addr={7'b0,regno,2'b00};wdata=data;
   @(negedge clk);enable=1;
   @(posedge clk);#1.5;captured=new_read;
  end
 endtask
 task automatic idle(input integer count);
  integer n;
  begin
   for(n=0;n<count;n=n+1) begin
    @(negedge clk);sel=0;enable=0;write=n[0];addr=n;wdata=32'hcafe0000 ^ (n*73+19);
   end
  end
 endtask
 task automatic reset_uart;
  begin
   @(negedge clk);sel=0;enable=0;write=0;reset_n=0;
   repeat(4) @(negedge clk);
   reset_n=1;
   idle(2);
  end
 endtask
 task automatic configure(input reg[15:0] divisor);
  begin
   transfer(1,3,32'h83); // 8 data bits, DLAB set
   transfer(1,0,{24'h123456,divisor[7:0]});
   transfer(1,1,{24'habcdef,divisor[15:8]});
   transfer(0,0,32'h55);if(captured!=={24'b0,divisor[7:0]}) $fatal(1,"DLL readback");
   transfer(0,1,32'haa);if(captured!=={24'b0,divisor[15:8]}) $fatal(1,"DLM readback");
   transfer(0,3,32'h12);if(captured!==32'h83) $fatal(1,"DLAB LCR readback");
   transfer(1,3,32'h03);
   transfer(1,1,32'h07); // RX, TX and error IRQ enables
   transfer(0,1,32'h99);if(captured!==32'h07) $fatal(1,"IER readback");
  end
 endtask
 initial begin
  reset_uart();
  for(i=0;i<8;i=i+1) transfer(0,i[2:0],32'h44000000+i);
  configure(16'd64);
  // Faster legal APB writes than serial consumption: reach real FIFO full.
  for(i=0;i<48;i=i+1) transfer(1,0,32'hdead0000+(i*29+1));
  idle(2);
  if(full_rejects<16) $fatal(1,"UART_EQ FIFO full coverage missing");
  for(i=0;i<8;i=i+1) transfer(0,i[2:0],32'h77000000+i);
  idle(14000); // naturally drain; no force/override of FIFO or serial readiness
  transfer(0,5,32'h1234);
  if((captured&32'h60)!==32'h60) $fatal(1,"UART_EQ TX did not drain");
  transfer(0,2,0); // read IIR, clear TX-empty interrupt
  for(i=0;i<6;i=i+1) transfer(1,0,32'habcd0080+i);
  transfer(1,2,32'hc6); // clear both FIFOs while serializer may be active
  for(i=0;i<8;i=i+1) transfer(1,i[2:0],32'h80+i);
  reset_uart(); // reset in non-idle TX/FIFO state
  loopback=1;configure(16'd8);
  for(i=0;i<12;i=i+1) transfer(1,0,32'h11110000+(i*17+3));
  idle(2200);
  for(i=0;i<16;i=i+1) begin transfer(0,5,32'h12+i);transfer(0,0,32'h34+i); end
  transfer(1,2,32'h06);
  idle(20);
  reset_uart();configure(16'd2);
  for(i=0;i<8;i=i+1) transfer(1,0,32'hbebe0055+i);
  idle(500);
  @(negedge clk);sel=0;enable=0;
  if(checks<16000 || enqueues<30 || full_rejects<16 || dlab_writes<6 || reads<50 ||
     consecutive<70 || reset_events!=3 || invalid_differences<100 || tx_edges<40 || irq_edges<2 || rx_reads<16)
   $fatal(1,"UART_EQ required coverage missing");
  $display(""); // Original uart_tx prints transmitted bytes without line breaks.
  $display("UART_EQ_RESULT checks=%0d enqueues=%0d full_rejects=%0d thr_writes=%0d dlab_writes=%0d reads=%0d writes=%0d consecutive=%0d resets=%0d invalid_differences=%0d tx_edges=%0d irq_edges=%0d rx_reads=%0d",checks,enqueues,full_rejects,thr_writes,dlab_writes,reads,writes,consecutive,reset_events,invalid_differences,tx_edges,irq_edges,rx_reads);
  $display("PASS: UART valid-enqueue and external transaction equivalence");
  $finish;
 end
endmodule
`default_nettype wire
