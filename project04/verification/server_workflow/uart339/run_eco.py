"""Independent one-line UART repair mapped ECO after actualVCS equivalence guard.
Remove only24transparent-data latches; preserve everyother mapped physicalcell.
No clock exceptions, CPU/config/format/ports or originalsource modifications.
"""
from pathlib import Path
from collections import Counter
import json,hashlib,subprocess,csv,re,time
R=Path(__file__).resolve().parent;P=R.parent;sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();M=json.loads((R/'MANIFEST.json').read_text());assert all(sha(R/n)==h for n,h in M.items());B=P/'native_repair163';b=json.loads((B/'result.json').read_text());assert b['pass'];oldmap=B/'synth/mapped.v';oldddc=B/'synth/mapped.ddc';before=(sha(oldmap),sha(oldddc));assert before[0]==b['mapped_sha256'];G=P/'native_uart332/official_guard/overlay_guard.json';g=json.loads(G.read_text());assert g['status']=='passed'and g['functional_equivalence_verified']and g['official_platform_verified']and not g['errors'];assert all(sha(n)==h for k in ['inputs_sha256','outputs_sha256']for n,h in g[k].items());assert sha(g['result'])==g['result_sha256']and sha(g['overlay'])==g['overlay_sha256'];assert all(v==0 for v in g['exit_codes'].values());models=json.loads((P/'native_probe51/result.json').read_text())['vendor_models_sha256'];assert all(sha(n)==h for n,h in models.items())
# Actual suppliedcellmodels must show Q follows D with E=1 andholds with E=0.
T=R/'truth';T.mkdir();tb='`timescale 1ns/1fs\nmodule latch_truth; reg e=0,d=0;wire q0,q2; LAHQV0_12TR40 a(.E(e),.D(d),.Q(q0));LAHQV2_12TR40 b(.E(e),.D(d),.Q(q2));integer k;initial begin e=1; for(k=0;k<6;k=k+1)begin d=k[0];#2;if(q0!==d||q2!==d)$fatal(1,"Latch Q notpositive D");end e=0;d=0;#2;if(q0!==1||q2!==1)$fatal(1,"Latch does nothold");$display("PASS actualLAHQpositive-transparency");$finish;end endmodule\n';(T/'truth.sv').write_text(tb)
def call(name,cmd,cwd,limit=900):
 log=R/(name+'.log')
 with log.open('w')as f:q=subprocess.run(list(map(str,cmd)),cwd=str(cwd),stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,timeout=limit)
 s=log.read_text(errors='replace');assert q.returncode==0 and not re.search(r'(?:^Error:|Error-\[|Fatal:|FATAL:)',s,re.M),name;return s
