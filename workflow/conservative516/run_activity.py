"""Crop current mapped cold-task activity to its measured hardware window."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import argparse,json,hashlib,sys
ap=argparse.ArgumentParser();ap.add_argument('--mapping',type=Path,required=True);ap.add_argument('--function',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
R=Path('/home/2026contest/server6/s6_19usr/kwt_systembus_joint_20261111_01');sys.path.insert(0,str(R/'native_activity372'))
from crop_case import crop_case,sha
O=a.out;assert not O.exists();O.mkdir();syn=json.loads(a.mapping.read_text());f=json.loads(a.function.read_text());assert syn['pass']and f['pass']and len(f['cases'])==16
assert sha(Path(syn['mapped']))==syn['mapped_sha256']==f['mapped_sha256']
cases=sorted([c for c in f['cases']if c['case']<12 and c['command_gap']==c['response_gap']==0],key=lambda c:c['case']);assert [c['case']for c in cases]==list(range(12))
r={'pass':False,'mapped_sha256':syn['mapped_sha256'],'function_result_sha256':sha(a.function),'firmware_sha256':f['firmware_sha256'],'testbench_sha256':f['testbench_sha256'],'helper_sha256':{p.name:sha(p)for p in (R/'native_activity372').iterdir()if p.suffix in ['.py','.cpp']},'activity_cases':[]}
def save():(O/'result.json').write_text(json.dumps(r,indent=2)+'\n')
def one(c):
 p=Path(c['VCD_path']);assert sha(p)==c['VCD_sha256'];return crop_case(p,O/('case%d'%c['case']),c,Path(syn['leaf_cells']),syn['mapped_sha256'])
save();r['activity_cases'].append(one(cases[0]));save()
# Compile the pinned scanner once before concurrent use. Each case has its own output.
with ProcessPoolExecutor(max_workers=2)as ex:
 for f in as_completed([ex.submit(one,c)for c in cases[1:]]):r['activity_cases'].append(f.result());save()
r['activity_cases'].sort(key=lambda c:c['case']);assert len(r['activity_cases'])==12 and all(c['pass']for c in r['activity_cases']);r['pass']=True;save()
