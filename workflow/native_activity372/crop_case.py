"""Exact final-netlist cold crop and complete56 macro/clock visibility guard."""
from pathlib import Path
from collections import Counter
import hashlib,json,csv
from vcd_window import read_header
import fast_vcd_window_v3 as scanner
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb')as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
def crop_case(source,out,case,leaf_table,mapped_sha):
 out.mkdir();start,end=case['window_start_ns'],case['window_end_ns'];source_sha=sha(source)
 root='native_cpu_tb/u_soc';shapes={'RAMSP128X16':(128,16),'RAMSP1024X16':(1024,16),'RAMSP4KX64':(4096,64),'RAMSP8KX32':(8192,32)};common={'CLK':1,'CEN':1,'GWEN':1,'EMA':3,'EMAW':2,'RET1N':1};rom={'CLK':1,'CEN':1,'A':10,'Q':32,'CENY':1,'AY':10,'EMA':3,'TEN':1,'BEN':1,'TCEN':1,'TA':10,'TQ':32,'PGEN':1,'KEN':1}
 with source.open()as f:header,scale,definitions,paths=read_header(f)
 mode_pins={root+'/io_pads_aon_erst_n_i_ival':'1',root+'/io_pads_bootrom_n_i_ival':'0',root+'/io_pads_aon_pmu_dwakeup_n_i_ival':'1',root+'/kwt_sysmem_rst_n':'1'}
 for i in range(3):mode_pins[root+'/io_pads_dbgmode%d_n_i_ival'%i]='1'
 tracked=[root+'/hfextclk',root+'/lfextclk']+list(mode_pins);macros=[];counts=Counter()
 for row in csv.DictReader(leaf_table.open(),delimiter='\t'):
  ref=row['ref']
  if ref not in shapes and ref!='ROM1KX32':continue
  scope=root+'/'+row['name'];pins=dict(rom)if ref=='ROM1KX32'else dict(common,A=(shapes[ref][0]-1).bit_length(),D=shapes[ref][1],Q=shapes[ref][1],WEN=shapes[ref][1]);counts[ref]+=1
  for pin,width in pins.items():assert paths.get(scope+'/'+pin,{}).get('width')==width,'Missing/wrong actual mapped macro pin '+scope+'/'+pin
  macros.append({'reference':ref,'scope':scope,'pins':pins});tracked.extend(scope+'/'+pin for pin in pins)
 assert dict(counts)=={'RAMSP8KX32':20,'RAMSP4KX64':4,'RAMSP1024X16':7,'RAMSP128X16':24,'ROM1KX32':1};assert all(p in paths for p in tracked)
 r={'pass':False,'scope':__doc__,'mapped_sha256':mapped_sha,'source_waveform_expected_sha256':source_sha,'macros':macros,'actual_macro_inventory':dict(counts),'all56_macro_port_shapes_exact':True,'cold_cycles':case['cold_cycles'],'window_ns':[start,end],'STA_qualified':False,'official_loader_qualified':False,'power_qualified':False}
 result=scanner.scan_and_crop(source,out/'cold_task.vcd',str(start),str(end),tracked,rebase=True);processing=scanner.LAST_RUN;assert processing['source_sha256']==source_sha;assert result['output_start_tick']==0 and not result['dump_off_gaps_within_window'];assert len(result['observed_ids'])==len(definitions),'Missing waveform ID snapshot'
 r['clock_stats_before_acceptance']={name:result['tracked_stats'][paths[root+'/'+name]['code']]for name in ['hfextclk','lfextclk']};(out/'clock_statistics.json').write_text(json.dumps(r['clock_stats_before_acceptance'],indent=2)+'\n')
 for name,period in [('hfextclk',20/3),('lfextclk',30517.578125)]:
  code=paths[root+'/'+name]['code'];s=result['tracked_stats'][code];assert s['unknown_ticks']==0 and s['rising_edges']>2 and abs(s['mean_rising_period_ns']-period)<1e-5,name+' actual clock mismatch';r[name+'_actual_stats']=s;assert all(abs(s[k]*float(scale)-period)<=1.1*float(scale)+1e-10 for k in ['min_period_ticks','max_period_ticks']),name+' actual period jitter/glitch'
 r['functional_mode_pin_stats']={}
 for pin,expected in mode_pins.items():
  stat=result['tracked_stats'][paths[pin]['code']];assert stat['initial']==stat['last']==expected and stat['changes']==stat['unknown_ticks']==0,'Functionalmodepinnotconstant '+pin;r['functional_mode_pin_stats'][pin]=stat
 r['scan']={k:v for k,v in result.items()if k not in ['definitions','by_path','observed_ids','changed_ids','unknown_ids','tracked_stats']};r['full_identifier_counts']={'declared':len(definitions),'observed':len(result['observed_ids']),'changed':len(result['changed_ids']),'ever_unknown':len(result['unknown_ids'])};r['macro_pin_stats']={p:result['tracked_stats'][paths[p]['code']]for p in tracked if p not in [root+'/hfextclk',root+'/lfextclk']};r['processing']=processing;r['pass']=True;(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');return {'pass':True,'case':case['case'],'mode':case['mode'],'mapped_sha256':mapped_sha,'path':str(out/'cold_task.vcd'),'sha256':processing['destination_sha256'],'bytes':(out/'cold_task.vcd').stat().st_size,'audit_path':str(out/'result.json'),'audit_sha256':sha(out/'result.json'),'duration_ns':end-start,'cold_cycles':case['cold_cycles']}
