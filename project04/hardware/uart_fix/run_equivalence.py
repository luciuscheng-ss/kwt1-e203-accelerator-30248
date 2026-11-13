#!/usr/bin/env python3
"""Hash-bound original/repaired UART transaction equivalence; no source mutation."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import transform_uart

HERE = Path(__file__).resolve().parent
KEYS = ('checks','enqueues','full_rejects','thr_writes','dlab_writes','reads','writes',
        'consecutive','resets','invalid_differences','tx_edges','irq_edges','rx_reads')


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def run(command, log, cwd, timeout=180):
    with log.open('w') as stream:
        completed = subprocess.run([str(c) for c in command], cwd=str(cwd), stdout=stream,
                                   stderr=subprocess.STDOUT, timeout=timeout)
    return completed.returncode, log.read_text(errors='replace')


def clean(text, compile_stage=False):
    bad = re.findall(r'(?im)^.*(?:\bFatal\s*:|\bError[-:\[]|Timing violation|\$hold|\$setup).*$' , text)
    if compile_stage:
        bad += re.findall(r'(?im)^.*(?:Warning-\[(?:IPDW|PCWM[^\]]*)\]|implicit(?:ly)? (?:wire|net)|port connection width mismatch).*$' , text)
    if bad:
        raise ValueError('Simulator error diagnostics: ' + ' | '.join(bad[:4]))


def parse(text):
    clean(text)
    pattern = '^UART_EQ_RESULT ' + ' '.join(key + r'=(\d+)' for key in KEYS) + '$'
    rows = re.findall(pattern, text, re.M)
    if len(rows) != 1 or text.splitlines().count('PASS: UART valid-enqueue and external transaction equivalence') != 1:
        raise ValueError('Missing/duplicated complete UART equivalence marker')
    result = dict(zip(KEYS, map(int, rows[0])))
    minimum = {'checks':16000,'enqueues':30,'full_rejects':16,'dlab_writes':6,'reads':50,
               'consecutive':70,'invalid_differences':100,'tx_edges':40,'irq_edges':2,'rx_reads':16}
    if any(result[k] < v for k,v in minimum.items()) or result['resets'] != 3:
        raise ValueError('UART transaction coverage below reviewed minimum')
    return result


def executable(name):
    found = shutil.which(str(name))
    if not found:
        raise ValueError('Missing simulator executable: ' + str(name))
    return Path(found).absolute()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-root', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--simulator', choices=('vcs','iverilog'), default='vcs')
    ap.add_argument('--execution-environment', choices=('local-public','official-platform'), default='local-public')
    ap.add_argument('--vcs', default='vcs'); ap.add_argument('--iverilog', default='iverilog')
    ap.add_argument('--vvp', default='vvp'); ap.add_argument('--iverilog-base', type=Path)
    x = ap.parse_args(); source = x.source_root.resolve(); out=x.output.resolve()
    if out.exists():
        raise ValueError('Choose a new result directory; previous evidence remains immutable')
    if x.execution_environment == 'official-platform' and x.simulator != 'vcs':
        raise ValueError('Official-platform guard requires the actual VCS execution')
    out.mkdir(parents=True)
    result = {'schema':'kwt-uart-equivalence-v1','status':'running','errors':[], 'passes':[],
              'simulator':x.simulator,'execution_environment':x.execution_environment,
              'official_platform_verified':False,'physical_timing_verified':False,'exit_codes':{}}
    save(out/'result.json',result)
    try:
        review_path=HERE/'reviewed_original.json'; review=json.loads(review_path.read_text())
        inputs={str(source/name):digest for name,digest in review['sources_sha256'].items()}
        for name,digest in inputs.items():
            if transform_uart.sha(name)!=digest: raise ValueError('Reviewed official UART/dependency changed: '+name)
        for path in [Path(__file__).resolve(),HERE/'transform_uart.py',HERE/'uart_equivalence_tb.sv',review_path]:
            inputs[str(path)] = transform_uart.sha(path)
        correction=transform_uart.generate(source,out/'overlay'/transform_uart.RELATIVE)
        original=(source/transform_uart.RELATIVE).read_bytes()
        anchor=b'module apb_uart_sv '
        if original.count(anchor)!=1: raise ValueError('Original module rename is ambiguous')
        renamed=out/'apb_uart_original.v';renamed.write_bytes(original.replace(anchor,b'module apb_uart_original ',1))
        corrected=Path(correction['overlay_path']);tb=HERE/'uart_equivalence_tb.sv'
        dependencies=[source/name for name in review['sources_sha256'] if name!=transform_uart.RELATIVE]
        sources=[renamed,corrected]+dependencies+[tb]
        for path in sources:inputs[str(path)]=transform_uart.sha(path)
        compiler=executable(x.vcs if x.simulator=='vcs' else x.iverilog)
        inputs[str(compiler)]=transform_uart.sha(compiler)
        version_cmd=[compiler,'-ID' if x.simulator=='vcs' else '-V']
        if x.simulator=='iverilog' and x.iverilog_base: version_cmd[1:1]=['-B',x.iverilog_base.resolve()]
        code,version=run(version_cmd,out/'compiler-version.log',out)
        result['exit_codes']['version']=code
        if code!=0:raise ValueError('Compiler version query failed')
        binary=out/'simv'
        if x.simulator=='vcs':
            command=[compiler,'-full64','-sverilog','-timescale=1ns/1fs','-debug_access+all',
                     '-top','uart_equivalence_tb','-o',binary]+sources
            runtime=[binary]
        else:
            command=[compiler]
            if x.iverilog_base: command+=['-B',x.iverilog_base.resolve()]
            command+=['-g2012','-s','uart_equivalence_tb','-o',binary]+sources
            vvp=executable(x.vvp);inputs[str(vvp)]=transform_uart.sha(vvp);runtime=[vvp,binary]
        result['compile_command']=[str(v) for v in command];result['run_command']=[str(v) for v in runtime]
        code,text=run(command,out/'compile.log',out);result['exit_codes']['compile']=code
        clean(text,True)
        if code!=0:raise ValueError('UART compile returned '+str(code))
        inputs[str(binary)]=transform_uart.sha(binary)
        code,text=run(runtime,out/'run.log',out);result['exit_codes']['run']=code
        if code!=0:raise ValueError('UART simulation returned '+str(code))
        counts=parse(text)
        for path,digest in inputs.items():
            if transform_uart.sha(path)!=digest:raise ValueError('UART input changed during verification: '+path)
        result.update(status='passed',counts=counts,inputs_sha256=inputs,correction=correction,
            official_platform_verified=x.execution_environment=='official-platform',
            passes=['same APB reads/PREADY/PSLVERR every checked cycle','same serial TX and IRQ every checked cycle',
                    'same valid&&!full FIFO enqueue payload, including direct PWDATA byte oracle',
                    'DLAB writes, FIFO-full rejection, FIFO clear, reset, back-to-back APB, loopback exercised'],
            invalid_payloads_compared_for_equivalence=False,
            note='PREADY remains 1; full FIFO rejects enqueue rather than stretching APB. No internal signal was forced. Latch/STA closure requires the subsequent mapped synthesis reports.')
        result['outputs_sha256']={str(out/n):transform_uart.sha(out/n) for n in ['compiler-version.log','compile.log','run.log']}
        save(out/'result.json',result)
        guard={'schema':'kwt-uart-latch-fix-guard-v1','status':'passed',
            'official_platform_verified':result['official_platform_verified'],
            'physical_timing_verified':False,'functional_equivalence_verified':True,
            'official_profile_sha256':review['official_profile_sha256'],
            'original_sources_sha256':review['sources_sha256'],
            'original_source_sha256':correction['original_sha256'],
            'overlay':correction['overlay_path'],'overlay_sha256':correction['overlay_sha256'],
            'inputs_sha256':inputs,'outputs_sha256':result['outputs_sha256'],
            'result':str(out/'result.json'),'result_sha256':transform_uart.sha(out/'result.json'),
            'counts':counts,'passes':result['passes'],'errors':[], 'exit_codes':result['exit_codes'],
            'simulator':x.simulator,'execution_environment':x.execution_environment,
            'change':correction['change'],'latch_elimination_requires_new_synthesis_report':True}
        save(out/'overlay_guard.json',guard)
        print(json.dumps({'status':'passed','official_platform_verified':result['official_platform_verified'],
                          'counts':counts,'guard':str(out/'overlay_guard.json')},indent=2))
    except Exception as error:
        result.update(status='failed');result['errors'].append(str(error));save(out/'result.json',result)
        raise


if __name__=='__main__':
    try: main()
    except Exception as error:
        print('UART verification failed: '+str(error),file=sys.stderr);sys.exit(2)
