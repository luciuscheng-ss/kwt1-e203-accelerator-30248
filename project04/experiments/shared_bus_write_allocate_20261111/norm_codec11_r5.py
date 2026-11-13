"""Lossless transport for the frozen11/11, M4/shift6, O14 format."""
import numpy as np
from codec import Bits,encode_output,decode_output
def encode_source(x,w,bias,mult,shift):
 x=np.asarray(x);w=np.asarray(w);bias=np.asarray(bias);mult=np.asarray(mult);shift=np.asarray(shift)
 if(x.shape,w.shape,bias.shape,mult.shape,shift.shape)!=((99,64),(64,256),(256,),(256,),(256,)):raise ValueError('Geometry')
 if np.any(abs(x)>1023)or np.any(abs(w)>1023)or np.any(bias<-(1<<31))or np.any(bias>=(1<<31))or np.any(mult<1)or np.any(mult>15)or np.any(shift<0)or np.any(shift>38):raise ValueError('Format code range')
 result=[]
 for g in range(16):
  result.extend(int(z)&0xffffffff for z in bias[g*16:g*16+16]);s=Bits()
  for m,r in zip(mult[g*16:g*16+16],shift[g*16:g*16+16]):s.put(int(m)|(int(r)<<4),10)
  result.extend(s.words());s=Bits()
  for k in range(32):
   for c in range(g*16,g*16+16):
    for z in w[k*2:k*2+2,c]:s.put(z,11)
  result.extend(s.words())
  if g==0:
   s=Bits()
   for r in range(0,100,5):
    for k in range(64):
     for row in range(r,r+5):s.put(x[row,k]if row<99 else 0,11)
   result.extend(s.words())
 assert len(result)==8168;return result
def decode_source(words):
 if len(words)!=8168:raise ValueError('Length')
 x=np.zeros((99,64),dtype=np.int64);w=np.zeros((64,256),dtype=np.int64);bias=np.zeros(256,dtype=np.int64);mult=np.zeros(256,dtype=np.int64);shift=np.zeros(256,dtype=np.int64);at=0
 for g in range(16):
  for c in range(g*16,g*16+16):
   z=int(words[at]);at+=1;bias[c]=z-(1<<32)if z&(1<<31)else z
  view=sum(int(z)<<(32*i)for i,z in enumerate(words[at:at+5]));at+=5
  for c in range(16):z=(view>>(10*c))&1023;mult[g*16+c]=z&15;shift[g*16+c]=z>>4
  view=sum(int(z)<<(32*i)for i,z in enumerate(words[at:at+352]));at+=352;bit=0
  for k in range(32):
   for c in range(g*16,g*16+16):
    for f in range(k*2,k*2+2):
     z=(view>>bit )&2047;bit+=11;w[f,c]=z-2048 if z&1024 else z
  if g==0:
   view=sum(int(z)<<(32*i)for i,z in enumerate(words[at:at+2200]));at+=2200;bit=0
   for r in range(0,100,5):
    for k in range(64):
     for row in range(r,r+5):
      z=(view>>bit )&2047;bit+=11
      if row<99:x[row,k]=z-2048 if z&1024 else z
      elif z:raise ValueError('Padding row')
 assert at==8168
 return x,w,bias,mult,shift
