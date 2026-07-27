# 备忘录：把“结构化结论的语义守恒”做成项目级 Skill 约束

日期：2026-07-25  
状态：讨论稿，尚未创建 Skill，尚未改变项目规则

## 一、这次讨论要解决什么

Calendar C2 的真实结果暴露了一个可复用的问题：扁平 artifact 升成 `Finding`、`Claim`、ledger 或报告时，结构化并不是中性的整理动作。字段、枚举、内容寻址 ID 和 rollup 会赋予结论机器可传播的权威；一处原本只存在于 prose 中的 over-claim，进入结构化层后会被自动聚合、展示、比较，甚至触发门禁。

因此需要一条项目级纪律：

> 派生后的结构化结论，不得比预注册规则、原始证据和 provenance 三者共同支持的最窄交集更强；遇到不对称、缺失或歧义时，只允许缩小范围，不允许自动补全意义。

这条纪律不仅适用于 Calendar C2，也适用于以后所有 RawArtifact / Observation / TrialOutcome 到 Finding / Claim / ledger / report 的转换。

## 二、当前建议：不是只建一个 Skill，而是三层配合

建议采用下面的结构：

```text
AGENTS.md
└── 存放必须始终生效的短规则，以及何时强制使用项目 Skill

.agents/skills/
└── preserve-claim-semantics/
    └── SKILL.md
        存放详细、可重复执行的语义守恒审查流程

src/tests/ + Pydantic validators + 必要的 hooks/CI
└── 对可机械判断的不变量作真正的 fail-closed 强制
```

三层职责不同：

- `AGENTS.md`：持久、自动进入项目上下文，负责说“什么时候必须这样做”。
- Skill：按任务触发后加载，负责说“具体怎样审查和实施”。
- tests/validators：不依赖 agent 是否理解或记得，负责真正阻止错误实现。

`Project_Memory.md` 继续保存历史、理由和设计演化，但不应成为唯一约束载体：它内容很长，也不是每次任务都会自动读取。

## 三、为什么项目级存放比用户级 Skill 更合适

Codex 当前支持把仓库专属 Skill 提交到 `$REPO_ROOT/.agents/skills`，并从当前工作目录向仓库根扫描 `.agents/skills`。根目录 Skill 因而可供整个仓库使用，也能跟随 Git 共享给协作者。

这类规则不宜只放进 `~/.agents/skills`：它是 Ithuriel 对 Evidence/Finding/Claim 的特定纪律，不应污染其它项目。也不需要先做成 plugin；单仓库、纯指令型 workflow 用 repo Skill 已经足够。

官方参考：

