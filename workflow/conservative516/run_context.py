from pathlib import Path
from decimal import Decimal
import json,hashlib,csv,re,sys,subprocess,os,time
import argparse
ap=argparse.ArgumentParser()
for name in ['mapping','timing','activity','cache','out']:ap.add_argument('--'+name,type=Path,required=True)
args=ap.parse_args();ROOT=Path('/home/2026contest/server6/s6_19usr/kwt_systembus_joint_20261111_01');R=args.out;assert not R.exists();R.mkdir();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
H=ROOT/'native_context435'
for n in ['cold_sram_audit.cpp','test_checker.py','test_ranges.py','reviewed_module_logic.json']:(R/n).write_bytes((H/n).read_bytes())
F=ROOT/'native_activity372';C=args.cache.parent;syn=json.loads(args.mapping.read_text());full={'source_sha256':syn['source_sha256'],'mapped_sha256':syn['mapped_sha256']};mapped=Path(syn['mapped']);assert syn['pass']and sha(mapped)==syn['mapped_sha256'];cache=json.loads(args.cache.read_text());assert cache['pass']and cache['mapped_sha256']==syn['mapped_sha256'];exe=R/'audit';subprocess.run(['g++','-std=c++11','-O3',str(R/'cold_sram_audit.cpp'),'-o',str(exe)],check=True);sys.path.insert(0,str(R));from test_checker import run as original_tests;from test_ranges import run as range_tests;assert len(original_tests(exe,R/'original_selftest')['fixtures'])==17;assert len(range_tests(exe,R/'range_selftest')['fixtures'])==4;sys.path.insert(0,str(F));from vcd_window import read_header,groups,bits
norm=lambda s:re.sub(r'\s+','',re.sub(r'//[^\n]*|/\*.*?\*/','',s,flags=re.S));logic=json.loads((R/'reviewed_module_logic.json').read_text());sources={}
for n,h in logic.items():
 ps=[Path(p)for p in full['source_sha256']if Path(p).name==n];assert len(ps)==1 and sha(ps[0])==full['source_sha256'][str(ps[0])];assert hashlib.sha256(norm(ps[0].read_text()).encode()).hexdigest()==h,n;sources[str(ps[0])]=sha(ps[0])
text=re.sub(r'//[^\n]*|/\*.*?\*/','',mapped.read_text(),flags=re.S);modules={m.group(1):m.group(2)for m in re.finditer(r'\bmodule\s+(\\[^\s]+|[A-Za-z_][A-Za-z0-9_$]*)\s*\((.*?)\bendmodule\b',text,re.S)};refs='|'.join(re.escape(n)for n in sorted(modules,key=len,reverse=True));ins=re.compile(r'(?<![A-Za-z0-9_$\\])('+refs+r')\s+(\\[^\s]+|[A-Za-z_$][A-Za-z0-9_$]*)\s*\(');tree={}
def walk(ref,scope):
 assert scope not in tree;tree[scope]=ref
 for m in ins.finditer(modules[ref]):walk(m[1],scope+'/'+m[2].lstrip('\\'))
walk('e203_soc_top','');cross=list(csv.DictReader((args.timing.parent/'async_crossing_endpoints.tsv').open(),delimiter='\t'))
single=[v for v in cross if re.search(r'/u_(?:wdg_irq_sync|rtc_irq_sync|aon_rtctoggle_sync)/',v['endpoint'])and v['endpoint'].endswith('/D')];assert len(single)==3
static=[v for v in cross if 'cdc'not in(v['startpoint']+'/'+v['endpoint']).lower()and v not in single]
assert all('bootrom_deglitch'in v['startpoint']or v['endpoint'].endswith(('/RDN','/SDN'))for v in static),'Unreviewedclockcrossingkind'
(R/'single_bit_paths.json').write_text(json.dumps({'paths':single,'all_crossings':cross},indent=2)+'\n');targets=[]
for sp in sorted(set(v['startpoint']for v in static)):
 assert sp.endswith('/CK');cell=sp[:-3];parent,leaf=cell.rsplit('/',1);body=modules[tree['/'+parent]];raw=leaf if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*',leaf)else'\\'+leaf;ms=list(re.finditer(r'(?<!\S)'+re.escape(raw)+r'\s*\((.*?)\)\s*;',body,re.S));assert len(ms)==1,cell
 qs=re.findall(r'\.(Q|QN)\s*\(\s*([^()]+?)\s*\)',ms[0][1]);assert qs,cell
 for pin,net in qs:
  net=net.strip().lstrip('\\');assert re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*(?:\[\d+\])?',net),net;targets.append({'startpoint':sp,'pin':pin,'path':'native_cpu_tb/u_soc/'+parent+'/'+net})
