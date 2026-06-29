# 数据准备与核验 — NetFlow v3 迁移（2026-06-28）

> 本文件记录项目一数据基座从 **dhoogla v2 镜像** 迁到 **NetFlow v3** 的下载来源、溯源核验、
> 格式转换与去重/IP/时间戳检查的**过程与结果**。结论喂给 `findings.md`（§0 局限节与三张表）。
> 背景动机见 [`related-work-perspectives.md`](related-work-perspectives.md)（视角 2/8）。

## 0. 为什么迁 v3

dhoogla v2 镜像是**清洗版**：已去重（exact dup=0）、**删除了 IP 列**（见 `findings.md §0` 旧记）。
这让项目一新叙事主轴（**IP 泄漏 + 重复流泄漏 + 真 temporal split**）在该镜像上**无法演示**。
v3（53 特征，原作者 Sarhan/Layeghy/Moustafa/Portmann，arXiv 2503.04404）一次解开三处：
含真 IP、含真时间戳（`FLOW_START/END_MILLISECONDS` + IAT）、疑未去重 —— 本次已逐项实测确认。

## 1. 下载来源与溯源核验

**官方源当时不可达**（2026-06-28 实测）：
- `staff.itee.uq.edu.au/marius/NIDS_datasets/`（旧镜像）→ **HTTP 502**（多次重试均失败）。
- UQ 官方项目页 `cyber.uq.edu.au/project/machine-learning-based-nids-datasets`→ 200，但**只列 V1/V2，无 V3**。
- RDA DOI `10.48610/44D7C5E`（NF-ToN-IoT-v3）→ 跳转 UQ eSpace `UQ:44d7c5e`，是 **JS-SPA（仅 3 KB，无直链）**，curl 拿不到下载地址。

**实际采用：Kaggle 镜像**（非官方再分发，溯源已核验）：

| 数据集 | Kaggle ref | 原始 CSV 大小 |
|---|---|---|
| NF-UNSW-NB15-v3 | `seyhed/nf-unsw-nb15-v3` | 577,360,958 B |
| NF-ToN-IoT-v3 | `seyhed/nf-ton-iot-v3` | 5,302,886,266 B |
| NF-CSE-CIC-IDS2018-v3 | `seyhed/nf-cicids2018-v3` | 4,222,783,755 B |

**溯源核验要点：**
- ✅ **跨镜像字节一致**：`seyhed`、`ndayisabae`、`athena21/netflow-v3-datasets`（全套打包）的
  `NF-UNSW-NB15-v3.csv` 大小**完全相同**（577,360,958 B）→ 同一原始文件，非各自清洗。
- ❌ **避开清洗变体**：`sayandeepp/...-v3-CLEANED`（2.0 GB，名字带 CLEANED）疑似又一次去重——
  正是 v2 镜像那种陷阱，**未采用**。
- 原始 CSV 的 sha256 记于 `data/v3_raw/_checksums.sha256`，钉住本次溯源。

**许可 / 治理**：UQ 学术条款（引用论文后用，商业需联系作者）。Kaggle 是非官方镜像，
正式叙事中引**原始论文 + arXiv 2503.04404**，并注明数据经第三方镜像获取。
真 IP = PII，仅用于演示 IP 泄漏，**不入 git**（`data/.gitignore` 已排除），诚实模型 (honest) 训练前即移除。

## 2. Schema 核验

先用 12 MB 的 `seyhed/nf-unsw-nb15-v3-trunc` 样本**低成本验 schema**，再下全量，避免盲下 ~10 GB。

- 列数 **55** = 53 特征 + `Label` + `Attack`，与 arXiv 2503.04404 Table 1/2 一致。
- ✅ 含 IP：`IPV4_SRC_ADDR` / `IPV4_DST_ADDR`（→ IP 泄漏可演示）。
- ✅ 含真时间戳：`FLOW_START_MILLISECONDS` / `FLOW_END_MILLISECONDS` + IAT 四统计
  （`SRC_TO_DST_IAT_{MIN,MAX,AVG,STDDEV}`、`DST_TO_SRC_IAT_*`）（→ 真 temporal split 可做）。
- 三个数据集 55 列 schema **完全一致**（duckdb 逐列比对，无 only_here / missing）→ 可直接 LODO。

## 3. 格式转换（CSV → parquet）

