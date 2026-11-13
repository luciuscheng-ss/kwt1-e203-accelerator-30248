"""Deterministic source-format conversion only. No linear-layer calculation."""
import numpy as np
def rounded(x):return np.sign(x)*np.floor(np.abs(x)+.5)
def convert(x,bias,cfg,qw):
 if cfg['input_bits']!=12 or cfg['output_bits']!=14 or cfg['input_rule']!='per_task_absmax_after_frozen_feature_scale':raise ValueError('Frozen format')
 x=np.asarray(x,dtype=np.float64);bias=np.asarray(bias,dtype=np.float64);qw=np.asarray(qw,dtype=np.int64)
 if x.shape[-2:]!=(99,64)or bias.shape!=(256,)or qw.shape!=(64,256):raise ValueError('Geometry')
 S=np.asarray(cfg['input_feature_scale']);sw=np.asarray(cfg['weight_scale']);bound=np.asarray(cfg['output_training_bound'])
 if not np.all(np.isfinite(x))or np.any(S<=0)or np.any(sw<=0)or np.any(bound<=0):raise ValueError('Nonfinite input/bad scales')
 xx=x/S;sx=np.maximum(np.max(abs(xx),axis=(-2,-1))/2047,cfg['minimum_input_scale'])
 qx=np.clip(rounded(xx/sx[...,None,None]),-2047,2047).astype(np.int64)
 qb=rounded(bias/(sx[...,None]*sw)).astype(np.int64)
 if np.any(qb<-(1<<31))or np.any(qb>=(1<<31)):raise ValueError('Bias range')
 shift=np.maximum(0,np.ceil(np.log2(bound/(8191*sx[...,None]*sw)))).astype(np.int64)
 if np.any(shift>32)or np.any(abs(qw)>(1<<(cfg['weight_bits']-1))-1):raise ValueError('Code range')
 return qx,qw,qb,shift,sx
def decode_output(qy,cfg,shift,sx):
 qy=np.asarray(qy,dtype=np.int64);sw=np.asarray(cfg['weight_scale'])
 if qy.shape[-2:]!=(99,256)or np.any(abs(qy)>8191):raise ValueError('Output code range')
 return qy.astype(np.float64)*sx[...,None,None]*sw*np.exp2(shift[...,None,:])
