# MOCK_TEST_REPORT

## 1. mock 测试目的

按照 PRD 的工程流程，在正式验收前验证接口、帧结构、同步流程和端到端恢复是否可行，并根据测试结果修订设计。

## 2. 测试环境

- 工作目录：`/Users/gjzhang/Desktop/文华班作业/无线通信技术`
- Python：3.13.9
- 测试命令：`python -m pytest tests -q`
- 标准验收命令：`python main.py --input Test.txt --output results/received.txt --snr 12 --seed 2026 --mod qpsk --channel awgn`

## 3. 当前测试结果

| 项目 | 结果 |
| --- | --- |
| 自动测试 | 22 passed |
| 标准验收命令 | 正常退出 |
| `results/received.txt` | 与 `Test.txt` 完全一致 |
| `results/metrics.json` | 已生成，包含 PRD 最低字段 |
| `results/constellation.png` | 已生成 |
| `results/ber_curve.png` | 已生成 |
| `results/sync_peak.png` | 已生成 |
| 12 dB QPSK/AWGN BER | 0.0 |
| 12 dB QPSK/AWGN FER | 0.0 |
| 文本一致率 | 1.0 |
| CRC 校验 | 通过 |
| 同步误差 | 0 个符号 |

## 4. mock 发现与修订

本节记录 mock 测试暴露的设计风险、缺陷与问题，以及针对 `DESIGN.md` 的修订。核心缺陷是帧头长度字段未受 FEC 保护，属于低 SNR 下的高风险问题，已在设计中修订。

| 发现（风险/缺陷/问题） | 影响 | 修订 |
| --- | --- | --- |
| 早期方案只保护 payload，帧头长度字段未受 FEC 保护 | 长度字段一旦误码，接收端可能错误截取 payload | 将 `orig_len/coded_len` 双长度字段用 3×重复码保护 |
| 单一重复码能通过基础测试，但编码效率低、解释价值有限 | 与优秀 PR 的提高项差距明显 | 默认 payload 改为卷积码 K=7 `(171,133)` + Viterbi，保留 Hamming(7,4) 对比 |
| 伪随机前导可以同步，但课程答辩中 Barker 序列更容易解释 | 同步设计表达不够标准 | 改为 Barker-13 重复 8 次作为前导 |
| 原实现只支持 QPSK/AWGN | 无 Level 3 对比实验 | 增加 BPSK、16-QAM、Rayleigh、Rician、ZF/MMSE |
| 图表若依赖 matplotlib 可能在隐藏环境缺包 | 图表生成不稳定 | 使用标准库直接写 PNG |

## 5. 结论

mock 测试后，系统已从基础 Level 2 版本升级为包含 Level 3 对比模块的版本。标准 PRD 命令仍能在 12 dB、QPSK、AWGN、seed 2026 下完全恢复 `Test.txt`，并输出 metrics 和三张图。扩展模块用于实验分析和答辩说明，不影响基础验收入口。