- [Codex customization — Skills](https://developers.openai.com/codex/concepts/customization#skills)
- [Codex customization — AGENTS guidance](https://developers.openai.com/codex/concepts/customization#agents-guidance)

## 四、拟议 Skill

暂定名称：`preserve-claim-semantics`

建议触发范围：

- 新增或修改 parser、normalizer、deriver、aggregator；
- RawArtifact / Observation / TrialOutcome 向 Finding 的转换；
- Finding 向 Claim、CoverageLedger 或报告的转换；
- 修改 status、scope、evidence_refs、verdict provenance 或内容寻址规则；
- 新增 comparison、rollup 或 assurance 呈现；
- 评审任何可能提高 claim 强度或扩大 claim scope 的 schema/代码变更。

拟议 frontmatter：

```yaml
---
name: preserve-claim-semantics
description: Preserve Ithuriel's claim boundaries when deriving or reviewing Evidence, Findings, Claims, scopes, comparisons, ledgers, reports, provenance, or content-addressed identities. Use for any change that converts observations into structured assurance conclusions or could strengthen, widen, aggregate, or relabel a claim.
---
```

## 五、Skill 应钉住的核心约束

### 1. 语义守恒

结构化输出的 claim strength 和 scope 只能等于或弱于源材料共同支持的范围，不能因字段化而升级。

### 2. 三层分离

必须分别回答：

1. 实际观察到了什么；
2. 测量是否允许解释这些观察；
3. 在该测量和范围下，控制结论是什么。

Observation、measurement assessment 和 Finding 不得相互冒充。即使测量无效，原始事件证据也不能被删除；只是不能升级成可断言的目标结论。

### 3. 保持分支非对称

不得为了简化 schema，把后果不同的状态压成一个布尔值或统一状态。每个分支必须保留它原本的 claim 后果。

Calendar C2 是当前 grounding：C2a 失败使整轮不可形成目标易感性结论；C2b 失败只缩小范围，不自动撤销 C2a，也不构成目标易感或不易感证据。

### 4. Provenance、validity、fidelity 正交

- receipt 完整，只证明 artifact 的授权来源和字节链；
- measurement valid，只证明本次测量满足相应判据；
- target fidelity，决定结论可否外推到真实目标。

任何一个维度都不得替代另外两个。receipt verified 不等于 oracle 正确、provider attestation 真实、mock 等于生产环境或 root cause 已被证明。

### 5. 裁定证据闭合

所有真正参与裁定的证据都必须进入 manifest、evidence refs 或相应身份计算。如果结论依赖正臂和负对照，那么只哈希正臂是不完整的。

### 6. 无效或不足的测量不得升级

遇到缺失、不充分、歧义或无效测量，只能产生 `inconclusive`、结构化 gap、空 Claim，或更窄 scope；不得生成目标 pass/fail 或默认为安全。

### 7. 身份分层

`finding_id` 表示一次有具体证据支撑的裁定。若未来要把多次复跑归为“同一个长期漏洞”，应另建 issue identity，而不是削弱 Finding 的内容寻址。

### 8. 必须有负向契约测试

测试不只验证“应该生成什么”，还要验证“绝不能生成什么”，例如：

- C2b fail 不得变成“目标不易感”；
- receipt verified 不得变成“独立审计”；
- policy severity 不得描述成统计推导结果；
- advisory root cause 不得描述成因果实验结论；
- mock 不得渲染成真实 Gmail/Google；
- run-local measurement validity 不得渲染成 instrument qualification。

## 六、Skill 每次应执行的最小流程

1. 找到本次转换真正受约束的源材料：预注册、ADR、artifact、receipt、schema 和既有测试。
2. 写出以下六格映射：

   | 层次 | 必须回答的问题 |
   |---|---|
   | 原始观察 | 实际发生了什么？ |
   | 测量闸门 | 什么条件允许解释观察？ |
   | 结构化裁定 | Finding/Claim 最多能说什么？ |
   | 范围 | 只适用于哪些配置、目标和时间窗？ |
   | 禁止结论 | 下游绝不能据此推出什么？ |
   | 身份依赖 | 哪些输入变化必须改变 ID？ |

3. 核查所有分支是否保持原有非对称后果。
4. 核查 provenance、measurement validity 和 fidelity 是否被分别表达。
5. 核查 evidence closure 和内容寻址敏感性。
6. 为 permitted 与 prohibited claims 分别写契约测试。
7. 若源材料无法唯一支持某个映射，停止升级 claim；报告歧义或产生更窄结果，不自行补全语义。

## 七、根 `AGENTS.md` 的最小触发规则草案

```md
## Assurance semantic constraints

When changing parsers, derivers, Findings, Claims, comparisons, ledgers,
reports, evidence identity, scope, or verdict mappings, use
$preserve-claim-semantics.

- Structured output must not assert more than the narrowest intersection
  supported by preregistration, evidence, and provenance.
- Keep observation, measurement validity, target verdict, provenance,
  and fidelity separate.
- Preserve asymmetric verdict branches.
- Add negative contract tests for prohibited claims.
- Enforce mechanical invariants in validators or tests, not solely in
  agent instructions.
```

这段应保持短小。具体历史、例子和操作步骤放 Skill 或既有项目文档，不把根指令膨胀成第二份 `Project_Memory`。

## 八、不应放在哪里

- 不应只放 `Project_Memory.md`：它适合解释“为什么”，不适合保证每次触发。
- 不应只放用户级 `~/.agents/skills`：作用域过宽。
- 不应只靠 Skill 隐式触发：描述匹配不是硬保证，所以需要 `AGENTS.md` 明确路由。
- 不应放 `.codex/config.toml`：那更适合 sandbox、MCP、hooks、模型等运行配置，而非 assurance 语义。
- 不应只写成 prose 而无测试：agent 纪律不能替代机器不变量。
- 当前不需要 plugin、脚本、assets 或额外 README；先做 instruction-only Skill。

## 九、明天需要拍板的问题

1. 是否采用 `preserve-claim-semantics` 这个名称，还是更具体的 `derive-assurance-safely`？
2. 约束是全仓库生效，还是只覆盖 `src/ithuriel`、`src/tests`、`reports` 和相关治理文档？
3. 是否现在就创建根 `AGENTS.md`，还是先只提交 Skill、观察一次真实触发？
4. 哪些项目文档是 Skill 的最小必读源？应引用精确文件/搜索词，避免要求每次通读全部 Memory。
5. Calendar C2 只作为简短 grounding，还是单独放进 `references/calendar-c2.md`？当前倾向是只保留简短例子，不复制阈值和状态机真相源。
6. 是否在实现 `derive_calendar_c2` 之前先落 Skill，使首次实现本身成为 forward test？当前倾向是“是”。
7. 是否需要兼顾其它 agent 工具；如果需要，应确定唯一规范源，避免在多个工具目录复制并漂移。
8. 哪些约束已经能立刻变成 validators/tests，哪些只能作为审查纪律？

## 十、当前建议

如果明天决定落地，建议顺序是：

1. 在仓库根创建 `.agents/skills/preserve-claim-semantics/`；
2. 用 `skill-creator` 初始化一个 instruction-only Skill；
3. 把本文第五、六节压缩成短 `SKILL.md`；
4. 创建最小根 `AGENTS.md`，只负责强制路由；
5. 用尚未实现的 Calendar C2 deriver 作第一次真实 forward test；
6. 将 forward test 暴露的机械不变量转成代码测试，而不是继续堆 prose。

今天只记录设计，不提前把讨论稿变成正式项目约束。