r={'pass':False,'scope':'AllcurrentnonCDCconfiguration/resetcrossingcontextknownstaticinall12coldwindows;3actualasyncsinglebitfirst-Dpathsseparately2FFguarded;nonewSTAexceptionorDUTchange','mapped_sha256':sha(mapped),'source_logic_sha256':sources,'cross_endpoints':len(static),'asynchronous_single_bit_paths_review':sha(R/'single_bit_paths.json'),'physical_source_outputs':targets,'cases':[],'semantic_fixtures':21,'checker_source_sha256':sha(R/'cold_sram_audit.cpp'),'checker_executable_sha256':sha(exe)}
def write():(R/'result.json').write_text(json.dumps(r,indent=2)+'\n')
write();activity=json.loads(args.activity.read_text());assert activity['pass']
for case in range(12):
 a=next(v for v in activity['activity_cases']if v['case']==case);wave=Path(a['path']);spec=(C/('case%d'%case)/'config.tsv').read_text();d=R/('case%d'%case);d.mkdir()
 with wave.open()as f:
  header,scale,defs,paths=read_header(f);tm,events=next(groups(f));assert tm==0;initial={code:value for kind,code,value,*rest in events if kind=='value'}
 end=int(Decimal(str(a['duration_ns']))/scale);bindings=[]
 for t in targets:
  key=t['path'];bit=0
  if key not in paths:
   m=re.fullmatch(r'(.*)\[(\d+)\]',key);assert m;key=m[1];bit=int(m[2])
  p=paths[key];width=p['width'];assert 1<=width<=32 and bit<width
  if width>1:
   pattern=r'\$var\s+\S+\s+'+str(width)+r'\s+'+re.escape(p['code'])+r'\s+\\?'+re.escape(key.split('/')[-1])+r'\s+\['+str(width-1)+r':0\]\s+\$end';assert re.search(pattern,header),key
  val=initial.get(p['code']);assert val is not None;raw=bits(val,width);selected=raw[-1-bit];assert selected in '01',(key,bit,raw);expected=int(selected)<<bit;mask=1<<bit
  spec+='R\t'+t['path']+'\t'+p['code']+'\t0\t'+str(end)+'\t'+str(expected)+'\t'+str(width)+'\t'+format(mask,'x')+'\n';bindings.append(dict(t,value=int(selected),declaration_width=width,selected_bit=bit,VCD_path=key))
 (d/'config.tsv').write_text(spec);(d/'bindings.json').write_text(json.dumps(bindings,indent=2)+'\n');p=subprocess.Popen([str(exe),str(d/'config.tsv')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE);digest=hashlib.sha256()
 try:
  with wave.open('rb')as f:
   for b in iter(lambda:f.read(4*1024*1024),b''):digest.update(b);p.stdin.write(b)
 except BrokenPipeError:
  try:p.stdin.close()
  except BrokenPipeError:pass
  p.stdin=None;out,err=p.communicate(timeout=30);(d/'stderr.log').write_bytes(err);raise AssertionError('Checker stopped: '+err.decode(errors='replace')[-500:])
 p.stdin.close();p.stdin=None;out,err=p.communicate(timeout=900);(d/'stdout.json').write_bytes(out);(d/'stderr.log').write_bytes(err);assert p.returncode==0 and not err,err.decode()[-500:];v=json.loads(out.decode());assert v['pass']and digest.hexdigest()==a['sha256'];r['cases'].append({'case':case,'pass':True,'static_outputs':len(bindings),'wave_sha256':digest.hexdigest(),'bindings_sha256':sha(d/'bindings.json'),'result_sha256':sha(d/'stdout.json')});write()
assert len(r['cases'])==12;r['pass']=True;write()
