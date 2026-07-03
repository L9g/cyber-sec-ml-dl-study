# 云端 GPU 算力实施计划(cyber-sec 工作区)

> 开发机**无 GPU**(8 核 / 31 GiB RAM,`nvidia-smi` 不可用);需 GPU 的实验**迁云主机**(用户已认可这条退路,
> 见 auto-memory `project-compute-no-gpu-cloud-fallback`)。本文件把**该上云的实验**集中登记、排优先级、给实例/成本粗估,
> 避免「本机能跑的也上云 = 花钱买延迟」与「该上云的漏排」。最后更新 **2026-07-03**。

---

## 0. 决策规则:什么上云、什么留本机

**上云的充分条件(命中任一)**:
1. **模型/权重必须 GPU**——大 FM 推理(TabPFN-2.5/3、TabDPT)、LLM 微调/推理(DeBERTa、TABULA-8B)、
   时序多快照 GNN(EvolveGCN ≈ 49× 单 GCN/epoch)。
2. **CPU 上算力不可行**——实测 wall-time 到「小时–天」级(如 TabPFN 全 92k test @ 大 context ≈134h,见 nb10 §2.2)。
3. **需商用 token 的更强权重**(TabPFN-2.5/3、RealTabPFN)。

**⚠️ 留本机、别上云(反直觉,常被误排)**:CPU 分钟级就能跑的一律先本机做——静态地址图 GraphSAGE(实测 26min/CPU)、
**RealMLP、TabM、MotherNet、TabR(faiss-cpu)**。把这些塞进云阶段违反「先本机做 CPU 可行的」纪律,还会**延迟**加固主线。
原则:**先用本机把「表格上限」叙事做到滴水不漏,再花云钱买「更强 FM 也补不上」的最后一击。**

---

## 1. 项目四(04-aml-gnn)—— 已就绪,主体

**主线**:queue disagreement 的解 = **label provenance**(不是 scoring granularity、不是图/模型强弱)。
tx 投影 0.74 是 guilt-by-association 的回溯标签循环、**非可学信号**;地址特征诚实上限 0.30–0.38。
云阶段的**每个**实验都服务同一目的:**再加一个更强/更贵的证人,证明它仍卡在 0.30–0.38 带 << 0.74**——
证人价值排序 = 「测**新机制**」>「只是又一个落带内的点」。

### 1a. 云 GPU 槽位(按证人价值排序)

