# 数据下载说明

> **本目录不提交原始数据**（数据治理硬规矩，主文档 6.2）。仅放下载说明 + checksum。
> 下载后的文件被 `.gitignore` 排除。

## 主数据集：NetFlow-v2 统一系列

由 Sarhan et al. 统一成 43 个 NetFlow 特征（`sarhan2021standardfeature`），支持跨数据集 LODO。

来源（✅ 2026-06 核实）：
- **官方主页**：UQ Cyber Research Centre — https://www.cyber.uq.edu.au/project/machine-learning-based-nids-datasets
- 旧镜像（仍可达）：`https://staff.itee.uq.edu.au/marius/NIDS_datasets/`
- Kaggle 镜像：https://www.kaggle.com/datasets/dhoogla/nfunswnb15v2
- **许可**：学术研究引用论文后永久授权；商业用途需联系 Mohanad Sarhan 取得同意。

> ✅ **当前主基座已迁到 NetFlow v3（2026-06-28）**，替代下方 v2 镜像。v3 含真 IP + 真时间戳 + 未去重，
> 解锁了「IP 泄漏 + 重复流泄漏 + 真 temporal split」叙事。**下载来源、溯源核验、去重/IP/时间戳实测全过程见**
> [`../reports/data-prep-v3.md`](../reports/data-prep-v3.md)。当前 `data/` 下的工作文件：
> `NF-UNSW-NB15-v3.parquet` / `NF-ToN-IoT-v3.parquet` / `NF-CSE-CIC-IDS2018-v3.parquet`（原始 CSV 留 `data/v3_raw/`）。
> v3 经 Kaggle 镜像 `seyhed/nf-{unsw-nb15,ton-iot,cicids2018}-v3` 获取（官方 itee 镜像当时 502），
> 已核验跨镜像字节一致、避开 CLEANED 变体；许可=UQ 学术条款，真 IP=PII 不入 git。

---

下方为**已弃用的 v2 路径**（保留作历史记录）：

- ~~MVP 用其中之一起步，建议 **NF-UNSW-NB15-v2**（原始 2,390,275 条流，攻击 3.98%）。~~
- ~~**实际 MVP 用的是 dhoogla Kaggle 镜像**（清洗版：已去重 1,986,745 流 / 攻击 3.78%、**删了 IP 列**）。~~
  该镜像缺 IP、已去重，故 IP/重复流泄漏无法演示——正是迁 v3 的原因。
- ~~LODO 实验需要 **NF-ToN-IoT-v2** 与 **NF-CSE-CIC-IDS2018-v2**。~~

放置约定：
```
data/
├── NF-UNSW-NB15-v2.csv        # 或 .parquet
├── NF-ToN-IoT-v2.csv
└── NF-CSE-CIC-IDS2018-v2.csv
```

## 辅数据集：修正版 CICIDS2017

⚠️ **用修正版，不要原始 bug 版**（`engelen2021troubleshooting`, `lanvin2023errors`）。来源（✅ 2026-06 核实）：

- **推荐用最新合并版 CNS2022**：把 Engelen 的修正 + Lanvin 的 "Attempted" 标签整合，覆盖 CIC-IDS-2017 **与** CSE-CIC-IDS-2018，标注逻辑已逆向修正并公开。
  页面 https://intrusion-detection.distrinet-research.be/CNS2022/index.html → `Dataset_Download.html`。引用 **Liu et al., IEEE CNS 2022**。
- 原始 WTMC2021（Engelen）版：数据 + 工具页 https://intrusion-detection.distrinet-research.be/WTMC2021/tools_datasets.html ；修正版 CICFlowMeter https://github.com/GintsEngelen/CICFlowMeter ；Kaggle 镜像 https://www.kaggle.com/datasets/dhoogla/distrinetcicids2017 。
- Lanvin "Attempted" 标签的**论文**（非数据本身）：https://hal.science/hal-03775466（数据已并入上面 CNS2022 发行）。CIDRE / CentraleSupélec。

## checksum

下载后生成并核对，写入 `checksums.sha256`：
```bash
sha256sum data/*.csv data/*.parquet > data/checksums.sha256
# 复现时校验：
sha256sum -c data/checksums.sha256
```

## 许可

每个数据集的 license / 来源 URL / 再分发权限在升 Portfolio 档时写入 `../data_card.md`。
用 Kaggle/HF 镜像前先确认其再分发合法。
