# 来源与许可
自研加速器 RTL、DMA、仲裁、存储包装、驱动、测试台、数值工具和适配脚本以根目录 MIT 许可证公开。
冻结权重、偏置及其派生量化数据来自 ARM-software/keyword-transformer 的指定 KWT-1 预训练模型，保留上游 Apache-2.0 许可证：third_party/keyword_transformer_LICENSE.txt；上游提交 237e4097afd4f6851e0b82f0a8d65c2dfe8eae30。
赛事提供的 2025 E203 平台、标准单元工艺库和 SRAM/ROM 厂商模型由评测平台提供，本仓库包含接入它们的自研代码与资源哈希，不分发这些原件。
project04 是原冻结快照，文件 SHA 保持不变；其中 PACKAGE_STATUS 和准备器字段记录生成阶段状态。最终实现与验证结果见 evidence，不用准备阶段字段替代最终验收结果。
历史未实例化的输出压缩模块保留在源快照中以保持清单一致；当前顶层连接使用 fixed_matrix_writer，输出为完整定长矩阵。
