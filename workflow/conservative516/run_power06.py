"""Same-netlist, exact cold-window, whole digital SoC averaged preCTS power."""
from pathlib import Path
from decimal import Decimal
from collections import Counter
from concurrent.futures import ThreadPoolExecutor,as_completed
import argparse,json,hashlib,re,subprocess,os,time,csv,sys
ap=argparse.ArgumentParser()
for n in ['mapping','function','timing','activity','out']:ap.add_argument('--'+n,type=Path,required=True)
a=ap.parse_args();R=Path('/home/2026contest/server6/s6_19usr/kwt_systembus_joint_20261111_01');sys.path.insert(0,str(R/'native_power389'));from report_parsers import annotation
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
O=a.out;assert not O.exists();O.mkdir();syn=json.loads(a.mapping.read_text());func=json.loads(a.function.read_text());pt=json.loads(a.timing.read_text());act=json.loads(a.activity.read_text())
assert all(q['pass']for q in [syn,func,pt,act]);assert len(func['cases'])==16 and len(act['activity_cases'])==12
assert len({q['mapped_sha256']for q in [syn,func,pt,act]})==1
mapped=Path(syn['mapped']);assert sha(mapped)==syn['mapped_sha256'];assert all(sha(Path(n))==h for n,h in syn['library_sha256'].items())
assert act['function_result_sha256']==sha(a.function)and act['firmware_sha256']==func['firmware_sha256']and act['testbench_sha256']==func['testbench_sha256']
sdcp=a.timing.parent/'pt_written.sdc';assert sha(sdcp)==pt['actual_SDC_sha256']
loc=Path('/home/2026contest/server6/s6_19usr/kwt_side_20261111_005646/mainchat01/closeout105/resource_locations01.json');libs=json.loads(Path(json.loads(loc.read_text())['config']).read_text())['libraries']
(O/'cdc_guard97.tcl').write_bytes((a.timing.parent/'cdc_guard97.tcl').read_bytes())
leaf=list(csv.DictReader(Path(syn['leaf_cells']).open(),delimiter='\t'))
r={'pass':False,'mapped_sha256':syn['mapped_sha256'],'source_manifest_sha256':syn['source_manifest_sha256'],'mapping_result_sha256':sha(a.mapping),'function_result_sha256':sha(a.function),'activity_result_sha256':sha(a.activity),'timing_result_sha256':sha(a.timing),'actual_final_SDC_sha256':sha(sdcp),'library_sha256':syn['library_sha256'],'firmware_sha256':func['firmware_sha256'],'testbench_sha256':func['testbench_sha256'],'corner':'SS0.99V125C','frequency_Hz':150000000,'scope':__doc__,'initial_x_transitions':True,'window':'input/parameterloading andCPUconfiguration through final12672writeACK; noCPUtail/oracle','case_selection':'frozenentry0for12layers;validation;notselectedonscore','cases':[],'final_source_timing_warning_review_complete':False}
def save():(O/'result.json').write_text(json.dumps(r,indent=2)+'\n')
def tl(xs):return '[list '+' '.join('{'+str(x)+'}'for x in xs)+']'
number=r'[+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?';units={'W':Decimal(1),'mW':Decimal('1e-3'),'uW':Decimal('1e-6'),'nW':Decimal('1e-9'),'pW':Decimal('1e-12')}
def numeric_power(D):
 texts=[(D/'power.rpt').read_text(),(D/'power_verbose.rpt').read_text()];factors=[];lines={}
 for label in ['Dynamic Power Units','Leakage Power Units']:
  rows=[s for s in texts[1].splitlines()if re.match(r'\s*'+label+r'\s*=',s)];assert len(rows)==1
  m=re.fullmatch(r'\s*'+label+r'\s*=\s*('+number+r')\s*(W|mW|uW|nW|pW)\s*',rows[0]);assert m;factors.append(Decimal(m[1])*units[m[2]]);lines[label]=rows[0]
 assert factors[0]==factors[1]and factors[0]>0
 totals=[]
 for label,t in zip(['default','verbose'],texts):
  rows=[s for s in t.splitlines()if re.match(r'\s*Total Power\s*=',s)];assert len(rows)==1
  m=re.fullmatch(r'\s*Total Power\s*=\s*('+number+r')(?:\s+\([^\r\n]*\))?\s*',rows[0]);assert m;totals.append(Decimal(m[1]));lines[label+'_total']=rows[0]
 assert totals[0]==totals[1]and totals[0]>0
 groups={}
 for name in ['memory','black_box']:
  rows=[s for s in texts[0].splitlines()if re.match(r'\s*'+name+r'\s+',s)];assert len(rows)==1,(name,rows)
  vals=re.findall(number,rows[0].split(name,1)[1]);assert len(vals)>=4;groups[name]={'line':rows[0],'first_four_library_units':vals[:4]}
 assert Decimal(groups['memory']['first_four_library_units'][0])>0 and Decimal(groups['memory']['first_four_library_units'][2])>0,'Macrointernal/leakagepowernotmodeled'
 assert all(Decimal(z)==0 for z in groups['black_box']['first_four_library_units']),'Unmodeledblackboxpower'
 return totals[0]*factors[0],lines,groups
