# KWT-1 E203 原总线加速器 30248

本科组初赛第1—3项任务的公开技术工程。普通 MODE0，原 System Bus 配置1，完整99×256结果以 signed16 定长写入共享SRAM。自研RTL、CPU驱动、验证工程、数值模型、参数转换脚本及冻结参数均在本仓库中，可直接下载。

## 当前实现与结果
150MHz；冷任务2305.103499 task/s，CPU返回2303.333692 task/s；本地validation精度9.651493/10；新增面积0.359715599 mm²；全数字SoC功耗估算29.1mW，平均12.6µJ/任务。PPA条件SS0.99V125℃、pre-CTS理想时钟、无提取互连。吞吐从CPU配置和装载前计时至全部输出写回应答完成。
最终网表SHA256：d450453c3757474b56e5d1736357a786d73da36102be05522b9dd450b53947eb。

## 材料
- project04/hardware：完整自研RTL、原平台集成脚本、资源哈希与UART等适配验证。
- project04/firmware：248字节CPU调度驱动汇编、编译脚本、ELF/BIN及ITCM镜像。
- project04/verification：完整SoC测试台、观察器、16项回归入口、14任务验证向量及读回工具。
- project04/experiments/shared_bus_write_allocate_20261111/numeric_reference_native51.py：与RTL逐位对应的软件整数参考模型。
- numeric/portable_convert.py：Python3.6+标准库参数/输入转换和完整signed16输出解码入口。
- project04/experiments/joint_search_8000_20261111：12层冻结格式配置及权重；路径保留原工程命名。
- workflow：当前综合、驱动修复、映射后验证、STA、面积、活动和功耗复现脚本及其自研辅助代码。
- evidence：同一冻结版本的指标和技术审阅；reports：实际工具报告节选及综合说明；最终PDF在仓库Releases提供。

## 独立数值复现
```sh
python3 -m pip install -r requirements-numeric.txt
python3 tools/verify_release.py
python3 numeric/portable_convert.py encode --project project04 --input project04/examples/layer_00_input.npy --layer 0 --source-hex source0.hex --decode-metadata meta0.json
python3 project04/experiments/shared_bus_write_allocate_20261111/numeric_reference_native51.py --input project04/examples/layer_00_input.npy --layer 0 --reference-output reference0.npz
```
数值模型只用于验证，golden结果不送入硬件输入包。硬件完成64项点积、Alpha校正、偏置、舍入和饱和。测试程序逐层核对8168源字、12672输出字及25344反量化结果。

## 原平台RTL与网表验证
在赛事提供的SoC及厂商模型目录执行：
```sh
cd project04
python3 hardware/prepare.py --soc-root SOC_ROOT --vendors-record VENDOR_MODELS.json --out NEW_PREPARED
python3 verification/run_release.py --prepared NEW_PREPARED/source_manifest.json --soc SOC_ROOT --out NEW_RTL
python3 verification/run_release.py --prepared NEW_PREPARED/source_manifest.json --soc SOC_ROOT --mapping MAPPING_RESULT.json --out NEW_MAPPED
```
VENDOR_MODELS.json记录实际模型绝对路径及SHA，MAPPING_RESULT.json记录实际最终网表和叶单元清单；这两个文件由平台准备/综合阶段生成，不用占位文件代替。工具为VCS2020.03-SP2-6、DC2022.03-SP5-5及PrimeTime，采用赛题库。
DMA读写仲裁→CPU/DMA仲裁→原System Bus→共享SRAM。SPLT_FIFO_OUTS_NUM=1，FIFO深度2及ready截断1；自研缓冲不改变原总线握手。先完成全部源字装载及应答，再由CPU启动DMA重读；不使用TCM任务数据或装载副本。

完整原平台RTL、最终网表/DDC、厂商模型和原始全量PPA材料同时保留在赛事分配账号的技术归档中。公开仓库提供全部自研实现、冻结数值数据及评委可直接读取的报告；无需登录即可下载。
