"""Fresh finalUART339/CPU236 publicMEMunmaskedloader368 MODE0 whole-digital activity, exact full368 qualification.
No old CPU-copy waveform, numerical configuration or loading route is reused.
"""
from pathlib import Path
import json,hashlib,csv,shutil,subprocess,re,time
from crop_case import crop_case
from concurrent.futures import ProcessPoolExecutor,as_completed
R=Path(__file__).resolve().parent;P=R.parent;F=P/'native_full368';S=P/'native_uart339/synth'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
M=json.loads((R/'MANIFEST.json').read_text());assert all(sha(R/n)==h for n,h in M.items())
deadline=time.time()+7200
while True:
 try:full=json.loads((F/'result.json').read_text())
 except(ValueError,OSError):full=None
 if full and full.get('pass'):break
 e=P/'launch_full368/exit.code';assert not e.exists()or e.read_text().strip()=='0','Full368 failed; no capture';assert time.time()<deadline;time.sleep(2)
assert full['mapped_mode0_tasks_s']>0
assert len(full['cases'])==56 and sha(S/'mapped.v')==full['mapped_sha256'];FM=json.loads((F/'MANIFEST.json').read_text());assert all(sha(F/n)==h for n,h in FM.items());assert sha(R/'crop_case.py')==M['crop_case.py']
r={'scope':__doc__,'pass':False,'activity_cases':[],'cases':[],'steps':[],'mapped_sha256':full['mapped_sha256'],'firmware_sha256':full['firmware_sha256'],'numeric_freeze_sha256':full['numeric_freeze_sha256'],'full_function_result_sha256':sha(F/'result.json'),'full_function_manifest_sha256':sha(F/'MANIFEST.json'),'testbench_sha256':full['testbench_sha256'],'acceptance_sha256':sha(R/'acceptance319.json'),'selected_mode':0,'official_loader_qualified':False,'power_qualified':False,'hard_floor_tasks_s':None,'team_acceptance':'User319acceptsordinaryMODE0~5467.5;6000notanofficialminimum','all12_mode0_mapped_activity_crops_complete':False}
def write():(R/'result.json').write_text(json.dumps(r,indent=2)+'\n')
write();B=P/'native_full368/mapped'
assert sha(B/'simv')==full['compiled_executable_sha256']['mapped']
def one(case):
 O=R/('mapped_case%d'%case);O.mkdir()
 for p in B.iterdir():
  if p.name in ['simv','simv.daidir']or p.suffix in ['.hex','.vh','.svh','.rcf']or p.is_symlink():(O/p.name).symlink_to(p)
 assert shutil.disk_usage(R).free>12*1024**3,'Need12GiB free before capture'
 vcd=O/('case%d_mode0.vcd'%case);log=O/'tool.log';t=time.time()
 with log.open('w')as f:p=subprocess.run([str(O/'simv'),'+CASE='+str(case),'+MODE=0','+GAP=0','+VCD='+str(vcd)],cwd=str(O),stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,timeout=1800)
 s=log.read_text(errors='replace');step={'case':case,'exit':p.returncode,'seconds':time.time()-t,'log_sha256':sha(log)};assert p.returncode==0 and not re.search(r'(?:Fatal:|FATAL:|Error-\[)',s)
 assert 'PASS scheduler CPU SystemBus loading sharedSRAM case='+str(case)+' mode=0'in s and 'PASS post-task physical sharedSRAM oracle words='in s
 rows=list(csv.DictReader((O/'cpu_cycles.csv').open()));assert len(rows)==1;v={k:float(z)if k.startswith('window_')else int(z)for k,z in rows[0].items()};ref=[x for x in full['cases']if x['implementation']=='mapped'and x['case']==case and x['mode']==0];assert len(ref)==1
 for k,z in v.items():assert z==ref[0][k],'Activity replay differs from full function: '+k
 assert v['TCM_task_data_words']==v['CPU_instruction_handshakes_while_loader']==0 and v['source_writes']==v['loader_commands']==v['loader_responses']==v['source_reads']==8168
 crop=crop_case(vcd,R/('activity_case%d_mode0'%case),v,S/'leaf_cells.tsv',r['mapped_sha256']);return v,crop,step
def accept(result):
 v,crop,step=result;r['cases'].append(v);r['activity_cases'].append(crop);r['steps'].append(step);write()
# Actual final-map single-case macro/clock/window crop preflight before parallel capture.
accept(one(0))
with ProcessPoolExecutor(max_workers=3)as pool:
 for f in as_completed([pool.submit(one,c)for c in range(1,12)]):accept(f.result())
assert len(r['activity_cases'])==12 and all(x['pass']for x in r['activity_cases']);r['all12_mode0_mapped_activity_crops_complete']=True;r['pass']=True;write()
