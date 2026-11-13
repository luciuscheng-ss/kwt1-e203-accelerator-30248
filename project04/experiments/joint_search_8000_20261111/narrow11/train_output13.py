"""Predeclared training-only X11/W11/O13 comparison; no validation/test tuning."""
import os
os.environ.update(OPENBLAS_NUM_THREADS='2',OMP_NUM_THREADS='2')
from pathlib import Path
import numpy as np,json,hashlib,time
from norm_convert import convert,decode
N=Path(__file__).resolve().parent;H=N.parent;R=H.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
W=np.load(R/'artifacts/reference/weights.npz');out=N/'training_o13';out.mkdir(exist_ok=False);rows=[];sources={};start=time.time()
for layer in range(12):
 cp=H/('dynamic12/w11_layer_%02d.json'%layer);qp=H/('dynamic12/w11_layer_%02d.npz'%layer);cfg0=json.loads(cp.read_text());qw=np.load(qp)['qw'];assert np.max(abs(qw))<=1023
 xp=R/('artifacts/reference/calibration/layer_%02d_input.npy'%layer);yp=R/('artifacts/reference/calibration/layer_%02d_output.npy'%layer)
 x=np.load(xp,mmap_mode='r');target=np.load(yp,mmap_mode='r');assert x.shape[0]==target.shape[0]==600
 sources.update({str(p.relative_to(R)):sha(p)for p in [cp,qp,xp,yp]})
 for xb in [11]:
  cfg=dict(cfg0,input_bits=xb,minimum_input_scale=cfg0['minimum_input_scale']*2047/((1<<(xb-1))-1));(out/f'x{xb}w11_layer_{layer:02d}.json').write_text(json.dumps(cfg,indent=2)+'\n')
  e2=t2=0.;maxsingle=0.;sat=0
  for at in range(0,600,25):
   xx=np.asarray(x[at:at+25],dtype=np.float64);yy=np.asarray(target[at:at+25],dtype=np.float64)
   qx,qw,qb,shift,mult,sx,bound=convert(xx,W[f'b{layer:02d}'],cfg,qw,4,13);raw=qx@qw+qb[:,None,:]
   assert np.all(abs(raw)<=bound[:,None,:]);half=np.where(shift>0,np.left_shift(np.int64(1),np.maximum(shift-1,0)),0)
   codes=((abs(raw)*mult[:,None,:]+half[:,None,:])>>shift[:,None,:])*np.sign(raw);assert np.max(abs(codes))<=4095
   pred=decode(codes,cfg,shift,mult,sx);diff=pred-yy;err=np.sum(diff*diff,axis=(1,2));eng=np.sum(yy*yy,axis=(1,2));e2+=float(np.sum(err));t2+=float(np.sum(eng));maxsingle=max(maxsingle,float(np.max(np.sqrt(err/np.maximum(eng,99*256*1e-16)))))
  error=(e2/max(t2,600*99*256*1e-16))**.5
  row={'layer':layer,'input_bits':xb,'weight_bits':11,'output_bits':13,'score':10-error/.003,'aggregate_nrmse':error,'max_single_nrmse':maxsingle,'saturation_codes':sat};rows.append(row);print(row,flush=True)
result={'scope':__doc__,'rows':rows,'scores':{f'X{xb}W11':min(r['score']for r in rows if r['input_bits']==xb)for xb in [11]},'testing_accessed':False,'validation_accessed':False,'calibration_samples_per_layer':600,'float_weights_unchanged':True,'free_bias_fitting':False,'sources':sources,'code_sha256':{str(p.relative_to(R)):sha(p)for p in [Path(__file__),N/'norm_convert.py',H/'dynamic12_convert.py']},'seconds':time.time()-start,'official_numeric_method_review_pending':True}
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result['scores'],flush=True)
