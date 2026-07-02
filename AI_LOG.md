# AI_LOG

## 1. 学生信息

- Student ID: 2022040399
- Name: 张桂嘉
- GitHub username: 123zgj123
- Fork repository URL: https://github.com/123zgj123/wireless-final-project-template
- Branch: main
- PR number: 22

## 2. AI 使用说明

本项目使用 Codex 辅助完成 PRD 理解、设计文档、测试计划、mock 测试、代码实现、调试和文档同步。下表按时间记录关键 prompt（提示词）、AI 输出与人工修改。每条 prompt 都经过人工复核后再采纳。项目代码没有绕过无线通信链路直接复制输入文件，也没有硬编码公开测试输出。

## 3. 关键 prompt 与处理记录

| 时间 | Prompt/任务 | AI 输出 | 采纳与修改 |
| --- | --- | --- | --- |
| 2026-07-02 | 深度理解 PRD 并完成任务 | 抽取固定链路、QPSK、AWGN、同步、metrics、图表和文档要求 | 先实现基础可验收版本 |
| 2026-07-02 | 参考优秀 PR 记录进一步优化 | 对比发现缺少卷积码、双长度字段、CRC-16、Barker 前导、多调制和衰落信道 | 升级为默认卷积码/Viterbi，补 Level 3 对比模块 |
| 2026-07-02 | 改进帧结构 | 建议保护帧头长度字段，避免低 SNR 下解析错误 | 采用 `REP3(orig_len + coded_len)` |
| 2026-07-02 | 增加测试覆盖 | 生成编码、调制、同步、信道、CLI 和鲁棒性测试 | 保留 22 项自动测试，全部通过 |

## 4. AI 生成内容

- `main.py`
- `src/source_codec.py`
- `src/source.py`
- `src/scrambling.py`
- `src/crypto.py`
- `src/channel_coding.py`
- `src/framing.py`
- `src/modulation.py`
- `src/channel.py`
- `src/synchronization.py`
- `src/metrics.py`
- `src/plots.py`
- `src/pipeline.py`
- `tests/test_core_modules.py`
- `PRD.md`
- `DESIGN.md`
- `TEST_PLAN.md`
- `MOCK_TEST_REPORT.md`
- `AI_LOG.md`
- `PR_DESCRIPTION.md`

## 5. 人工/工程判断

- 默认链路保留 PRD 指定 QPSK + AWGN，保证教师公开测试入口稳定。
- payload 使用卷积码 K=7 `(171,133)`，因为它比重复码更符合无线通信课程中的纠错编码要求。
- CRC-16 覆盖原始信息位并放入 FEC 保护范围，使校验字段自身也具备抗噪能力。
- 帧头使用 3×重复码保护，解决 mock 测试暴露的长度字段脆弱问题。
- 16-QAM、Rayleigh/Rician、ZF/MMSE 作为扩展模块，不替代基础 QPSK/AWGN 验收。
- 图表不依赖 matplotlib，降低环境依赖风险。

## 6. 验证记录

自动测试：

```bash
python -m pytest tests -q
```

结果：

```text
22 passed
```

标准验收：

```bash
python main.py --input Test.txt --output results/received.txt --snr 12 --seed 2026 --mod qpsk --channel awgn
```

结果摘要：

```text
BER=0
FER=0
text_match_rate=1
checksum_pass=True
```

扩展验证：

```bash
python main.py --input Test.txt --output results/received_16qam.txt --snr 18 --seed 2026 --mod 16qam --channel awgn
python main.py --input Test.txt --output results/received_rayleigh.txt --snr 24 --seed 2026 --mod qpsk --channel rayleigh --equalizer zf
```

结果均为 `BER=0`、`FER=0`、`text_match_rate=1`、`checksum_pass=True`。

## 7. 未实现或未声称内容

- 未实现完整 OFDM、多径信道估计、软判决 Viterbi 或自适应调制。
- 未声称本项目已有 69 项测试；当前项目实际自动测试为 22 项，并已全部通过。
