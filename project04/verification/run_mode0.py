"""Actual supplied full-SoC MODE0 source/mapped regression and cold activity."""
from pathlib import Path
import argparse,json,hashlib,csv,re,subprocess,time,sys
from cpu_bindings import generate as boot_bindings
from result_readback82 import generate,generate_dump
p=argparse.ArgumentParser();p.add_argument('--prepared',type=Path,required=True);p.add_argument('--soc',type=Path,required=True);p.add_argument('--mapping',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--smoke',action='store_true');p.add_argument('--activity',action='store_true');a=p.parse_args()
V=Path(__file__).resolve().parent;P=V.parent;O=a.out.resolve();assert not O.exists();O.mkdir(parents=True)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
m=json.loads(a.prepared.read_text());assert all(sha(n)==h for n,h in m['RTL_sources'].items());assert all(sha(n)==h for n,h in m['simulation_vendor_models'].items())
impl='mapped'if a.mapping else'rtl';mapping=json.loads(a.mapping.read_text())if a.mapping else None
if mapping:assert mapping['pass']and sha(Path(mapping['mapped']))==mapping['mapped_sha256']
r={'pass':False,'implementation':impl,'mode':0,'output_format':'fixed16_rowmajor_v1','cases':[],'steps':[],'source_manifest_sha256':sha(a.prepared),'firmware_sha256':sha(P/'firmware/cpu_copy_driver64.hex'),'testbench_sha256':sha(V/'loader_cpu_tb.sv'),'mapped_sha256':mapping['mapped_sha256']if mapping else None,'numeric_freeze_sha256':'f0d58263c179a89d164cffbf3f866db68d52f8c27ead48add034c49896becef2','official_score':None}
def save():(O/'result.json').write_text(json.dumps(r,indent=2)+'\n')
save();B=O/'build';B.mkdir()
for n in ['source.hex','raw.hex','codes.hex','matrix.hex','word_counts.hex','dual_params.vh']:(B/n).symlink_to(V/'vectors'/n)
for n in ['cpu_params.vh','cpu_copy_driver64.hex']:(B/n).symlink_to(P/'firmware'/n)
boot_bindings(a.soc,B/'native_cpu_bindings.svh')
generate(B/'result_readback82.svh',bool(mapping),Path(mapping['leaf_cells'])if mapping else None,Path(mapping['mapped'])if mapping else None)
if mapping:generate_dump(B/'dump_scopes.svh',Path(mapping['leaf_cells']),Path(mapping['mapped']))
else:(B/'dump_scopes.svh').write_text('task dump_current_scope;begin $dumpvars(0,u_soc);end endtask\n')
profile=json.loads((P/'hardware/integration/resource_profile.json').read_text())
for n,h in profile['required_resources'].items():
 if Path(n).name!='ROM1KX32_verilog.rcf':assert sha(a.soc/n)==h;(B/Path(n).name).symlink_to(a.soc/n)
(B/'ROM1KX32_verilog.rcf').write_text(''.join(format(v,'032b')+'\n'for v in[0x7ffff297,0x00028067]+[0]*1022))
flags=['+define+ARM_UD_MODEL+functional'+(''if mapping else'+KWT_NATIVE_GATES+DISABLE_SV_ASSERTION=1'),'+incdir+'+str(B)]+['+incdir+'+str(n)for n in m['include_dirs']]
cmd=['/eda/synopsys/vcs/vcs_2020.03-SP2-6/bin/vcs','-full64','-sverilog','-j1','-timescale=1ns/1fs','-top','native_cpu_tb','-Mdir='+str(B/'csrc'),'-o',str(B/'simv')]+(['+notimingcheck','-debug_access+all','-debug_region+cell']if mapping else[])+flags+([mapping['mapped']]if mapping else list(m['RTL_sources']))+list(m['simulation_vendor_models'])+[str(V/'loader_cpu_tb.sv')]
start=time.time()
with(O/'compile.log').open('w')as f:z=subprocess.run(cmd,cwd=B,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,timeout=3600)
t=(O/'compile.log').read_text(errors='replace');r['steps'].append({'name':'compile','exit':z.returncode,'seconds':time.time()-start});save();assert z.returncode==0 and not re.search(r'Error-\[|Warning-\[(?:IPDW|PCWM)',t),'compile/width diagnostics'
def one(case,gap=0,rspgap=0):
 D=O/('case%d_gap%d_rsp%d'%(case,gap,rspgap));D.mkdir()
 for f in B.iterdir():
  if f.name in ['simv','simv.daidir']or f.suffix in['.hex','.vh','.svh','.rcf']:(D/f.name).symlink_to(f)
 args=[str(D/'simv'),'+CASE='+str(case),'+MODE=0','+GAP='+str(gap),'+RSPGAP='+str(rspgap)]
 if a.activity and gap==rspgap==0 and case<12:args.append('+VCD='+str(D/'cold.vcd'))
 begin=time.time()
 with(D/'run.log').open('w')as f:z=subprocess.run(args,cwd=D,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,timeout=3600)
 text=(D/'run.log').read_text(errors='replace');assert z.returncode==0 and 'PASS scheduler CPU SystemBus loading sharedSRAM'in text and 'PASS post-task physical sharedSRAM oracle words=12672'in text,(D.name,text[-1500:])
 rows=list(csv.DictReader((D/'cpu_cycles.csv').open()));assert len(rows)==1;v={k:float(x)if k.startswith('window_')else int(x)for k,x in rows[0].items()}
 assert v['mode']==v['TCM_task_data_words']==v['CPU_instruction_handshakes_while_loader']==0
 assert v['source_writes']==v['source_reads']==v['loader_commands']==v['loader_responses']==8168
 assert v['output_writes']==v['output_acks']==v['physical_pin_readback_words']==12672
 assert v['raw_codes']==v['quant_codes']==25344
 assert v['original_split_peak']==v['shared_port_peak']==1
 assert v['dma_merge_peak']<=8 and v['cpu_dma_merge_peak']<=8
 assert abs(v['window_end_ns']-v['window_start_ns']-v['cold_cycles']*6.666666)<.001
 v.update(command_gap=gap,response_gap=rspgap,seconds=time.time()-begin,run_log_sha256=sha(D/'run.log'))
 if(D/'cold.vcd').exists():v['VCD_path']=str(D/'cold.vcd');v['VCD_sha256']=sha(D/'cold.vcd')
 return v
# Complete source regression before mapping; independent cases share no mutable data.
from concurrent.futures import ThreadPoolExecutor,as_completed
jobs=[(c,0,0)for c in range(1 if a.smoke else 14)]
if not a.smoke:jobs +=[(0,3,5),(11,1,2)]
with ThreadPoolExecutor(max_workers=2)as ex:
 for f in as_completed([ex.submit(one,*j)for j in jobs]):
  r['cases'].append(f.result());save()
if not a.smoke:
 vals=[v for v in r['cases']if v['case']<12 and v['command_gap']==v['response_gap']==0];assert len(vals)==12
 r['cold_tasks_s']=12*150e6/sum(v['cold_cycles']for v in vals);r['CPU_return_tasks_s']=12*150e6/sum(v['driver_return_cycles']for v in vals)
r['pass']=True;save();print(json.dumps({'pass':True,'implementation':impl,'cases':len(r['cases']),'cold_tasks_s':r.get('cold_tasks_s')}))
