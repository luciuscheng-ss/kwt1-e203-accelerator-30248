"""Independent full-event C++ VCD crop adapter with one-pass raw SHA-256.

API-compatible with frozen vcd_window.scan_and_crop. No signal is removed from
the PT waveform. The C++ process parses the exact byte stream hashed here.
Python 3.6 and a C++11 compiler; no Python packages or vendor APIs required.
"""
import argparse
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import time

from vcd_window import read_header

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'vcd_window_fast.cpp'
LAST_RUN = None


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def identity(value):
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def ensure_engine():
    command = shlex.split(os.environ.get('CXX', 'g++'))
    if not command or not shutil.which(command[0]):
        raise ValueError('C++11 compiler unavailable; the frozen Python scanner remains separate')
    command[0] = os.path.abspath(shutil.which(command[0]))
    source_sha, compiler_sha = sha(SOURCE), sha(command[0])
    key = hashlib.sha256((source_sha + compiler_sha + json.dumps(command)).encode('utf-8')).hexdigest()
    cache = HERE / 'results/vcd_fast_engine_cache' / key
    executable, manifest = cache / 'vcd_window_fast', cache / 'build.json'
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix='building-', dir=str(cache.parent)))
        try:
            args = command + ['-std=c++11', '-O3', '-DNDEBUG', str(SOURCE), '-o', str(temporary / 'vcd_window_fast')]
            result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, timeout=120)
            (temporary / 'compile.log').write_text(result.stdout)
            if result.returncode:
                raise ValueError('C++ VCD scanner compile failed: ' + result.stdout[-4000:])
            if sha(SOURCE) != source_sha or sha(command[0]) != compiler_sha:
                raise ValueError('Compiler/source changed during build')
            build = {'source': str(SOURCE), 'source_sha256': source_sha,
                     'compiler': command[0], 'compiler_sha256': compiler_sha,
                     'compile_command': args, 'executable_sha256': sha(temporary / 'vcd_window_fast'),
                     'compile_log_sha256': sha(temporary / 'compile.log')}
            (temporary / 'build.json').write_text(json.dumps(build, indent=2) + '\n')
            try:
                os.rename(str(temporary), str(cache))
            except OSError:
                if not cache.is_dir():
                    raise
        finally:
            if temporary.exists():
                shutil.rmtree(str(temporary))
    build = json.loads(manifest.read_text())
    if (build['source_sha256'] != source_sha or build['compiler_sha256'] != compiler_sha or
            build['executable_sha256'] != sha(executable) or build['compile_log_sha256'] != sha(cache / 'compile.log')):
        raise ValueError('Cached VCD scanner provenance changed')
    return executable, manifest, build


class HeaderLines:
    def __init__(self, stream):
        self.stream = stream
        self.size = 0

    def __iter__(self):
        return self

    def __next__(self):
        line = self.stream.readline()
        if not line:
            raise StopIteration
        self.size += len(line)
        return line.decode('ascii')


def parse_statistics(path, scale, definitions, by_path, start, end, rebase):
    observed, changed, unknown, stats, controls_start, controls_end, gaps = set(), set(), set(), {}, [], [], []
    meta, complete, seen = None, False, set()
    def optional(value):
        return None if value == '-1' else int(value)
    with Path(path).open(encoding='ascii') as stream:
        for line in stream:
            row = line.rstrip('\n').split('\t')
            if row[0] == 'META' and len(row) == 4 and meta is None:
                meta = row[1:]
            elif row[0] == 'START_CONTROL' and len(row) == 2:
                controls_start.append(row[1])
            elif row[0] == 'END_CONTROL' and len(row) == 2:
                controls_end.append(row[1])
            elif row[0] == 'GAP' and len(row) == 3:
                gaps.append([int(row[1]), int(row[2])])
            elif row[0] == 'ID' and len(row) in (6, 17):
                code = row[1]
                if code in seen or code not in definitions:
                    raise ValueError('Duplicate/unknown identifier in C++ scanner result')
                seen.add(code)
                if any(v not in ('0', '1') for v in row[2:6]):
                    raise ValueError('Invalid activity flags')
                if row[2] == '1': observed.add(code)
                if row[3] == '1': changed.add(code)
                if row[4] == '1': unknown.add(code)
                if row[5] == '1':
                    if len(row) != 17:
                        raise ValueError('Missing tracked statistics')
                    entry = {'initial': None if row[6] == '-' else row[6], 'last': None if row[7] == '-' else row[7],
                             'last_time': int(row[8]), 'changes': int(row[9]), 'bit_flips_known': int(row[10]),
                             'unknown_ticks': int(row[11]), 'rising_edges': int(row[12]),
                             'first_rise': optional(row[13]), 'last_rise': optional(row[14]),
                             'min_period_ticks': optional(row[15]), 'max_period_ticks': optional(row[16])}
                    entry['unknown_duration_ns'] = float(Decimal(entry['unknown_ticks']) * scale)
                    if entry['rising_edges'] > 1:
                        entry['mean_rising_period_ns'] = float(Decimal(entry['last_rise'] - entry['first_rise']) * scale / (entry['rising_edges'] - 1))
                    stats[code] = entry
                elif len(row) != 6:
                    raise ValueError('Unexpected untracked statistics')
            elif row == ['COMPLETE', '1'] and not complete:
                complete = True
            else:
                raise ValueError('Malformed C++ scanner report row')
    if not complete or meta is None or seen != set(definitions):
        raise ValueError('Incomplete full-identifier C++ scan')
    return {'timescale_ns': str(scale), 'start_tick': start, 'end_tick': end,
            'output_start_tick': 0 if rebase else start, 'output_end_tick': end-start if rebase else end,
            'origin_shift_ticks': start if rebase else 0, 'raw_first_tick': optional(meta[0]), 'raw_last_tick': int(meta[1]),
            'initial_snapshot_mode': meta[2], 'start_dump_controls': controls_start, 'end_dump_controls': controls_end,
            'dump_off_gaps_within_window': gaps, 'unique_vcd_ids': len(definitions),
            'definitions': definitions, 'by_path': by_path, 'observed_ids': observed, 'changed_ids': changed,
            'unknown_ids': unknown, 'tracked_stats': stats}


