"""Decode the complete row-major signed16 matrix read from shared SRAM."""
from pathlib import Path
import argparse,json,numpy as np
from encode_task_native51 import decode_output_words,SHA

def decode_packet(words,metadata):
 if metadata.get('numeric_freeze_sha256')!=SHA:raise ValueError('Numeric format version differs')
 if metadata.get('output_format')!='fixed16_rowmajor_v1':raise ValueError('Fixed16 row-major format required')
 if metadata.get('output_shape')!=[99,256]:raise ValueError('Output shape differs')
 words=list(words)
 if len(words)!=12672 or any(not isinstance(v,(int,np.integer))or v<0 or v>0xffffffff for v in words):raise ValueError('Full matrix requires12672 unsigned32 words')
 m=np.asarray(metadata['M']);r=np.asarray(metadata['R']);s=np.asarray(metadata['weight_scale']);sx=float(metadata['input_scale'])
 if m.shape!=(256,)or r.shape!=(256,)or s.shape!=(256,)or np.any(m<1)or np.any(m>15)or np.any(m!=np.floor(m))or np.any(r<0)or np.any(r>38)or np.any(r!=np.floor(r))or np.any(s<=0)or not np.all(np.isfinite(s))or not np.isfinite(sx)or sx<=0:raise ValueError('Invalid decode scales')
 return decode_output_words(words,metadata)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--result-hex',type=Path,required=True);ap.add_argument('--decode-metadata',type=Path,required=True);ap.add_argument('--decoded',type=Path,required=True);a=ap.parse_args()
 if a.decoded.suffix!='.npy'or a.decoded.exists():raise ValueError('Use a fresh.npy output')
 words=[int(v,16)for v in a.result_hex.read_text().split()];out=decode_packet(words,json.loads(a.decode_metadata.read_text()));np.save(a.decoded,out);print('DECODED ACTUAL HARDWARE RESULT',out.shape)

if __name__=='__main__':main()
