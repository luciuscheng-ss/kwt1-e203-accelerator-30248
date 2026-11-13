"""Software numeric reference only; never used to produce hardware source data.

The runtime source formatter is narrow11/norm_convert.py plus the lossless
source encoder. GEMM below is the explicitly submitted verification model;
its answers never enter CPU task memory or the accelerator input packet.
"""
from pathlib import Path
import json,hashlib,importlib.util,argparse
import numpy as np
from norm_codec11_r5 import encode_source,decode_source
D=Path(__file__).resolve().parent;ROOT=D.parents[1];H=ROOT/'experiments/joint_search_8000_20261111';N=H/'narrow11'
FREEZE='f0d58263c179a89d164cffbf3f866db68d52f8c27ead48add034c49896becef2'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def frozen_configs():
 p=N/'freeze_X11W11O13.json';f=json.loads(p.read_text());assert sha(p)==FREEZE
 assert all(sha(ROOT/n)==h for n,h in f['numeric_configs_and_code'].items())
 return f

def reference_task(x,layer):
 """Return source packet plus reference raw/codes/output, strictly separate."""
 if not 0<=layer<12:raise ValueError('Layer must be0..11')
 if np.shape(x)!=(99,64):raise ValueError('Input must be99x64')
 spec=importlib.util.spec_from_file_location('native51_format_conversion',N/'norm_convert.py');convert=importlib.util.module_from_spec(spec);spec.loader.exec_module(convert)
 cfg=json.loads((N/f'training_o13/x11w11_layer_{layer:02d}.json').read_text());weights=np.load(ROOT/'artifacts/reference/weights.npz');qw=np.load(H/f'dynamic12/w11_layer_{layer:02d}.npz')['qw']
 qx,qw,qb,shift,mult,sx,bound=convert.convert(x,weights[f'b{layer:02d}'],cfg,qw,4,13)
 source=encode_source(qx,qw,qb,mult,shift);assert len(source)==8168
 # The only matrix operation in this file belongs to software verification.
 raw=qx@qw+qb;assert np.all(abs(raw)<=bound)and np.max(abs(raw))<1<<32
 half=np.where(shift>0,np.left_shift(np.int64(1),np.maximum(shift-1,0)),0)
 codes=np.minimum((abs(raw)*mult+half)>>shift,4095)*np.sign(raw)
 import sys
 sys.path.insert(0,str(ROOT/'software'))
 from fixed16_matrix import encode_matrix,decode_matrix
 matrix=encode_matrix(codes);assert np.array_equal(codes,decode_matrix(matrix))
 decoded=convert.decode(codes,cfg,shift,mult,sx)
 assert np.all(np.isfinite(decoded))
 return {'source_words':np.asarray(source,dtype=np.uint32),'raw':raw,'codes':codes,'matrix_words':matrix,'decoded':decoded,'input_scale':sx,'M':mult,'R':shift}

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',type=Path,required=True);ap.add_argument('--layer',type=int,required=True);ap.add_argument('--reference-output',type=Path,required=True);a=ap.parse_args()
 if a.reference_output.suffix!='.npz':raise ValueError('Reference output must end with.npz')
 if a.reference_output.exists():raise ValueError('Refuse overwrite; use a new verification output')
 frozen_configs();r=reference_task(np.load(a.input),a.layer)
 # This output is a golden/reference artifact, never a loader input file.
 np.savez(a.reference_output,**r);print('REFERENCE ONLY',a.reference_output,'SOURCE WORDS',len(r['source_words']),'RESULT WORDS',len(r['matrix_words']))

if __name__=='__main__':main()
