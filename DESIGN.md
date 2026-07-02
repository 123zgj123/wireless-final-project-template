# DESIGN

学生信息：

- Student ID: 2022040399
- Name: 张桂嘉
- GitHub username: 123zgj123
- Fork repository URL: https://github.com/123zgj123/wireless-final-project-template
- Branch: main

## 1. 目标与统一入口

本项目实现一个端到端无线通信文件传输基带仿真系统。发送端读取 `Test.txt`，经过源编码、PN 扰码、信道编码、帧封装、调制和信道；接收端完成同步、均衡、解调、译码、解扰、CRC 校验和 UTF-8 文件恢复。

PRD 必需入口保持不变：

```bash
python main.py --input Test.txt --output results/received.txt --snr 12 --seed 2026 --mod qpsk --channel awgn
```

扩展入口支持：

```bash
python main.py --input Test.txt --output results/received.txt --snr 24 --seed 2026 --mod qpsk --channel rayleigh --equalizer zf
python main.py --input Test.txt --output results/received.txt --snr 18 --seed 2026 --mod 16qam --channel awgn
```

## 1.1 固定系统链路

本项目严格遵循 PRD 规定的固定链路，发送端到接收端依次为：

```text
Test.txt -> Source Encode -> Encrypt/Scramble -> Channel Encode -> Frame Build -> QPSK Modulate -> Channel -> Synchronization -> QPSK Demodulate -> Channel Decode -> Decrypt/Descramble -> Source Decode -> received.txt -> Metrics/Plots
```

各阶段对应关系：Source Encode（源编码）、Encrypt/Scramble（加密/扰码）、Channel Encode（信道编码）、Frame Build（帧封装）、QPSK Modulate（QPSK 调制）、Channel（无线信道）、Synchronization（同步）、QPSK Demodulate（QPSK 解调）、Channel Decode（信道译码）、Source Decode（源解码），最终由 Metrics 模块输出指标与图表。

## 2. 模块划分

| 模块 | 文件 | 功能 |
| --- | --- | --- |
| 源编码 | `src/source_codec.py`, `src/source.py` | UTF-8 文本与 MSB-first bitstream 互转 |
| 扰码 | `src/scrambling.py`, `src/crypto.py` | 16 bit LFSR PN 序列异或扰码/解扰 |
| 信道编码 | `src/channel_coding.py` | 默认卷积码 K=7 `(171,133)` rate-1/2 + 硬判决 Viterbi；保留 Hamming(7,4) 和 3×重复码 |
| 帧结构 | `src/framing.py` | Barker-13 重复前导、orig_len/coded_len 双长度字段、CRC-16 |
| 调制 | `src/modulation.py` | BPSK、PRD 必需 QPSK、16-QAM |
| 信道 | `src/channel.py` | AWGN、flat Rayleigh、flat Rician、ZF/MMSE 均衡 |
| 同步 | `src/synchronization.py` | 前导归一化互相关峰值检测 |
| 指标 | `src/metrics.py` | BER、FER、文本一致率 |
| 图表 | `src/plots.py` | 星座图、BER-SNR 曲线、同步峰值图 |
| 总链路 | `src/pipeline.py` | 端到端仿真和结果输出 |

## 3. 发送端流程

1. 读取 `Test.txt`，按 UTF-8 编码为 bytes。
2. 将 bytes 转换为 MSB-first bitstream。
3. 使用固定 16 bit LFSR PN 序列对原始 payload bits 做 XOR 扰码。
4. 计算 CRC-16/CCITT，CRC 覆盖原始信息位。
5. 将 `scrambled_payload + crc16` 送入卷积码 K=7 `(171,133)` rate-1/2，并添加 6 bit 终止尾比特。
6. 构造帧：Barker-13 重复前导 + 3×保护的 `orig_len` 和 `coded_len` + 卷积编码后的 coded payload。
7. 默认使用 QPSK Gray 映射调制；扩展支持 BPSK 和 16-QAM。
8. 在帧前添加 0-128 个随机调制符号，模拟未知帧起点。
9. 通过 AWGN 或 flat fading 信道。

## 4. 帧结构

```text
BARKER13_REPEAT8_PREAMBLE
+ REP3(ORIG_LEN_32 + CODED_LEN_32)
+ CONV_K7_171_133(SCRAMBLED_PAYLOAD + CRC16)
```

- `ORIG_LEN_32`：源编码后、扰码前的原始 payload bit 数。
- `CODED_LEN_32`：卷积编码后的 coded payload bit 数。
- `CRC16`：覆盖原始 payload bits 对应 bytes，并位于卷积码保护范围内。
- 帧头长度字段使用 3×重复码保护，修复 mock 阶段发现的“长度字段未受保护导致低 SNR 下解析错误”问题。

## 5. 调制与 SNR 口径

PRD 基础调制采用 QPSK Gray 映射：

| Bits | Symbol |
| --- | --- |
| 00 | `(1+j)/sqrt(2)` |
| 01 | `(-1+j)/sqrt(2)` |
| 11 | `(-1-j)/sqrt(2)` |
| 10 | `(1-j)/sqrt(2)` |

QPSK 平均符号功率归一化为 1。SNR 定义为接收端调制符号平均功率与复高斯噪声平均功率之比。指标中额外记录 `ebn0_db`，按 `Eb/N0 = SNR - 10log10(bits_per_symbol)` 计算；QPSK 下即 `Eb/N0 = SNR - 3.01 dB`。

## 6. 信道编码

默认 payload 采用卷积码：

- 约束长度：K=7
- 生成多项式：`171, 133` 八进制
- 码率：1/2
- 译码：硬判决 Viterbi
- 终止方式：补 6 个 0，使编码器回到 0 状态

同时保留：

- 3×重复码：用于帧头 `orig_len/coded_len` 保护。
- Hamming(7,4)：作为可解释的对比基线和单元测试覆盖。

## 7. 同步与均衡

同步不假设接收端知道帧起点。接收端用相同前导调制后，逐符号滑动计算归一化互相关：

```text
score[k] = |sum(rx[k+i] * conj(preamble[i]))| / sqrt(E_rx * E_preamble)
```

最大峰值位置作为 `sync_start_index`。默认偏移范围为 0-128 个调制符号。

AWGN 信道不需要均衡；Rayleigh/Rician 使用已知 flat fading 系数做 ZF 或 MMSE 均衡，用于 Level 3 对比实验。

## 8. 输出

标准运行生成：

- `results/received.txt`
- `results/metrics.json`
- `results/constellation.png`
- `results/ber_curve.png`
- `results/sync_peak.png`

`metrics.json` 包含 PRD 最低字段，并额外记录：

- `coded_payload_bits`
- `crc_type`
- `true_sync_offset_symbols`
- `sync_error_symbols`
- `preamble`
- `channel_code`
- `header_code`
- `equalizer`
- `fading_coefficient`
- `noise_power`
- `ebn0_db`
- `ber_curve`

## 9. 风险与处理

| 风险 | 处理 |
| --- | --- |
| 低 SNR 下帧头误码 | `orig_len/coded_len` 使用 3×重复码，多数判决恢复 |
| payload 多比特误码 | 卷积码 + Viterbi 提供纠错能力 |
| 同步偏移未知 | Barker-13 重复前导 + 归一化互相关 |
| 衰落信道幅相畸变 | ZF/MMSE 均衡 |
| UTF-8 恢复失败 | 解码使用 `errors="replace"`，保证输出指标而不崩溃 |
| 隐藏测试反硬编码 | 链路完全基于输入内容、SNR、seed 动态生成，不复制输入到输出 |
