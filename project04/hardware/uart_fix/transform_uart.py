#!/usr/bin/env python3
"""One default assignment; preserve every original byte and module interface."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RELATIVE = 'rtl/e203/perips/apb_uart/apb_uart.v'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def transform(source, expected):
    data = Path(source).read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('UART source SHA differs from reviewed official version')
    # Match the unique write-block default, not the asserted-valid THR branch.
    anchor = b"        fifo_tx_valid   = 1'b0;        \n"
    if data.count(anchor) != 1 or data.count(b'fifo_tx_data  = PWDATA[7:0];') != 1:
        raise ValueError('UART default/THR structure differs; review new source explicitly')
    fixed = data.replace(anchor, anchor + b'        fifo_tx_data    = PWDATA[7:0]; // defined also when TX enqueue is invalid\n', 1)
    if fixed.replace(b'        fifo_tx_data    = PWDATA[7:0]; // defined also when TX enqueue is invalid\n', b'', 1) != data:
        raise ValueError('More than the reviewed default assignment changed')
    return fixed


def generate(source_root, output):
    review = json.loads((HERE / 'reviewed_original.json').read_text())
    source = Path(source_root) / RELATIVE
    fixed = transform(source, review['sources_sha256'][RELATIVE])
    output = Path(output)
    if output.exists():
        raise ValueError('Choose a new overlay path; do not overwrite prior input')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(fixed)
    return {'original_path': str(source.resolve()), 'original_sha256': sha(source),
            'overlay_path': str(output.resolve()), 'overlay_sha256': sha(output),
            'change': 'Add fifo_tx_data=PWDATA[7:0] only in the existing combinational default section.'}


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root', required=True); p.add_argument('--output', required=True)
    args = p.parse_args()
    print(json.dumps(generate(args.source_root, args.output), indent=2))
