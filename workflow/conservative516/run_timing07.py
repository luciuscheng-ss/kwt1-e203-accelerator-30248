"""Same-map functional150MHz preCTS STA, including source-guarded CDC checks."""
from pathlib import Path
from collections import Counter
import argparse,json,hashlib,subprocess,os,time,re
ap=argparse.ArgumentParser();ap.add_argument('--mapping',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
R=Path('/home/2026contest/server6/s6_19usr/kwt_systembus_joint_20261111_01');C=R/'conservative516';O=a.out;assert not O.exists();O.mkdir()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();syn=json.loads(a.mapping.read_text());assert syn['pass'];mapped=Path(syn['mapped']);assert sha(mapped)==syn['mapped_sha256'];assert all(sha(Path(n))==h for n,h in syn['library_sha256'].items())
cfg=Path(json.loads(Path('/home/2026contest/server6/s6_19usr/kwt_side_20261111_005646/mainchat01/closeout105/resource_locations01.json').read_text())['config']);libs=json.loads(cfg.read_text())['libraries']
text=(a.mapping.parent/'constraints.sdc').read_text().replace('set_fix_hold [all_clocks]','# Implementation-only hold repair command omitted from analysis.')
text+='\n'+''.join('set_case_analysis 1 [get_ports io_pads_dbgmode%d_n_i_ival]\n'%i for i in range(3))+'set_case_analysis 0 [get_ports io_pads_bootrom_n_i_ival]\nset_case_analysis 1 [get_ports io_pads_aon_pmu_dwakeup_n_i_ival]\nset_case_analysis 1 [get_ports io_pads_aon_erst_n_i_ival]\n'
for n in ['cdc_guard97.tcl','async_cdc388.tcl']:(O/n).write_bytes((R/'native_pt395'/n).read_bytes())
text+=(O/'async_cdc388.tcl').read_text();(O/'constraints.sdc').write_text(text)
def tl(xs):return '[list '+' '.join('{'+str(x)+'}'for x in xs)+']'
cmd=['set_host_options -max_cores 1','set_app_var link_path '+tl(['*']+list(syn['library_sha256'])),'read_verilog {'+str(mapped)+'}','current_design e203_soc_top','link_design e203_soc_top','set_operating_conditions -library {'+libs['operating_library']+'} {'+libs['operating_conditions']+'}','source {'+str(O/'constraints.sdc')+'}','set audit_out {'+str(O)+'}','source {'+str(O/'cdc_guard97.tcl')+'}','update_timing -full']
reports={'units.rpt':'report_units','check_timing.rpt':'check_timing -verbose','coverage.rpt':'report_analysis_coverage -status_details {untested violated}','setup.rpt':'report_timing -delay_type max -path_type full_clock_expanded -input_pins -nets -max_paths 40 -slack_lesser_than 1000000 -significant_digits 12','hold.rpt':'report_timing -delay_type min -path_type full_clock_expanded -input_pins -nets -max_paths 40 -slack_lesser_than 1000000 -significant_digits 12','constraints.rpt':'report_constraint -all_violators -significant_digits 12','disabled_timing.rpt':'report_disable_timing','case_analysis.rpt':'report_case_analysis','clocks.rpt':'report_clock -attributes'}
cmd += ['redirect {'+str(O/n)+'} {'+v+'}'for n,v in reports.items()]
cmd += ['set f [open {'+str(O/'async_crossing_endpoints.tsv')+'} w];puts $f "from_clock\tto_clock\tstartpoint\tendpoint\tslack"','foreach pair {{core_clk lf_clk} {lf_clk core_clk}} {lassign $pair a b;set ps [get_timing_paths -from [get_clocks $a] -to [get_clocks $b] -delay_type max -max_paths 10000 -nworst 1 -slack_lesser_than 1000000];if {[sizeof_collection $ps]==0||[sizeof_collection $ps]>=10000} {error "Incomplete async crosspath enumeration"};foreach_in_collection p $ps {set sp [get_object_name [get_attribute $p startpoint]];set ep [get_object_name [get_attribute $p endpoint]];if {[string match {*u_kwt*} "$sp/$ep"]} {error "Unreviewed accelerator clock crossing"};puts $f "$a\t$b\t$sp\t$ep\t[get_attribute $p slack]"}};close $f']
cmd += ['set f [open {'+str(O/'physical_output_fanout.tsv')+'} w];puts $f "pin\treceiver_pins\tports"','foreach_in_collection p [get_pins -hierarchical * -filter {direction == out}] {set c [get_cells -of_objects $p];if {[sizeof_collection $c]!=1||[get_attribute $c is_hierarchical]} {continue};set ns [get_nets -quiet -of_objects $p];set receivers {};set ports {};if {[sizeof_collection $ns]>0} {set receivers [get_pins -quiet -of_objects $ns -filter {direction == in}];set ports [get_ports -quiet -of_objects $ns]};puts $f "[get_object_name $p]\t[sizeof_collection $receivers]\t[sizeof_collection $ports]"};close $f']
cmd += ['set f [open {'+str(O/'register_clock_pins.tsv')+'} w]','puts $f "pin\tclock_count"','foreach_in_collection p [all_registers -clock_pins] {puts $f "[get_object_name $p]\t[sizeof_collection [get_attribute $p clocks]]"}','close $f','write_sdc {'+str(O/'pt_written.sdc')+'}','write_sdf {'+str(O/'mapped.sdf')+'}','puts {FIXED16_CURRENT_STA_DONE}','quit']
(O/'run.tcl').write_text('\n'.join(cmd)+'\n');r={'pass':False,'mapped_sha256':syn['mapped_sha256'],'mapping_result_sha256':sha(a.mapping),'library_sha256':syn['library_sha256'],'corner':'SS0.99V125C','frequency_Hz':150000000,'stage':'preCTS logical idealclock,zero nominal latency,no extracted wires','source_guarded_CDC_script_sha256':sha(O/'cdc_guard97.tcl'),'asynchronous_delay_script_sha256':sha(O/'async_cdc388.tcl')}
def save():(O/'result.json').write_text(json.dumps(r,indent=2)+'\n')
save();start=time.time()
with(O/'tool.log').open('w')as f:z=subprocess.run(['/eda/synopsys/prime/prime_2022.03-SP5-1/bin/pt_shell','-f',str(O/'run.tcl')],cwd=O,stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,timeout=3600,env=dict(os.environ,SYNOPSYS_LC_ROOT='/eda/synopsys/lib_compiler/lib_compiler_2022.03-SP5'))
t=(O/'tool.log').read_text(errors='replace');r.update(exit=z.returncode,seconds=time.time()-start,errors=re.findall(r'^Error:.*$',t,re.M));save();assert z.returncode==0 and not r['errors']and'FIXED16_CURRENT_STA_DONE'in t
for key in ['setup','hold']:
 v=[float(x)for x in re.findall(r'slack\s*\([^)]*\)\s*([+-]?[0-9.]+)',(O/(key+'.rpt')).read_text(),re.I)];assert v;r[key+'_min_ns']=min(v)
lines=(O/'check_timing.rpt').read_text().splitlines();heads=[]
for i,s in enumerate(lines):
 m=re.search(r"Information:\s*Checking\s+'([^']+)'",s,re.I)
 if m:heads.append((i,m[1]))
sections={}
for key in ['noclock','unconstrainedendpoints']:
 hits=[i for i,n in heads if re.sub(r'[_\s]+','',n).lower()==key];assert len(hits)==1
 i=hits[0];end=next((j for j,n in heads if j>i),len(lines));sections[key]=[s.strip()for s in lines[i+1:end]if s.strip()]
reason=Counter();pins=Counter();last=''
for s in(O/'coverage.rpt').read_text().splitlines():
 if 'u_e203_subsys_top/'in s or'u_kwt'in s:last=s.strip()
 m=re.search(r'\buntested\s+(\w+)\s*$',s,re.I)
 if m:reason[m[1]]+=1
 if re.search(r'\buntested\s+no_clock\s*$',s,re.I):pins[last.rsplit('/',1)[-1]]+=1
r.update(check_timing_sections=sections,untested_reason_counts=dict(reason),no_clock_pin_classes=dict(pins),actual_SDC_sha256=sha(O/'pt_written.sdc'),reports_sha256={p.name:sha(p)for p in O.glob('*.rpt')})
r['numeric_timing_met']=r['setup_min_ns']>=0 and r['hold_min_ns']>=0
r['coverage_review_pass']=all(not x for x in sections.values())and all(re.fullmatch(r'(RDN|SDN)\s*\(LOW\)',k,re.I)for k in pins)and set(reason).issubset({'constant_disabled','false_paths','no_clock'})
import csv
def parse_capacities(lines):
 result={};category=''
 for i,line in enumerate(lines):
  label=line.strip()
  if re.fullmatch(r'(?:max|min)_[a-z_]+',label):category=label
  if '(VIOLATED)'not in line or category not in ['max_capacitance','min_capacitance']:continue
  tokens=line.split('(VIOLATED')[0].split()
  # PrimeTime may print name+numbers on one line, name on previous line,
  # or the marker on its own line. Require three numeric values in all forms.
  if len(tokens)<3:
   assert i>=2;tokens=lines[i-1].split();pin=lines[i-2].strip()
  elif len(tokens)==3:pin=lines[i-1].strip()
  else:pin=' '.join(tokens[:-3]);tokens=tokens[-3:]
  assert len(tokens)==3 and pin and ' 'not in pin,(category,line)
  result.setdefault(category,[]).append({'pin':pin,'required':float(tokens[0]),'actual':float(tokens[1]),'slack':float(tokens[2])})
 return result
sections_cap=parse_capacities((O/'constraints.rpt').read_text().splitlines())
fan={v['pin']:v for v in csv.DictReader((O/'physical_output_fanout.tsv').open(),delimiter='\t')};unloaded=[];active=[]
for v in sections_cap.get('min_capacitance',[]):
 f=fan.get(v['pin']);assert f is not None,v['pin'];v.update(receiver_pins=int(f['receiver_pins']),ports=int(f['ports']))
 (unloaded if v['actual']==0 and v['receiver_pins']==0 and v['ports']==0 else active).append(v)
r.update(max_capacitance_violations=sections_cap.get('max_capacitance',[]),active_min_capacitance_violations=active,unloaded_output_min_capacitance_diagnostics=unloaded,capacitance_guard_pass=not sections_cap.get('max_capacitance')and not active)
r['pass']=r['numeric_timing_met']and r['coverage_review_pass']and r['capacitance_guard_pass'];save();print(json.dumps({'pass':r['pass'],'setup':r['setup_min_ns'],'hold':r['hold_min_ns'],'coverage':r['coverage_review_pass']}))
