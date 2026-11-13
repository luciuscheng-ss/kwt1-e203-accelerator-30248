"""Rebuild frozen scheduler into a fresh directory; compare executable payload.
Use --tool-prefix /path/to/riscv32-linux-gnu- to select the provided toolchain.
"""
from pathlib import Path
import argparse,subprocess,hashlib,json,shutil
D=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--tool-prefix',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists();a.out.mkdir(parents=True);O=a.out.resolve();source=O/'cpu_copy_driver.s';shutil.copy2(D/'cpu_copy_driver.s',source)
commands=[[a.tool_prefix+'as','-march=rv32im_zicsr','-mabi=ilp32','-o',str(O/'cpu_copy_driver.o'),str(source)],[a.tool_prefix+'ld','-melf32lriscv','-Ttext=0x80000000','-e','_start','-o',str(O/'cpu_copy_driver.elf'),str(O/'cpu_copy_driver.o')],[a.tool_prefix+'objcopy','-O','binary','--only-section=.text',str(O/'cpu_copy_driver.elf'),str(O/'cpu_copy_driver.bin')]]
for c in commands:subprocess.run(c,check=True)
b=(O/'cpu_copy_driver.bin').read_bytes();assert b==(D/'cpu_copy_driver.bin').read_bytes(),'Rebuilt firmware payload differs from frozen scheduler';code=b+b'\0'*((-len(b))%8);text=''.join('%016x\n'%int.from_bytes(code[i:i+8],'little')for i in range(0,len(code),8));assert text==(D/'cpu_copy_driver64.hex').read_text();(O/'cpu_copy_driver64.hex').write_text(text);(O/'cpu_params.vh').write_text('`define CPU_CODE_WORDS %d\n'%(len(code)//8));r={'pass':True,'executable_bytes':len(b),'ITCM64_words':len(code)//8,'firmware_sha256':hashlib.sha256(b).hexdigest(),'task_data_in_TCM':False,'commands':commands};(O/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items()if k!='commands'}))
