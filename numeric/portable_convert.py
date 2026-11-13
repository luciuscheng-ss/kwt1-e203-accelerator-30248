"""Python3.6+ stdlib adapter for the existing frozen format. No MAC or Alpha calculation."""
from pathlib import Path
import argparse,ast,hashlib,json,math,struct,zipfile
FREEZE='f0d58263c179a89d164cffbf3f866db68d52f8c27ead48add034c49896becef2'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read_npy_bytes(data):
 if data[:6]!=b'\x93NUMPY':raise ValueError('NPY required')
 major,minor=data[6:8]
 if major==1:n=struct.unpack('<H',data[8:10])[0];off=10
 elif major in (2,3):n=struct.unpack('<I',data[8:12])[0];off=12
 else:raise ValueError('Unsupported NPY version')
 header=ast.literal_eval(data[off:off+n].decode('utf8'if major==3 else'latin1'));shape=header['shape'];dtype=header['descr']
 if header['fortran_order']or not isinstance(shape,tuple)or any(not isinstance(s,int)or s<0 for s in shape):raise ValueError('C-order numeric shape required')
 types={'f4':'f','f8':'d','i1':'b','i2':'h','i4':'i','i8':'q','u1':'B','u2':'H','u4':'I','u8':'Q'}
 if not isinstance(dtype,str)or dtype[0]not in '<>=|'or dtype[1:]not in types:raise ValueError('Fixed numeric NPY dtype required')
 count=1
 for s in shape:count*=s
 if count>10000000:raise ValueError('NPY too large')
 byteorder='>'if dtype[0]=='>'else'<'
 fmt=byteorder+str(count)+types[dtype[1:]]
 if len(data)-off-n!=struct.calcsize(fmt):raise ValueError('NPY payload length')
 return shape,list(struct.unpack(fmt,data[off+n:]))
def read_npy(p):return read_npy_bytes(Path(p).read_bytes())
def read_npz(p,key):
 with zipfile.ZipFile(str(p))as z:return read_npy_bytes(z.read(key+'.npy'))
def write_npy(p,shape,values):
 text=repr({'descr':'<f8','fortran_order':False,'shape':tuple(shape)})
 head=(text+' '*((16-(10+len(text)+1)%16)%16)+'\n').encode('ascii')
 Path(p).write_bytes(b'\x93NUMPY'+b'\x01\x00'+struct.pack('<H',len(head))+head+struct.pack('<'+str(len(values))+'d',*values))
