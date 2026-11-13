"""Fresh-unpack, hash-verify, rebuild and rerun the released RTL and mapped SoC."""
from pathlib import Path
from collections import Counter
import argparse,json,hashlib,zipfile,subprocess,sys,time
ap=argparse.ArgumentParser();ap.add_argument('--package',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
C=Path('/home/2026contest/server6/s6_19usr/kwt_systembus_joint_20261111_01/conservative516');O=a.out;assert not O.exists();O.mkdir()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
package=json.loads(a.package.read_text());assert package['pass'];archive=Path(package['archive']);assert sha(archive)==package['archive_sha256']
U=O/'extracted';U.mkdir()
with zipfile.ZipFile(archive)as z:
 assert z.testzip()is None and all(not Path(n).is_absolute()and'..'not in Path(n).parts for n in z.namelist());z.extractall(U)
index=json.loads((U/'TECHNICAL_INDEX.json').read_text());assert sha(U/'TECHNICAL_INDEX.json')==package['index_sha256']
assert all(sha(U/n)==v['sha256']for n,v in index['files'].items());assert all(sha(Path(n))==v['sha256']for n,v in index['external_server_resources'].items())
V=U/'reproducible_source';soc=U/'platform_original_versioned';mapping=json.loads((U/'evidence/synthesis06/result.json').read_text());mapping.update(mapped=str(U/'mapped/mapped.v'),leaf_cells=str(U/'mapped/leaf_cells.tsv'));assert sha(Path(mapping['mapped']))==index['mapped_sha256'];mp=O/'mapping.json';mp.write_text(json.dumps(mapping,indent=2)+'\n')
r={'pass':False,'archive_sha256':sha(archive),'index_sha256':sha(U/'TECHNICAL_INDEX.json'),'mapped_sha256':index['mapped_sha256'],'archive_entries_verified':len(index['files']),'steps':[]}
def save():(O/'result.json').write_text(json.dumps(r,indent=2)+'\n')
def run(name,args):
 start=time.time()
 with(O/(name+'.log')).open('w')as f:z=subprocess.run([str(x)for x in [sys.executable,'-B']+args],cwd=O,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,timeout=14400)
 r['steps'].append({'stage':name,'exit':z.returncode,'seconds':time.time()-start,'log_sha256':sha(O/(name+'.log'))});save();assert z.returncode==0,name
save();run('prepare',[V/'hardware/prepare.py','--soc-root',soc,'--vendors-record',U/'VENDOR_MODELS.json','--out',O/'prepared'])
m=json.loads((O/'prepared/source_manifest.json').read_text());expected_rtl=[v['sha256']for n,v in index['files'].items()if n.startswith('actual_RTL/')];assert len(expected_rtl)==index['source_RTL_files'];assert Counter(m['RTL_sources'].values())==Counter(expected_rtl)
checked=[]
for kind,extra in [('RTL',[]),('mapped',['--mapping',mp])]:
 dest=O/('full_'+kind);run(kind,[V/'verification/run_release.py','--prepared',O/'prepared/source_manifest.json','--soc',soc,'--out',dest]+extra)
 q=json.loads((dest/'result.json').read_text());old=json.loads((U/'evidence'/('rtl_full04'if kind=='RTL'else'mapped_full06')/'result.json').read_text());assert q['pass']and len(q['cases'])==len(old['cases'])==16
 for case in q['cases']:
  ref=next(x for x in old['cases']if all(x[k]==case[k]for k in ['case','command_gap','response_gap']))
  keys=['cold_cycles','driver_return_cycles','TCM_task_data_words','source_writes','source_reads','output_writes','output_acks','raw_codes','quant_codes','physical_pin_readback_words','loader_commands','loader_responses','original_split_peak','shared_port_peak']
  assert all(case[k]==ref[k]for k in keys),(kind,case['case'])
 checked.append({'implementation':kind,'cases':16,'source_and_result_transactions_exact':True,'all_frozen_cycle_counts_exact':True,'result_sha256':sha(dest/'result.json')})
# The installed default server Python also exercises the relocated public converter.
import struct,importlib.util
PD=U/'evaluation_support/portable04';spec=importlib.util.spec_from_file_location('relocated_stdlib_adapter',PD/'portable_convert.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
expected=json.loads((PD/'expected.json').read_text());src=[int(x,16)for x in(V/'verification/vectors/source.hex').read_text().split()];matrix=[int(x,16)for x in(V/'verification/vectors/matrix.hex').read_text().split()];PO=O/'portable_CLI';PO.mkdir();portable=[]
for c in expected:
 k=c['layer'];h=PO/('source%d.hex'%k);meta=PO/('meta%d.json'%k);raw=PO/('result%d.hex'%k);out=PO/('decoded%d.npy'%k)
 run('encode%d'%k,[PD/'portable_convert.py','encode','--project',V,'--input',V/('examples/layer_%02d_input.npy'%k),'--layer',k,'--source-hex',h,'--decode-metadata',meta]);assert sha(h)==c['source_hex_sha256']and[int(x,16)for x in h.read_text().split()]==src[k*8168:(k+1)*8168]
 raw.write_text(''.join('%08x\n'%v for v in matrix[k*12672:(k+1)*12672]));run('decode%d'%k,[PD/'portable_convert.py','decode','--result-hex',raw,'--decode-metadata',meta,'--decoded',out]);shape,values=mod.read_npy(out);assert shape==(99,256)and hashlib.sha256(struct.pack('<25344d',*values)).hexdigest()==c['decoded_f64_payload_sha256'];portable.append({'layer':k,'source_words_exact':8168,'decoded_float64_values_exact':25344})
r.update(pass_=True,cases=checked,actual_prepared_source_hash_multiset_exact=True,full_cold_relocated_RTL_and_mapped_pass=True,relocated_stdlib_CLI_cases=portable);r['pass']=True;save()
