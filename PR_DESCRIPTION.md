# 2022040399-张桂嘉-无线通信期末项目

## Student Information

- Student ID: 2022040399
- Name: 张桂嘉
- GitHub username: 123zgj123
- Fork repository URL: https://github.com/123zgj123/wireless-final-project-template
- Branch: main
- PR number: （创建后由 GitHub 自动分配）

## Checklist

- [x] I have read `PRD.docx`.
- [x] I have completed `DESIGN.md`.
- [x] I have completed `TEST_PLAN.md`.
- [x] I have completed `MOCK_TEST_REPORT.md`.
- [x] I have completed `AI_LOG.md`.
- [x] The project supports the required command (`python main.py --input Test.txt --output results/received.txt --snr 12 --seed 2026 --mod qpsk --channel awgn`).
- [x] The project generates `results/received.txt`.
- [x] The project generates `results/metrics.json`.
- [x] The project generates at least two required plots.
- [x] I understand the communication principles and code logic of my submission.

## Notes

实现要点：

- 基础链路：Gray 映射 QPSK + AWGN；符号功率 SNR 口径（QPSK 下 Eb/N0 = SNR - 3.01 dB）。
- 信道编码：卷积码 K=7 (171,133) rate-1/2 + 硬判决 Viterbi（含 Hamming(7,4) 对比基线）。
- 帧结构：Barker-13 重复前导 + orig_len/coded_len 双长度字段（3×重复保护）+ CRC-16；CRC 覆盖原始信息位并受 FEC 保护。
- 同步：前导归一化互相关，覆盖 0-128 符号偏移，12 dB 标准用例同步误差为 0 符号。
- 提高模块（Level 3）：Rayleigh/Rician 衰落 + ZF/MMSE 均衡；BPSK/QPSK/16-QAM 多调制对比。
- 工程流程：PRD -> DESIGN -> TEST_PLAN -> mock -> TDD -> 验证，全程记录于 AI_LOG.md；mock 测试发现并修订“帧头长度字段未受 FEC 保护”缺陷。
- 本地测试：自动测试 22 项全部通过；SNR >= 12 dB/seed 2026 下 `received.txt` 与 `Test.txt` 完全一致。
