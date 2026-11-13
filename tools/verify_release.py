from pathlib import Path
import sys,json,hashlib
import numpy as np
R=Path(__file__).resolve().parents[1];P=R/'project04';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();manifest=json.loads((P/'SOURCE_SHA256.json').read_text());assert all(sha(P/n)==h for n,h in manifest.items())
sys.path.insert(0,str(R/'numeric'));from portable_convert import encode,decode
sys.path.insert(0,str(P/'experiments/shared_bus_write_allocate_20261111'));from numeric_reference_native51 import reference_task
source=np.array([int(x,16)for x in(P/'verification/vectors/source.hex').read_text().split()],dtype=np.uint32).reshape(14,8168)
matrix=np.array([int(x,16)for x in(P/'verification/vectors/matrix.hex').read_text().split()],dtype=np.uint32).reshape(14,12672)
for k in range(12):
 x=P/('examples/layer_%02d_input.npy'%k);words,meta=encode(P,x,k);ref=reference_task(np.load(x),k)
 assert words==source[k].tolist()==ref['source_words'].tolist()
 assert np.array_equal(ref['matrix_words'],matrix[k])
 assert np.array_equal(np.array(decode(matrix[k].tolist(),meta)).reshape(99,256),ref['decoded'])
 print('PASS layer',k,'8168 source words / 12672 output words / 25344 decoded values')
print('PASS',len(manifest),'frozen file hashes; all12 software models and portable converters exact')
