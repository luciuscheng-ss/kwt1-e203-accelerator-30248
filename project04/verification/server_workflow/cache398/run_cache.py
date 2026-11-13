from pathlib import Path
from decimal import Decimal
import json,hashlib,re,subprocess,time,sys,os
R=Path(__file__).resolve().parent;P=R.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
M=json.loads((R/'MANIFEST.json').read_text());assert all(sha(R/n)==h for n,h in M.items())
F=P/'native_activity372';assert sha(F/'vcd_window.py')=='f832525ce3b175815221932dedc9c2cc07dffafdf059daa1841919bd8cf09ce6';sys.path.insert(0,str(F));from vcd_window import read_header
full=json.loads((P/'native_full368/result.json').read_text());assert full['pass'];xsrc=next(n for n in full['source_sha256']if Path(n).name=='pair_x_store11_r5.sv');assert full['source_sha256'][xsrc]=='8454c278e64a50dfb3bd5e76f655407dc8713860878a0e3e57803b54c926b654';assert sha(xsrc)==full['source_sha256'][xsrc]
r={'pass':False,'scope':'Independent current-cold-window physical SRAM read-before-current-write bit-validity audit and CPU MEM ownership quiescence. No DUT stimulus/clock/response modifications. Initial cached payload bits may be arbitrary; every consumed bit must be actually written during this task before reading.','mapped_sha256':full['mapped_sha256'],'source_X_padding_guard_sha256':sha(xsrc),'cpp_source_sha256':sha(R/'cold_sram_audit.cpp'),'cases':[]}
def write():(R/'result.json').write_text(json.dumps(r,indent=2)+'\n')
def identity(s):return(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
write();cmd=['g++','-std=c++11','-O3',str(R/'cold_sram_audit.cpp'),'-o',str(R/'audit')]
with(R/'compile.log').open('w')as f:q=subprocess.run(cmd,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,timeout=120)
assert q.returncode==0;r['executable_sha256']=sha(R/'audit');sys.path.insert(0,str(R));from test_checker import run
q=run(R/'audit',R/'selftest');assert q['pass']and len(q['fixtures'])==17;r['selftest_sha256']=sha(R/'selftest/result.json');write()
for case in range(12):
 deadline=time.time()+7200
 while True:
  try:a=json.loads((F/'result.json').read_text())
  except(ValueError,OSError):a=None
  matches=[c for c in a['activity_cases']if c['case']==case]if a else[]
  if len(matches)==1:break
  e=P/'launch_activity372/exit.code';assert not e.exists()or e.read_text().strip()=='0','Activity failed';assert time.time()<deadline;time.sleep(2)
 c=matches[0];assert c['mode']==0 and c['mapped_sha256']==r['mapped_sha256'];audit=Path(c['audit_path']);assert sha(audit)==c['audit_sha256'];meta=json.loads(audit.read_text());assert meta['pass'];wave=Path(c['path']);dest=R/('case%d'%case);dest.mkdir()
 with wave.open()as f:header,scale,definitions,paths=read_header(f)
 specs=[];memories=[];counts={'X':0,'W':0,'ALPHA':0}
 for m in meta['macros']:
  scope=m['scope'];ref=m['reference']
  if ref=='RAMSP1024X16':
   z=re.search(r'/xs/x_banks\[(\d+)\]',scope);assert z;kind='X';bank=int(z.group(1));assert 0<=bank<7;aw=10
  elif ref=='RAMSP128X16':
   z=re.search(r'/ws/w_banks\[(\d+)\]',scope)
   if z:kind='W';bank=int(z.group(1));assert 0<=bank<22
   else:z=re.search(r'/xs/alpha_banks\[(\d+)\]',scope);assert z;kind='ALPHA';bank=int(z.group(1));assert 0<=bank<2
   aw=7
  else:continue
  pins=[paths[scope+'/'+n]['code']for n in ['CLK','CEN','GWEN','A','WEN','D']];specs.append('\t'.join(['M',scope,kind,str(bank)]+pins+[str(aw)]));counts[kind]+=1;memories.append({'scope':scope,'kind':kind,'bank':bank,'required_bits':'X110bitsnormally/88bitslasttile19, exactbankmask; W/Alphaall16'})
 assert counts=={'X':7,'W':22,'ALPHA':2}
 base='native_cpu_tb/u_soc/u_e203_subsys_top/u_e203_subsys_main/u_kwt_systembus/';gates={'engine/xs/rows_ready':(1<<20)-1,'engine/ws/buffer_ready':3,'engine/busy':1,'engine/kernel_valid':1,'engine/quant_valid':1,'engine/packed_valid':1,'engine/fcount':None,'engine/wqcount':None,'engine/pending_writes':None,'source_buffer/used':None,'source_buffer/reserved':None,'cache/tag_count':None,'cache/armed':1,'cache/c_rsp_valid':1,'cache/u_rsp_valid':1}
 for n,mask in gates.items():
  p=base+n;assert p in paths,'Missing actualcoldstate pin '+p;v=paths[p];w=v['width'];assert 0<w<=32
  if mask is None:mask=(1<<w)-1
  assert mask<(1<<w);specs.append('\t'.join(['V',p,v['code'],str(w),format(mask,'x'),'0']))
 log=F/('mapped_case%d'%case)/'tool.log';text=log.read_text();beg=re.findall(r'LOADER_OWNERSHIP_BEGIN cycle=(\d+)',text);end=re.findall(r'LOADER_OWNERSHIP_END cycle=(\d+)',text);assert len(beg)==len(end)==1
 period=meta['hfextclk_actual_stats']['min_period_ticks'];assert period==meta['hfextclk_actual_stats']['max_period_ticks'];start_ticks=Decimal(str(full['cases'][0]['window_start_ns']))
 ref=next(v for v in full['cases']if v['case']==case and v['mode']==0 and v['implementation']=='mapped');shift=int(Decimal(str(ref['window_start_ns']))/scale);lo=int(beg[0])*period-shift+1;hi=int(end[0])*period-shift-1;assert 0<lo<hi<int(Decimal(str(c['duration_ns']))/scale)
 core='native_cpu_tb/u_soc/u_e203_subsys_top/u_e203_subsys_main/u_e203_cpu_top/u_e203_cpu/u_e203_core/';quiet={core+'u_e203_biu/clk':0,core+'u_e203_biu/biu_active':0,core+'clk_core_ifu':0,core.rsplit('/u_e203_cpu/',1)[0]+'/core_wfi':1}
 # CPU_TOP is the existing parent of u_e203_cpu; no synthetic clock is introduced.
 for p,expected in quiet.items():
  assert p in paths and paths[p]['width']==1,'Missing actualCPUownership pin '+p;specs.append('\t'.join(['R',p,paths[p]['code'],str(lo),str(hi),str(expected)]))
 spec=dest/'config.tsv';spec.write_text('\n'.join(specs)+'\n');(dest/'binding.json').write_text(json.dumps({'macros':memories,'cold_validity_gates':gates,'loader_interval_ticks':[lo,hi],'CPU_ownership_levels':quiet,'source_wave_sha256':c['sha256']},indent=2)+'\n')
 start=time.time();p=subprocess.Popen([str(R/'audit'),str(spec)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 with wave.open('rb')as f:
  before=identity(os.fstat(f.fileno()));raw=hashlib.sha256();count=0
  try:
   for b in iter(lambda:f.read(4*1024*1024),b''):raw.update(b);count+=len(b);p.stdin.write(b)
   p.stdin.close();p.stdin=None;stdout,stderr=p.communicate(timeout=900)
  except BrokenPipeError:
   try:p.stdin.close()
   except BrokenPipeError:pass
   p.stdin=None;stdout,stderr=p.communicate(timeout=10)
  (dest/'stdout.json').write_bytes(stdout);(dest/'stderr.log').write_bytes(stderr);assert p.returncode==0 and not stderr,'Physicalread/coldstate/CPUownership auditfailed: '+stderr.decode(errors='replace')[-800:]
  assert identity(os.fstat(f.fileno()))==identity(wave.stat())==before and count==before[2]and raw.hexdigest()==c['sha256']
 v=json.loads(stdout.decode());assert v['pass']and v['memories']==31 and v['cold_validity_signals']==15 and all(m['reads']>0 and m['writes']>0 for m in v['macros']);v.update(case=case,wave_sha256=raw.hexdigest(),audit_metadata_sha256=sha(audit),binding_sha256=sha(dest/'binding.json'),seconds=time.time()-start,stream_hashed_exact_bytes=True,CPU_ownership_range_count=len(quiet));r['cases'].append(v);write()
assert len(r['cases'])==12;r['pass']=True;write()