def scan_and_crop(source, destination, start_ns, end_ns, tracked_paths, rebase=False):
    global LAST_RUN
    LAST_RUN = None
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination:
        raise ValueError('Refusing to overwrite original activity')
    executable, build_path, build = ensure_engine()
    destination.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    work = Path(tempfile.mkdtemp(prefix='vcd-fast-', dir=str(destination.parent)))
    process = None
    try:
        with source.open('rb') as stream:
            source_identity = identity(os.fstat(stream.fileno()))
            lines = HeaderLines(stream)
            header, scale, definitions, by_path = read_header(lines)
            header_bytes = header.encode('ascii')
            if lines.size != len(header_bytes):
                raise ValueError('VCD header byte accounting differs')
            start_exact, end_exact = Decimal(str(start_ns))/scale, Decimal(str(end_ns))/scale
            start, end = int(start_exact.to_integral_value()), int(end_exact.to_integral_value())
            if abs(Decimal(start)-start_exact)>Decimal('0.001') or abs(Decimal(end)-end_exact)>Decimal('0.001'):
                raise ValueError('log window cannot be represented in VCD ticks; increase timing-log precision')
            if start<0 or end<=start:
                raise ValueError('Invalid VCD crop window')
            if end > (1 << 63) - 1:
                raise ValueError('VCD timestamps exceed reviewed signed 64-bit engine range')
            tracked = {by_path[p]['code'] for p in tracked_paths if p in by_path}
            config = work / 'config.tsv'
            config.write_text('%d %d %d %d\n' % (lines.size, start, end, bool(rebase)) + ''.join(
                '%s\t%d\t%d\n' % (code, entries[0]['width'], code in tracked) for code, entries in sorted(definitions.items())))
            stats_path = work / 'statistics.tsv'
            args = [str(executable), str(config), str(destination), str(stats_path)]
            process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stream.seek(0)
            raw_hash, count, prefix = hashlib.sha256(), 0, 0
            try:
                for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
                    if prefix < len(header_bytes):
                        n = min(len(block), len(header_bytes)-prefix)
                        if block[:n] != header_bytes[prefix:prefix+n]:
                            raise ValueError('VCD header changed between declaration review and byte-stream scan')
                        prefix += n
                    raw_hash.update(block)
                    count += len(block)
                    process.stdin.write(block)
                process.stdin.close()
                process.stdin = None
                stdout, stderr = process.communicate(timeout=3600)
            except BrokenPipeError:
                try:
                    process.stdin.close()
                except BrokenPipeError:
                    pass
                process.stdin = None
                stdout, stderr = process.communicate(timeout=10)
                raise ValueError('C++ VCD parser rejected input: ' + stderr.decode('utf-8', errors='replace')[-4000:])
            if process.returncode or stdout != b'VCD_FAST_COMPLETE\n' or stderr:
                raise ValueError('C++ VCD scan failed: ' + stderr.decode('utf-8', errors='replace')[-4000:])
            if identity(os.fstat(stream.fileno())) != source_identity or identity(source.stat()) != source_identity or count != source_identity[2]:
                raise ValueError('Raw VCD changed during the exact hashed scan')
        result = parse_statistics(stats_path, scale, definitions, by_path, start, end, rebase)
        if set(result['tracked_stats']) != tracked:
            raise ValueError('Tracked macro/clock identifiers were omitted')
        if sha(executable) != build['executable_sha256'] or sha(SOURCE) != build['source_sha256']:
            raise ValueError('VCD engine changed during scan')
        output_identity = identity(destination.stat())
        output_sha = sha(destination)
        if identity(destination.stat()) != output_identity:
            raise ValueError('Cropped VCD changed during output hashing')
        LAST_RUN = {'engine': 'independent_cpp11_full_event_scanner', 'source': str(source),
                    'source_identity': source_identity, 'source_sha256': raw_hash.hexdigest(), 'source_bytes': count,
                    'source_hash_and_parser_same_byte_stream': True,
                    'destination': str(destination), 'destination_identity': output_identity, 'destination_sha256': output_sha,
                    'all_vcd_signal_events_preserved_in_window': True, 'source_full_reads': 1,
                    'wall_seconds': time.monotonic()-started, 'engine_binary': str(executable),
                    'engine_binary_sha256': build['executable_sha256'], 'engine_source': str(SOURCE),
                    'engine_source_sha256': build['source_sha256'], 'engine_build': str(build_path),
                    'engine_build_sha256': sha(build_path), 'raw_header_sha256': hashlib.sha256(header_bytes).hexdigest(),
                    'statistics_sha256': sha(stats_path), 'physical_timing_verified': False}
        return result
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            if process.stdin is not None:
                try:
                    process.stdin.close()
                except BrokenPipeError:
                    pass
                process.stdin = None
            process.communicate()
        shutil.rmtree(str(work))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--vcd',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--start-ns')
    p.add_argument('--end-ns')
    p.add_argument('--log',type=Path,help='Extract the sole GPIO window when explicit bounds are omitted')
    p.add_argument('--profile',type=Path,help='Track all declared macro pins and HF/LF signals in this profile')
    p.add_argument('--track',action='append',default=[])
    p.add_argument('--report',type=Path,required=True)
    p.add_argument('--compare-frozen',action='store_true',help='Also run the frozen scanner once; require identical scan data and cropped bytes')
    x=p.parse_args()
    if x.output.exists() or x.report.exists():p.error('Use new crop/report paths')
    start,end=x.start_ns,x.end_ns
    if start is None or end is None:
        if not x.log:p.error('Provide both bounds or a GPIO timing log')
        rows=re.findall(r'^KWT_GPIO_ACTIVITY_WINDOW start_ns=([0-9.]+) end_ns=([0-9.]+) cycles=\d+ mcycle_cycles=\d+\s*$',x.log.read_text(),re.M)
        if len(rows)!=1:p.error('Expected exactly one GPIO window')
        start,end=rows[0]
    tracked=list(x.track)
    if x.profile:
        profile=json.loads(x.profile.read_text())
        tracked += [profile['clock_signal'],profile['lf_clock_signal']]
        for macro in profile['macros']:tracked += [macro['scope']+'/'+pin for pin in macro['pins']]
    result=scan_and_crop(x.vcd,x.output,start,end,tracked,rebase=True)
    comparison=None
    if x.compare_frozen:
        from vcd_window import scan_and_crop as reference_scan
        reference=x.output.with_name(x.output.name+'.frozen-reference.vcd')
        if reference.exists():p.error('Frozen comparison destination already exists')
        began=time.monotonic()
        expected=reference_scan(x.vcd,reference,start,end,tracked,rebase=True)
        elapsed=time.monotonic()-began
        reference_sha=sha(reference)
        if expected!=result or reference_sha!=LAST_RUN['destination_sha256']:
            raise ValueError('Actual VCD differs between frozen and fast scanners; do not use fast output')
        if identity(x.vcd.stat())!=LAST_RUN['source_identity']:
            raise ValueError('Raw VCD changed during frozen comparison')
        comparison={'all_scan_fields_equal':True,'cropped_bytes_sha_equal':True,'reference_vcd':str(reference.resolve()),
                    'reference_sha256':reference_sha,'frozen_scan_seconds':elapsed,'fast_scan_seconds_with_hashes':LAST_RUN['wall_seconds'],
                    'speedup':elapsed/LAST_RUN['wall_seconds']}
    compact={key:value for key,value in result.items() if key not in ('definitions','by_path','observed_ids','changed_ids','unknown_ids')}
    for key in ('observed_ids','changed_ids','unknown_ids'):compact[key]=sorted(result[key])
    x.report.parent.mkdir(parents=True,exist_ok=True)
    x.report.write_text(json.dumps({'status':'scanned_not_power_accepted','scan':compact,'processing':LAST_RUN,'comparison':comparison},indent=2)+'\n')
    print(json.dumps({'status':'scanned_not_power_accepted','bytes':LAST_RUN['source_bytes'],
                      'wall_seconds':LAST_RUN['wall_seconds'],'raw_sha256':LAST_RUN['source_sha256'],
                      'crop_sha256':LAST_RUN['destination_sha256'],'comparison':comparison}))


if __name__=='__main__':main()
