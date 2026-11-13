"""Fixed-size SRAM result layout, with unchanged frozen numerical codes."""
import numpy as np
SHAPE=(99,256)
WORDS=12672
def encode_matrix(codes):
 q=np.asarray(codes,dtype=np.int64)
 if q.shape!=SHAPE or np.any(q < -4095) or np.any(q > 4095):raise ValueError('Output codes/shape')
 a=q.reshape(-1)&65535
 return (a[0::2]|(a[1::2]<<16)).astype(np.uint32)
def decode_matrix(words):
 a=np.asarray(words,dtype=np.uint32)
 if a.shape!=(WORDS,):raise ValueError('A complete matrix requires12672words')
 q=np.empty(WORDS*2,dtype=np.int64);q[0::2]=a&65535;q[1::2]=a>>16
 q=np.where(q&32768,q-65536,q)
 if np.any(q < -4095) or np.any(q > 4095):raise ValueError('Sign extension/O13 range')
 return q.reshape(SHAPE)
def decode_float(words,metadata):
 q=decode_matrix(words)
 return q*float(metadata['input_scale'])*np.asarray(metadata['weight_scale'])*np.exp2(np.asarray(metadata['R']))/np.asarray(metadata['M'])
