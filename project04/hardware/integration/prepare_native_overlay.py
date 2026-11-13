"""Hash-bound SystemBus/shared-SRAM overlay. Original sources are read-only.
No accelerator/DMA TCM ports; no new SoC pin or host loading port.
"""
from pathlib import Path
import re,json,hashlib,argparse,importlib.util
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
PINNED={'rtl/e203/subsys/e203_subsys_main.v':'4258161cac87bc56ef19f22ee8c82dbcae9d3effb2f0159282d3f8acd85c015c','rtl/e203/subsys/e203_subsys_top.v':'dcf1a6d8161f724926ef5fb58c52b67c9911444abbd08901b5fb9bd158b0339f','rtl/e203/soc/e203_soc_top.v':'97bfe3fd1119b4682589a48f57a60e108d496e2c1c1a53d7c0255b50fe79c02b'}
fields={'cmd_valid':1,'cmd_ready':1,'cmd_read':1,'cmd_addr':32,'cmd_wdata':32,'cmd_wmask':4,'rsp_valid':1,'rsp_ready':1,'rsp_rdata':32,'rsp_err':1}
def declarations(prefix,exclude=()):return '\n'.join(' wire '+(f'[{w-1}:0] 'if w>1 else'')+prefix+n+';'for n,w in fields.items()if n not in exclude)+'\n'
def connection(prefix,net):return ',\n'.join(' .'+prefix+n+'('+net+n+')'for n in fields)
def replace_argument(text,port,new):
 pattern=r'(\.'+re.escape(port)+r'\s*\()\s*[^)]*(\))'
 text,n=re.subn(pattern,lambda m:m[1]+new+m[2],text);assert n==1,(port,n)
 return text

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--soc-root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--native-platform-repairs',action='store_true');a=ap.parse_args();O=a.out;assert not O.exists()
 pinned=dict(PINNED)
 if a.native_platform_repairs:pinned.update({'rtl/e203/mem_wrap/sram_wrap_32KX64.v':'e285d9ce317ebe18b7edfa4d2791cfa4cbae3dee70a50b3720cec579af1d47d9','rtl/e203/mem_wrap/sram_wrap_64KX32.v':'e2b8f0380b24c290027af6c72a14941a0cb166a0cb285ae66f7e7055c59b5786','rtl/e203/mems/sirv_mrom_top.v':'4a142b388f286a1cafe15e9351e1c7ca3b3fa42eade369b90da2c5ff65def85a'})
 for n,h in pinned.items():assert sha(a.soc_root/n)==h,'Native base version changed: '+n
 source={n:(a.soc_root/n).read_bytes().decode('latin1')for n in pinned};result={}
 n='rtl/e203/subsys/e203_subsys_main.v';s=source[n];assert s.count('module e203_subsys_main(')==1
 s=s.replace('module e203_subsys_main(','module e203_subsys_main(\n output kwt_shared_rst_n,',1)
 start=s.index('e203_subsys_mems u_e203_subsys_mems(');end=s.index('\n  );',start)+len('\n  );');old=s[start:end];inst=old
 for suffix in fields:
  inst=replace_argument(inst,'mem_icb_'+suffix,'kwt_f_'+suffix)
  inst=replace_argument(inst,'sysmem_icb_'+suffix,'kwt_s_'+suffix)
 # Original DM/QSPI/ROM links remain byte-for-byte outside these20 arguments.
 decl=declarations('kwt_f_')+declarations('kwt_s_')+''' wire kwt_start,kwt_stream_mode,kwt_busy,kwt_done,kwt_fault;
 wire [31:0] kwt_source_base,kwt_result_base,kwt_cycles;
 wire [13:0] kwt_source_requests,kwt_source_writes,kwt_source_acks,kwt_source_reads;
 wire [15:0] kwt_result_words;
 assign kwt_shared_rst_n=bus_rst_n;
'''
 status=''' .task_start(kwt_start),.stream_mode(kwt_stream_mode),.source_base(kwt_source_base),.result_base(kwt_result_base),
 .busy(kwt_busy),.done(kwt_done),.fault(kwt_fault),.cycles(kwt_cycles),
 .source_requests(kwt_source_requests),.source_writes(kwt_source_writes),.source_acks(kwt_source_acks),.source_reads(kwt_source_reads),.result_words(kwt_result_words)'''
 attach=' kwt_soc_engine_attachment u_kwt_systembus(\n .clk(hfclk),.rst_n(bus_rst_n),\n'+connection('u_','mem_icb_')+',\n'+connection('f_','kwt_f_')+',\n'+status+'\n );\n'
 csr=' kwt_sysmem_csr u_kwt_sysmem_csr(\n .clk(hfclk),.rst_n(bus_rst_n),\n'+connection('','kwt_s_')+',\n'+connection('m_','sysmem_icb_')+',\n'+status+'\n );\n'
 # Preserve the provided memory-fabric parameterization exactly.
 # Original instance: ICB_FIFO_DP=2, ICB_FIFO_CUT_READY=1, SPLT_FIFO_OUTS_NUM=1.
 # No hierarchy defparam overrides of original fabric or buffer counters.
 params=''
 s=s[:start]+decl+attach+csr+inst+params+s[end:];result[n]=s
 n='rtl/e203/subsys/e203_subsys_top.v';s=source[n];s=s.replace('module e203_subsys_top(','module e203_subsys_top(\n output kwt_sysmem_clk,kwt_sysmem_rst_n,',1)
 needle='e203_subsys_main  u_e203_subsys_main(';assert s.count(needle)==1;s=s.replace(needle,needle+'\n .kwt_shared_rst_n(kwt_sysmem_rst_n),',1)
 needle='wire hfclk;';assert s.count(needle)==1;s=s.replace(needle,needle+'\n assign kwt_sysmem_clk=hfclk;',1);result[n]=s
 n='rtl/e203/soc/e203_soc_top.v';s=source[n];needle='e203_subsys_top u_e203_subsys_top(';assert s.count(needle)==1
 decl=declarations('sysmem_icb_',exclude=('cmd_valid','cmd_ready'))+' wire kwt_sysmem_clk,kwt_sysmem_rst_n;\n'
 memory=' kwt_shared_sram512 u_kwt_shared_sram(\n .clk(kwt_sysmem_clk),.rst_n(kwt_sysmem_rst_n),\n'+connection('','sysmem_icb_')+'\n );\n'
 s=s.replace(needle,decl+memory+needle+'\n .kwt_sysmem_clk(kwt_sysmem_clk),.kwt_sysmem_rst_n(kwt_sysmem_rst_n),',1)
 for suffix in fields:s=replace_argument(s,'sysmem_icb_'+suffix,'sysmem_icb_'+suffix)
 assert re.search(r'module e203_soc_top\s*\((.*?)\);',s,re.S)[0]==re.search(r'module e203_soc_top\s*\((.*?)\);',source[n],re.S)[0],'SoC pin list changed'
 result[n]=s
 if a.native_platform_repairs:
  for n,width,macro in [('rtl/e203/mem_wrap/sram_wrap_32KX64.v',12,'RAMSP4KX64'),('rtl/e203/mem_wrap/sram_wrap_64KX32.v',13,'RAMSP8KX32')]:
   original=source[n]
   # Four-bank native wrappers drive an extra address bit into fixed macros.
   # Make the existing implicit lower-bit cast explicit, retaining all bank
   # selects, capacity, aliases, control/data ports and actual native macros.
   pattern=r'(\.A\s*\(\s*Address)\s*\[\s*AddrWidth\s*-\s*3\s*:\s*0\s*\](\s*\))'
   transformed,count=re.subn(pattern,lambda m:m[1]+'['+str(width-1)+':0]'+m[2],original,flags=re.IGNORECASE)
   assert count==4 and len(re.findall(r'\b'+macro+r'\s+\w+\s*\(',original))==4,'Unexpected provided TCM four-bank pin binding: '+n+' matches='+str(count)
   result[n]=transformed
  n='rtl/e203/mems/sirv_mrom_top.v';path=Path(__file__).with_name('rom_adapter.py');spec=importlib.util.spec_from_file_location('kwt_native_ROM_adapter',path);adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter);result[n]=adapter.transform(source[n])
 O.mkdir(parents=True)
 for n,s in result.items():p=O/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(s.encode('latin1'))
 report={'scope':__doc__,'original_sha256':pinned,'generated_sha256':{n:sha(O/n)for n in result},'top_pins_unchanged':True,'new_host_loading_port':False,'accelerator_or_DMA_TCM_data_ports':False,'original_cpu_bus_peripherals_and_always_on_sources':'Three integration overlays; optional native pin-cast/ROM handshake repairs separately recorded, original CPU/TCM datapath never connects to AI','SystemBus_route':'DMAread/writeorderedarbiter -> CPU/DMAorderedarbiter -> originale203_subsys_mems.u_sirv_mem_fab32bitSystemBus -> SysMemCSR/memorymux -> single32bitshared512KiBSRAMinterface;CPU joinsbeforeoriginalfabric;noTCM/bankparallel/writeport/streambypass','clock':'original PLL hfclk; shared SRAM receives exported same clock and original synchronized bus reset; no replacement clock','native_platform_repairs':{'enabled':a.native_platform_repairs,'TCM':'Original four-bank ITCM/DTCM, explicit native12/13-bit casts only; supplied capacity/aliases preserved, no extension','ROM':'Real synchronous native ROM1-cycle response repair, actual-model protocol test required','actual_model_protocol_verified':False},'source_modes':{'reset_default':0,'mode0':'allparametersphysicallywrittenfirst,CPUstart,ordinarySystemBusSRAMreads','other':'CSRrejects;nostreamcopyconsumerpath'},'original_fabric_parameters':{'SPLT_FIFO_OUTS_NUM':1,'ICB_FIFO_DP':2,'ICB_FIFO_CUT_READY':1,'overrides':[],'basis':'Originalserverinstanceverified20261113;teamconservativechoice,notofficialmultipleoutstandingban'},'numeric_format':'training-frozen X11/W11 M4/R6 O13, five rows x16cols','official_loader_qualified':False,'full_soc_qualified':False,'generator_sha256':sha(__file__)}
 (O/'overlay_manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