| 优先级 | 实验 | 测什么新机制 | 输入前提 | 实例粗估 |
|---|---|---|---|---|
| **P1** | **TabDPT**(arXiv:2410.18164, NeurIPS'25, CC BY 4.0) | **真实表预训练** FM + retrieval + SSL → 堵「合成 prior 才不行」的借口 | 复用 nb10 骨架(同 8000 test 子样本、same-pipeline);HF `Layer6/TabDPT` | T4/L4 单卡,推理为主,个位数美元 |
| **P1** | **TabPFN-2.5 / 3**(需商用 `TABPFN_TOKEN`) | uncapped:集成 + 大 context(2.5≈100k / 3≈1M 行)+ **全 92k test** | 注册 ux.priorlabs.ai + 接受许可;nb10 的 n_est=1/2k context 是本机受限档 | L4/A10,推理;注意 token 配额/联网 |
| **P2** | **EvolveGCN**(49 时间步快照 + RNN) | **跨期时序**的动态利用(把地址图的跨期结构用满) | config.seed 已扩;2.87M 边对 GPU 很小 | T4/L4,训练数十小时 → 一整轮个位数–低两位数美元 |
| **P2** | **G2T-FM 全结构列**(arXiv:2508.20906) | 补 PageRank / assortativity / clustering(nb10 只做了 degree+邻居 illicit 比例) | 大图上算 PageRank 吃内存/算力 | 可 CPU 大内存或 GPU 图算子 |
| **P3·stretch** | **TABULA-8B**(LLM-for-tables) | LLM 直接预测 → 但你的源都说数值精度场景不如专用模型 | 定位=**orchestrator/演示**,非 AML 预测器 | A100/多卡或 API,成本高 |
| **跳过** | **CARTE**(行=星图 graph-transformer) | 与已有 GNN / G2T-FM 线**重叠**,边际低 | — | — |

### 1b. 本机先做(不上云,但排在云阶段之前 —— 加固天花板)

| 实验 | 为什么本机 & 为什么先做 |
|---|---|
| **RealMLP + meta-tuned GBDT defaults**(arXiv:2407.04491, NeurIPS'24) | CPU 可跑。**最优先**——直接堵审计「你 GBDT/MLP 欠调,天花板不算数」。不先做,云上更强 FM 的数字会被「可你连基线都没调」打折。 |
| **TabM**(arXiv:2410.24210, ICLR'25) | 轻量 MLP+BatchEnsemble,CPU 可跑。强 MLP 证人。 |
| **MotherNet**(arXiv:2312.08598, NeurIPS'24, microsoft/ticl) | hypernetwork 生成小子网,子网 CPU 秒级推理。又一 FM 点(可选)。 |
| **TabR**(arXiv:2307.14338, ICLR'24) | retrieval MLP,faiss-cpu 可跑。**retrieval = 检索相似已标注行 = guilt-by-assoc 的又一形态**——涨分=检索到定义标签的信号、非新证据(主线相关,值得做)。 |

> **主线钩子(贯穿 1a/1b)**:retrieval(TabR/TabDPT)、real-prior(TabDPT)这些「更强」路子,恰恰都在**更狠地复用
> 「是否触过 illicit」这个定义标签的信号**——它们若涨分,不是发现新证据,是把回溯循环换个更高效的入口再走一遍。
> 这把 nb10 的论点从「TabPFN 一家」升级为「**整个 2024–2026 tabular DL SOTA 谱系补不上标签口径的坑**」。

### 1c. 复现纪律(所有云实验共守)

- **same-pipeline**:所有「模型 vs 模型」差值,分子分母必须来自**同一评估集**(nb10 的共享 test 子样本口径)。
  借跨管线数只能当 magnitude 参照(天花板/地板),**不当减法操作数**(skill `same-pipeline-for-model-deltas`)。
- **strict inductive + retrospective 标注纪律**不变;结果落 `results/experiments.csv` 用 upsert(逻辑键)。
- **许可**:商用权重(TabPFN-2.5/3、RealTabPFN)非商用许可 → 仅研究/求职演示,顶部+README 各标一句。

---

## 2. 项目二(LLM 注入防御)—— 占位,未开工

auto-memory 记:项目二若要**微调 DeBERTa 等**判别式模型 / 跑较大 LLM 做注入检测,属 GPU 触发信号。开工时在此登记:
数据集、基线、需 GPU 的训练/推理项、实例粗估。**当前未开工**(项目四收尾后转此)。

---

## 3. 项目一 / 项目三

暂无 GPU 需求登记(项目一 NF3-v3 表格/传统 ML,CPU 足;项目三 SIEM 未开工)。有需要再加节。

---

## 4. 已核验模型登记表(2026-07-03 WebSearch 逐条核)

| 模型 | arXiv / 会议 | 代码 | 许可 | 真需 GPU? |
|---|---|---|---|---|
| TabDPT | 2410.18164 / NeurIPS'25 | layer6ai-labs/TabDPT-inference;HF Layer6/TabDPT | CC BY 4.0 | 是(FM 推理) |
| TabPFN v2 / 2.5 / 3 | Nature 2025 / 2511.08667 / — | `tabpfn` PyPI(8.x 需 token;2.2.0 开放) | 8.x 商用 token;2.2.0 开放 | 2.5/3 是 |
| TabR | 2307.14338 / ICLR'24 | yandex-research/tabular-dl-tabr | 仅随数据集许可 | 否(faiss-cpu 可) |
| TabM | 2410.24210 / ICLR'25 | yandex-research/tabm | 开源 | 否(轻量) |
| MotherNet | 2312.08598 / NeurIPS'24 | microsoft/ticl | 查 repo | 否(子网 CPU) |
| RealMLP / Better-by-Default | 2407.04491 / NeurIPS'24 | 有(pytabkit) | 开源 | 否(CPU) |
| G2T-FM | 2508.20906 | 有(论文附) | 查 repo | 部分(大图结构算子) |
| CARTE | 2402.16785 / ICML'24 | soda-inria/carte | 开源 | 与本项目重叠→跳过 |
| TABULA-8B | LLM-for-tables | 有 | Llama-3 系许可 | 是(8B) |

> 核验层级:代码仓库存在性 + 许可 + GPU 必要性已核;论文卷期/DOI 属标题级,正式外发前建议再逐条核 DOI。
