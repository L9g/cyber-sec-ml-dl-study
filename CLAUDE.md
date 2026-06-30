# Rules — cyber-sec 项目集（工作区根）

跨项目通用硬约束。项目特定规则见各 repo 的 `CLAUDE.md`（如 `01-honest-nids/CLAUDE.md`）。
背景/理由在 `docs/` 与 auto-memory，本文件只列**要遵守什么**。

## 工作区
- 会话 cwd = 工作区根 `/home/l9g/works/cyber-sec`；下辖 4 个项目（01-honest-nids / 注入防御 / SIEM / AML）。
- Claude Code skills 放**工作区根** `.claude/skills/`，不要埋进子 repo（从根启动可能不被发现）。

## 评估指标
- 不平衡安全数据（入侵/欺诈）**优先 PR-AUC**，ROC-AUC 仅作辅助。
- PR-AUC 的**随机基线 = 正样本(攻击)占比**，不是 0.5；报告时必须给出该基线供对比。
- 不看裸 accuracy 下结论（攻击占比极低时全猜良性也高分）。

## 测试（两层，别混写）
- **代码契约**（确定性、与模型无关）→ `src/tests/` pytest 单测：贴死精确值/边界。
- **叙事回归**（模型分数相关）→ notebook 内嵌 `test_` cell：**只用方向性/带 margin 的相对断言**
  （如 `pr_auc - 攻击占比 > 0.5`），**禁止硬阈值**（如 `> 0.95`）——分数会随种子/版本/镜像漂移。
- marimo 原生支持无头测试：`python nb.py`（冒烟，异常→exit 1）、`pytest nb.py`（收集 cell 内 test_）。不用 papermill。

## 数据治理
- **原始数据不入 git**（`data/**` gitignore，仅留 README + checksum）。
- 依赖新数据集前先核实：论文真实 + 可下载 + 许可允许；镜像要验溯源、避开未声明的清洗/去重变体。
- 真 IP/PII：最小化、脱敏、不入库；下载来源+许可+SHA256 写进 repo 文档。

## Notebooks
- 只用 **marimo `.py`** 单格式（不维护双 `.ipynb`）。
- 路径**锚定到文件而非 CWD**（`mo.notebook_dir()`，不用 `sys.path.append("..")`）；见 skill `anchor-paths-to-file-not-cwd`。
- 展示用 `marimo run`（只读）；测试用 `python`/`pytest`。

## 交付与复现
- 分档交付：**MVP → Reference-grade → Research-grade**；先把项目推到 MVP 再升档，避免大计划拖延。
- 固定 `SEED=42`；实验结果落 `results/experiments.csv`，用 **upsert**（按逻辑键，不靠 timestamp）。

## 工作方式
- **如实报告**：结果与先前结论矛盾时直说并改文档，不 over-claim、不粉饰（如「4/6 跌破随机」核实后是「3/6」就改）。
- 用户专业，要**真实异议与精化**，不要一味附和。
- 文档里相对日期转绝对日期。重视英国监管信号（NCSC/GDPR/FCA·PRA）作为治理叙事。
