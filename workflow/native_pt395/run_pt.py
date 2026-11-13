"""UART339/quant104 whole digital SoC SS timing audit with exact guarded LF first-D exceptions.
No timing/official-condition qualification is inferred from tool exit0.
"""
from pathlib import Path
import csv
import json,hashlib,subprocess,time,re,os
R=Path(__file__).resolve().parent;P=R.parent;S=P/'native_uart339';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
M=json.loads((R/'MANIFEST.json').read_text());assert all(sha(R/n)==h for n,h in M.items());A=P/'native_uart339';syn=json.loads((A/'result.json').read_text());assert syn['pass']and syn['memory_inventory_complete']and not syn['unmapped_or_black_boxes']
assert json.loads((P/'native_repair115/master_result.json').read_text())['pass'];assert syn['source_sha256'][next(n for n in syn['source_sha256']if Path(n).name=='scaled_quantize2.sv')]=='2451debded5ce3530ac7139cf0f1ab977d9a6f3ced335f9e8e031b73e3e3bb2f';mapped=S/'synth/mapped.v';assert sha(mapped)==syn['mapped_sha256'];assert all(sha(n)==h for n,h in syn['library_sha256'].items())
loc=Path('/home/2026contest/server6/s6_19usr/kwt_side_20261111_005646/mainchat01/closeout105/resource_locations01.json');cfg=json.loads(Path(json.loads(loc.read_text())['config']).read_text());libs=cfg['libraries'];db=list(syn['library_sha256'])
source=S/'synth/constraints.sdc';text=source.read_text();assert text.count('set_fix_hold [all_clocks]\n')==1
text=text.replace('set_fix_hold [all_clocks]\n','# DC hold-fixing implementation command omitted from PT analysis only.\n');text+='\n# Native CPU64 normal functional mode; inspect000 remains separate diagnostic.\n'+'\n'.join('set_case_analysis 1 [get_ports io_pads_dbgmode%d_n_i_ival]'%i for i in range(3))+'\n';text+='\n# Actual fixed inference board straps, verified in the same frozen testbench.\nset_case_analysis 0 [get_ports io_pads_bootrom_n_i_ival]\nset_case_analysis 1 [get_ports io_pads_aon_pmu_dwakeup_n_i_ival]\n';text+='\n# Functional inference mode: external reset deasserted throughout cold window. Reset/boot excluded by guide and separately tested.\nset_case_analysis 1 [get_ports io_pads_aon_erst_n_i_ival]\n';g=json.loads((P/'guard387/result.json').read_text());assert all(g[n]['matches_public_local_reviewed_logic']for n in ['sirv_gnrl_sync','sirv_gnrl_cdc_tx','sirv_gnrl_cdc_rx'])and g['actual_async_depths']==['2'];text+='\n'+(R/'async_cdc388.tcl').read_text();sdc=R/'constraints.sdc';sdc.write_text(text)
r={'scope':__doc__,'pass':False,'timing_qualified':False,'official_conditions_qualified':False,'mapped_sha256':sha(mapped),'parent_synthesis_result_sha256':sha(A/'result.json'),'library_sha256':syn['library_sha256'],'original_constraints_sha256':sha(source),'PT_constraints_sha256':sha(sdc),'constraint_delta':'DC hold-fix implementation instruction omitted; normal111 mode on three external dbgmode pins matching actual CPU64; all timing budgets and live data/gate checks preserved; exact4 source/connectivity-guarded LF-to-first-D exceptions; no broad clock groups; PT77/PT84 diagnostics retained','clock_model':'preCTS nominal latency0 and clock slew0.1ns, setup/hold uncertainty0.1ns; no extracted wires/CTS claim','corner':'actual engineering SS0.99V125C for both setup/min-delay audit; no FF result claimed','steps':[]}
r['tool_process_env']={'SYNOPSYS_LC_ROOT':'/eda/synopsys/lib_compiler/lib_compiler_2022.03-SP5','scope':'PT child only; no global configuration changes'}
assert Path(r['tool_process_env']['SYNOPSYS_LC_ROOT']+'/bin/lc_shell').is_file()
def write():(R/'result.json').write_text(json.dumps(r,indent=2)+'\n')
def tl(xs):return '[list '+' '.join('{'+str(z)+'}'for z in xs)+']'
F=P/'native_probe51';profile=json.loads((F/'resource_profile.json').read_text());meta=json.loads((P/'native_audit01/dependency_compare23.json').read_text());SOC=Path(meta['native_rtl_root']).parent.parent
mode_files=['rtl/e203/subsys/e203_subsys_main.v','rtl/e203/perips/sirv_aon_wrapper.v','rtl/e203/perips/apb_adv_timer/input_stage.v','rtl/e203/perips/apb_adv_timer/timer_module.v','rtl/e203/perips/apb_adv_timer/apb_adv_timer.v']
assert all(sha(SOC/n)==profile['source_sha256'][n]for n in mode_files)
tb=P/'native_full368/loader_cpu_tb.sv';tbtext=tb.read_text()
assert all(('.io_pads_dbgmode%d_n_i_ival(1\'b1)'%i)in tbtext for i in range(3))
r['normal_mode_case_analysis']={'io_pads_dbgmode%d_n_i_ival'%i:1 for i in range(3)};r['normal_mode_case_analysis'].update(io_pads_bootrom_n_i_ival=0,io_pads_aon_pmu_dwakeup_n_i_ival=1);assert ".io_pads_bootrom_n_i_ival(1'b0)"in tbtext and".io_pads_aon_pmu_dwakeup_n_i_ival(1'b1)"in tbtext
r['mode_source_proof_sha256']={n:sha(SOC/n)for n in mode_files};r['actual_CPU236_testbench_sha256']=sha(tb)
r['external_reset_mode']='Only deasserted functional inference, no fabricatedclock/falsepath or data/reset-register case. Raw-reset timing remains separately inspectable in342.';r['normal_mode_case_analysis']['io_pads_aon_erst_n_i_ival']=1;assert tbtext.count('rst_n=1;')==1 and tbtext.count('rst_n=0;')==1 and 'force rst_n'not in tbtext; r['mode_applicability']='Actual frozenCPU236 inference mode:dbg111/bootROMstrap0/externalwakeinactive1. Boardconfigurationpins only, no data/reset/internalUART/register cuts. UART24latches physicallyrepaired339; allactivepaths remain timed. Allotheroriginalclock/IO budgets unchanged.'
r['async_CDC_source_guard_sha256']=sha(P/'guard387/result.json');r['async_constraint_file_sha256']=sha(R/'async_cdc388.tcl');r['CDC_model']='PhysicalHF/LF asynchronous4phasehelddatawithactual2FFsync, source-normalized exactguard387; explicitmaxoneRECEIVERcycle-.1ns,min0 data delay ignoresclocklatency, no interstagecut or clockfrequencychange. LF-onlycontroloutputsprovenexactlaunchclockbeforeIOassociation. PTE052doesnotgoverntheseexplicitdelaychecks.';r['CDC_exceptions_applied']='Only4 lfextclk-to-first-D pairs, fresh source/connectivity checked in CDC97 Tcl; all interstage and functional paths still timed'
commands=[
 'set_host_options -max_cores 1',
 'set_app_var link_path '+tl(['*']+db),
 'read_verilog {'+str(mapped)+'}','current_design e203_soc_top','link_design e203_soc_top',
 'set_operating_conditions -library {'+libs['operating_library']+'} {'+libs['operating_conditions']+'}',
 'source {'+str(sdc)+'}',
 'update_timing -full',
 'set audit_out {'+str(R)+'}',
 'set f [open {'+str(R/'slow_output_clock_proof.tsv')+'} w];puts $f "port\tclocks\tstartpoints";foreach row $kwt_slow_output_proof {puts $f [join $row "\t"]};close $f',

 'source {'+str(R/'cdc_probe84.tcl')+'}',
 'source {'+str(R/'cdc_guard97.tcl')+'}',
 'update_timing -full',
 'redirect {'+str(R/'units.rpt')+'} {report_units}',
 'redirect {'+str(R/'check_timing.rpt')+'} {check_timing -verbose}',
 'redirect {'+str(R/'coverage.rpt')+'} {report_analysis_coverage -status_details {untested violated}}',
 'redirect {'+str(R/'global_timing.rpt')+'} {report_global_timing}',
 'redirect {'+str(R/'setup.rpt')+'} {report_timing -delay_type max -path_type full_clock_expanded -input_pins -nets -max_paths 40 -slack_lesser_than 1000000 -significant_digits 6}',
 'redirect {'+str(R/'hold.rpt')+'} {report_timing -delay_type min -path_type full_clock_expanded -input_pins -nets -max_paths 40 -slack_lesser_than 1000000 -significant_digits 6}',
 'redirect {'+str(R/'violations.rpt')+'} {report_constraint -all_violators}',
 'redirect {'+str(R/'clocks.rpt')+'} {report_clock -attributes}',
 'redirect {'+str(R/'reg2reg_setup.rpt')+'} {report_timing -from [all_registers -output_pins] -to [all_registers -data_pins] -delay_type max -path_type full_clock_expanded -max_paths 40 -slack_lesser_than 1000000 -significant_digits 6}',
 'redirect {'+str(R/'reg2reg_hold.rpt')+'} {report_timing -from [all_registers -output_pins] -to [all_registers -data_pins] -delay_type min -path_type full_clock_expanded -max_paths 40 -slack_lesser_than 1000000 -significant_digits 6}',
 'set async_endpoints [get_pins -hierarchical -filter {full_name =~ *erst_reset_r*_reg/SDN}]',
 'if {[sizeof_collection $async_endpoints]!=2} {error "Expectedexact2originalAONasync-set pins"}',
 'set f [open {'+str(R/'async_control_context.tsv')+'} w];puts $f "pin\tfanin_startpoints\tcell";foreach_in_collection p $async_endpoints {set xs {};foreach_in_collection x [all_fanin -to $p -flat -startpoints_only] {lappend xs [get_object_name $x]};puts $f "[get_object_name $p]\t[join $xs ,]\t[get_object_name [get_cells -of_objects $p]]"};close $f',
 'redirect {'+str(R/'async_control_timing.rpt')+'} {report_timing -to $async_endpoints -delay_type max -max_paths 5 -slack_lesser_than 1000000 -path_type full_clock_expanded}',
 'set f [open {'+str(R/'register_clock_domains.tsv')+'} w];puts $f "clock\tregisters";foreach c {core_clk lf_clk jtag_clk} {puts $f "$c\t[sizeof_collection [all_registers -clock $c]]"};close $f',
 'redirect {'+str(R/'lf_clk_to_core_clk_max.rpt')+'} {report_timing -from [get_clocks lf_clk] -to [get_clocks core_clk] -delay_type max -max_paths 10000 -nworst 1 -slack_lesser_than 1000000 -path_type full_clock_expanded}',
 'redirect {'+str(R/'lf_clk_to_core_clk_min.rpt')+'} {report_timing -from [get_clocks lf_clk] -to [get_clocks core_clk] -delay_type min -max_paths 10000 -nworst 1 -slack_lesser_than 1000000 -path_type full_clock_expanded}',
 'redirect {'+str(R/'core_clk_to_lf_clk_max.rpt')+'} {report_timing -from [get_clocks core_clk] -to [get_clocks lf_clk] -delay_type max -max_paths 10000 -nworst 1 -slack_lesser_than 1000000 -path_type full_clock_expanded}',
 'redirect {'+str(R/'core_clk_to_lf_clk_min.rpt')+'} {report_timing -from [get_clocks core_clk] -to [get_clocks lf_clk] -delay_type min -max_paths 10000 -nworst 1 -slack_lesser_than 1000000 -path_type full_clock_expanded}',
 'set f [open {'+str(R/'async_crossing_endpoints.tsv')+'} w];puts $f "from_clock\tto_clock\tstartpoint\tendpoint\tslack"',
 'foreach pair {{core_clk lf_clk} {lf_clk core_clk}} {lassign $pair a b;set ps [get_timing_paths -from [get_clocks $a] -to [get_clocks $b] -delay_type max -max_paths 10000 -nworst 1 -slack_lesser_than 1000000];if {[sizeof_collection $ps]==0||[sizeof_collection $ps]>=10000} {error "Incomplete async crosspath enumeration"};foreach_in_collection p $ps {set sp [get_object_name [get_attribute $p startpoint]];set ep [get_object_name [get_attribute $p endpoint]];if {[string match {*u_kwt*} "$sp/$ep"]} {error "Unreviewed accelerator clock crossing"};puts $f "$a\t$b\t$sp\t$ep\t[get_attribute $p slack]"}};close $f',
 'write_sdf {'+str(R/'mapped.sdf')+'}',
 'write_sdc {'+str(R/'pt_written.sdc')+'}',
 'puts {KWT_FULL_SOC_PT_AUDIT_COMPLETED}', 'quit']
