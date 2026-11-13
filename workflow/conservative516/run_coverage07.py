from pathlib import Path
from collections import Counter
import re,json,hashlib,argparse
ap=argparse.ArgumentParser();ap.add_argument('--mapping',type=Path,required=True);ap.add_argument('--timing',type=Path,required=True);a=ap.parse_args();O=a.timing.parent
mapping=json.loads(a.mapping.read_text());timing=json.loads(a.timing.read_text());assert mapping['pass']and timing['pass']and mapping['mapped_sha256']==timing['mapped_sha256'];assert hashlib.sha256(Path(mapping['mapped']).read_bytes()).hexdigest()==mapping['mapped_sha256']
lines=(O/'disabled_timing.rpt').read_text().splitlines();started=False;cell='';rows=[];unknown=[]
pending=None
for l in lines:
 if re.search(r'Cell or Port\s+From\s+To',l):started=True;continue
 if not started:continue
 s=l.strip()
 if not s or set(s)=={'-'}or s=='1':continue
 if ('/'in s and len(s.split())==1)or s.startswith('io_pads'):
  if pending:unknown.append('Unfinished arc '+repr(pending));pending=None
  cell=s;continue
 m=re.match(r'^(\S+)\s+(\S+)\s+(\S+)\s+([cCdDfFlLmMpPuU]+)(?:\s+(.*))?$',s)
 if m:
  if pending:unknown.append('Unfinished arc '+repr(pending));pending=None
  rows.append({'cell':cell,'from':m[1],'to':m[2],'sense':m[3],'flags':m[4],'reason':m[5]or''});continue
 m=re.match(r'^(\S+)\s+(\S+)\s+(\S+)$',s)
 if m and not re.match(r'^[cCdDfFlLmMpPuU]\s',s):
  if pending:unknown.append('Unfinished arc '+repr(pending))
  pending={'cell':cell,'from':m[1],'to':m[2],'sense':m[3]};continue
 m=re.match(r'^([cCdDfFlLmMpPuU]+)(?:\s+(.*))?$',s)
 if m and pending:
  pending.update(flags=m[1],reason=m[2]or'');rows.append(pending);pending=None;continue
 if rows and not pending:rows[-1]['reason']+=' '+s
 else:unknown.append(s)
if pending:unknown.append('Unfinished arc '+repr(pending))
flags=Counter(v['flags']for v in rows)
loops=[r for r in rows if 'l'in r['flags']or'L'in r['flags']]
t=(O/'check_timing.rpt').read_text().splitlines();heads=[]
for i,s in enumerate(t):
 m=re.search(r"Information:\s*Checking\s+'([^']+)'",s)
 if m:heads.append((i,m[1]))
sections={}
for at,(i,n)in enumerate(heads):
 end=heads[at+1][0]if at+1<len(heads)else len(t);ss=[s.strip()for s in t[i+1:end]if s.strip()];sections[n]=ss
r={'pass':len(rows)>0 and not unknown and not loops and set(flags).issubset({'p','c','C','d'}),'mapped_sha256':json.loads(a.mapping.read_text())['mapped_sha256'],'timing_result_sha256':hashlib.sha256(a.timing.read_bytes()).hexdigest(),'flag_counts':dict(flags),'actual_loop_cut_arcs':loops,'unknown_rows':unknown,'all_disabled_arcs':rows,'all_check_timing_sections':sections,'reports_sha256':{n:hashlib.sha256((O/n).read_bytes()).hexdigest()for n in['disabled_timing.rpt','check_timing.rpt','coverage.rpt']}}
(O/'coverage_review07.json').write_text(json.dumps(r,indent=2)+'\n');assert r['pass'];print(json.dumps({'pass':r['pass'],'flag_counts':r['flag_counts'],'arcs':len(rows),'unknown':len(unknown),'loops':len(loops)}))
