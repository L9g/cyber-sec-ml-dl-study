# Honest NIDS — Exposing Data Leakage & Cross-Dataset Generalisation Gaps

> 网络入侵检测 (NIDS) 的 portfolio 高度饱和，把 CICIoT2023 刷到 99% 没有差异化。
> **本项目的卖点不是分类器，而是揭穿并避免 benchmark 虚高**：数据泄漏、随机切分过于乐观、跨数据集泛化崩塌——资深从业者最常吐槽的痛点。

配套文档：`../docs/DS-ML-DL-Cyber-Security-v2.md` 第三章项目一 ｜ 阅读清单：`../docs/project1-reading-list.md` ｜ 文献库：`../knowledge-base/`

---

## 当前档位：MVP 🚧

MVP 锚点（2-3 周出货）：**随机切分 LightGBM baseline + 「乐观 vs 诚实」对比表**。
本 README 的结果区会随实验填充。不在 MVP 阶段上 Docker / CI / Makefile（见主文档第五、六章三档原则）。

---

## 问题背景

找攻击与一般 ML 任务本质不同——极低基率、误报代价高、缺真实标注、闭世界假设不成立（`sommer2010outside`）。
因此**只看 accuracy 会严重误导**；这正是项目一要量化展示的（`arp2022dodonts` 的 10 大陷阱 → 见 `reports/findings.md`）。

## 数据集

| 角色 | 数据集 | 说明 |
|---|---|---|
| 主 | **NetFlow v3 统一系列** NF-UNSW-NB15-v3 / NF-ToN-IoT-v3 / NF-CSE-CIC-IDS2018-v3 | 53 个统一 NetFlow 特征（arXiv 2503.04404），**含真 IP + 真时间戳 + 未去重**，天然支持 LODO；来源/核验见 `reports/data-prep-v3.md` |
| 辅 | **修正版 CICIDS2017** | 用 Engelen/Lanvin 修正版，非原始 bug 版（`engelen2021troubleshooting`, `lanvin2023errors`） |
| 扩展 | CICIoT2023 / CICIoMT2024 | IoT/医疗差异化场景 |

> ⚠️ **不提交原始数据**（真 IP = PII）。下载说明 + checksum 见 `data/README.md` 与 `reports/data-prep-v3.md`。

## 方法（6 步叙事）

| 步骤 | 做什么 | 产物 | 档位 |
|---|---|---|---|
| 1 乐观 baseline | 随机切分 + 全特征 → 虚高 99% | optimistic 行 | MVP |
| 2 诚实重做 | temporal split + 移除泄漏特征 | 乐观 vs 诚实对比表 | MVP |
| 3 跨数据集 LODO | A 训 B 测，量化 F1 跌幅 | LODO 矩阵 | Portfolio |
| 4 建模/不平衡 | LightGBM + class_weight/SMOTE；macro-F1/PR-AUC/per-class recall | 指标表 | MVP→Portfolio |
| 5 可解释 | SHAP global + per-attack | SHAP 图 | Portfolio |
| 6 漂移监控 | 性能随时间衰减曲线 | drift 曲线 | Research |

## 仓库结构

```
01-honest-nids/
├── config.py              # SEED 与路径
├── data/README.md         # 下载说明 + checksum（不含原始数据）
├── src/
│   ├── data.py            # 加载 + temporal split
│   ├── feature_engineering.py  # 特征泄漏/捷径策略
│   └── evaluation.py      # 诚实指标 + base-rate 误报量 + 实验落盘
├── notebooks/             # 01_optimistic … 06_drift（见 notebooks/README.md）
├── reports/findings.md    # 乐观 vs 诚实 / LODO / base-rate 表
└── results/experiments.csv
```

## 复现

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# 按 data/README.md / reports/data-prep-v3.md 下载数据到 data/
marimo run notebooks/01_optimistic_baseline.py   # 只读展示；或 python notebooks/01_*.py 无头跑
python scripts/run_lodo.py                        # 跨数据集 LODO 矩阵
pytest src/tests/                                 # 确定性代码契约单测（~1s）
```

固定随机种子见 `config.py` (`SEED = 42`)。所有实验结果落盘到 `results/experiments.csv`。
测试分两层：`src/tests/`（代码契约，确定性）+ notebook 内嵌 `test_`（叙事方向性断言）——
详见 `notebooks/README.md`。

## 结果

> _待 MVP 实验填充：乐观 vs 诚实对比表 + base-rate 误报量分析。见 `reports/findings.md`。_

## 合规 / 治理

- **数据治理**：仓库不含原始数据，仅 `data/README.md` 的下载脚本 + SHA-256；许可证写入 `data_card.md`（升 Portfolio 档时补）。
- **诚实评估即 model risk 意识**：暴露泄漏/泛化崩塌、用真实 base rate 重解读误报，呼应 NCSC 检测指南与英国岗位的 model risk / 可审计信号。

## 参考

BibTeX 见 `../knowledge-base/references.bib`。核心：`sommer2010outside`, `arp2022dodonts`, `pendlebury2019tesseract`, `axelsson2000baserate`, `engelen2021troubleshooting`, `lanvin2023errors`, `sarhan2021standardfeature`, `crossdataset2024nids`。
