"""Full originalCPUpublicMEM loader withoutCPUinternalresponseforce andUART-only339ECO, realCPU236.
14 fixed tasks in2modes inRTL andmapped.12validation-entry0 tasks define selected
ordinaryMODE0 cold rate. No TCM taskpayload. Team adapter/source applicability
review is explicit, not an organizer benchmark or a waived compliance gate.
"""
from pathlib import Path
import json,hashlib,csv,re,subprocess,time,shutil
from result_readback82 import generate,generate_dump
R=Path(__file__).resolve().parent;P=R.parent;sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();M=json.loads((R/'MANIFEST.json').read_text());assert all(sha(R/n)==h for n,h in M.items())
B=P/'native_loader220';smoke=json.loads((B/'result.json').read_text());assert smoke['pass'];assert sha(R/'cpu_copy_driver64.hex')=='37ec5bbb8988e92b57e9367a54ee4fde069e0c7a5ded05e01364323218b7fce6'

A=P/'native_uart339';S=A/'synth';syn=json.loads((A/'result.json').read_text());timing=json.loads((P/'native_pt362/result.json').read_text());assert syn['pass']and timing['pass']and timing['engineering_setup_hold_nonnegative'];mapped=S/'mapped.v';assert sha(mapped)==syn['mapped_sha256']==timing['mapped_sha256'];current=dict(smoke['hardware_source_sha256']);G=json.loads((P/'native_uart332/official_guard/overlay_guard.json').read_text());key=next(n for n in current if Path(n).name=='apb_uart.v');assert current[key]==G['original_source_sha256'];del current[key];current[G['overlay']]=G['overlay_sha256'];assert all(sha(n)==h for n,h in current.items());assert json.loads((P/'native_uart365/result.json').read_text())['pass'];assert json.loads((P/'native_loader359/result.json').read_text())['pass'];inputs=list(current);F=P/'native_probe51';base=json.loads((F/'result.json').read_text());vendors=list(base['vendor_models_sha256']);assert all(sha(n)==h for n,h in base['vendor_models_sha256'].items());profile=json.loads((F/'resource_profile.json').read_text());meta=json.loads((P/'native_audit01/dependency_compare23.json').read_text());SOC=Path(meta['native_rtl_root']).parent.parent
r={'scope':__doc__,'pass':False,'steps':[],'cases':[],'mapped_sha256':sha(mapped),'source_sha256':current,'parent_source_and_smoke_result_sha256':sha(B/'result.json'),'firmware_sha256':sha(R/'cpu_copy_driver64.hex'),'numeric_freeze_sha256':smoke['numeric_freeze_sha256'],'selected_mode_for_performance':0,'hard_floor_tasks_s':None,'official_score':None,'official_loader_qualified':False,'loader_adapter_team_owned':True,'hardware_UART_only_changed':True,'CPU_configuration_changed':False,'STA_coverage_review_closed':False,'power_qualified':False,'physical_oracle_after_window_and_CPU_return':True,'TCM_task_data_words':0,'CPU_wait_is_architectural_WFI_not_TB_clock_or_reset_force':True,'testbench_sha256':sha(R/'loader_cpu_tb.sv'),'oracle_bindings':{},'data_selection':'fixed native56 validation entry0 at each12layers, plus2synthetic exact-integer stresscases; not testing or numericalselection','activity_not_yet_captured':True,'mapped_binding_adaptation':'Architectural CPU WFI plus existing externalIRQ completion. Force only originalCPU MEM command fields and response-ready. No internalCPU response force/mask. Actual8168 sharedSRAM writes/reads, drainedresponses andCPU resume required.'}
def write():(R/'result.json').write_text(json.dumps(r,indent=2)+'\n')
def run(name,cmd,O):
 log=R/(name+'.log');t=time.time()
 with log.open('w')as f:p=subprocess.run(list(map(str,cmd)),cwd=str(O),stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,timeout=1800)
 s=log.read_text(errors='replace');r['steps'].append({'name':name,'exit':p.returncode,'seconds':time.time()-t,'log_sha256':sha(log)});write();assert p.returncode==0 and not re.search(r'(?:Error-\[|FATAL:|Fatal:)',s),name+' failed'
 if 'compile'in name:assert not re.search(r'Warning-\[(?:IPDW|PCWM)',s),'Portwidth warning'
 return s
