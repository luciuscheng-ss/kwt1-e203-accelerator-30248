from pathlib import Path
import argparse,subprocess,json,hashlib
HEADER='''$timescale 1fs $end
$scope module fixture $end
$var wire 1 a CLK $end
$var wire 1 b CEN $end
$var wire 1 c GWEN $end
$var wire 10 d A $end
$var wire 16 e WEN $end
$var wire 16 f D $end
$var wire 2 g VALID $end
$upscope $end
$enddefinitions $end
'''
def b(v):return 'b'+format(v,'b')
def initial(clock=0,cen=1,gwen=1,addr=0,wen=65535,data='bx',valid='b0'):
 return '#0\n$dumpvars\n%da\n%db\n%dc\n%s d\n%s e\n%s f\n%s g\n$end\n'%(clock,cen,gwen,b(addr),b(wen),data,valid)
def cycle_write(addr=0,wen=0,data='b1010010110100101'):
 return '#5\n0b\n0c\n%s d\n%s e\n%s f\n#10\n1a\n'%(b(addr),b(wen),data)
def read20():return '#15\n0a\n1c\n#20\n1a\n#25\n0a\n1b\n#30\n'
def fixtures():
 cases=[]
 def add(n,text,ok,kind='ALPHA',bank=0,gatewidth=2,gatemask=1):cases.append((n,HEADER+text,ok,kind,bank,gatewidth,gatemask))
 add('write_then_read',initial()+cycle_write()+read20(),True)
 add('read_unwritten',initial(cen=0)+'#10\n1a\n#20\n',False)
 add('partial_write_not_full',initial()+cycle_write(wen=65280)+read20(),False)
 add('two_partial_writes',initial()+cycle_write(wen=65280)+'#15\n0a\nb11111111 e\n#20\n1a\n#25\n0a\n1c\n#30\n1a\n#35\n',True)
 add('initial_high_not_edge',initial(clock=1,cen=0)+'#5\n0a\n0c\nb0 e\nb101 f\n#10\n1a\n'+read20(),True)
 add('enable_after_edge_not_read',initial()+'#10\n1a\n0b\n#15\n0a\n1b\n#20\n1a\n#25\n',True)
 add('disable_after_edge_still_read',initial(cen=0)+'#10\n1a\n1b\n#15\n0a\n#20\n',False)
 add('cold_valid_nonzero',initial(valid='b1')+'#10\n1a\n#20\n',False)
 add('unknown_enabled_write_data',initial()+cycle_write(data='bx')+read20(),False)
 add('X_last_tile_unused_bank6',initial(cen=0,addr=608)+'#10\n1a\n#20\n',True,'X',6)
 add('X_last_tile_bank5_low8',initial()+cycle_write(addr=608,wen=65280)+read20(),True,'X',5)
 add('X_normal_bank6_14bits',initial()+cycle_write(wen=49152)+read20(),True,'X',6)
 add('X_normal_bank6_missing_bits',initial()+cycle_write(wen=65280)+read20(),False,'X',6)
 add('explicit_unobserved_valid_bit',initial(valid='bx0')+'#10\n1a\n#20\n',True)
 add('CPU_idle_range',initial()+'#10\n1a\n#15\n0a\n#20\n1a\n#30\n',True)
 add('CPU_active_inside_range',initial()+'#10\n1a\nb1 g\n#15\n0a\nb0 g\n#20\n1a\n#30\n',False)
 add('CPU_active_outside_range',initial()+'#2\nb1 g\n#3\nb0 g\n#10\n1a\n#15\n0a\n#20\n1a\n#30\n',True)
 return cases
def run(exe,out):
 out=Path(out);assert not out.exists();out.mkdir(parents=True);results=[]
 for name,text,ok,kind,bank,gw,gm in fixtures():
  d=out/name;d.mkdir();(d/'wave.vcd').write_text(text);(d/'spec.tsv').write_text('M\tfixture\t%s\t%d\ta\tb\tc\td\te\tf\t10\nV\tvalid\tg\t%d\t%x\t0\n'%(kind,bank,gw,gm))
  if name.startswith('CPU_'):
   with(d/'spec.tsv').open('a')as f:f.write('R\tcpu_active\tg\t5\t25\t0\n')
  with(d/'wave.vcd').open('rb')as f:p=subprocess.run([str(exe),str(d/'spec.tsv')],stdin=f,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
  assert (p.returncode==0)==ok,(name,p.returncode,p.stdout,p.stderr)
  if ok:assert json.loads(p.stdout.decode())['pass']
  else:assert b'AUDIT_FAIL'in p.stderr
  results.append({'fixture':name,'expected_pass':ok,'actual_exit':p.returncode,'pass':True})
 q={'pass':True,'fixtures':results,'CPP_checker_sha256':hashlib.sha256(Path(__file__).with_name('cold_sram_audit.cpp').read_bytes()).hexdigest(),'executable_sha256':hashlib.sha256(Path(exe).read_bytes()).hexdigest()};(out/'result.json').write_text(json.dumps(q,indent=2)+'\n');return q
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--exe',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();q=run(a.exe,a.out);print(json.dumps({'pass':q['pass'],'fixtures':len(q['fixtures'])}))
