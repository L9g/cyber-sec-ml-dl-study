# Honest NIDS — Exposing Data Leakage & Cross-Dataset Generalisation Gaps

> 网络入侵检测 (NIDS) 的公开 benchmark 普遍存在**虚高**：把 CICIoT2023 之类刷到 99% 很容易，
> 但这个分数往往来自数据泄漏、过于乐观的随机切分、以及只在单一数据集内自评。
> **本项目研究的不是又一个分类器，而是如何揭穿并避免这种虚高**——量化数据泄漏、
> 用真 temporal split 与跨数据集 LODO 检验泛化，并在真实基率下重新解读误报。

配套文档：`../docs/DS-ML-DL-Cyber-Security-v2.md`（项目一章节）｜ 阅读清单：`../docs/project1-reading-list.md` ｜ 文献库：`../knowledge-base/`

---

## 三个数字

| 数字 | 含义 |
|---|---|
| **1.0 → 0.03** | 分布内 PR-AUC 满分（NF-UNSW-NB15-v3）；换一个数据集（→UNSW 方向）崩到 **随机基线以下** |
| **40** | UNSW-v3 全集（2.37M 流）只有 40 个 src IP、100% label 纯——「检测」其实是背诵一张查找表 |
| **0.998** | 连单特征决策树桩在分布内都能拿到 macro-F1=0.998 —— 满分来自合成 benchmark 指纹，不是攻击本质 |

> 一句话：**PR-AUC=1.0 的 NIDS 换个数据集可能低于随机基线**，且四个模型族都救不回来——
> 高分源于数据/评估设定，而非可泛化的攻击特征（`arp2022dodonts` P9 / Layeghy 2024 A2）。

---

## 当前完成度

| 步骤 | 内容 | 状态 |
|---|---|---|
| 1 乐观 baseline | 随机切分 + 全特征（含 IP）→ PR-AUC=1.0 | ✅ |
| 2 诚实重做 | 真 temporal split + 去泄漏特征 → PR-AUC 仍 1.0（合成数据平凡可分） | ✅ |
| 2.1 IP 泄漏消融 | IP-only 满分→跨域崩塌；OHE 封堵，delta=0.000 | ✅ |
| 3 跨数据集 LODO | 3×3 矩阵 + 多模型扫描 + 训练量敏感性审计 | ✅ |
| 4 可解释 (SHAP) | SHAP global + per-attack 类 | ⏳ 计划中 |
| 5 漂移监控 | 性能随时间衰减曲线 | ⏳ 研究级 |

当前为完整评估阶段（MVP 之上）；按主文档三档原则，此阶段不上 Docker / CI / Makefile。

---

## 问题背景

找攻击与一般 ML 任务本质不同——极低基率、误报代价高、缺真实标注、闭世界假设不成立（`sommer2010outside`）。
因此**只看 accuracy 会严重误导**；这正是项目要量化展示的（`arp2022dodonts` 的 10 大陷阱 → 见 `reports/findings.md`）。

前置决策：主模型为何选择 LightGBM 见 `reports/model-selection-decision.md`。

---

## 结果（NetFlow v3，seed=42，LightGBM）

> 完整数字、局限分析与 Arp 自查见 [`reports/findings.md`](reports/findings.md)。

### ① 分布内满分 ≠ 检测能力

NF-UNSW-NB15-v3 上，乐观（随机切分 + 含 IP）与诚实（真 temporal split + 去 IP/端口 + 去绝对时间戳，47 特征）**均满分**（PR-AUC=1.0，macro-F1=1.0）。落差为零不是「封堵没用」，而是更深的警讯：**合成数据集本身平凡可分**——连单特征决策树桩 macro-F1=0.998（Arp P6 / Layeghy 视角8）。满分来自数据集指纹，不是攻击本质。

### ② 换一个数据集，PR-AUC 崩向随机基线

| 训练 → 测试 | PR-AUC | 随机基线 | Δ |
|---|---|---|---|
| UNSW → ToN-IoT | 0.715 | 0.390 | +0.325 |
| UNSW → CSE-CIC | 0.183 | 0.129 | +0.054 |
| ToN-IoT → UNSW | 0.031 | 0.054 | **−0.023 ⚠️ 低于随机** |
| ToN-IoT → CSE-CIC | 0.097 | 0.129 | **−0.032 ⚠️ 低于随机** |
| CSE-CIC → UNSW | 0.050 | 0.054 | **−0.004 ⚠️ 低于随机** |
| CSE-CIC → ToN-IoT | 0.429 | 0.390 | +0.039 |

随机基线 = 测试集攻击占比（PR-AUC 特有，不是 0.5）。**四模型族**（stump / LogReg / MLP / LightGBM）在「测 UNSW」方向 PR-AUC 全落 0.03–0.11——落在哪个量级带主要由**测哪个数据集**决定，不由模型族（Layeghy 2024 A2；同一对内读数仍受模型/训练量影响）。

**核心结论**：分布内 PR-AUC=1.0 的 NIDS，换一个数据集可能低于随机基线，且**四个模型族都无法恢复分布内表现**——说明问题主要来自数据/评估设定而非单一模型选择，高分源于合成 benchmark 特有指纹，而非攻击的可泛化本质（`arp2022dodonts` P9）。