def one(c):
 case=c['case'];D=O/('case%d'%case);D.mkdir();vcd=Path(c['path']);audit=Path(c['audit_path']);assert c['pass']and sha(vcd)==c['sha256']and sha(audit)==c['audit_sha256']
 q=json.loads(audit.read_text());assert q['pass']and q['all56_macro_port_shapes_exact']and sum(q['actual_macro_inventory'].values())==56 and q['mapped_sha256']==syn['mapped_sha256']
 commands=['set_host_options -max_cores 1','set_app_var power_enable_analysis true','set_app_var power_analysis_mode averaged','set_app_var power_include_initial_x_transitions true','set_app_var link_path '+tl(['*']+list(syn['library_sha256'])),'read_verilog {'+str(mapped)+'}','current_design e203_soc_top','link_design e203_soc_top','set_operating_conditions -library {'+libs['operating_library']+'} {'+libs['operating_conditions']+'}','source {'+str(sdcp)+'}','set audit_out {'+str(D)+'}','source {'+str(O/'cdc_guard97.tcl')+'}','update_timing -full']
 reports={'units.rpt':'report_units','check_timing.rpt':'check_timing -verbose','coverage.rpt':'report_analysis_coverage -status_details {untested violated}','constraints.rpt':'report_constraint -all_violators','setup.rpt':'report_timing -delay_type max -max_paths 10 -slack_lesser_than 1000000 -significant_digits 6','hold.rpt':'report_timing -delay_type min -max_paths 10 -slack_lesser_than 1000000 -significant_digits 6','disabled_timing.rpt':'report_disable_timing','case_analysis.rpt':'report_case_analysis','clocks.rpt':'report_clock -attributes'}
 commands+=['redirect {'+str(D/n)+'} {'+v+'}'for n,v in reports.items()]
 commands+=['read_vcd -strip_path native_cpu_tb/u_soc {'+str(vcd)+'}','update_power']
 reports={'activity.rpt':'report_switching_activity','activity_unannotated.rpt':'report_switching_activity -list_not_annotated','power.rpt':'report_power','power_verbose.rpt':'report_power -verbose','power_hierarchy.rpt':'report_power -hierarchy'}
 commands+=['redirect {'+str(D/n)+'} {'+v+'}'for n,v in reports.items()]+['puts {CURRENT_FIXED16_WHOLE_SOC_POWER_DONE}','quit'];(D/'run.tcl').write_text('\n'.join(commands)+'\n');start=time.time()
 with(D/'tool.log').open('w')as f:z=subprocess.run(['/eda/synopsys/prime/prime_2022.03-SP5-1/bin/pt_shell','-f',str(D/'run.tcl')],cwd=D,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,timeout=3600,env=dict(os.environ,SYNOPSYS_LC_ROOT='/eda/synopsys/lib_compiler/lib_compiler_2022.03-SP5'))
 log=(D/'tool.log').read_text(errors='replace');assert z.returncode==0 and not re.search(r'^Error:',log,re.M)and'CURRENT_FIXED16_WHOLE_SOC_POWER_DONE'in log
 watts,lines,groups=numeric_power(D);counts=annotation(D/'activity.rpt');assert counts==annotation(D/'activity_unannotated.rpt')
 warnings=Counter(re.findall(r'^Warning:.*\(([A-Z]+-\d+)\)',log,re.M));assert set(warnings)<=set(['PWR-278','PTE-003','PTE-052']),warnings
 empty={}
 for name in set(re.findall(r"The hierarchical cell '([^']+)' is an empty cell",log)):
  matched=[v for v in leaf if v['name']==name or v['name'].startswith(name+'/')];pseudo=[v for v in matched if v['ref'].lower()in ['**logic_0**','**logic_1**']];assert all(v['area']in ['', '0', '0.0']and int(v['library_matches'])==0 for v in pseudo);empty[name]=len(matched)-len(pseudo)
 assert not any(empty.values()),empty
 slacks={}
 for name in ['setup','hold']:
  vals=[float(x)for x in re.findall(r'slack\s*\([^)]*\)\s*([+-]?[0-9.]+)',(D/(name+'.rpt')).read_text(),re.I)];assert vals and min(vals)>=0;slacks[name]=min(vals)
 duration=Decimal(str(c['duration_ns']));energy=watts*duration*Decimal('1e-9')
 return {'pass':True,'case':case,'cold_cycles':c['cold_cycles'],'duration_ns':str(duration),'watts':str(watts),'joules':str(energy),'actual_numeric_lines':lines,'memory_and_blackbox_groups':groups,'direct_activity_and_probability_nets':counts,'warnings':dict(warnings),'timing_warning_lines':[s for s in log.splitlines()if'(PTE-003)'in s or'(PTE-052)'in s],'PWR278_leaf_counts':empty,'setup_min_ns':slacks['setup'],'hold_min_ns':slacks['hold'],'activity_sha256':c['sha256'],'audit_sha256':c['audit_sha256'],'reports_sha256':{p.name:sha(p)for p in D.iterdir()if p.is_file()},'seconds':time.time()-start}
save()
with ThreadPoolExecutor(max_workers=2)as ex:
 for f in as_completed([ex.submit(one,c)for c in act['activity_cases']]):r['cases'].append(f.result());save()
r['cases'].sort(key=lambda c:c['case']);assert [c['case']for c in r['cases']]==list(range(12))
energy=sum(Decimal(c['joules'])for c in r['cases']);seconds=sum(Decimal(c['duration_ns'])for c in r['cases'])*Decimal('1e-9')
r.update(mean_energy_J=str(energy/12),time_weighted_watts=str(energy/seconds),cold_tasks_s=str(Decimal(12)/seconds));r['pass']=True;save()
