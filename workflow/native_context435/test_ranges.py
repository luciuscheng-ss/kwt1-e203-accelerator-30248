from pathlib import Path
import subprocess,json
from test_checker import HEADER,initial

def run(exe,out):
 out=Path(out);out.mkdir();rows=[]
 for name,wave,ok in [('held_selected_unknown_others',initial(valid='b10')+'#10\nb1x g\n#20\n',True),('unknown_selected',initial(valid='bx0')+'#10\n#20\n',False),('changed_selected',initial(valid='b10')+'#10\nb0 g\n#20\n',False),('changed_unselected',initial(valid='b10')+'#10\nb11 g\n#20\n',True)]:
  d=out/name;d.mkdir();(d/'wave.vcd').write_text(HEADER+wave);(d/'config.tsv').write_text('M\tfixture\tALPHA\t0\ta\tb\tc\td\te\tf\t10\nR\tselectedbit\tg\t0\t20\t2\t2\t2\n')
  with(d/'wave.vcd').open('rb')as f:q=subprocess.run([str(exe),str(d/'config.tsv')],stdin=f,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)
  assert (q.returncode==0)==ok,(name,q.stdout,q.stderr);rows.append({'name':name,'expected':ok,'exit':q.returncode,'pass':True})
 r={'pass':True,'fixtures':rows};(out/'result.json').write_text(json.dumps(r,indent=2)+'\n');return r