(R/'run.tcl').write_text('\n'.join(commands)+'\n');write();start=time.time()
with(R/'tool.log').open('w')as f:p=subprocess.run(['/eda/synopsys/prime/prime_2022.03-SP5-1/bin/pt_shell','-f',str(R/'run.tcl')],cwd=str(R),stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,timeout=1800,env=dict(os.environ,SYNOPSYS_LC_ROOT='/eda/synopsys/lib_compiler/lib_compiler_2022.03-SP5'))
log=(R/'tool.log').read_text(errors='replace');r['steps'].append({'step':'same_mapped_whole_SoC_PT_SS','exit':p.returncode,'seconds':time.time()-start,'log_sha256':sha(R/'tool.log')});r['errors']=re.findall(r'^Error:.*$',log,re.M);write()
assert p.returncode==0 and not r['errors']and 'KWT_FULL_SOC_PT_AUDIT_COMPLETED'in log
for name in ['setup','hold']:
 t=(R/(name+'.rpt')).read_text();r['SS_'+name+'_slacks_ns']=[float(z)for z in re.findall(r'slack\s*\([^)]*\)\s*([+-]?[0-9.]+)',t,re.I)]
 r[name+'_path_endpoints']=re.findall(r'^\s*(?:Startpoint|Endpoint):\s*(.*)$',t,re.M)
 assert r['SS_'+name+'_slacks_ns']
r['cdc_candidates']=list(csv.DictReader((R/'cdc_candidates.tsv').open(),delimiter='\t'));r['cdc_candidate_register_cells']=len(set(v['cell']for v in r['cdc_candidates']))
for nm in ['reg2reg_setup','reg2reg_hold']:
 t=(R/(nm+'.rpt')).read_text();r[nm+'_slacks_ns']=[float(v)for v in re.findall(r'slack\s*\([^)]*\)\s*([+-]?[0-9.]+)',t,re.I)];r[nm+'_path_endpoints']=re.findall(r'^\s*(?:Startpoint|Endpoint):\s*(.*)$',t,re.M)
r['reports_sha256']={p.name:sha(p)for p in R.glob('*.rpt')};r['engineering_setup_hold_nonnegative']=min(r['SS_setup_slacks_ns'])>=0 and min(r['SS_hold_slacks_ns'])>=0;r['coverage_manual_review_pending']=True;r['pass']=True;r['status']='SS_timing_audit_completed_qualification_requires_slack_and_coverage_review';r['positive_path_reporting']='Explicit slack_lesser_than1000000 prevents empty all-positive hold report';write()
