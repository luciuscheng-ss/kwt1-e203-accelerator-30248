# KWT 第一线性层共享 SRAM 工程

本科初赛保守版，普通 MODE0。源数据 8168 个 32 位字先经原 System Bus 写入共享 SRAM，CPU 随后启动 DMA。DMA 全量读取源数据，硬件完成点积、偏置和数值转换，将完整 99×256 矩阵按 signed16 定长容器写回共享 SRAM，共 12672 字、50688 字节。

DMA 读写先仲裁，再与 CPU 仲裁，合流后进入原 e203_subsys_mems 内存互连。原互连配置保持服务器原件：SPLT_FIFO_OUTS_NUM=1、ICB_FIFO_DP=2、ICB_FIFO_CUT_READY=1；没有层次 defparam 覆盖。自研缓冲、两级仲裁保留，遵循下游握手。没有 TCM 数据替代、独立 SRAM 写口、bank 并行旁路或装载副本直接消费。

数值配置保留 X11 W11 O13、M4 R6 和原舍入规则。输出每个值由 14 位量化器结果符号扩展至 16 位，按行优先存放。具体布局和解码见 FIXED16_FORMAT.json 与 experiments/shared_bus_write_allocate_20261111/FORMAT_NATIVE51.json。

在原平台环境准备硬件：

    python3 hardware/prepare.py --soc-root SOC_ROOT --vendors-record VENDOR_RECORD --out NEW_PREPARED

完整 RTL 冷任务回归：

    python3 verification/run_release.py --prepared NEW_PREPARED/source_manifest.json --soc SOC_ROOT --out NEW_RTL

同一网表的完整回归增加 --mapping MAPPING_RESULT.json。默认 14 组正常与边界测试、2 组命令和响应背压测试。每组检查全部原始码、量化码、矩阵写回和真实 SRAM 读回；独立观察器检查两级仲裁的请求、响应归属和顺序，以及原总线分流器最多一笔在途。

软件编码入口为 encode_task_native51.py，定长解码入口为 decode_task_native51.py；numeric_reference_native51.py 只生成验证期望值。最新指标与原总线参数核查见本版最终证据索引，历史配置 2 的结果保留在独立历史目录。
