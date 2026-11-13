from pathlib import Path
import json,hashlib,re,subprocess,os,csv
import argparse
ap=argparse.ArgumentParser()
for name in ['mapping','timing','context','cdc','out']:ap.add_argument('--'+name,type=Path,required=True)
args=ap.parse_args();ROOT=Path('/home/2026contest/server6/s6_19usr/kwt_systembus_joint_20261111_01');R=args.out;assert not R.exists();R.mkdir();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();A=json.loads(args.mapping.read_text());F={'source_sha256':A['source_sha256'],'mapped_sha256':A['mapped_sha256']};mapped=Path(A['mapped']);assert A['pass']and sha(mapped)==A['mapped_sha256'];G=json.loads(args.cdc.read_text());assert G['pass'];(R/'source_review.json').write_bytes((ROOT/'native_sync446/source_review.json').read_bytes());(R/'chain_guard.tcl').write_bytes((ROOT/'native_sync446/chain_guard.tcl').read_bytes())
norm=lambda s:re.sub(r'\s+','',re.sub(r'//[^\n]*|/\*.*?\*/','',s,flags=re.S));sources={}
def instance436(s,name):
 s=re.sub(r'//[^\n]*|/\*.*?\*/','',s,flags=re.S)
 def paren(i):
  while s[i].isspace():i+=1
  assert s[i]=='(';j=i+1;depth=1
  while depth:
   assert j<len(s);depth+=(s[j]=='(')-(s[j]==')');j+=1
  return j
 out=[]
 for m in re.finditer(r'\bsirv_gnrl_sync\s*#\s*',s):
  j=paren(m.end());a=re.match(r'\s*([A-Za-z_]\w*)\s*',s[j:]);assert a;j+=a.end()
  if a[1]!=name:continue
  j=paren(j)
  while s[j].isspace():j+=1
  assert s[j]==';';out.append(re.sub(r'\s+','',s[m.start():j+1]))
 assert len(out)==1,name
 return out[0]
for n,h in json.loads((R/'source_review.json').read_text()).items():
 ps=[Path(p)for p in F['source_sha256']if Path(p).name==n];assert len(ps)==1 and sha(ps[0])==F['source_sha256'][str(ps[0])];assert all(hashlib.sha256(instance436(ps[0].read_text(),name).encode()).hexdigest()==expected for name,expected in h.items()),n;sources[str(ps[0])]=sha(ps[0])
paths=json.loads((args.context.parent/'single_bit_paths.json').read_text())['paths'];assert len(paths)==3;db=A['library_sha256'];assert all(sha(Path(n))==h for n,h in db.items());sdc=args.timing.parent/'pt_written.sdc'
t=['set_app_var link_path [list * '+' '.join('{'+n+'}'for n in db)+']','read_verilog {'+str(mapped)+'}','current_design e203_soc_top','link_design e203_soc_top','source {'+str(sdc)+'}','update_timing -full','set firsts [list '+' '.join('{'+v['endpoint']+'}'for v in paths)+']','set f [open {'+str(R/'physical_chains.tsv')+'} w]','puts $f "first_D\tfirst_Q\tsecond_D\tfirst_D_fanin\tsetup_slack\thold_slack"',(R/'chain_guard.tcl').read_text()]
(R/'run.tcl').write_text('\n'.join(t)+'\n')
with(R/'tool.log').open('w')as f:q=subprocess.run(['/eda/synopsys/prime/prime_2022.03-SP5-1/bin/pt_shell','-f',str(R/'run.tcl')],cwd=str(R),stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,timeout=1200,env=dict(os.environ,SYNOPSYS_LC_ROOT='/eda/synopsys/lib_compiler/lib_compiler_2022.03-SP5'))
s=(R/'tool.log').read_text();assert q.returncode==0 and not re.search(r'^Error:',s,re.M)and'KWT_SINGLEBIT436_PASS'in s;rows=list(csv.DictReader((R/'physical_chains.tsv').open(),delimiter='\t'));assert len(rows)==3
for v,w in zip(rows,paths):assert v['first_D']==w['endpoint']and v['first_D_fanin']==w['startpoint'];assert float(v['setup_slack'])>=0 and float(v['hold_slack'])>=0
r={'pass':True,'scope':'Actual3originalasyncsinglebitinputs WDGIRQ/RTCIRQ/RTCToggle. Provided2FFsource andactualfirstQonlysecondD, bothstagescore_clk, interstagetimingnonnegative. No newfalsepaths orDUTchange, noanalogMTBFclaim.','mapped_sha256':sha(mapped),'source_sha256':sources,'source_equivalence_scope':'Exact3relevantsyncinstantiations plusgenericmodule387; wholePLIC/CLINTfilesareversion-hash-bound, notclaimedbyteequalpublicupstream','generic_source_guard_sha256':sha(args.cdc),'actual_SDC_sha256':sha(sdc),'physical_chains':rows,'reports_sha256':{'tool.log':sha(R/'tool.log'),'physical_chains.tsv':sha(R/'physical_chains.tsv')}}
(R/'result.json').write_text(json.dumps(r,indent=2)+'\n')