write();dirs={}
for impl in ['rtl','mapped']:
 O=R/impl;O.mkdir();dirs[impl]=O
 for n in ['source.hex','raw.hex','codes.hex','packed.hex','word_counts.hex','dual_params.vh']:(O/n).symlink_to(P/'native_validation56/vectors'/n)
 for n in ['cpu_params.vh','cpu_copy_driver64.hex']:(O/n).symlink_to(R/n)
 (O/'native_cpu_bindings.svh').symlink_to(P/'native_cpu49/cpu/native_cpu_bindings.svh');(O/'ROM1KX32_verilog.rcf').symlink_to(P/'native_cpu49/cpu/ROM1KX32_verilog.rcf')
 for n in profile['required_resources']:
  if Path(n).name!='ROM1KX32_verilog.rcf':(O/Path(n).name).symlink_to(SOC/n)
 r['oracle_bindings'][impl]=generate(O/'result_readback82.svh',impl=='mapped',S/'leaf_cells.tsv',mapped)
 if impl=='mapped':r['capture_scope_manifest']=generate_dump(O/'dump_scopes.svh',S/'leaf_cells.tsv',mapped)
 else:(O/'dump_scopes.svh').write_text('task dump_current_scope;begin $dumpvars(0,u_soc);end endtask\n')
 write()
 flags=['+define+ARM_UD_MODEL+functional'+('+KWT_NATIVE_GATES+DISABLE_SV_ASSERTION=1'if impl=='rtl'else''),'+incdir+'+str(O)]+['+incdir+'+str(SOC/n)for n in profile['include_dirs']]
 cmd=['/eda/synopsys/vcs/vcs_2020.03-SP2-6/bin/vcs','-full64','-sverilog','-j1','-timescale=1ns/1fs','-top','native_cpu_tb','-Mdir='+str(O/'csrc'),'-o',O/'simv']+(['+notimingcheck','-debug_access+all','-debug_region+cell']if impl=='mapped'else[])+flags+(inputs if impl=='rtl'else[mapped])+vendors+[R/'loader_cpu_tb.sv'];run(impl+'_compile',cmd,O)

from concurrent.futures import ThreadPoolExecutor,as_completed
B=R
def one(impl,case,mode,gap=0,rspgap=0):
 name='%s_case%d_mode%d'%(impl,case,mode)+('_gap%d_rsp%d'%(gap,rspgap)if gap or rspgap else'');O=R/name;O.mkdir(exist_ok=True);assert not list(O.iterdir());C=B/impl
 for p in C.iterdir():
  if p.name in ['simv','simv.daidir']or p.suffix in ['.hex','.vh','.svh','.rcf']or p.is_symlink():(O/p.name).symlink_to(p)
 log=O/'tool.log';t=time.time()
 with log.open('w')as f:p=subprocess.run([str(O/'simv'),'+CASE='+str(case),'+MODE='+str(mode),'+GAP='+str(gap),'+RSPGAP='+str(rspgap)],cwd=str(O),stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,timeout=1800)
 s=log.read_text(errors='replace');step={'name':name,'exit':p.returncode,'seconds':time.time()-t,'log_sha256':sha(log)};assert p.returncode==0 and not re.search(r'(?:Error-\[|FATAL:|Fatal:)',s),name+' failed'
 assert 'PASS scheduler CPU SystemBus loading sharedSRAM case='+str(case)+' mode='+str(mode)in s and'PASS post-task physical sharedSRAM oracle words='in s
 rows=list(csv.DictReader((O/'cpu_cycles.csv').open()));assert len(rows)==1;v={k:float(z)if k.startswith('window_')else int(z)for k,z in rows[0].items()};assert v['case']==case and v['mode']==mode and v['TCM_task_data_words']==0 and v['source_writes']==v['loader_commands']==v['loader_responses']==8168 and v['source_reads']==(0 if mode else 8168)and v['raw_codes']==v['quant_codes']==25344 and v['output_acks']==v['output_writes']==v['physical_pin_readback_words']and v['CPU_instruction_handshakes_while_loader']==0 and v['CPU_WFI_host_cycles']>=100
 assert v['driver_return_cycles']>=v['cold_cycles'];assert abs((v['window_end_ns']-v['window_start_ns'])-v['cold_cycles']*6.666666)<.001
 v.update(implementation=impl,tasks_s_at150MHz=150e6/v['cold_cycles'],fixed_validation_entry=case<12,activity_capture=False);return v,step