call('truth_compile',['/eda/synopsys/vcs/vcs_2020.03-SP2-6/bin/vcs','-full64','-sverilog','-top','latch_truth','+notimingcheck','+define+functional+ARM_UD_MODEL','-o',T/'simv']+list(models)+[T/'truth.sv'],T);assert'PASS actualLAHQpositive-transparency'in call('truth_run',[T/'simv'],T)
O=R/'synth';O.mkdir();(O/'constraints.sdc').write_bytes((B/'synth/constraints.sdc').read_bytes())
def tl(xs):return '[list '+' '.join('{'+str(x)+'}'for x in xs)+']'
t=['set_host_options -max_cores 1','set_app_var target_library '+tl(list(b['library_sha256'])),'set_app_var link_library '+tl(['*']+list(b['library_sha256'])),'read_ddc {'+str(oldddc)+'}','current_design e203_soc_top','link',
'set refs {};foreach_in_collection c [get_cells -hierarchical -filter {ref_name =~ apb_uart*}] {lappend refs [get_attribute $c ref_name]}',
'set refs [lsort -unique $refs];if {[llength $refs]!=3} {error "Expected3 actualUARTreferences"}',
'set audit [open {'+str(O/'uart_eco.tsv')+'} w];puts $audit "design\tcell\tDnet\tQnet\tsinks";set changed 0',
'foreach ref $refs {',
' current_design $ref;set cs [get_cells -filter {ref_name =~ LAHQ*}];set plans {}',
' foreach_in_collection c $cs {',
'  set n [get_object_name $c];if {![regexp {^fifo_tx_data_reg\[([0-7])\]$} $n -> bit]} {continue}',
'  set dp {};set qp {};foreach_in_collection p [get_pins -of_objects $c] {set leaf [lindex [split [get_object_name $p] /] end];if {$leaf eq "D"} {set dp $p};if {$leaf eq "Q"} {set qp $p}}',
'  if {$dp eq ""||$qp eq ""} {error "Exact D/Q pins notfound"}',
'  set dn [get_nets -of_objects $dp];set qn [get_nets -of_objects $qp];if {[sizeof_collection $dn]!=1||[sizeof_collection $qn]!=1} {error "Ambiguous latch nets"}',
'  if {[get_object_name $dn] ne [format {PWDATA[%d]} $bit]} {error "Data notdirect matching originalPWDATA bit"}',
'  set loads [remove_from_collection [all_connected $qn] $qp];if {[sizeof_collection $loads]<1} {error "Missing originalFIFOconsumer"}',
'  lappend plans [list $c $dn $qn $loads]',
' }',
' if {[llength $plans]!=8} {error "Expected8 transparent-data latches perUART"}',
' foreach v $plans {lassign $v c dn qn loads;puts $audit "$ref\t[get_object_name $c]\t[get_object_name $dn]\t[get_object_name $qn]\t[sizeof_collection $loads]";disconnect_net $qn $loads;connect_net $dn $loads;remove_cell $c;incr changed}',
'}',
'close $audit;if {$changed!=24} {error "Exact24latch edits required"}',
'current_design e203_soc_top;link',
'redirect {'+str(O/'check_design.rpt')+'} {check_design}',
'redirect {'+str(O/'area.rpt')+'} {report_area -hierarchy}',
'set f [open {'+str(O/'leaf_cells.tsv')+'} w];puts $f "name\tref\tarea\tlibrary_matches"',
'foreach_in_collection c [get_cells -hierarchical -filter {is_hierarchical == false}] {set ref [get_attribute $c ref_name];puts $f "[get_object_name $c]\t$ref\t[get_attribute $c area]\t[sizeof_collection [get_lib_cells -quiet */$ref]]"};close $f',
'write -format verilog -hierarchy -output {'+str(O/'mapped.v')+'}',
'write -format ddc -hierarchy -output {'+str(O/'mapped.ddc')+'}',
'puts {UART24_DATA_LATCH_ECO_DONE};quit']
(O/'eco.tcl').write_text('\n'.join(t)+'\n');call('dc_eco',['/eda/synopsys/dc/dc_2022.03-SP5-5/bin/dc_shell','-f',O/'eco.tcl'],O)
assert before==(sha(oldmap),sha(oldddc)),'Baselinechanged';assert'UART24_DATA_LATCH_ECO_DONE'in(R/'dc_eco.log').read_text();old=list(csv.DictReader((B/'synth/leaf_cells.tsv').open(),delimiter='\t'));new=list(csv.DictReader((O/'leaf_cells.tsv').open(),delimiter='\t'));phys=lambda rows:{v['name']:v for v in rows if not v['ref'].startswith('**logic_')};x,y=phys(old),phys(new);removed=set(x)-set(y);assert len(removed)==24 and not set(y)-set(x)and all('fifo_tx_data_reg['in n and x[n]['ref'].startswith('LAHQ')for n in removed);assert all(x[n]['ref']==v['ref']and abs(float(x[n]['area'])-float(v['area']))<1e-8 for n,v in y.items());assert all(int(v['library_matches'])>=1 for v in y.values());inv=Counter(v['ref']for v in y.values()if v['ref'].startswith('RAMSP')or v['ref']=='ROM1KX32');assert dict(inv)=={'RAMSP8KX32':20,'RAMSP4KX64':4,'RAMSP1024X16':7,'RAMSP128X16':24,'ROM1KX32':1};delta=sum(float(x[n]['area'])for n in removed)
r=dict(b);r.update(scope=__doc__,pass_=True,mapped_sha256=sha(O/'mapped.v'),parent_mapped_sha256=before[0],parent_DDC_sha256=before[1],uart_guard_sha256=sha(G),uart_removed_cells=sorted(removed),removed_stdcell_area_library_units=delta,conditional_conservative_added_area_mm2=b['conditional_conservative_added_area_mm2']-delta/1e6,leaf_area_sum_library_units=sum(float(v['area'])for v in y.values()),source_manifest_sha256=sha(R/'MANIFEST.json'),implementation_change='24UARTdata LAHQ latches removed, eachpositiveQconsumer rewiredtoexactsamePWDATA Dbit. Actualcelltruth andRTL UART guardpassed. Allother physicalcell names/ref/area identical; same56macros.',STA_qualified=False,energy_qualified=False,full_SoC_qualified=False,official_loader_qualified=False,steps=[{'step':'readDDC_only_UART24wireECO','pass':True}],macro_counts=dict(inv));r['pass']=True;src=dict(b['source_sha256']);k=next(k for k in src if Path(k).name=='apb_uart.v');assert src[k]==g['original_source_sha256'];del src[k];src[g['overlay']]=g['overlay_sha256'];r['source_sha256']=src;(R/'result.json').write_text(json.dumps(r,indent=2)+'\n')
