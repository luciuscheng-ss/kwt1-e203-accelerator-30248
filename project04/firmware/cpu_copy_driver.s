/* Existing-platform CPU scheduler for front-door SystemBus task loading.
 * Program initialization is once-only. No task data, GEMM/Alpha or expected
 * output is in ITCM/DTCM. All numerical source words are written to shared SRAM
 * by the testbench access adapter, using the existing SystemBus interface.
 * GPIOA: bit0 task doorbell, bit2 stream mode. Loading completion uses existing externalIRQ.
 * GPIOB bit0 boot ready; value3 means configured/armed and waiting for loader.
 */
.section .text
.globl _start
_start:
 li t0,0x10040000
 li t1,-1
 sw t1,0(t0)
 li t1,1
 sw t1,8(t0)
 li t0,0x10012000
 sw zero,0(t0)
wait_task:
 lw t1,4(t0)
 andi t2,t1,1
 beqz t2,wait_task
 li s1,0
 li t0,0xa0080000
 lw t1,40(t0)
 li t2,0x0b0b0d16
 bne t1,t2,failure
 li t1,0xa0000000
 sw t1,4(t0)
 li t1,0xa0040000
 sw t1,8(t0)
 sw s1,44(t0)
 beqz s1,signal_loader
 li t1,1
 sw t1,0(t0)
signal_loader:
 /* MEIE enables WFI wakeup; global MIE stays clear, so no trap/ISR substitutes
  * the real driver's continuation. Existing platform TB external IRQ wakes it. */
 li t1,0x800
 csrs mie,t1
 csrci mstatus,8
 li t0,0x10040000
 li t1,3
 sw t1,8(t0)
wait_loaded:
 wfi
 li t1,0x800
 csrc mie,t1
 li t0,0xa0080000
 bnez s1,poll
 li t1,1
 sw t1,0(t0)
poll:
 lw t1,12(t0)
 andi t2,t1,4
 bnez t2,failure
 andi t2,t1,2
 beqz t2,poll
 lw s3,24(t0)
 beqz s3,failure
 li t1,12672
 bne s3,t1,failure
 addi t1,s3,-1
 slli t1,t1,2
 li t2,0xa0040000
 add t2,t2,t1
 lw t3,0(t2)
 li t2,0x10040000
 sw t3,8(t2)
 sw zero,0(t0)
success:
 j success
failure:
 li t0,0xa0080000
 li t1,2
 sw t1,0(t0)
 j failure
