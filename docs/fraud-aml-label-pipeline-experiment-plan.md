# 实验计划:真实 fraud/AML 标签管线的病理与纠正(补"标签是怎么被生产出来的"这块经验短板)

> 状态:**计划,未编码**(2026-07-03)。目的=补用户自评的短板——**不是建模,而是"真实 fraud/AML 的标签怎么被生产出来"这整条脏管线的经验**
> (标注延迟/选择性标注/代理噪声/连坐传播/弱监督/反馈闭环/容量操作点)。Kaggle fraud 把这些全抹掉了,所以显得像玩具。
> 关联:[[project-aml-gnn-status]]、[`amlworld-clean-label-control-plan.md`](amlworld-clean-label-control-plan.md)(其 GATE 已定 **AMLSim** 为账户级真相实验台,本计划复用)、
> [`review-eval-methodology-and-gotchas.md`](review-eval-methodology-and-gotchas.md)、cross-domain 里 **reject inference=P1** 的落点。
> 复用 nb06/nb09/nb10 骨架与 same-pipeline 纪律;survival/删失一环焊到用户的 **RAMS/可靠性护城河**。

---

## 0. 核心动机(一句话)

真实世界里,**标签不是数据集自带的真相,而是一条会出错、会滞后、会被旧策略偏置的生产管线的输出**。用户会建模、会评估,但**没在这条标签管线里踩过坑**。
本计划用"已知真相 + 注入真实病理 + 度量偏置 + 上缓解 + 度量回收"的方式,把这条管线的每种病理**称出重量**,补上短板,且全程复用项目一贯的诚实评估纪律。

---

## 1. ⭐ 使能洞察(会翻转"合成=玩具"的顾虑)

**要"量"任何一种标签偏置,你必须有一个已知真相去对照——而真实脏数据恰恰没有真相,所以它测不出偏置。**
因此:**对"标签管线"这门手艺,合成带真值的数据不是玩具,是唯一严谨的实验室。** 真实脏数据只能当"我也扛得住"的锚,不能当度量台。
这直接接上 [`amlworld-clean-label-control-plan.md`](amlworld-clean-label-control-plan.md) 的 GATE 结论:**AMLSim 你能自己生成、且有账户级 SAR 真相**,它就是本计划的实验台。

---

## 2. 真实标签管线的"缺陷"表(要补的七层)

| # | 病理 | 真实机制 | 本质 | 本计划覆盖 |
|---|---|---|---|---|
| 1 | **标签延迟 / 成熟度** | chargeback 滞后 30–120 天;SAR 数月到数年才定 | 近期数据标签"未成熟"= **右删失** | **Stage A(做)** |
| 2 | **选择性标注 / 验证偏置** | 只有被审/被批的案子才有真值;**被拒的没有反事实结果** | selective labels + **reject inference** | **Stage B(headline,做)** |
| 3 | **代理标签噪声** | chargeback≠fraud(友善欺诈);SAR≠洗钱(**假阳 >90%**) | 你建模的是"分析师/规则",**不是犯罪** | **Stage C(加料,做)** |
| 4 | **标签传播 / 连坐** | 账户被标→其全部交易可疑;网络污染邻居 | guilt-by-association,**标注层版** | 已在 AML-GNN 覆盖;本计划 §7 桥接 |
| 5 | **弱监督多源冲突** | 规则/制裁名单/分析师处置/客户争议/执法反馈,各自噪声且打架 | data programming / 真相推断 | Stage D(Research 可选) |
| 6 | **反馈闭环** | 模型决定谁被审→谁被标→下轮训练集 | runaway loop,盲区**自我确认** | Stage E(Research 可选) |
| 7 | **容量约束操作点** | alert/天、SAR 转化率、precision@k,不是冻结 ROC 上阈值 | 运营指标 | 贯穿所有 stage 的评估口径 |

---

## 3. 统一实验模板(每个 stage 都照它走)

