"""Read-only current library area/LEF geometry audit, no architecture metrics reuse."""
from pathlib import Path
import json,hashlib,csv,statistics,re
from collections import Counter
from area_units import parse_lef
R=Path(__file__).resolve().parent;P=R.parent;sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();M=json.loads((R/'MANIFEST.json').read_text());assert all(sha(R/n)==h for n,h in M.items())
A=P/'native_uart339';area=json.loads((A/'result.json').read_text());assert area['pass'];assert all(sha(n)==h for n,h in area['library_sha256'].items())
q=json.loads((P/'native_help103/lef_candidates.json').read_text());assert len(q['LEF'])==1;lef=Path(q['LEF'][0]);geom=parse_lef(lef)['cells'];raw={};counts=Counter()
for v in csv.DictReader((A/'synth/leaf_cells.tsv').open(),delimiter='\t'):
 ref=v['ref']
 if ref.lower()in ['**logic_0**','**logic_1**']:continue
 x=float(v['area']);assert ref not in raw or abs(raw[ref]-x)<1e-8;raw[ref]=x;counts[ref]+=1
std=[n for n in raw if not(n.startswith('RAMSP')or n.startswith('ROM1KX32'))];rows=[];missing=[]
for n in std:
 if n not in geom:missing.append(n);continue
 rows.append({'ref':n,'mapped_instances':counts[n],'library_area':raw[n],'LEF_area_um2':geom[n]['area_um2'],'um2_per_library_unit':geom[n]['area_um2']/raw[n]})
ratios=[x['um2_per_library_unit']for x in rows];assert ratios
r={'pass':False,'scope':__doc__,'library_sha256':area['library_sha256'],'mapped_sha256':area['mapped_sha256'],'parent_area_result_sha256':sha(A/'result.json'),'std_LEF':{'path':str(lef),'sha256':sha(lef),'geometry_basis':'LEF SIZE width and height in micrometres'},'standard_rows':rows,'missing_standard_refs':missing,'standard_refs':len(std),'standard_mapped_ref_geometry_complete':not missing,'standard_um2_per_library_unit_min':min(ratios),'standard_um2_per_library_unit_max':max(ratios),'standard_um2_per_library_unit_median':statistics.median(ratios),'macro_geometry':[],'macro_geometry_missing':[],'original_library_files_remain_server_only':True,'official_PPA_conditions_qualified':False,'official_added_area_qualified':False}
# Only bounded descendants of each actual vendor-model resource directory.
frozen=json.loads((P/'native_probe51/result.json').read_text());vendors=frozen['vendor_models_sha256'];assert all(sha(n)==h for n,h in vendors.items());candidates=[];entries=0
for n in vendors:
 path=Path(n)
 if not any(ref.lower()in path.name.lower()for ref in area['macro_inventory']):continue
 root=path.parent.parent;level=[root]
 for depth in range(3):
  nxt=[]
  for d in level[:24]:
   try:items=list(d.iterdir())
   except OSError:continue
   for p in items:
    entries+=1
    if p.is_file()and p.suffix.lower()=='.lef':candidates.append(p)
    if p.is_dir()and not p.is_symlink()and p.name.lower()not in ['gds','gdsii','verilog','vhdl']:nxt.append(p)
  level=nxt
r['bounded_macro_resource_entries']=entries;found={}
for p in sorted(set(candidates)):
 try:cells=parse_lef(p)['cells']
 except ValueError:continue
 for ref in area['macro_inventory']:
  if ref in cells:
   v={'reference':ref,'library_area':raw[ref],'LEF_area_um2':cells[ref]['area_um2'],'um2_per_library_unit':cells[ref]['area_um2']/raw[ref],'LEF_path':str(p),'LEF_sha256':sha(p)}
   if ref in found:assert abs(found[ref]['LEF_area_um2']-v['LEF_area_um2'])<1e-6,'Conflicting macro geometry'
   found[ref]=v
r['macro_geometry']=list(found.values());r['macro_geometry_missing']=sorted(set(area['macro_inventory'])-set(found));r['all_macro_geometry_complete']=not r['macro_geometry_missing'];r['pass']=True
(R/'result.json').write_text(json.dumps(r,indent=2)+'\n')
