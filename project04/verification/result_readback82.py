"""Generate read-only post-task shared-SRAM oracle pins, never task inputs.
Only after CPU completion and VCD off; no accelerator/DMA TCM connection.
"""
from pathlib import Path
import re,hashlib

def generate(path,mapped,leaf_tsv=None,mapped_verilog=None):
 path=Path(path);assert not path.exists()
 if mapped:
  names={}
  for line in Path(leaf_tsv).read_text().splitlines()[1:]:
   n,ref,*_=line.split('\t')
   if not(n.startswith('u_kwt_shared_sram/')and ref=='RAMSP8KX32'):continue
   match=re.search(r'banks\[(\d+)\]\.macro$',n);assert match,n;names[int(match[1])]=n
  assert sorted(names)==list(range(16))
  def esc(part):return part if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*',part)else '\\'+part+' '
  paths=['u_soc.'+'.'.join(esc(p)for p in names[i].split('/'))for i in range(16)]
  source=Path(mapped_verilog).read_text()
  assert all(names[i].split('/')[-1]in source for i in range(16))
 else:
  paths=['u_soc.u_kwt_shared_sram.banks[%d].macro'%i for i in range(16)]
 lines=['// Oracle only: all real outputs written/ACKed, CPU done, VCD off.',
        'reg [3:0] rb_bank=0;reg [12:0] rb_addr=0;',
        'wire [31:0] rb_q[0:15];integer physical_pin_readback_words=0;']
 for i,p in enumerate(paths):
  lines+=['wire rb_cen_%d=!(rb_bank==4\'d%d);'%(i,i),'assign rb_q[%d]=%s.Q;'%(i,p)]
 lines+=['task physical_result_check;','integer j;reg [31:0] address_offset;','begin',
         ' if(clk!==0 || u_soc.u_kwt_shared_sram.cmd_valid!==0 || u_soc.u_kwt_shared_sram.rsp_valid!==0) $fatal(1,"Shared SRAM oracle requires idle controller after real CPU completion");',
         ' address_offset=`AI.engine.result_base-32\'ha0000000;',
         ' if(address_offset[1:0]!=0 || address_offset>=32\'h80000)$fatal(1,"Invalid physical result base");',
         ' rb_bank=address_offset[18:15];rb_addr=address_offset[14:2];']
 for i,p in enumerate(paths):
  for pin,value in [('CEN','rb_cen_%d'%i),('GWEN',"1'b1"),('WEN',"32'hffffffff"),('A','rb_addr')]:lines.append(' force %s.%s=%s;'%(p,pin,value))
 lines+=[' for(j=0;j<out_at;j=j+1)begin',
         '  @(posedge clk);if(u_soc.u_kwt_shared_sram.cmd_valid!==0)$fatal(1,"Real bus activity during post-task physical oracle");',
         '  @(negedge clk);',
         '  if(rb_q[rb_bank]!==gold_words[offset+j])$fatal(1,"Mapped physical SRAM result mismatch index=%0d got=%h expected=%h",j,rb_q[rb_bank],gold_words[offset+j]);',
         '  physical_pin_readback_words=physical_pin_readback_words+1;',
         '  address_offset=address_offset+4;rb_bank=address_offset[18:15];rb_addr=address_offset[14:2];',
         ' end']
 for p in paths:
  for pin in ['CEN','GWEN','WEN','A']:lines.append(' release %s.%s;'%(p,pin))
 lines+=[' if(physical_pin_readback_words!=out_at)$fatal(1,"Incomplete physical SRAM oracle");',
         ' $display("PASS post-task physical sharedSRAM oracle words=%0d",physical_pin_readback_words);',
         'end','endtask','']
 path.write_text('\n'.join(lines))
 return {'mapped':mapped,'pins':paths,'header_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'verification_only_after_CPU_done_and_VCD_off':True,'no_memory_array_backdoor':True,'macro_pins_written':False}

def generate_dump(path,leaf_tsv,mapped_verilog):
 import csv,json
 source=Path(mapped_verilog).read_text()
 text=re.sub(r'//[^\n]*|/\*.*?\*/','',source,flags=re.S)
 modules={}
 pattern=r'\bmodule\s+(\\[^\s]+|[A-Za-z_][A-Za-z0-9_$]*)\s*\((.*?)\bendmodule\b'
 for m in re.finditer(pattern,text,re.S):
  name=m.group(1);assert name not in modules;modules[name]=m.group(2)
 assert 'e203_soc_top'in modules and len(modules)>10
 ref_pattern=r'(?<![A-Za-z0-9_$\\])('+ '|'.join(re.escape(n)for n in sorted(modules,key=len,reverse=True))+r')\s+(\\[^\s]+|[A-Za-z_$][A-Za-z0-9_$]*)\s*\('
 inst=re.compile(ref_pattern);names=set();visited=set();hierarchy=[]
 def walk(ref,scope,stack):
  assert ref not in stack,'Recursive mapped module';names.add(scope);visited.add(ref)
  for m in inst.finditer(modules[ref]):
   child,raw=m.group(1),m.group(2);component=raw+' 'if raw.startswith('\\')else raw
   hierarchy.append({'parent':scope,'ref':child,'instance':raw});walk(child,scope+'.'+component,stack+[ref])
 walk('e203_soc_top','u_soc',[])
 macros=0
 def esc(p):return p if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*',p)else '\\'+p+' '
 for row in csv.DictReader(Path(leaf_tsv).open(),delimiter='\t'):
  if not(row['ref'].startswith('RAMSP')or row['ref'].startswith('ROM1KX32')):continue
  names.add('u_soc.'+'.'.join(esc(p)for p in row['name'].split('/')));macros+=1
 assert macros==56
 text='task dump_current_scope;begin\n'+'\n'.join(' $dumpvars(1,'+n+');'for n in sorted(names))+'\nend endtask\n';Path(path).write_text(text)
 return {'scope':'Depth1 of each real Verilog module reachable from actual mapped top plus all56 macro leaves; synthetic arithmetic leaf names are not inferred as hierarchy. All actual mapped module wires remain covered; no temporal sampling. PT100percentdirectannotation required.','scopes':sorted(names),'macro_leaves':macros,'mapped_modules':len(modules),'visited_module_definitions':len(visited),'unreachable_module_definitions':sorted(set(modules)-visited),'hierarchy':hierarchy,'mapped_verilog_sha256':hashlib.sha256(Path(mapped_verilog).read_bytes()).hexdigest(),'include_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'PT_direct_annotation_required':True}
