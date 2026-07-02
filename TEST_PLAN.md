# TEST_PLAN

## 1. 测试目标

测试覆盖 PRD 基础验收、公开测试边界和参考 PR 中的提高项：

- UTF-8 文本与 bitstream 双向转换。
- PN 扰码/解扰可逆。
- QPSK Gray 映射符合 PRD。
- 卷积码 K=7 `(171,133)` 和硬判决 Viterbi 可纠错。
- Hamming(7,4) 可作为对比基线修正单比特错误。
- 帧结构正确封装 Barker 前导、`orig_len/coded_len`、coded payload 和 CRC-16。
- AWGN 固定 seed 可复现。
- 前导同步能处理 0-128 个符号前置偏移。
- BPSK/QPSK/16-QAM 均能在高 SNR 下端到端恢复。
- Rayleigh/Rician + ZF/MMSE 在高 SNR 下能端到端恢复。
- CLI 能生成 `received.txt`、`metrics.json` 和三张图。
- 低 SNR 不崩溃，输出 BER/FER/text_match_rate/checksum 失败标记。

## 2. 自动测试

运行：

```bash
python -m pytest tests -q
```

当前测试数：22 项。

主要覆盖：

| 类别 | 用例 |
| --- | --- |
| 源编码 | 中文 UTF-8 round trip |
| 扰码 | PN XOR 可逆 |
| 调制 | QPSK PRD 映射；BPSK/QPSK/16-QAM 无噪声 round trip |
| 信道编码 | 卷积码/Viterbi；Hamming(7,4) |
| 帧结构 | 长度字段、coded length、CRC-16、payload 解析 |
| 同步 | 37 符号偏移、12 dB AWGN 下误差不超过 1 |
| 信道 | AWGN/Rayleigh/Rician 长度和噪声功率检查 |
| 端到端 | QPSK 12 dB；BPSK/QPSK/16-QAM 高 SNR；Rayleigh/Rician 高 SNR |
| CLI | 必需命令生成文件、metrics 和图表 |
| 鲁棒性 | 低 SNR 不崩溃；不支持调制抛出清晰错误 |

## 3. PRD 公开验收命令

```bash
python main.py --input Test.txt --output results/received.txt --snr 12 --seed 2026 --mod qpsk --channel awgn
```

通过条件：

- 程序退出码为 0。
- `results/received.txt` 存在。
- `results/metrics.json` 存在。
- `results/received.txt` 与 `Test.txt` 完全一致。
- `metrics.json` 包含 `snr_db`、`seed`、`modulation`、`channel`、`payload_bits`、`ber`、`fer`、`text_match_rate`、`checksum_pass`、`sync_start_index`。
- 至少两张图存在；本实现生成 `constellation.png`、`ber_curve.png`、`sync_peak.png` 三张。

## 4. 扩展验收命令

```bash
python main.py --input Test.txt --output results/received_16qam.txt --snr 18 --seed 2026 --mod 16qam --channel awgn
python main.py --input Test.txt --output results/received_rayleigh.txt --snr 24 --seed 2026 --mod qpsk --channel rayleigh --equalizer zf
python main.py --input Test.txt --output results/received_rician.txt --snr 24 --seed 2026 --mod qpsk --channel rician --equalizer mmse
```

预期：高 SNR 下文本完全恢复，CRC 通过。

## 5. 人工检查

- 查看 `results/constellation.png`，确认星座聚类符合所选调制。
- 查看 `results/sync_peak.png`，确认红色检测线处于明显相关峰值。
- 查看 `results/ber_curve.png`，确认 BER 随 SNR 提升整体下降。
- 查看 `metrics.json` 中 `sync_error_symbols`，12 dB AWGN 下应不超过 1。
- 确认文档与代码一致，没有声称未实现功能。

