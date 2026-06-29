# Notebooks 叙事顺序

每个 notebook 是叙事的一环（marimo `.py` 格式），导入 `src/` 模块、结果落盘到
`results/experiments.csv`。数据基座为 NetFlow **v3**（见 `../reports/data-prep-v3.md`）。

| # | notebook | 内容 | 状态 |
|---|---|---|---|
| 01 | `01_optimistic_baseline.py` | 随机切分 + 全特征（**含真 IP**）LightGBM → 满分（IP 泄漏） | ✅ |
| 03 | `03_honest_temporal_split.py` | `drop_leakage_features` + **真 temporal split**（`FLOW_START_MILLISECONDS`）+ base-rate | ✅ |
| 04 | `04_lodo_cross_dataset.py` | A 训 B 测 LODO 矩阵，跨数据集 recall 崩塌 | ✅ |

> 串成一条故事链：**01 踩坑（满分）→ 03 诚实（仍满分=合成数据平凡可分）→ 04 跨数据集崩塌**。
> 核心结论与三张表见 `../reports/findings.md`。

约定：notebook 顶部 `import sys; sys.path.append(str(mo.notebook_dir().parent))`
（把路径锚定到文件而非 CWD，见 skill `anchor-paths-to-file-not-cwd`），
再 `from config import seed_everything; seed_everything()` 与 `from src import data, ...`。

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
| **叙事回归**（方向性、对数字漂移鲁棒） | 各 notebook 内嵌 `test_*` cell | 乐观/诚实远超随机基线、跨数据集 recall/macro-F1 崩塌、PR-AUC 跌破随机 | `pytest notebooks/`（会重跑 notebook，04 较慢） |

> notebook 内只放**方向性/带 margin 的相对断言**（如 `pr_auc - 攻击占比 > 0.5`、
> `lodo.recall.max() < 0.2`），**不写硬阈值**（如 `> 0.95`）——模型分数不是代码契约，
> 换种子/版本/镜像会漂移。确定性逻辑才放 `src/tests/` 贴死。