1. **取已知真相** `y_true`(AMLSim 账户级 SAR / AMLworld 交易级,generator 给的完整标签)。
2. **注入病理**:用一个可控过程把 `y_true` 劣化成"观测标签" `y_obs`(延迟/选择/噪声…)。
3. **度量偏置**:同管线训练两个模型——`M_obs`(用 `y_obs`) vs `M_oracle`(用 `y_true`),称 PR-AUC / 校准 / 特征重要度 / 操作点指标的**差**。
4. **上缓解**:加对应的纠正(成熟度加权/IPW/reject inference/去噪…),得 `M_fix`。
5. **度量回收**:`M_fix` 相对 `M_obs` 向 `M_oracle` **回收了多少**。
- 全程 **SEED=42**;差值**同管线**(same-pipeline skill:同 split/同特征/同 test/同调参约定/同 metric fn),否则差反映的是管线变动不是病理;
- PR-AUC 报**随机基线=正样本占比**;**跨 stage/跨数据集不做 PR-AUC 减法**,只在**同一实验台内**比 `M_obs`/`M_oracle`/`M_fix`。

---

## 4. 实验台与数据

- **主实验台 = AMLSim**(github.com/IBM/AMLSim,多智能体自生成)。**有账户级真相**:`accounts.csv` 的 `IS_SAR` + `alert_members.csv`。
  ⚠️ 坑(承 GATE):`IS_SAR` 也是**参与派生**;**真正独立的真相把手 = 生成前的 SAR 账户设定 / alert 主账户(main account)**,须从生成配置侧抽,别直接用 `IS_SAR` 当独立真值。
- **真实脏数据锚 = IEEE-CIS Fraud(Vesta)**:~590k 笔、有 `TransactionDT` 时间轴。**只做**"时间切分 + 标签成熟度处理"当"我在没有真相的真数据上也站得稳"的锚,**不在其上测偏置**(无真相)。
  注:IEEE-CIS 的 `isFraud` 本就带 ~120 天成熟窗口逻辑——正好是 Stage A 的真实注脚。
- **数据治理**:AMLSim 生成**配置入 git、原始输出 gitignore + checksum**;IEEE-CIS 属 Kaggle 竞赛数据,**license 核实后**只留下载说明 + checksum,不重分发。原始数据不入 git(同 Elliptic 纪律)。

---

## 5. Stage A — 标签延迟 / 成熟度(⭐ 焊到可靠性/生存护城河)

- **真实机制**:正样本的真值滞后到达(chargeback/SAR)。在训练截断点 `T`,到达时间 > `T` 的正样本**看着像负样本**。
- **建**:给每个正样本采样"标签到达时间" = 事件时间 + 延迟 ~ 分布(对 chargeback 用 lognormal/exponential 拟合窗口);按 `T` 制造 `y_obs`(未成熟标签)。
- **度量**:`M_obs` vs `M_oracle` 的 PR-AUC 差;尤其称**最近窗口的虚高**(隐藏正样本→假阳看着低→近期指标被高估)。
- **缓解(⭐ 你的地盘)**:①成熟度加权 / 剔除未成熟窗口;②**把"到标签的时间"当生存问题**——未标记的近期样本视为**右删失**,用 KM/生存重加权估 `P(fraud)`,校正延迟导致的 prevalence 偏差。
- **叙事**:"你最近一个月的 AUC 是虚高的,因为欺诈还没成熟;这是我按删失校正后的真实估计。"——**全场只有你能把它讲成 RUL/生存问题。**
- **测试断言(方向性、带 margin)**:`naive_recent_pr_auc − mature_recent_pr_auc > m`(虚高存在);校正后 `|corrected − oracle| < |naive − oracle|`(确有回收)。
- **档位**:MVP。

---

## 6. Stage B — 选择性标注 / reject inference(headline,你最缺、最值钱)

- **真实机制**:只有被"历史策略"选中审查/批准的案子才有真值;**被拒的案子没有反事实结果**(counterfactual missing)。你训练用的标签 = 昨天策略的产物。
- **建**:在已知真相上定义有偏历史策略 `π₀`(如按金额/typology/旧模型分数选,外加随机成分)。两种设定:
  (i) **验证偏置**:只有被 `π₀` flag 的才拿真值,其余**假定为负**;
  (ii) **reject inference**:被 `π₀` 拒的**完全无标签**。只用观测标签训练 `M_obs`。
