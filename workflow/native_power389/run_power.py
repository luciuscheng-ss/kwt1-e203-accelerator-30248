"""Full digital UART339/CPU236 loader368 mode0 cold-window averaged preCTS energy.
Actual whole-SoC activity only; no default activity replacement, analog/offchip
power, old TCM architecture metrics, or official-loader equivalence claim.
"""
from pathlib import Path
from decimal import Decimal
from collections import Counter
import json,hashlib,re,subprocess,os,time
from report_parsers import annotation
def stream_sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
 return h.hexdigest()
R=Path(__file__).resolve().parent;P=R.parent;A=P/'native_uart339';F=P/'native_activity372';T=P/'native_pt395';sha=lambda p:stream_sha(p)
M=json.loads((R/'MANIFEST.json').read_text());assert all(sha(R/n)==h for n,h in M.items())
deadline=time.time()+7200
while not(F/'result.json').exists():
 e=P/'launch_activity372/exit.code';assert not e.exists()or e.read_text().strip()=='0','Activity372 failed';assert time.time()<deadline;time.sleep(2)
syn=json.loads((A/'result.json').read_text());full=json.loads((F/'result.json').read_text());pt=json.loads((T/'result.json').read_text());function=json.loads((P/'native_full368/result.json').read_text());assert syn['pass']and function['pass']and len(function['cases'])==56 and pt['pass'];assert full['mapped_sha256']==function['mapped_sha256']and full['firmware_sha256']==function['firmware_sha256']and full['testbench_sha256']==function['testbench_sha256'];assert pt['engineering_setup_hold_nonnegative'];mapped=A/'synth/mapped.v';assert sha(mapped)==syn['mapped_sha256']==full['mapped_sha256']==pt['mapped_sha256'];assert all(sha(n)==h for n,h in syn['library_sha256'].items())
loc=Path('/home/2026contest/server6/s6_19usr/kwt_side_20261111_005646/mainchat01/closeout105/resource_locations01.json');libs=json.loads(Path(json.loads(loc.read_text())['config']).read_text())['libraries']
r={'scope':__doc__,'pass':False,'numeric_reports_complete':False,'coverage_review_pending':True,'official_conditions_qualified':False,'official_loader_qualified':False,'power_qualified':False,'mapped_sha256':sha(mapped),'synthesis_result_sha256':sha(A/'result.json'),'mapped_function_result_sha256':sha(P/'native_full368/result.json'),'activity_workflow_manifest_sha256':sha(F/'MANIFEST.json'),'team_acceptance_sha256':sha(F/'acceptance319.json'),'PT_result_sha256':sha(T/'result.json'),'actual_final_SDC_sha256':sha(T/'pt_written.sdc'),'actual_final_SDC_path':str(T/'pt_written.sdc'),'library_sha256':syn['library_sha256'],'firmware_sha256':full['firmware_sha256'],'data_split':'validation','case_selection':'fixed entry0 for all12 layers, never selected from measured scores','mode':0,'initial_x_policy':True,'analysis':'averaged whole digital preCTS, engineering SS0.99V125C, realCPU236+WFI existing MEM boundary timed loader','cases':[]}
def write():(R/'result.json').write_text(json.dumps(r,indent=2)+'\n')
def tl(xs):return '[list '+' '.join('{'+str(z)+'}'for z in xs)+']'
def ref(p):return {'path':str(p),'sha256':sha(p)}
number=r'[+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?';units={'W':Decimal(1),'mW':Decimal('1e-3'),'uW':Decimal('1e-6'),'nW':Decimal('1e-9'),'pW':Decimal('1e-12')}
def numeric_power(O):
 text=(O/'power.rpt').read_text();verbose=(O/'power_verbose.rpt').read_text();out={};factors=[]
 for label in ['Dynamic Power Units','Leakage Power Units']:
  rows=[s for s in verbose.splitlines()if re.match(r'\s*'+label+r'\s*=',s)];assert len(rows)==1
  m=re.fullmatch(r'\s*'+label+r'\s*=\s*('+number+r')\s*(W|mW|uW|nW|pW)\s*',rows[0]);assert m;factors.append(Decimal(m.group(1))*units[m.group(2)]);out[label]=rows[0]
 assert factors[0]==factors[1]and factors[0]>0,'Mixed or invalid report units require component review'
 vals=[]
 for key,t in [('default',text),('verbose',verbose)]:
  rows=[s for s in t.splitlines()if re.match(r'\s*Total Power\s*=',s)];assert len(rows)==1
  m=re.fullmatch(r'\s*Total Power\s*=\s*('+number+r')(?:\s+\([^\r\n]*\))?\s*',rows[0]);assert m;vals.append(Decimal(m.group(1)));out[key+'_total']=rows[0]
 assert vals[0]==vals[1]and vals[0]>0;return vals[0]*factors[0],out
