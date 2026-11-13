from pathlib import Path
import subprocess,json,hashlib
O=Path(__file__).resolve().parent;R=O.parents[2];B=R/'.tools/extras/usr/bin';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
commands=[[B/'riscv32-linux-gnu-as','-march=rv32im_zicsr','-mabi=ilp32','-o',O/'cpu_copy_driver.o',O/'cpu_copy_driver.s'],[B/'riscv32-linux-gnu-ld','-melf32lriscv','-Ttext=0x80000000','-e','_start','-o',O/'cpu_copy_driver.elf',O/'cpu_copy_driver.o'],[B/'riscv32-linux-gnu-objcopy','-O','binary','--only-section=.text',O/'cpu_copy_driver.elf',O/'cpu_copy_driver.bin']]
assert not(O/'manifest.json').exists()
for c in commands:subprocess.run(list(map(str,c)),check=True)
data=(O/'cpu_copy_driver.bin').read_bytes();words=(len(data)+7)//8;data+=b'\0'*(words*8-len(data));(O/'cpu_copy_driver64.hex').write_text(''.join('%016x\n'%int.from_bytes(data[n:n+8],'little')for n in range(0,len(data),8)));(O/'cpu_params.vh').write_text('`define CPU_CODE_WORDS %d\n'%words)
assert words<4096
files=['cpu_copy_driver.s','cpu_copy_driver.o','cpu_copy_driver.elf','cpu_copy_driver.bin','cpu_copy_driver64.hex','cpu_params.vh','build.py'];r={'scope':'Existing CPU scheduler with architectural WFI/externalIRQ ownership handoff; no TCM task staging or answers. Adapter applicability review pending.','CPU_task_header_words':0,'source_words':8168,'task_staged_words':0,'cpu_code_bytes':len((O/'cpu_copy_driver.bin').read_bytes()),'ITCM64_words':words,'GEMM_Alpha_or_expected_results_in_firmware':False,'accelerator_or_DMA_TCM_data_ports':False,'commands':list(map(lambda c:list(map(str,c)),commands)),'files_sha256':{n:sha(O/n)for n in files},'tool_sha256':{str(c[0]):sha(c[0])for c in commands}}
(O/'manifest.json').write_text(json.dumps(r,indent=2)+'\n');print('BUILT',r['cpu_code_bytes'],'BYTES',words,'CODE WORDS',r['task_staged_words'],'TASK WORDS')
