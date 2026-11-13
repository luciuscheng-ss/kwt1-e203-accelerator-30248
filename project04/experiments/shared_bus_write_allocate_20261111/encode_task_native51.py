"""Encode input/parameters only. No GEMM, Alpha terms or expected outputs.
Decode metadata contains scales and the fixed matrix dimensions, never answers.
"""
from pathlib import Path
import argparse,hashlib,json,importlib.util
import numpy as np
from norm_codec11_r5 import encode_source
D=Path(__file__).resolve().parent;ROOT=D.parents[1];H=ROOT/'experiments/joint_search_8000_20261111';N=H/'narrow11'
SHA='f0d58263c179a89d164cffbf3f866db68d52f8c27ead48add034c49896becef2'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def encode_task(x,layer):
 if not 0<=layer<12:raise ValueError('Layer0..11 required')
 if np.shape(x)!=(99,64):raise ValueError('Input99x64 required')
 f=N/'freeze_X11W11O13.json';F=json.loads(f.read_text());assert sha(f)==SHA
 assert all(sha(ROOT/p)==h for p,h in F['numeric_configs_and_code'].items())
 spec=importlib.util.spec_from_file_location('frozen_source_convert',N/'norm_convert.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 cfg=json.loads((N/f'training_o13/x11w11_layer_{layer:02d}.json').read_text());qw=np.load(H/f'dynamic12/w11_layer_{layer:02d}.npz')['qw'];bias=np.load(ROOT/'artifacts/reference/weights.npz')[f'b{layer:02d}']
 qx,qw,qb,shift,mult,sx,_=module.convert(x,bias,cfg,qw,4,13)
 words=encode_source(qx,qw,qb,mult,shift);assert len(words)==8168
 metadata={'layer':layer,'numeric_freeze_sha256':SHA,'input_scale':float(sx),'weight_scale':cfg['weight_scale'],'M':mult.tolist(),'R':shift.tolist(),'output_shape':[99,256],'output_format':'fixed16_rowmajor_v1','output_word_count':12672,'source_word_count':8168,'expected_outputs_present':False,'purpose':'Float decode scales and fixed format dimensions; no accelerator answers'}
 return words,metadata

def decode_output_words(words,metadata):
 import sys
 sys.path.insert(0,str(ROOT/'software'))
 from fixed16_matrix import decode_float
 out=decode_float(words,metadata)
 if not np.all(np.isfinite(out)):raise ValueError('Nonfinite decoded result')
 return out

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',type=Path,required=True);ap.add_argument('--layer',type=int,required=True);ap.add_argument('--source-hex',type=Path,required=True);ap.add_argument('--decode-metadata',type=Path,required=True);a=ap.parse_args()
 if a.source_hex.exists()or a.decode_metadata.exists():raise ValueError('Use fresh output files')
 if a.source_hex.resolve()==a.decode_metadata.resolve():raise ValueError('Distinct output paths required')
 words,metadata=encode_task(np.load(a.input),a.layer);payload=''.join(f'{z:08x}\n'for z in words);metadata['source_hex_sha256']=hashlib.sha256(payload.encode()).hexdigest();metadata['input_file_sha256']=sha(a.input);metadata['encoder_sha256']=sha(__file__)
 a.source_hex.write_text(payload);a.decode_metadata.write_text(json.dumps(metadata,indent=2)+'\n');print('ENCODED SOURCE ONLY',len(words),'WORDS')

if __name__=='__main__':main()
