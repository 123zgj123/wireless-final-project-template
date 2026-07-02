# 无线通信技术期末项目 PRD 摘要与本实现对齐说明

项目名称：基于 AI 辅助编程的无线通信文件传输基带仿真系统

学生信息：

- Student ID: 2022040399
- Name: 张桂嘉
- GitHub username: 123zgj123
- Fork repository URL: https://github.com/123zgj123/wireless-final-project-template
- Branch: main

## 1. 固定系统链路

`Test.txt -> Source Encode -> Encrypt/Scramble -> Channel Encode -> Frame Build -> QPSK Modulate -> Channel -> Synchronization -> QPSK Demodulate -> Channel Decode -> Decrypt/Descramble -> Source Decode -> received.txt -> Metrics/Plots`

## 2. 统一命令行入口

```bash
python main.py --input Test.txt --output results/received.txt --snr 12 --seed 2026 --mod qpsk --channel awgn
```

## 3. PRD 基础要求与实现状态

| PRD 要求 | 本实现 |
| --- | --- |
| UTF-8 文本与 bitstream 互转 | `src/source_codec.py` |
| 可逆扰码或加密 | 16 bit LFSR PN 序列 XOR 扰码 |
| 至少一种信道编码 | 默认卷积码 K=7 `(171,133)` rate-1/2 + 硬判决 Viterbi |
| 帧结构包含前导、长度、载荷、校验 | Barker-13 重复前导 + `orig_len/coded_len` + coded payload + CRC-16 |
| QPSK 必做 | PRD 指定 Gray 映射 QPSK |
| AWGN 必做 | 支持 AWGN，SNR 为符号功率/复噪声功率 |
| 同步不能假设起点已知 | 前导归一化互相关检测，支持 0-128 符号偏移 |
| 输出 `metrics.json` | 已输出最低字段和扩展字段 |
| 至少两张图 | 已生成星座图、BER 曲线、同步峰值图三张 |

## 4. QPSK 映射

基础系统采用 PRD 指定 Gray 编码：

- `00 -> (1+j)/sqrt(2)`
- `01 -> (-1+j)/sqrt(2)`
- `11 -> (-1-j)/sqrt(2)`
- `10 -> (1-j)/sqrt(2)`

## 5. SNR 与 Eb/N0

SNR 定义为接收端调制符号平均功率与复高斯噪声平均功率之比，单位 dB。`metrics.json` 额外记录 `ebn0_db`，按 `Eb/N0 = SNR - 10log10(bits_per_symbol)` 计算；QPSK 下为 `SNR - 3.01 dB`。

## 6. 提高模块

在不影响 PRD 必需入口的基础上，项目增加以下对比实验能力：

- BPSK/QPSK/16-QAM 多调制。
- Rayleigh/Rician flat fading。
- ZF/MMSE 均衡。
- Hamming(7,4) 对比基线。

## 7. 提交物

- `PRD.md`
- `DESIGN.md`
- `TEST_PLAN.md`
- `MOCK_TEST_REPORT.md`
- `AI_LOG.md`
- `PR_DESCRIPTION.md`
- `Test.txt`
- `main.py`
- `src/`
- `tests/`
- `results/`
