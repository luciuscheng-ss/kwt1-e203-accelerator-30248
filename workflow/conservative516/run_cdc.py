from pathlib import Path
import json,hashlib,subprocess,re,time
import argparse
ap=argparse.ArgumentParser();ap.add_argument('--prepared',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
ROOT=Path('/home/2026contest/server6/s6_19usr/kwt_systembus_joint_20261111_01');R=a.out;assert not R.exists();R.mkdir();P=ROOT;sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();m=json.loads(a.prepared.read_text());assert all(sha(Path(p))==h for p,h in m['RTL_sources'].items());full={'source_sha256':m['RTL_sources']};base={'vendor_models_sha256':m['simulation_vendor_models']};assert all(sha(Path(p))==h for p,h in base['vendor_models_sha256'].items())
meta=json.loads((ROOT/'native_audit01/dependency_compare23.json').read_text());soc=Path(meta['native_rtl_root']).parent.parent;profile=json.loads((ROOT/'native_probe51/resource_profile.json').read_text())
p=Path(next(n for n in m['RTL_sources']if Path(n).name=='sirv_gnrl_bufs.v'));text=p.read_text();expected={'sirv_gnrl_sync':'2516e16a3caeca8f8aa7ddb1d5190593b60e7cecab79a2361750f7c8ceacba72','sirv_gnrl_cdc_tx':'d9a0fe7ca75498dc61ce4e579d1b6338c28dda940082644d3a0fc07010e3af64','sirv_gnrl_cdc_rx':'dee70efac93c748931615cc08a6d399d5fdd0f77a0cc34c8cdd8e6fd44573fab'};guard={}
for name,h in expected.items():
 t=re.search(r'\bmodule\s+'+name+r'\b.*?\bendmodule\b',text,re.S)[0];t=re.sub(r'//[^\n]*|/\*.*?\*/','',t,flags=re.S);t=re.sub(r'\s+','',t);actual=hashlib.sha256(t.encode()).hexdigest();assert actual==h,name;guard[name]=actual
levels=re.findall(r'`define\s+E203_ASYNC_FF_LEVELS\s+(\d+)',(soc/'rtl/e203/core/e203_defines.v').read_text());assert levels==['2']
(R/'source_guard.json').write_text(json.dumps({'pass':True,'modules':guard,'source_sha256':sha(p),'actual_async_depths':levels},indent=2)+'\n');(R/'cdc_handshake_tb.sv').write_bytes((ROOT/'native_cdc394/cdc_handshake_tb.sv').read_bytes())
r={'pass':False,'scope':'Currentprovided2FF4phaseCDCsource,150MHz/32768Hz,bothdirections128transfers,backpressure,inflightresetandphasesweep','source_guard_sha256':sha(R/'source_guard.json'),'prepared_manifest_sha256':sha(a.prepared),'source_sha256':m['RTL_sources'],'TB_sha256':sha(R/'cdc_handshake_tb.sv'),'steps':[],'runs':[]}
def write():(R/'result.json').write_text(json.dumps(r,indent=2)+'\n')
def call(name,cmd):
 p=R/(name+'.log');start=time.time()
 with p.open('w')as f:q=subprocess.run(list(map(str,cmd)),cwd=str(R),stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,timeout=900)
 t=p.read_text(errors='replace');r['steps'].append({'name':name,'exit':q.returncode,'seconds':time.time()-start,'log_sha256':sha(p)});write();assert q.returncode==0 and not re.search(r'(?:Error-\[|Fatal:|FATAL:|Warning-\[(?:IPDW|PCWM))',t),name;return t
write();cmd=['/eda/synopsys/vcs/vcs_2020.03-SP2-6/bin/vcs','-full64','-j1','-sverilog','-timescale=1ns/1fs','-top','cdc_handshake_tb','-o',R/'simv','+notimingcheck','+define+ARM_UD_MODEL+functional+KWT_NATIVE_GATES+DISABLE_SV_ASSERTION=1']+['+incdir+'+str(soc/n)for n in profile['include_dirs']]+list(full['source_sha256'])+list(base['vendor_models_sha256'])+[R/'cdc_handshake_tb.sv'];call('compile',cmd)
for i,phase in enumerate(['0','0.05','3.333333','6.6']):
 t=call('phase%d'%i,[R/'simv','+PHASE='+phase]);matches=re.findall(r'^PASS actualCDC phase=([0-9.]+) HFsent=(\d+) LFreceived=(\d+) LFsent=(\d+) HFreceived=(\d+) holdHF=(\d+) holdLF=(\d+) resets=(\d+)',t,re.M);assert len(matches)==1;v=matches[0];assert all(int(z)==128 for z in v[1:5])and int(v[7])==2;r['runs'].append({'phase_ns':v[0],'HF_to_LF':128,'LF_to_HF':128,'held_data_HF_cycles':int(v[5]),'held_data_LF_cycles':int(v[6]),'reset_events':int(v[7])});write()
r['pass']=True;write()