- **度量**:`M_obs` vs `M_oracle`(合成才有的完整真相)在 PR-AUC / 校准 / **特征重要度 / 决策边界**上的偏差——展示选择性如何扭曲学到的边界。
- **缓解**:①**IPW**(按被审概率倒数加权);②**reject inference**(重分类/增广/parcelling 或反事实法);③**selective-labels-aware 评估**(Lakkaraju 的 contraction:只在策略同意审的子集上比,或用合成真相给出界)。
- **叙事**:"你训练用的标签是昨天风控策略的输出;这是它带来的偏差量,和我把它纠回来的方法。"
- **诚实**:reject inference 有**不可能性边界**——不做假设无法完全恢复反事实。**显式声明 MAR vs MNAR 假设**,承认选择性偏差**只能部分纠正**。
- **测试断言**:`bias(M_obs) − bias(M_fix) > m`(IPW/RI 确有纠偏,bias 用对 oracle 的距离度量);`M_fix` 向 `M_oracle` 回收但不必完全追平。
- **档位**:Reference(headline)。**注**:本 stage 的"传播/连坐"特例(缺陷表 #4)= amlworld-plan 的 §3;两者可**合并叙述、避免重复**,见 §7。

> **✅ 编码状态(2026-07-04):骨架已落 `notebooks/13_selective_labeling_reject_inference.py`**,可跑(`NB13_SMOKE=1 python/pytest` 均绿,4 断言过),
> 用**合成已知真相 stand-in**(`make_truth_world()` 是唯一 SEAM,待换 AMLSim)。**骨架实测翻转了原设想的 headline(如实报告)**:
> IPW 对 GBDT+overlap **基本无回收**(≈0),真正的病害与解药是——**把未审案子当负样本(assume-negative)是头号损害**
> (oracle 0.67 → vbias 0.54,−0.13),**reject inference=只用被审真标签训练**把它大幅拿回(→0.64),**IPW 仅微精修**
> (−0.005,符合"GBDT 下 IPW 收益有限、其价值在参数模型/无 overlap/更强 MNAR"的诚实边界)。→ 面试叙事从"IPW 万能"改为
> "**头号错误是臆造负标签,主缓解是 reject-inference 纪律,IPW 视条件而定**"。升档待办见 nb13 收口 cell(MNAR 变体证 IPW 失效 / PU-learning 对照 / AMLSim 真相)。
> **原理讲解**(通俗+数学+代码,含 `E[ỹ|x]=e(x)η(x)` / reject 的 MAR 推导 / IPW Horvitz-Thompson 恒等式 / MAR-MNAR 边界 / 面试话术):
> `docs/reject-inference-and-ipw-explainer.md`。

---

## 7. Stage C — 代理标签噪声(廉价加料,强化"标签是瓶颈")

- **真实机制**:你拿到的标签是代理——`chargeback`(含友善欺诈)、`SAR`(假阳 >90%),**不是**"真的是不是犯罪"。
- **建**:`y_proxy` = `y_true` 的**非对称噪声函数**(SAR 高假阳:大量真负被 flag;部分真正被漏)。训练用 `y_proxy`、评估用 `y_true`。
- **度量**:退化幅度;并对比 `M_proxy` vs `M_true` 的**特征重要度**——展示"你建模的是**分析师/规则的行为**,不是洗钱本身"。
- **缓解**:confident learning / cleanlab 估噪 + 噪声鲁棒损失;或显式建模标签噪声。
- **测试断言**:`pr_auc(M_true_on_truth) − pr_auc(M_proxy_on_truth) > m`;去噪后 gap 收窄。
- **档位**:Reference(加料)。

> **§7 桥接缺陷表 #4(连坐传播)**:AML-GNN 已证 Elliptic 上"沾过 illicit 就算坏"的循环;amlworld-plan §3 想在已知真相上称其重量。**本计划把它归位为标签管线的第 4 种病理**,与 Stage B 同框(都是"观测标签 ≠ 真相"的选择/传播机制)。建议把 amlworld-plan §3 作为 Stage B 的一个子案例并进来,避免两份文档各写一半。

---

## 8. 分档交付(先 MVP 再升档)

- **MVP**:Stage A 在 AMLSim 上跑绿(注入延迟→测虚高→删失校正→测回收)+ 内嵌方向性断言。**先把"注入/度量/缓解/回收"这套模板跑通一次。**
- **Reference**:加 Stage B(headline,含 IPW + reject inference + MAR/MNAR 诚实边界)+ Stage C(代理噪声)+ **IEEE-CIS 真实锚**(时间切分 + 成熟度处理)。
- **Research(可选)**:Stage D 弱监督(Snorkel labeling functions 多源合并 vs 真相)、Stage E 反馈闭环(多轮模拟盲区自我确认 + 随机审计留出集破环)。
- **交付物**:`04-aml-gnn/notebooks/12_label_delay_censoring.py`(A)、`13_selective_labeling_reject_inference.py`(B)、`14_proxy_noise_and_real_anchor.py`(C+IEEE-CIS);
  `reports/fraud-aml-label-pipeline.md`;`results/experiments.csv` 增行(**upsert 逻辑键**:`dataset, stage, pathology, label_variant, mitigation, model`);README 增步骤。

---

## 9. 判定准则与诚实边界

- **这补的是方法论短板**(能推理并纠正标签管线病理)——稀缺、开门靠它。**不等于**"在 FIU/银行风控团队干过"的**运营资历**,那随岗位来。**面试如实讲,不吹成"我运营过真实 SAR 流程"。**
- **合成易学性混淆**:AMLSim 模式可能太规整。**缓解**=重点看**偏置/回收的相对度量**(与"易学性"无关,是机制),不看绝对 PR-AUC;并报"结论是*标签管线病理能造成 X 量级偏差*,不是*AMLSim 上分数高*"。
- **reject inference 的假设**:显式声明 MAR/MNAR;承认部分不可纠。
- **same-pipeline**:所有 `M_obs`/`M_oracle`/`M_fix` 差值同管线;跨数据集只当量级参照,不做减法操作数。
- **PR-AUC 基线**=正样本占比,报告必给。

---

## 10. 算力 · 数据治理 · 交付

- **算力**:全 **CPU**——LightGBM、IPW、生存重加权、cleanlab、IEEE-CIS(~590k 行)均本机可跑。AMLSim 生成亦 CPU。无需上云。
- **数据治理**:AMLSim 生成配置入 git;原始输出 + IEEE-CIS gitignore,仅留 README + checksum + license 核实;真 PII 不涉及(合成/竞赛脱敏)。
- **复现**:SEED=42;experiments.csv upsert(按上面逻辑键,不靠 timestamp)。

---

## 11. 不做什么(scope guard)

- **不**把缺陷表七种全做——先 A+B(+C),D/E 只在有余力时。别摊成"哪都浅"。
- **不**在 IEEE-CIS 等真实数据上"测偏置"(无真相,测不了);它只当扛得住真数据的锚。
- **不**过度包装成运营资历(§9)。
- **不**另起炉灶——这是 AML-GNN"给定标签的 provenance"方法学**向上游挪一步**去模拟标签生成过程,连续的。
- **不**跨 stage/跨数据集做 PR-AUC 减法。

---

## 12. 落地顺序(下次开工第一步)

1. **AMLSim 落地**:生成 HI 类小规模图,抽出**独立 SAR 真相把手**(生成前设定/alert 主账户),建 loader + temporal/inductive split(与 amlworld-plan 的 AMLSim 台**共用**)。
2. **Stage A(MVP)**:注入延迟→测虚高→删失校正→测回收,跑绿方向性断言。
3. **Stage B(Reference headline)**:选择性标注 + IPW + reject inference + MAR/MNAR 边界;把 amlworld-plan §3 作为子案例并入。
4. **Stage C + IEEE-CIS 锚**:代理噪声 + 真实数据成熟度处理。
5. 写报告,桥接回 AML-GNN 与 amlworld-plan。

> **本文件只是计划。** 编码从第 1 步(AMLSim 台)开始,与 amlworld-plan 共用同一实验台。
