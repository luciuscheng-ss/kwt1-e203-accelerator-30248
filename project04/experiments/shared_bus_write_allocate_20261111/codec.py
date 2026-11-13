"""Pure lossless framing of already quantized codes; no model calculation."""
import numpy as np
class Bits:
 def __init__(self):self.value=0;self.n=0
 def put(self,v,n):self.value|=(int(v)&((1<<n)-1))<<self.n;self.n+=n
 def words(self):return [(self.value>>(32*i))&0xffffffff for i in range((self.n+31)//32)]
def encode_source(x,w,bias,shift):
 x=np.asarray(x);w=np.asarray(w);bias=np.asarray(bias);shift=np.asarray(shift)
 if (x.shape,w.shape,bias.shape,shift.shape)!=((99,64),(64,256),(256,),(256,)):raise ValueError('geometry')
 if np.any(abs(x)>4095)or np.any(abs(w)>2047)or np.any(bias<-(1<<31))or np.any(bias>=(1<<31))or np.any(shift<0)or np.any(shift>32):raise ValueError('range')
 result=[]
 for g in range(16):
  result.extend(int(z)&0xffffffff for z in bias[g*16:g*16+16])
  s=Bits()
  for z in shift[g*16:g*16+16]:s.put(z,8)
  result.extend(s.words());s=Bits()
  for k in range(32):
   for col in range(g*16,g*16+16):
    for z in w[k*2:k*2+2,col]:s.put(z,12)
  result.extend(s.words())
  if g==0:
   s=Bits()
   for r in range(0,100,4):
    for k in range(64):
     for row in range(r,r+4):s.put(x[row,k]if row<99 else 0,13)
   result.extend(s.words())
 assert len(result)==9064
 return result
def decode_source(words):
 if len(words)!=9064:raise ValueError('Source length')
 x=np.zeros((99,64),dtype=np.int64);w=np.zeros((64,256),dtype=np.int64);bias=np.zeros(256,dtype=np.int64);shift=np.zeros(256,dtype=np.int64);at=0
 for g in range(16):
  for c in range(g*16,g*16+16):
   z=int(words[at]);at+=1;bias[c]=z-(1<<32)if z&(1<<31)else z
  view=sum(int(z)<<(32*i)for i,z in enumerate(words[at:at+4]));at+=4
  for c in range(16):shift[g*16+c]=(view>>(8*c))&255
  view=sum(int(z)<<(32*i)for i,z in enumerate(words[at:at+384]));at+=384;bit=0
  for k in range(32):
   for c in range(g*16,g*16+16):
    for f in range(k*2,k*2+2):
     z=(view>>bit)&4095;bit+=12;w[f,c]=z-4096 if z&2048 else z
  if g==0:
   view=sum(int(z)<<(32*i)for i,z in enumerate(words[at:at+2600]));at+=2600;bit=0
   for r in range(0,100,4):
    for k in range(64):
     for row in range(r,r+4):
      z=(view>>bit)&8191;bit+=13
      if row<99:x[row,k]=z-8192 if z&4096 else z
      elif z!=0:raise ValueError('Invalid padding row')
 assert at==9064
 return x,w,bias,shift
def encode_output(y):
 y=np.asarray(y,dtype=np.int64)
 if y.shape!=(99,256)or np.any(abs(y)>8191):raise ValueError('Output geometry/range')
 groups=[];bits=[]
 for g in range(16):
  stream=Bits();previous=np.zeros(16,dtype=np.int64)
  for row in y[:,g*16:g*16+16]:
   delta=row-previous;u=np.where(delta>=0,2*delta,-2*delta-1)
   width=int(u.max()).bit_length();raw=width>=14;stream.put(15 if raw else width,4)
   for z in row if raw else u:stream.put(z,14 if raw else width)
   previous=row.copy()
  groups.append(stream.words());bits.append(stream.n)
 return groups,bits
def decode_output(groups):
 y=np.zeros((99,256),dtype=np.int64)
 for g,words in enumerate(groups):
  value=sum(int(z)<<(32*i)for i,z in enumerate(words));at=0;previous=np.zeros(16,dtype=np.int64)
  for row in range(99):
   tag=(value>>at)&15;at+=4
   if tag==14:raise ValueError('Reserved output tag')
   width=14 if tag==15 else tag
   for col in range(16):
    code=(value>>at)&((1<<width)-1);at+=width
    if tag==15:z=code-(1<<14)if code&(1<<13)else code
    else:z=previous[col]+(code//2 if code%2==0 else -(code//2)-1)
    if abs(z)>8191:raise ValueError('Invalid decoded output')
    previous[col]=z;y[row,g*16+col]=z
 return y