### ③ IP 泄漏：背诵不是检测；跨域是纯负债

UNSW-v3 仅 40 个 src IP，100% label 纯度 → **IP-only 随机/temporal 切分 PR-AUC=1.0**（背诵 40 行查找表）；但 temporal split **堵不住** IP 泄漏（40 IP 跨时段都在）——「切分干净 ≠ 特征干净」。

跨域对照：用 OHE(handle_unknown="ignore") 的 IP-only 模型，目标网络 IP 全部映射零向量，PR-AUC **恰好等于随机基线**（ToN=0.390，CSE=0.129，delta=0.000）。结论：IP 跨网络无任何可迁移信号，删 IP 在准确度（持平）、泛化（正收益）、隐私（消 PII）三维同时占优。

---

## 数据集

| 角色 | 数据集 | 说明 |
|---|---|---|
| 主 | **NetFlow v3 统一系列** NF-UNSW-NB15-v3 / NF-ToN-IoT-v3 / NF-CSE-CIC-IDS2018-v3 | 53 个统一 NetFlow 特征（arXiv 2503.04404），**含真 IP + 真时间戳 + 未去重**，天然支持 LODO；来源/核验见 `reports/data-prep-v3.md` |

> ⚠️ **不提交原始数据**（真 IP = PII）。下载说明 + checksum 见 `data/README.md` 与 `reports/data-prep-v3.md`。

---

## 仓库结构

```
01-honest-nids/
├── config.py                    # SEED=42 与路径
├── requirements.txt
├── data/
│   ├── README.md                # 下载说明 + SHA-256（不含原始数据）
│   └── checksums.sha256
├── src/
│   ├── data.py                  # 加载 + temporal split（duckdb 分层采样）
│   ├── feature_engineering.py  # 泄漏特征策略（Arp P3/P4）
│   ├── evaluation.py            # 诚实指标 + base-rate 误报量 + upsert 落盘
│   ├── models.py                # build_models()（stump/LogReg/MLP/LightGBM）
│   └── tests/                   # 代码契约单测（17 tests，~1s）
├── notebooks/
│   ├── conftest.py              # pytest 下修复 mo.notebook_dir() 退化
│   ├── 01_optimistic_baseline.py
│   ├── 02_ip_ablation.py        # IP-only 消融 + OHE 对照
│   ├── 03_honest_temporal_split.py
│   └── 04_lodo_cross_dataset.py
├── scripts/
│   ├── run_lodo.py              # LODO 3×3 矩阵
│   ├── run_model_scan.py        # 多模型扫描（Arp P6）
│   ├── run_size_audit.py        # 训练量敏感性审计（§2.1）
│   └── run_ip_ablation.py       # IP 消融脚本版（含稳定性检验）
├── reports/
│   ├── findings.md              # 三张表 + 局限分析（项目主文档）
│   ├── data-prep-v3.md          # 数据下载/去重/溯源全过程
│   └── related-work-perspectives.md
└── results/
    ├── experiments.csv          # §1/§3 结果（upsert，逻辑键去重）
    ├── ip_ablation.csv
    ├── model_scan.csv
    └── size_audit.csv
```

---

## 复现

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# 按 data/README.md 下载数据到 data/

# 展示（只读）
marimo run notebooks/01_optimistic_baseline.py
marimo run notebooks/04_lodo_cross_dataset.py

# 实验重跑
python notebooks/01_optimistic_baseline.py   # §1 乐观 baseline
python scripts/run_lodo.py                   # §2 LODO 3×3 矩阵
python scripts/run_ip_ablation.py            # §1.1 IP 消融 + OHE + 稳定性检验
python scripts/run_model_scan.py             # §2.2 多模型扫描

# 测试（两层）
pytest src/tests/                            # 代码契约（确定性，~1s）
pytest notebooks/01_optimistic_baseline.py \
       notebooks/02_ip_ablation.py \
       notebooks/03_honest_temporal_split.py \
       notebooks/04_lodo_cross_dataset.py -v # 叙事方向性断言（会重跑 notebook）
```

固定随机种子见 `config.py`（`SEED = 42`）。实验结果按逻辑键 upsert 到 `results/experiments.csv`（重复跑不会产生重复行）。

---

## 合规 / 治理

- **数据治理**：仓库不含原始数据，仅 `data/README.md` 的下载指引 + SHA-256；许可证写入 `data/README.md`（UQ 学术条款）。
- **PII 处理**：v3 含真实 IP（PII）；实验中仅用于消融演示、不落盘原始 IP；生产使用应脱敏或直接剔除（`drop_leakage_features` 默认删 IP/端口）。
- **诚实评估 = model risk 意识**：暴露泄漏 / 泛化崩塌、用真实 base rate 重解读误报，对应 NCSC 检测指南所强调的可审计与 model risk 实践。

---

## 参考

BibTeX 见 `../knowledge-base/references.bib`。核心：`sommer2010outside`, `arp2022dodonts`, `pendlebury2019tesseract`, `axelsson2000baserate`, `engelen2021troubleshooting`, `lanvin2023errors`, `sarhan2021standardfeature`, `crossdataset2024nids`。
</content>
</invoke>
