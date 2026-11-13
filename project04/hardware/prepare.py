"""Prepare current own RTL plus exact native-platform overlay, without editing base.
Run inside the authorized platform environment. The vendor record is the actual
vendor_models_sha256 mapping from native51/result.json, whose files remain there.
"""
from pathlib import Path
import argparse,json,hashlib,subprocess,sys,importlib.util,shutil
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--soc-root',type=Path,required=True);a.add_argument('--vendors-record',type=Path,required=True);a.add_argument('--out',type=Path,required=True);x=a.parse_args();here=Path(__file__).resolve().parent;assert not x.out.exists();I=here/'integration';profile=json.loads((I/'resource_profile.json').read_text())
 assert all(sha(x.soc_root/n)==h for n,h in profile['source_sha256'].items());assert all(sha(x.soc_root/n)==h for n,h in profile['required_resources'].items());record=json.loads(x.vendors_record.read_text());vendors=record['vendor_models_sha256'];assert len(vendors)==7 and all(sha(n)==h for n,h in vendors.items());x.out.mkdir(parents=True)
 subprocess.run([sys.executable,str(I/'prepare_native_overlay.py'),'--soc-root',str(x.soc_root),'--out',str(x.out/'overlay'),'--native-platform-repairs'],check=True)
 overlay=json.loads((x.out/'overlay/overlay_manifest.json').read_text());spec=importlib.util.spec_from_file_location('current_clockgate_adapter',I/'clockgate_adapter.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);n='rtl/e203/generic/GENERIC_RVT_SMIC.v';p=x.out/'GENERIC_RVT_SMIC.v';p.write_bytes(m.transform((x.soc_root/n).read_bytes().decode('latin1')).encode('latin1'))
 rtl=[]
 for n,v in profile['source_roles'].items():
  if v['role']not in ['rtl','simulation_only']:continue
  rtl.append(x.out/'overlay'/n if n in overlay['generated_sha256']else p if n=='rtl/e203/generic/GENERIC_RVT_SMIC.v'else x.soc_root/n)
 subprocess.run([sys.executable,str(here/'uart_fix/run_equivalence.py'),'--source-root',str(x.soc_root),'--output',str(x.out/'uart_guard'),'--simulator','vcs','--execution-environment','official-platform','--vcs','/eda/synopsys/vcs/vcs_2020.03-SP2-6/bin/vcs'],check=True)
 guard=json.loads((x.out/'uart_guard/overlay_guard.json').read_text());assert guard['status']=='passed'and guard['functional_equivalence_verified']and guard['official_platform_verified']and not guard['errors'];assert all(sha(n)==h for k in ['inputs_sha256','outputs_sha256']for n,h in guard[k].items());assert sha(guard['result'])==guard['result_sha256'] and sha(guard['overlay'])==guard['overlay_sha256']
 old=[z for z in rtl if z.name=='apb_uart.v'];assert len(old)==1 and sha(old[0])==guard['original_source_sha256'];rtl=[Path(guard['overlay'])if z==old[0]else z for z in rtl]
 owned=x.out/'owned_rtl';shutil.copytree(here/'rtl',owned);rtl+=sorted(owned.glob('*.sv'));assert len([p for p in rtl if p.name=='scaled_quantize2.sv'])==1
 assert sha(owned/'scaled_quantize2.sv')=='2451debded5ce3530ac7139cf0f1ab977d9a6f3ced335f9e8e031b73e3e3bb2f'
 r={'top':'e203_soc_top','RTL_sources':{str(n.resolve()):sha(n)for n in rtl},'simulation_vendor_models':vendors,'synthesis_exclude':['sirv_sim_ram.v'],'include_dirs':[str((x.soc_root/n).resolve())for n in profile['include_dirs']],'defines_simulation':['ARM_UD_MODEL','functional','KWT_NATIVE_GATES','DISABLE_SV_ASSERTION=1'],'defines_synthesis':['SYNTHESIS','DISABLE_SV_ASSERTION=1'],'actual_top_pins_unchanged':True,'accelerator_or_DMA_TCM_data_connection':False,'official_loader_qualified':False,'resource_profile_sha256':sha(I/'resource_profile.json'),'overlay_sha256':sha(x.out/'overlay/overlay_manifest.json'),'vendor_record_sha256':sha(x.vendors_record),'preparer_sha256':sha(__file__),'UART_guard_sha256':sha(x.out/'uart_guard/overlay_guard.json'),'output_format':'fixed16_rowmajor_v1','MODE0_only':True};(x.out/'source_manifest.json').write_text(json.dumps(r,indent=2)+'\n');print('Prepared original SystemBus/shared512KiB SoC;',len(rtl),'sources; team loader uses existing publicCPU MEM ports; see manual interface review')
if __name__=='__main__':main()