write()
for case in [0, 1, 2, 3]:
 deadline=time.time()+3600
 while True:
  full=json.loads((F/'result.json').read_text());matches=[c for c in full['activity_cases']if c['case']==case and c['mode']==0]
  if len(matches)==1:break
  assert len(matches)==0;exitfile=P/'launch_activity372/exit.code';assert not exitfile.exists()or exitfile.read_text().strip()=='0','Activity workflow failed; no missing data accepted';assert time.time()<deadline,'Activity not ready within bound';time.sleep(2)
 c=matches[0];assert c['pass'];activity=Path(c['path']);audit=Path(c['audit_path']);assert sha(activity)==c['sha256']and sha(audit)==c['audit_sha256'];q=json.loads(audit.read_text());assert q['pass']and q['all56_macro_port_shapes_exact']and q['mapped_sha256']==r['mapped_sha256'];assert sum(q['actual_macro_inventory'].values())==56
 O=R/('case%d'%case);O.mkdir();commands=['set_host_options -max_cores 1','set_app_var power_enable_analysis true','set_app_var power_analysis_mode averaged','set_app_var power_include_initial_x_transitions true','set_app_var link_path '+tl(['*']+list(syn['library_sha256'])),'read_verilog {'+str(mapped)+'}','current_design e203_soc_top','link_design e203_soc_top','set_operating_conditions -library {'+libs['operating_library']+'} {'+libs['operating_conditions']+'}','source {'+str(T/'pt_written.sdc')+'}','set audit_out {'+str(O)+'}','source {'+str(R/'cdc_guard97.tcl')+'}','update_timing -full']
 reports={'units.rpt':'report_units','check_timing.rpt':'check_timing -verbose','coverage.rpt':'report_analysis_coverage -status_details {untested violated}','constraints.rpt':'report_constraint -all_violators','timing_setup.rpt':'report_timing -delay_type max -max_paths 10 -slack_lesser_than 1000000 -significant_digits 6','timing_hold.rpt':'report_timing -delay_type min -max_paths 10 -slack_lesser_than 1000000 -significant_digits 6','disabled_timing.rpt':'report_disable_timing','case_analysis.rpt':'report_case_analysis','clocks.rpt':'report_clock -attributes'}
 commands+=['redirect {'+str(O/n)+'} {'+v+'}'for n,v in reports.items()];commands+=['read_vcd -strip_path native_cpu_tb/u_soc {'+str(activity)+'}','update_power']
 reports={'activity.rpt':'report_switching_activity','activity_unannotated.rpt':'report_switching_activity -list_not_annotated','power.rpt':'report_power','power_verbose.rpt':'report_power -verbose','power_hierarchy.rpt':'report_power -hierarchy'}
 commands+=['redirect {'+str(O/n)+'} {'+v+'}'for n,v in reports.items()];commands+=['puts {KWT_FINAL_WHOLE_DIGITAL_POWER_COMPLETED}','quit'];(O/'run.tcl').write_text('\n'.join(commands)+'\n');start=time.time()
 with(O/'tool.log').open('w')as f:p=subprocess.run(['/eda/synopsys/prime/prime_2022.03-SP5-1/bin/pt_shell','-f',str(O/'run.tcl')],cwd=str(O),stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,timeout=1800,env=dict(os.environ,SYNOPSYS_LC_ROOT='/eda/synopsys/lib_compiler/lib_compiler_2022.03-SP5'))
 log=(O/'tool.log').read_text(errors='replace');assert p.returncode==0 and not re.search(r'^Error:',log,re.M)and'KWT_FINAL_WHOLE_DIGITAL_POWER_COMPLETED'in log
 watts,lines=numeric_power(O);warnings=Counter(re.findall(r'^Warning:.*\(([A-Z]+-\d+)\)',log,re.M));ann={'pass':False}
 try:ann={'pass':True,'direct_activity_and_probability_nets':annotation(O/'activity.rpt')};assert annotation(O/'activity_unannotated.rpt')==ann['direct_activity_and_probability_nets']
 except(Exception)as e:ann={'pass':False,'requires_actual_coverage_review':str(e)}
 slacks={}
 for name in ['setup','hold']:
  slacks[name]=[float(z)for z in re.findall(r'slack\s*\([^)]*\)\s*([+-]?[0-9.]+)',(O/('timing_'+name+'.rpt')).read_text(),re.I)];assert slacks[name]and min(slacks[name])>=0
 duration=Decimal(str(c['duration_ns']));energy=watts*duration*Decimal('1e-9');v={'case':case,'mode':0,'cold_cycles':c['cold_cycles'],'duration_ns':str(duration),'watts':str(watts),'joules':str(energy),'actual_numeric_lines':lines,'annotation':ann,'warnings':dict(warnings),'setup_min_ns':min(slacks['setup']),'hold_min_ns':min(slacks['hold']),'activity':ref(activity),'audit':ref(audit),'reports':{str(n):sha(n)for n in O.iterdir()if n.is_file()},'tool_seconds':time.time()-start,'manual_macro_state_and_warning_review_pending':True};r['cases'].append(v);write();assert ann['pass'],'Incomplete direct activity/probability annotation, no further cases accepted'
assert len(r['cases'])==4;r['worker_subset']=[0, 1, 2, 3];r['worker_complete']=True;r['pass']=True;write()
