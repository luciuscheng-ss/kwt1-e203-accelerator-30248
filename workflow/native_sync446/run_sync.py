from pathlib import Path
import json,hashlib,re,subprocess,os,csv
R=Path(__file__).resolve().parent;P=R.parent;sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();M=json.loads((R/'MANIFEST.json').read_text());assert all(sha(R/n)==h for n,h in M.items())
F=json.loads((P/'native_full368/result.json').read_text());A=json.loads((P/'native_uart339/result.json').read_text());mapped=P/'native_uart339/synth/mapped.v';assert sha(mapped)==A['mapped_sha256']==F['mapped_sha256'];G=json.loads((P/'guard387/result.json').read_text());assert G['sirv_gnrl_sync']['matches_public_local_reviewed_logic']and G['actual_async_depths']==['2']
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
paths=json.loads((P/'cross412/async_single_bit434.json').read_text())['paths'];assert len(paths)==3;db=A['library_sha256'];assert all(sha(Path(n))==h for n,h in db.items());sdc=P/'native_pt395/pt_written.sdc'
t=['set_app_var link_path [list * '+' '.join('{'+n+'}'for n in db)+']','read_verilog {'+str(mapped)+'}','current_design e203_soc_top','link_design e203_soc_top','source {'+str(sdc)+'}','update_timing -full','set firsts [list '+' '.join('{'+v['endpoint']+'}'for v in paths)+']','set f [open {'+str(R/'physical_chains.tsv')+'} w]','puts $f "first_D\tfirst_Q\tsecond_D\tfirst_D_fanin\tsetup_slack\thold_slack"',(R/'chain_guard.tcl').read_text()]
(R/'run.tcl').write_text('\n'.join(t)+'\n')
with(R/'tool.log').open('w')as f:q=subprocess.run(['/eda/synopsys/prime/prime_2022.03-SP5-1/bin/pt_shell','-f',str(R/'run.tcl')],cwd=str(R),stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,timeout=1200,env=dict(os.environ,SYNOPSYS_LC_ROOT='/eda/synopsys/lib_compiler/lib_compiler_2022.03-SP5'))
s=(R/'tool.log').read_text();assert q.returncode==0 and not re.search(r'^Error:',s,re.M)and'KWT_SINGLEBIT436_PASS'in s;rows=list(csv.DictReader((R/'physical_chains.tsv').open(),delimiter='\t'));assert len(rows)==3
for v,w in zip(rows,paths):assert v['first_D']==w['endpoint']and v['first_D_fanin']==w['startpoint'];assert float(v['setup_slack'])>=0 and float(v['hold_slack'])>=0
r={'pass':True,'scope':'Actual3originalasyncsinglebitinputs WDGIRQ/RTCIRQ/RTCToggle. Provided2FFsource andactualfirstQonlysecondD, bothstagescore_clk, interstagetimingnonnegative. No newfalsepaths orDUTchange, noanalogMTBFclaim.','mapped_sha256':sha(mapped),'source_sha256':sources,'source_equivalence_scope':'Exact3relevantsyncinstantiations plusgenericmodule387; wholePLIC/CLINTfilesareversion-hash-bound, notclaimedbyteequalpublicupstream','generic_source_guard_sha256':sha(P/'guard387/result.json'),'actual_SDC_sha256':sha(sdc),'physical_chains':rows,'reports_sha256':{'tool.log':sha(R/'tool.log'),'physical_chains.tsv':sha(R/'physical_chains.tsv')}}
(R/'result.json').write_text(json.dumps(r,indent=2)+'\n')