# Require actual newRTL/newmapped MODE0 case0 match before fullparallelbatch.
for impl in ['rtl','mapped']:
 v,step=one(impl,0,0);r['cases'].append(v);r['steps'].append(step);write()
assert r['cases'][0]['cold_cycles']==r['cases'][1]['cold_cycles']
jobs=[(i,c,m)for c in range(14)for m in [0,1]for i in ['rtl','mapped']if not(c==0 and m==0)]
with ThreadPoolExecutor(max_workers=4)as pool:
 fs={pool.submit(one,*v):v for v in jobs}
 for f in as_completed(fs):
  try:v,step=f.result()
  except Exception as e:
   r['failure']={'job':fs[f],'error':str(e)};write()
   for z in fs:z.cancel()
   raise
  r['cases'].append(v);r['steps'].append(step);write()
assert len(r['cases'])==56
baseline=json.loads((P/'native_full267/result.json').read_text());r['same_cycles_as163_oldloader']=True
for case in range(14):
 for mode in [0,1]:
  a=[v for v in r['cases']if v['case']==case and v['mode']==mode];assert len(a)==2 and a[0]['cold_cycles']==a[1]['cold_cycles']
  old=next(v for v in baseline['cases']if v['case']==case and v['mode']==mode and v['implementation']=='mapped')
  if old['cold_cycles']!=a[0]['cold_cycles']:r['same_cycles_as163_oldloader']=False
for impl in ['rtl','mapped']:
 for mode in [0,1]:
  a=[v for v in r['cases']if v['implementation']==impl and v['case']<12 and v['mode']==mode];assert len(a)==12;r[impl+'_mode%d_tasks_s'%mode]=12*150e6/sum(v['cold_cycles']for v in a);r[impl+'_mode%d_driver_return_tasks_s'%mode]=12*150e6/sum(v['driver_return_cycles']for v in a)
r['interface_backpressure_cases']=[];write()
for case,gap,rspgap in [(0,3,5),(11,1,2)]:
 for impl in ['rtl','mapped']:
  v,step=one(impl,case,0,gap,rspgap);r['interface_backpressure_cases'].append(dict(v,response_gap=rspgap));r['steps'].append(step);write()
for case in [0,11]:
 v=[z for z in r['interface_backpressure_cases']if z['case']==case];assert len(v)==2 and v[0]['cold_cycles']==v[1]['cold_cycles']
r['full14_both_modes_RTL_and_mapped_function_pass']=True;r['selected_mode_for_performance']=0;r['hard_floor_tasks_s']=None;r['UART_observable_guard_result_sha256']=sha(P/'native_uart365/result.json');r['public_MEM_unmasked_loader_smoke_sha256']=sha(P/'native_loader359/result.json');r['compiled_executable_sha256']={impl:sha(R/impl/'simv')for impl in ['rtl','mapped']};r['pass']=True;write()
