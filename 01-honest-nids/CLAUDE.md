# Rules — 01-honest-nids（项目一：诚实 NIDS）

继承工作区根 `../CLAUDE.md` 的通用约束。本文件只列项目一特定规则。
卖点 = **揭穿并避免 NIDS benchmark 虚高**（数据泄漏 / 跨数据集泛化崩塌），不是分类器本身。

## Codex 项目记忆
- Codex 专用项目记忆在 `.codex/memory/`。新会话开始或做方法学决策前，先读：
  `.codex/memory/index.md`、`.codex/memory/current-context.md`、`.codex/memory/decisions.md`。
- 用户说“存记忆 / 保存上下文 / 把这个结论存进项目上下文”时，优先更新 `.codex/memory/`；
  若内容面向项目读者，再同步到 `reports/*.md` 或 README 链接。
- `.codex/memory/` 只存稳定项目事实、决策和待办；不要存原始数据、密钥、token、长篇论文摘录。

## 数据基座（NetFlow v3）
- 主数据 = **NetFlow v3**（53 特征，含真 IP + 真时间戳 + 未去重）。工作文件是 `data/*-v3.parquet`，
  原始 CSV 在 `data/v3_raw/`。来源/溯源/去重核验全过程见 `reports/data-prep-v3.md`。**勿回退到 v2 镜像**（已删 IP、已去重）。
- 大数据集（ToN-IoT 27.5M / CSE-CIC 20M）**必须用 `src/data.py::load_netflow_sampled`**
  （duckdb 在 parquet 层分层采样，默认 cap 3M）——直接 `pd.read_parquet` 全量读会 OOM。
  ⚠️ duckdb 的 `USING SAMPLE` 在 `WHERE` 之前作用，分层采样要**先子查询过滤、再采样**（否则少数类被稀释，见回归测试）。

## 泄漏 / 切分策略
- **乐观版**（notebook 01）：随机切分 + 保留全特征（含 IP/端口，factorize）→ 故意制造虚高。
- **诚实版**（notebook 03）：`fe.drop_leakage_features` 去 IP/端口 + 真 temporal split
  （`temporal_split(time_col="FLOW_START_MILLISECONDS", extra_drop=["FLOW_END_MILLISECONDS"])`）。
  绝对时间戳列只用于排序、**不进特征**（否则是另一种泄漏）。
- LODO（`scripts/run_lodo.py` / notebook 04）：训练前一律去泄漏特征。

## 项目论点（改动前先读 `reports/findings.md`，别静默推翻其结论）
- 单数据集满分（即便去 IP + 真 temporal split）= 合成数据平凡可分的实证，**不是 bug**；真正的诚实落差只在跨数据集 LODO。
- 卖点 = 「跨数据集 recall 崩塌 + PR-AUC 跌向随机基线」，不是分类器分数高。**具体数字以 `findings.md` 为准**（会随重跑微调）。
- base-rate 杀伤力条件于部署分布 FPR：单数据集 FPR≈0 故不咬人，跨数据集才显现。

## 命令
```bash
python scripts/run_lodo.py                       # §2 LODO 矩阵
python notebooks/0{1,3}_*.py                      # §1/§3（UNSW，快）
pytest src/tests/                                 # 代码契约单测（~1s）
pytest notebooks/0{1,3,4}_*.py                    # 叙事方向性断言（04 会重跑 LODO，慢）
```