def rounded(x):return (-1 if x<0 else 1)*int(math.floor(abs(x)+.5))
def isqrt(n):
 if n<0:raise ValueError('Negative norm energy')
 if n<2:return n
 x=1<<((n.bit_length()+1)//2)
 while True:
  y=(x+n//x)//2
  if y>=x:return x
  x=y
class Bits:
 def __init__(self):self.value=0;self.n=0
 def put(self,v,n):self.value|=(int(v)&((1<<n)-1))<<self.n;self.n+=n
 def words(self):return[(self.value>>(32*i))&0xffffffff for i in range((self.n+31)//32)]
def encode(project,input_path,layer):
 project=Path(project)
 if not 0<=layer<12:raise ValueError('Layer0..11 required')
 base=project/'experiments/joint_search_8000_20261111';p=base/'narrow11/freeze_X11W11O13.json'
 if sha(p)!=FREEZE:raise ValueError('Wrong numeric freeze')
 f=json.loads(p.read_text())
 if not all(sha(project/n)==h for n,h in f['numeric_configs_and_code'].items()):raise ValueError('Changed frozen parameter/source')
 cfg=json.loads((base/('narrow11/training_o13/x11w11_layer_%02d.json'%layer)).read_text())
 shape,x=read_npy(input_path);ws,qw=read_npz(base/('dynamic12/w11_layer_%02d.npz'%layer),'qw');bs,bias=read_npz(project/'artifacts/reference/weights.npz','b%02d'%layer)
 if shape!=(99,64)or ws!=(64,256)or bs!=(256,):raise ValueError('Geometry')
 if not all(math.isfinite(v)for v in x)or any(abs(z)>1023 for z in qw):raise ValueError('Finite input/code range required')
 S=cfg['input_feature_scale'];sw=cfg['weight_scale'];xx=[float(v)/S[i%64]for i,v in enumerate(x)]
 sx=max(max(abs(v)for v in xx)/1023,cfg['minimum_input_scale'])
 qx=[min(1023,max(-1023,rounded(v/sx)))for v in xx];qb=[rounded(float(bias[c])/(sx*sw[c]))for c in range(256)]
 if any(z<-(1<<31)or z>=(1<<31)for z in qb):raise ValueError('Bias range')
 energy=max(sum(v*v for v in qx[r*64:(r+1)*64])for r in range(99));M=[];R=[]
 for c in range(256):
  we=sum(qw[k*256+c]**2 for k in range(64));v=energy*we;root=isqrt(v);bound=max(1,root+(root*root!=v)+abs(qb[c]));r=max(0,bound.bit_length()+4-13);m=max(1,min(15,(4095<<r)//bound))
  if r>38:raise ValueError('Requantization shift')
  R.append(r);M.append(m)
 words=[]
 for g in range(16):
  words.extend(z&0xffffffff for z in qb[g*16:g*16+16]);b=Bits()
  for c in range(g*16,g*16+16):b.put(M[c]|(R[c]<<4),10)
  words.extend(b.words());b=Bits()
  for k in range(32):
   for c in range(g*16,g*16+16):
    for f in range(k*2,k*2+2):b.put(qw[f*256+c],11)
  words.extend(b.words())
  if g==0:
   b=Bits()
   for rowbase in range(0,100,5):
    for k in range(64):
     for row in range(rowbase,rowbase+5):b.put(qx[row*64+k]if row<99 else 0,11)
   words.extend(b.words())
 if len(words)!=8168:raise AssertionError('Source packet length')
 meta={'layer':layer,'numeric_freeze_sha256':FREEZE,'input_scale':sx,'weight_scale':sw,'M':M,'R':R,'output_shape':[99,256],'output_format':'fixed16_rowmajor_v1','output_word_count':12672,'source_word_count':8168,'expected_outputs_present':False,'input_file_sha256':sha(input_path),'encoder_sha256':sha(__file__)}
 return words,meta

def decode(words,meta):
 if meta.get('numeric_freeze_sha256')!=FREEZE or meta.get('output_format')!='fixed16_rowmajor_v1'or meta.get('output_shape')!=[99,256]:raise ValueError('Wrong format')
 if len(words)!=12672 or any(type(v)is not int or v<0 or v>0xffffffff for v in words):raise ValueError('Complete unsigned32 matrix words required')
 sx=float(meta['input_scale']);sw=meta['weight_scale'];M=meta['M'];R=meta['R']
 if not math.isfinite(sx)or sx<=0 or any(len(v)!=256 for v in[sw,M,R]):raise ValueError('Scale dimensions')
 if any(not math.isfinite(float(z))or float(z)<=0 for z in sw)or any(type(z)is not int or not 1<=z<=15 for z in M)or any(type(z)is not int or not 0<=z<=38 for z in R):raise ValueError('Scale/coefficients')
 out=[]
 for i,word in enumerate(words):
  for z in[word&65535,word>>16]:
   q=z-65536 if z&32768 else z;c=len(out)%256
   if not -4095<=q<=4095:raise ValueError('Sign extension/O13 range')
   v=q*sx*float(sw[c])*(2.**R[c])/M[c]
   if not math.isfinite(v):raise ValueError('Nonfinite decoded output')
   out.append(v)
 return out

def main():
 p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command');e=sub.add_parser('encode');e.add_argument('--project',type=Path,default=Path(__file__).resolve().parents[1]/'project04');e.add_argument('--input',type=Path,required=True);e.add_argument('--layer',type=int,required=True);e.add_argument('--source-hex',type=Path,required=True);e.add_argument('--decode-metadata',type=Path,required=True);d=sub.add_parser('decode');d.add_argument('--result-hex',type=Path,required=True);d.add_argument('--decode-metadata',type=Path,required=True);d.add_argument('--decoded',type=Path,required=True);a=p.parse_args()
 if a.command=='encode':
  if a.source_hex.exists()or a.decode_metadata.exists()or a.source_hex.resolve()==a.decode_metadata.resolve():raise ValueError('Fresh distinct output files required')
  words,meta=encode(a.project,a.input,a.layer);payload=''.join('%08x\n'%z for z in words);meta['source_hex_sha256']=hashlib.sha256(payload.encode()).hexdigest();a.source_hex.write_text(payload);a.decode_metadata.write_text(json.dumps(meta,indent=2)+'\n');print('Encoded',len(words),'sourcewords')
 elif a.command=='decode':
  if a.decoded.exists():raise ValueError('Fresh output required')
  values=decode([int(v,16)for v in a.result_hex.read_text().split()],json.loads(a.decode_metadata.read_text()));write_npy(a.decoded,(99,256),values);print('Decoded',len(values),'signed16codes')
 else:p.error('encode or decode command required')
if __name__=='__main__':main()
