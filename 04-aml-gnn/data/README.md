# 数据下载说明 — 项目四 AML 图学习

> **本目录不提交原始数据**（数据治理硬规矩，主文档 6.2）。仅放下载说明 + checksum。
> 下载后的文件被 `.gitignore` 排除（`data/raw/` 下）。

## 主数据集：Elliptic++（比特币交易图 + 地址图）

扩展自原始 Elliptic（Weber et al. 2019）。两套图：
- **交易图**：交易-交易，节点含特征 + illicit/licit/unknown 标签 + 49 个时间步。
- **地址图（actors）**：钱包地址-地址 / 地址-交易，822k+ 地址、56 特征。

来源（✅ 2026-06-30 核实）：
- **代码 + 教程 repo**：https://github.com/git-disl/EllipticPlusPlus （Elmougy & Liu, KDD 2023）
- **数据本体托管在 Google Drive**（非 git 直拉）：
  https://drive.google.com/drive/folders/1MRPXz79Lu_JGLlJ21MDfML44dKN9R08l

### 下载方式（gdown 全量拉）
```bash
.venv/bin/gdown --folder \
  "https://drive.google.com/drive/folders/1MRPXz79Lu_JGLlJ21MDfML44dKN9R08l" \
  -O data/raw
```
> 大文件（feature CSV）会触发 Google 病毒扫描确认页；gdown 自带处理。
> 若 folder 模式在某个大文件失败，回退到按单文件 ID 拉。

### 文件清单（Drive 提供）
**Transactions Dataset/**
- `txs_features.csv` — 203,769 笔交易 × 183 特征（原始 Elliptic 166 + Elliptic++ 新增 17）
- `txs_classes.csv` — 标签（1=illicit, 2=licit, unknown=未标注）
- `txs_edgelist.csv` — 交易→交易边

**Actors Dataset/**
- `wallets_features.csv` — 822,942 地址 × 56 特征
- `wallets_classes.csv` — 地址标签
- `AddrAddr_edgelist.csv` — 地址→地址
- `AddrTx_edgelist.csv` — 地址→交易
- `TxAddr_edgelist.csv` — 交易→地址

放置约定：拉到 `data/raw/`，下游 notebook 用 `mo.notebook_dir()` 锚定，不靠 CWD。

### ⚠️ 许可（进库引用前必须落实，勿 over-claim）
- git-disl/EllipticPlusPlus repo **未在页面显式声明数据许可**。原始 Elliptic 数据集
  为学术研究用途发布。**结论：仅作学术/求职演示用，引用 Weber 2019 + Elmougy 2023；
  商业用途前需向作者核实。** 此条待二次确认后更新（同主文档数据治理要求）。

## 辅数据集：IEEE-CIS Fraud（表格欺诈对照，可选）
- Kaggle 竞赛数据：https://www.kaggle.com/c/ieee-fraud-detection
- 定位：纯表格欺诈基线，给「图 vs 表格」叙事提供非加密金融场景对照。MVP 不必须，升档再加。

## checksum
下载完成后在 `data/raw/` 内生成裸文件名 checksum，并从同目录验证：
```bash
cd data/raw
sha256sum *.csv > ../checksums.sha256
sha256sum -c ../checksums.sha256
```
