# Notebooks 叙事顺序

每个 notebook 是叙事的一环（marimo `.py` 格式），导入 `src/` 模块、结果落盘到
`results/experiments.csv`。数据基座为 NetFlow **v3**（见 `../reports/data-prep-v3.md`）。

| # | notebook | 内容 | 状态 |
|---|---|---|---|
| 01 | `01_optimistic_baseline.py` | 随机切分 + 全特征（**含真 IP**）LightGBM → 满分（IP 泄漏） | ✅ |
| 02 | `02_ip_ablation.py` | IP 泄漏消融：IP-only 随机/temporal 满分、LODO 崩塌；drop-IP 在跨域反更好（Arp P4） | ✅ |
| 03 | `03_honest_temporal_split.py` | `drop_leakage_features` + **真 temporal split**（`FLOW_START_MILLISECONDS`）+ base-rate 分析 | ✅ |
| 04 | `04_lodo_cross_dataset.py` | A 训 B 测 LODO 矩阵：PR-AUC 量级从分布内 ≈1.0 崩向随机基线，四模型一起崩（Layeghy A2） | ✅ |

> 串成一条故事链：**01 踩坑（满分）→ 02 IP 泄漏机制 → 03 诚实（仍满分=合成数据平凡可分）→ 04 跨数据集崩塌**。
> 核心结论与三张表见 `../reports/findings.md`。

约定：每个 notebook 顶部 `import sys; sys.path.append(str(mo.notebook_dir().parent))`
把路径锚定到文件而非 CWD（见 skill `anchor-paths-to-file-not-cwd`）。
pytest 时 `mo.notebook_dir()` 退化为 CWD，由 `notebooks/conftest.py` 提前设好 sys.path
（见 skill `marimo-pytest-conftest`）。

## 运行 / 展示

```bash
marimo run notebooks/01_optimistic_baseline.py    # 只读展示（推荐给招聘者看）
marimo edit notebooks/01_optimistic_baseline.py   # 交互编辑
python notebooks/01_optimistic_baseline.py        # 无头端到端跑（cell 异常→exit 1）
```

## 测试（两层，见根目录约定）

| 层 | 位置 | 测什么 | 跑法 |
|---|---|---|---|
| **代码契约**（确定性、与模型无关） | `../src/tests/` | upsert 幂等、泄漏特征剔除、base-rate 公式、temporal split 不泄漏、**采样器分层（含 bug 回归）** | `pytest src/tests/`（~1s） |
| **叙事回归**（方向性、对数字漂移鲁棒） | 各 notebook 内嵌 `test_*` cell | 乐观/诚实分布内满分、IP-only 分布内满分但跨域崩塌、跨数据集 PR-AUC 量级崩塌 | 见下方命令（会重跑 notebook，04 较慢） |

> notebook 内只放**方向性/带 margin 的相对断言**（如 `pr_auc.max() < 0.9`），
> **不写硬阈值**——模型分数会随种子/版本/镜像漂移。确定性逻辑才放 `src/tests/` 贴死。

```bash
# 叙事回归（需显式列文件，pytest 默认发现规则不匹配数字前缀文件名）
pytest notebooks/01_optimistic_baseline.py \
       notebooks/02_ip_ablation.py \
       notebooks/03_honest_temporal_split.py \
       notebooks/04_lodo_cross_dataset.py -v
```
