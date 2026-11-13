"""Source numerical conversion: input quantization and Cauchy output range.

No XW or hardware Alpha terms are calculated here. Per-row input energy and
fixed weight energy set only the output format. The linear layer stays in RTL.
"""
import math,numpy as np
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from dynamic12_convert import rounded
def convert(x,bias,cfg,qw,multiplier_bits=6,output_bits=14):
 x=np.asarray(x,dtype=np.float64);bias=np.asarray(bias,dtype=np.float64);qw=np.asarray(qw,dtype=np.int64)
 if x.shape[-2:]!=(99,64)or qw.shape!=(64,256)or bias.shape!=(256,):raise ValueError('Geometry')
 if not np.all(np.isfinite(x))or np.any(abs(qw)>2047):raise ValueError('Codes/input')
 limit_x=(1<<(cfg['input_bits']-1))-1
 S=np.asarray(cfg['input_feature_scale']);sw=np.asarray(cfg['weight_scale']);xx=x/S
 sx=np.maximum(np.max(abs(xx),axis=(-2,-1))/limit_x,cfg['minimum_input_scale']);qx=np.clip(rounded(xx/sx[...,None,None]),-limit_x,limit_x).astype(np.int64)
 qb=rounded(bias/(sx[...,None]*sw)).astype(np.int64)
 if np.any(qb<-(1<<31))or np.any(qb>=(1<<31)):raise ValueError('Bias range')
 # Integer ceil-sqrt makes this a strict bound for every encoded dot product.
 # This norm is format metadata only and is never sent as a MAC/Alpha result.
 energy=np.max(np.sum(qx*qx,axis=-1),axis=-1);we=np.sum(qw*qw,axis=0);flat=np.atleast_1d(energy).ravel();biases=qb.reshape(-1,256);bounds=[]
 for n,b in zip(flat,biases):
  row=[]
  for e,z in zip(we,b):
   p=int(n)*int(e);root=math.isqrt(p);row.append(root+(root*root!=p)+abs(int(z)))
  bounds.append(row)
 bound=np.maximum(np.asarray(bounds,dtype=np.int64).reshape(qb.shape),1)
 bit_length=np.frexp(bound.astype(np.float64))[1];shift=np.maximum(0,bit_length+multiplier_bits-output_bits).astype(np.int64)
 limit=(1<<(output_bits-1))-1;mult=np.minimum((1<<multiplier_bits)-1,(np.left_shift(np.int64(limit),shift)//bound));mult=np.maximum(mult,1)
 assert np.all(shift<=38)and np.max(qx)<=limit_x and np.min(qx)>=-limit_x
 return qx,qw,qb,shift,mult,sx,bound
def decode(codes,cfg,shift,mult,sx):
 return np.asarray(codes,dtype=np.float64)*sx[...,None,None]*np.asarray(cfg['weight_scale'])*np.exp2(shift[...,None,:])/mult[...,None,:]
