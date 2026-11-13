"""Verify a training-frozen X11/W11 format; validation cannot tune it."""
import os
os.environ.update(OPENBLAS_NUM_THREADS='2',OMP_NUM_THREADS='2')
from pathlib import Path
import numpy as np,json,hashlib,argparse,time
from norm_convert import convert,decode
ap=argparse.ArgumentParser();ap.add_argument('--output-bits',type=int,choices=[13,14],required=True);a=ap.parse_args()
N=Path(__file__).resolve().parent;H=N.parent;R=H.parents[1];ob=a.output_bits;folder='training_o13'if ob==13 else'training';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=N/f'freeze_X11W11O{ob}.json';F=json.loads(p.read_text());assert all(sha(R/f)==v for f,v in F['numeric_configs_and_code'].items());out=N/f'validation_X11W11O{ob}.json';assert not out.exists()
W=np.load(R/'artifacts/reference/weights.npz');rows=[];sources={};start=time.time()
for layer in range(12):
 cfg=json.loads((N/folder/f'x11w11_layer_{layer:02d}.json').read_text());qw=np.load(H/f'dynamic12/w11_layer_{layer:02d}.npz')['qw']
 xp=R/f'artifacts/reference/validation/layer_{layer:02d}_input.npy';yp=R/f'artifacts/reference/validation/layer_{layer:02d}_output.npy';x=np.load(xp,mmap_mode='r');y=np.load(yp,mmap_mode='r');assert len(x)==len(y)==4445
 sources.update({str(z.relative_to(R)):sha(z)for z in [xp,yp]});e2=t2=0.;worst=0.;maxshift=0
 for at in range(0,4445,64):
  qx,qw,qb,shift,mult,sx,bound=convert(x[at:at+64],W[f'b{layer:02d}'],cfg,qw,4,ob);raw=qx@qw+qb[:,None,:];assert np.all(abs(raw)<=bound[:,None,:]);maxshift=max(maxshift,int(np.max(shift)))
  half=np.where(shift>0,np.left_shift(np.int64(1),np.maximum(shift-1,0)),0);codes=((abs(raw)*mult[:,None,:]+half[:,None,:])>>shift[:,None,:])*np.sign(raw);assert np.max(abs(codes))<1<<(ob-1)
  target=y[at:at+64].astype(np.float64);diff=decode(codes,cfg,shift,mult,sx)-target;err=np.sum(diff*diff,axis=(1,2));eng=np.sum(target*target,axis=(1,2));e2+=float(np.sum(err));t2+=float(np.sum(eng));worst=max(worst,float(np.max(np.sqrt(err/np.maximum(eng,99*256*1e-16)))))
 error=(e2/max(t2,4445*99*256*1e-16))**.5;row={'layer':layer,'samples':4445,'nrmse':error,'score':10-error/.003,'worst_sample_nrmse':worst,'output_saturation_codes':0,'max_shift':maxshift};rows.append(row);print(row,flush=True)
assert all(sha(R/f)==v for f,v in F['numeric_configs_and_code'].items());err=max(z['nrmse']for z in rows)
result={'scope':__doc__,'input_bits':11,'weight_bits':11,'output_bits':ob,'score':10-err/.003,'worst_layer_nrmse':err,'max_individual_nrmse':max(z['worst_sample_nrmse']for z in rows),'freeze_sha256':sha(p),'samples_per_layer':4445,'testing_accessed':False,'numeric_config_changed':False,'rows':rows,'validation_sources_sha256':sources,'script_sha256':sha(Path(__file__)),'seconds':time.time()-start,'framework_qualified':False,'official_score':None}
out.write_text(json.dumps(result,indent=2)+'\n');print('FINAL',result['score'],flush=True)
