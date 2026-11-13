"""Current-map leaf inventory, conservative added-area split and LEF unit audit."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,json,hashlib,csv,sys
ap=argparse.ArgumentParser();ap.add_argument('--mapping',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
R=Path('/home/2026contest/server6/s6_19usr/kwt_systembus_joint_20261111_01');O=a.out;assert not O.exists();O.mkdir();sys.path.insert(0,str(R/'native_area377'));from area_units import parse_lef
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();syn=json.loads(a.mapping.read_text());assert syn['pass']and sha(Path(syn['mapped']))==syn['mapped_sha256'];assert all(sha(Path(n))==h for n,h in syn['library_sha256'].items())
rows=[];refs={};counts=Counter();macros=Counter();roles=defaultdict(float)
for v in csv.DictReader(Path(syn['leaf_cells']).open(),delimiter='\t'):
 n,ref=v['name'],v['ref']
 if ref.lower()in['**logic_0**','**logic_1**']:continue
 area=float(v['area']);assert int(v['library_matches'])>0;assert ref not in refs or abs(refs[ref]-area)<1e-8;refs[ref]=area;counts[ref]+=1
 memory=ref.startswith('RAMSP')or ref.startswith('ROM1KX32')
 if memory:macros[ref]+=1
 if n.startswith('u_kwt_shared_sram/'):role='fixed_shared_macro'if ref=='RAMSP8KX32'else'added_shared_controller'
 elif'/u_kwt_systembus/'in n:role='added_accelerator_and_interface'
 elif'/u_kwt_sysmem_csr/'in n:role='added_CSR_and_mux'
 elif'/u_e203_subsys_mems/'in n:role='fixed_original_ROM_macro'if ref.startswith('ROM1KX32')else'conservative_added_original_mems_and_ROM_glue'
 elif'/u_e203_srams/'in n:role='fixed_TCM_macro'if memory else'conservative_added_native_TCM_pin_glue'
 elif ref=='CLKLANAQV4_12TR40':role='conservative_added_original_gate_library_binding'
 else:role='fixed_original_CPU_bus_peripheral_AON'
 roles[role]+=area;rows.append({'name':n,'ref':ref,'area_library_units':area,'role':role})
assert dict(macros)=={'RAMSP8KX32':20,'RAMSP4KX64':4,'RAMSP1024X16':7,'RAMSP128X16':24,'ROM1KX32':1},dict(macros)
candidate=json.loads((R/'native_help103/lef_candidates.json').read_text());assert len(candidate['LEF'])==1;stdlef=Path(candidate['LEF'][0]);stdgeom=parse_lef(stdlef)['cells'];geometry=[]
for ref,area in refs.items():
 if ref in macros:continue
 assert ref in stdgeom,ref;ratio=stdgeom[ref]['area_um2']/area;assert abs(ratio-1)<1e-4,(ref,ratio);geometry.append({'ref':ref,'instances':counts[ref],'area_um2':stdgeom[ref]['area_um2'],'library_area':area})
vendors=json.loads((R/'native_probe51/result.json').read_text())['vendor_models_sha256'];lefs=[]
for n,h in vendors.items():
 p=Path(n);assert sha(p)==h
 if not any(ref.lower()in p.name.lower()for ref in macros):continue
 levels=[p.parent.parent]
 for depth in range(3):
  nxt=[]
  for d in levels[:24]:
   try:items=list(d.iterdir())
   except OSError:continue
   for p in items:
    if p.is_file()and p.suffix.lower()=='.lef':lefs.append(p)
    if p.is_dir()and not p.is_symlink()and p.name.lower()not in['gds','gdsii','verilog','vhdl']:nxt.append(p)
  levels=nxt
macrogeom={}
for p in sorted(set(lefs)):
 try:cells=parse_lef(p)['cells']
 except ValueError:continue
 for ref in macros:
  if ref in cells:
   assert abs(cells[ref]['area_um2']/refs[ref]-1)<1e-4
   if ref in macrogeom:assert abs(macrogeom[ref]['area_um2']-cells[ref]['area_um2'])<1e-6
   macrogeom[ref]={'area_um2':cells[ref]['area_um2'],'instances':macros[ref],'LEF_path':str(p),'LEF_sha256':sha(p)}
assert set(macrogeom)==set(macros)
added=sum(v for k,v in roles.items()if k.startswith('added_')or k.startswith('conservative_added_'))/1e6;whole=sum(roles.values())/1e6
r={'pass':added<=2.25,'mapped_sha256':syn['mapped_sha256'],'mapping_result_sha256':sha(a.mapping),'added_area_mm2':added,'whole_digital_area_mm2':whole,'area_roles_library_units':dict(roles),'macro_inventory':dict(macros),'internal_accelerator_macros':31,'internal_accelerator_bytes':20480,'standard_ref_count':len(geometry),'standard_geometry':geometry,'macro_geometry':macrogeom,'standard_LEF_sha256':sha(stdlef),'unit_conversion':'Allmappedstandardandmacrorefs matchedLEFphysicalum2; mm2=um2/1e6','official_added_budget_mm2':2.25,'leaf_area_inventory':rows,'original_library_sources_exported':False}
(O/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k]for k in['pass','added_area_mm2','whole_digital_area_mm2','mapped_sha256']}))
