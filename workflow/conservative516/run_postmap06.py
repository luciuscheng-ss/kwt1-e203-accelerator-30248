"""Current frozen map: independent area/STA and full mapped cold-task regression."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import json,subprocess,sys,time,hashlib
R=Path('/home/2026contest/server6/s6_19usr/kwt_systembus_joint_20261111_01');C=R/'conservative516';P=C/'project04';M=C/'synthesis06/result.json';O=C/'postmap06';assert not O.exists();O.mkdir()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert json.loads(M.read_text())['pass'];assert all(sha(P/n)==h for n,h in json.loads((P/'SOURCE_SHA256.json').read_text()).items())
soc=Path(json.loads((R/'native_audit01/dependency_compare23.json').read_text())['native_rtl_root']).parent.parent
r={'pass':False,'mapping_result_sha256':sha(M),'stages':[]}
def save():(O/'result.json').write_text(json.dumps(r,indent=2)+'\n')
def run(name,args):
 start=time.time()
 with(O/(name+'.log')).open('w')as f:z=subprocess.run([str(x)for x in [sys.executable,'-B']+args],stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,cwd=C,timeout=21600)
 return {'stage':name,'exit':z.returncode,'seconds':time.time()-start}
save()
jobs=[('area',[C/'run_area.py','--mapping',M,'--out',C/'area06']),('timing',[C/'run_timing06.py','--mapping',M,'--out',C/'timing06']),('mapped_full',[P/'verification/run_mode0.py','--prepared',C/'prepared04/source_manifest.json','--soc',soc,'--mapping',M,'--out',C/'mapped_full06','--activity'])]
with ThreadPoolExecutor(max_workers=3)as ex:
 for f in as_completed([ex.submit(run,n,args)for n,args in jobs]):r['stages'].append(f.result());save()
assert all(s['exit']==0 for s in r['stages']),r
for n in ['area06','timing06','mapped_full06']:assert json.loads((C/n/'result.json').read_text())['pass'],n
r['stages'].append(run('activity',[C/'run_activity.py','--mapping',M,'--function',C/'mapped_full06/result.json','--out',C/'activity06']));save();assert r['stages'][-1]['exit']==0
r['stages'].append(run('power',[C/'run_power06.py','--mapping',M,'--function',C/'mapped_full06/result.json','--timing',C/'timing06/result.json','--activity',C/'activity06/result.json','--out',C/'power06']));save();assert r['stages'][-1]['exit']==0
r['stages'].append(run('cache',[C/'run_cache05.py','--mapping',M,'--function',C/'mapped_full06/result.json','--activity',C/'activity06/result.json','--out',C/'cache06']));save();assert r['stages'][-1]['exit']==0
r['pass']=True;save()
