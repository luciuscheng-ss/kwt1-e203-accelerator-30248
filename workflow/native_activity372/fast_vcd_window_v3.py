"""V3 full-event scanner; initial high levels never count as actual edges."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
ANCESTOR=HERE/'fast_vcd_window.py'
ANCESTOR_SHA='cc6e22fb0ec284e9cd10cb75fa35140db73d750858b73484bfe0d7ebd397b504'
HEADER_SHA='f832525ce3b175815221932dedc9c2cc07dffafdf059daa1841919bd8cf09ce6'
if hashlib.sha256(ANCESTOR.read_bytes()).hexdigest()!=ANCESTOR_SHA:
    raise ValueError('Frozen native adapter changed')
if hashlib.sha256((HERE/'vcd_window.py').read_bytes()).hexdigest()!=HEADER_SHA:
    raise ValueError('Frozen header/statistics reference changed')
spec=importlib.util.spec_from_file_location('vcd_v2_private_frozen_adapter',ANCESTOR)
adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
SOURCE=HERE/'vcd_window_fast_v3.cpp'
adapter.SOURCE=SOURCE
sha,identity,ensure_engine=adapter.sha,adapter.identity,adapter.ensure_engine
LAST_RUN=None


def scan_and_crop(source,destination,start_ns,end_ns,tracked_paths,rebase=False):
    global LAST_RUN
    LAST_RUN=None
    result=adapter.scan_and_crop(source,destination,start_ns,end_ns,tracked_paths,rebase=rebase)
    LAST_RUN=dict(adapter.LAST_RUN)
    LAST_RUN.update(engine='independent_cpp11_full_event_scanner_v3_actual_rises',
                    adapter_ancestor={'path':str(ANCESTOR),'sha256':ANCESTOR_SHA},
                    header_parser_sha256=HEADER_SHA,
                    v3_adapter={'path':str(Path(__file__).resolve()),'sha256':sha(__file__)})
    return result


def compact(result):
    value={k:v for k,v in result.items() if k not in ('definitions','by_path','observed_ids','changed_ids','unknown_ids')}
    for key in ('observed_ids','changed_ids','unknown_ids'):value[key]=sorted(result[key])
    return value


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('vcd','output','report'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--start-ns');p.add_argument('--end-ns');p.add_argument('--log',type=Path)
    p.add_argument('--profile',type=Path);p.add_argument('--track',action='append',default=[])
    p.add_argument('--reference-report',type=Path,help='Compare with a saved original fast scan report; never rerun the frozen Python parser')
    x=p.parse_args()
    if x.output.exists() or x.report.exists():p.error('Choose fresh output/report paths')
    start,end=x.start_ns,x.end_ns
    if start is None or end is None:
        if not x.log:p.error('Provide bounds or the actual sole GPIO timing log')
        rows=re.findall(r'^KWT_GPIO_ACTIVITY_WINDOW start_ns=([0-9.]+) end_ns=([0-9.]+) cycles=\d+ mcycle_cycles=\d+\s*$',x.log.read_text(),re.M)
        if len(rows)!=1:p.error('Expected exactly one GPIO timing window')
        start,end=rows[0]
    tracked=list(x.track)
    if x.profile:
        profile=json.loads(x.profile.read_text());tracked += [profile['clock_signal'],profile['lf_clock_signal']]
        for macro in profile['macros']:tracked += [macro['scope']+'/'+pin for pin in macro['pins']]
    reference=None
    if x.reference_report:
        reference_sha=sha(x.reference_report);reference=json.loads(x.reference_report.read_text())
        if reference.get('status')!='scanned_not_power_accepted' or 'scan' not in reference:p.error('Reference must be a saved complete original fast scan report')
    result=scan_and_crop(x.vcd,x.output,start,end,tracked,rebase=True);data=compact(result);comparison=None
    if reference:
        old=reference['processing']
        if (reference['scan']!=data or old['source_sha256']!=LAST_RUN['source_sha256'] or
            old['raw_header_sha256']!=LAST_RUN['raw_header_sha256'] or old['destination_sha256']!=LAST_RUN['destination_sha256'] or
            old['engine_source_sha256']!=sha(HERE/'vcd_window_fast.cpp') or sha(x.reference_report)!=reference_sha):
            raise ValueError('V3 statistics require explicit initial-level edge review; byte-equivalence check is separate')
        comparison={'all_scan_fields_equal':True,'same_header_definitions_and_aliases':True,'cropped_bytes_sha_equal':True,
                    'reference_report':{'path':str(x.reference_report.resolve()),'sha256':reference_sha},
                    'original_fast_seconds':old['wall_seconds'],'v2_seconds':LAST_RUN['wall_seconds'],
                    'speedup_vs_recorded_original':old['wall_seconds']/LAST_RUN['wall_seconds'],
                    'reference_engine_rerun':False,'frozen_python_parser_rerun':False}
    x.report.parent.mkdir(parents=True,exist_ok=True)
    with x.report.open('x') as stream:json.dump({'status':'scanned_not_power_accepted','scan':data,'processing':LAST_RUN,'comparison':comparison},stream,indent=2);stream.write('\n')
    print(json.dumps({'status':'scanned_not_power_accepted','source_bytes':LAST_RUN['source_bytes'],
        'seconds':LAST_RUN['wall_seconds'],'crop_sha256':LAST_RUN['destination_sha256'],'comparison':comparison}))


if __name__=='__main__':main()
