"""Source-bound native four-bank pin staging, no TCM hardware data port."""
import re, json, hashlib
from pathlib import Path

def generate(soc, out):
    soc,out=Path(soc),Path(out)
    root='u_soc.u_e203_subsys_top.u_e203_subsys_main.u_e203_cpu_top'
    cpu=root+'.u_e203_cpu'
    lines=['// Actual native instances; public pins only. Diagnostic fixture.',
           '`define IC '+cpu+'.u_e203_itcm_ctrl.u_sram_icb_ctrl.u_sirv_1cyc_sram_ctrl',
           '`define DC '+cpu+'.u_e203_dtcm_ctrl.u_sram_icb_ctrl.u_sirv_1cyc_sram_ctrl']
    banks={};evidence={}
    for role,wrapper,macro,width,ab in [('itcm','32KX64','RAMSP4KX64',64,12),('dtcm','64KX32','RAMSP8KX32',32,13)]:
        p=soc/('rtl/e203/mem_wrap/sram_wrap_'+wrapper+'.v')
        text=p.read_bytes().decode('latin1')
        names=re.findall(r'\b'+macro+r'\s+(\w+)\s*\(',text)
        assert len(names)==4 and len(set(names))==4,(role,names)
        assert sorted(int(re.search(r'_([0-3])$',n)[1])for n in names)==[0,1,2,3],names
        names.sort(key=lambda n:int(re.search(r'_([0-3])$',n)[1]))
        paths=[root+'.u_e203_srams.u_e203_'+role+'_ram.u_sram_wrap_'+wrapper+'.'+n for n in names]
        banks[role]=paths
        evidence[role]={'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'instances':paths,'capacity_extension':False}
        clkvec='{'+','.join(p+'.CLK' for p in paths)+'}'
        ctrl='`IC' if role=='itcm' else '`DC'
        lines += ['task check_'+role+'_idle; begin',
                  ' if(clk!==0 || '+ctrl+'.rst_n!==1 || '+ctrl+'.ram_cs!==0 || '+ctrl+'.u_ram_clkgate.clk_in!==0 || '+ctrl+'.u_ram_clkgate.clock_en!==0 || '+ctrl+'.u_ram_clkgate.test_mode!==0)',
                  '  $fatal(1,"Unsafe '+role+' clock handoff reset=%b CS=%b CK=%b EN=%b TEST=%b",'+ctrl+'.rst_n,'+ctrl+'.ram_cs,'+ctrl+'.u_ram_clkgate.clk_in,'+ctrl+'.u_ram_clkgate.clock_en,'+ctrl+'.u_ram_clkgate.test_mode);',
                  ' end endtask',
                  'task check_'+role+'_clocks_low; begin if('+clkvec+'!==4\'b0)$fatal(1,"'+role+' clock release not known low");end endtask',
                  'task release_'+role+'_clocks; begin check_'+role+'_idle();']
        lines += [' release '+p+'.CLK;' for p in paths]
        lines += [' end endtask', 'task hold_'+role+'_release_controls; begin']
        lines += [' force '+p+'.CLK=1\'b0;' for p in paths]
        lines += [' release '+p+'.'+pin+';' for p in paths for pin in ('CEN','GWEN','WEN','A','D')]
        lines += [' end endtask', 'task '+('begin_itcm_boot' if role=='itcm' else 'begin_dtcm_stage')+'; begin']
        for bank,p in enumerate(paths):
            # Code and task payload fit original physical bank0; retain all
            # original native bank mapping/aliases, never initialize through
            # a nonexistent expanded bank_gen overlay.
            values={'CLK':'clk','CEN':"1'b0" if bank==0 else "1'b1",'GWEN':"1'b0",'WEN':str(width)+"'b0",'A':'boot_addr' if role=='itcm' else 'stage_addr','D':'boot_data' if role=='itcm' else 'stage_data'}
            lines += [' force '+p+'.'+pin+'='+value+';' for pin,value in values.items()]
        lines += [' end endtask']
    lines += ['task hold_all_tcm_clocks; begin']
    lines += [' force '+p+'.CLK=1\'b0;' for paths in banks.values() for p in paths]
    lines += [' end endtask','']
    assert not out.exists();out.write_text('\n'.join(lines))
    return evidence