原始 CSV 共 ~10 GB，本机 15 GB RAM 直接 pandas 读 27 M 行会 OOM。
用 **duckdb 1.5.4**（`PRAGMA memory_limit='8GB'`）流式 `COPY ... TO ... (FORMAT parquet, COMPRESSION zstd)`，
内存安全、各 30 s 内完成。产物（存 `data/`，已 gitignore）：

| 文件 | parquet 大小 |
|---|---|
| `NF-UNSW-NB15-v3.parquet` | 105 MB |
| `NF-ToN-IoT-v3.parquet` | 424 MB |
| `NF-CSE-CIC-IDS2018-v3.parquet` | 325 MB |

后续去重统计与训练均基于 parquet（列式、压缩、可复读）。原始 CSV 留在 `data/v3_raw/`。

## 4. 去重 / IP / 时间戳实测（核心结果）

duckdb 在 parquet 上统计（内存安全）：

| 数据集 | 行数 | 攻击% | 完整行重复 | 去时间戳后重复 | unique 源 IP | unique 目的 IP |
|---|---|---|---|---|---|---|
| **UNSW** | 2,365,424 | 5.40% | 14,815 (0.63%) | 24,417 (1.03%) | **40** | **40** |
| **ToN-IoT** | 27,520,260 | 38.98% | 1,816,137 (6.60%) | **8,907,277 (32.37%)** | 15,270 | 8,777 |
| **CSE-CIC** | 20,115,529 | 12.93% | 628,474 (3.12%) | 1,170,178 (5.82%) | 181,876 | 29,036 |

> 「去时间戳后重复」= 除 `FLOW_*_MILLISECONDS` 外所有列都相同的流，更贴近“同一流被重复记录”的泄漏定义。

**确认未去重**：UNSW 2,365,424 行 ≈ 原始 2.39 M（**远高于** dhoogla 去重镜像 1,986,745），
攻击占比 5.40%（v2 镜像 3.78%）。→ v3 保留了重复流，迁移目标达成。

**诚实的细微点（写进 findings §0，避免 over-claim）：**
1. **「重复流泄漏」强度高度依赖数据集**，不是普遍大效应：
   - UNSW 精确重复仅 **0.6%**（去时间戳 1.0%）——在 UNSW 上重复流**不是**主泄漏源。
   - ToN-IoT 去时间戳后重复高达 **32%**（870 万近重复流）——这才是重复流泄漏的主舞台。
   - CSE-CIC 居中（3–6%）。
2. **IP 泄漏在 UNSW 最极端**：236 万条流仅 **40 个源 IP / 40 个目的 IP**（实验室固定靶机/攻击机），
   模型可直接把 IP 当标签背下来 → IP 是 UNSW 上最强捷径。CSE-CIC 的 IP 空间较真实（18 万源 IP）。
3. 故两条泄漏卖点**各有主场**：UNSW 演示 **IP 泄漏**，ToN-IoT 演示 **重复流泄漏**——
   诚实地按数据集分工陈述，比笼统说「v3 到处是泄漏」更经得起追问。

## 5. 口径变化对三张表的影响（✅ 已在 v3 重跑，结果见 `findings.md`）

- 攻击占比变了（UNSW 3.78%→5.40%）→ §1/§3 base-rate 基线、§2 LODO 随机基线已全部在 v3 重算。
- §1 乐观行保留 IP（factorize 后喂 LightGBM）、诚实行用真 `FLOW_START_MILLISECONDS` temporal split + 去 IP/端口。
- 大数据集（ToN 27.5 M、CSE 20 M）用 `src/data.py::load_netflow_sampled`（duckdb 在 parquet 层分层采样至 3 M）防 OOM。

**实际结果（与预期的偏差，诚实记录，详见 `findings.md`）：**
- **IP 泄漏被"数据集本身平凡可分"掩盖**：乐观(带IP)与诚实(去IP+真temporal)在 UNSW 上**都满分**，
  落差≈0。这不是 bug，而是合成 benchmark 太易可分的实证（视角 8）。单独量化 IP 贡献需在"不可分"设定做消融。
- **诚实落差只在 §2 LODO 出现**：跨数据集 attack_recall 全 ≤3%（同分布=1.0），macro-F1 全崩到 0.38–0.49。
- **采样 bug 已修**：duckdb 的 `USING SAMPLE` 在 `WHERE` 之前作用于扫描，最初版本"先全表抽样再过滤"
  把少数类稀释（CSE-CIC 攻击率 12.9%→2.2%）。已改为"先子查询过滤、再采样"，并实测分层占比恢复正确。
