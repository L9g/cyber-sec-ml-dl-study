---
name: write-flowing-prose-not-symbol-shorthand
description: >
  Use when writing or editing the BODY PROSE of any document meant to be
  read as prose — a README, design doc, ADR narrative, planning doc, report,
  or any Markdown/artifact paragraph. Two requirements: (1) prose must read
  smoothly as connected sentences, flow is a first-class requirement not an
  afterthought; (2) do NOT use shorthand symbols as sentence connectors in
  body prose — arrows, not-equal, plus, em-dash / long dash, and similar
  operator glyphs — write the relation out in words instead. Exceptions where
  the symbols are fine: inside math formulas, inside code / code spans, and
  when a line is deliberately formatted AS a math-like statement (a definition
  line, a rule expression). Scope boundary: this applies ONLY to prose written
  INTO a document artifact. It explicitly does NOT govern chat replies or
  messages shown to the user in conversation — there the priority is output
  efficiency and the user's reading speed, so symbol shorthand is fine and
  even preferred. Also excludes terminal output, token tables, and scratch notes.
---

# 文档正文要行文流畅，不用符号缩写代替句子

## 什么时候用（怎么认出来在写"正文"）

- 在写 README、设计文档、ADR 叙事段、规划草案、报告、artifact 段落——
  也就是**给人当散文读**的连续段落。
- 句子里正想图省事塞进 `→`、`≠`、`+`、破折号（`——` / `-`）这类符号，
  把两件事的关系压成一个记号，而不是把关系用词写清楚。

## 范围边界（只管"写进文档的正文"）

这套约束**只**管写进文档产物里的正文段落。**和用户对话、给用户看的消息不受此约束**——
那里以**输出效率和用户的阅读速度**为主要考量，符号缩写不但可用，往往更好（密度高、扫读快）。
终端输出、纯记号表、草稿速记同样不在此列。

一句话判据：**这段字最终落进文件当散文读，就守约束；只是说给用户听、看完即弃，就不守。**

## 两条要求

**一、行文流畅是硬要求。** 正文要读得通顺、一句接一句成段，不是把要点用符号
和缩写串成的电报。写完自检：一个没有本项目上下文的读者，能顺着句子读下去吗？

**二、正文里不用符号缩写当连接词。** 下列记号在**正文散文**中避免，改用文字把关系说出来：

- `→` 表示"导致 / 变成 / 进而"——写成"导致""于是""接着"。
- `≠` 表示"不同于 / 不是"——写成"不等于""区别于""并非"。
- `+` 表示"加上 / 以及"——写成"外加""并且""连同"。
- 破折号（`——`、`-`）当停顿或补充——改用逗号、冒号，或拆成两句。
- 同类的还有 `⊥`、`⊗`、`×`、`∧`、`∨`、`≤` 等运算/逻辑记号，正文里一律用词写出。

## 例外（这些地方符号是对的，别改）

1. **数学公式**：`P(x) ≤ 0.5`、`recall = TP / (TP + FN)` 保留原样。
2. **代码与代码跨度**：`` `not_applicable` ``、`assertable = valid and not underpowered`
   这类代码或伪代码照写。
3. **刻意做成"类数学表述"的一行**：定义行、规则表达式，如
   `裁定序：¬assertable ∨ 未测 ∨ confound → inconclusive`——
   当它明确是被格式化成一条式子（而非段落里的句子），符号是恰当的。

判据是**这一处是散文还是式子**：散文用词，式子/公式/代码用符号。

## 反例（正文里别这么写）

> 不好：`bare ASR=0 → inconclusive 非 pass`；`unsupported ≠ not_applicable`（进分母 vs 出分母）。

> 改好：当裸跑注入成功率为 0 时，结论应是"无定论"而不是"通过"，因为缺少正对照
> 并不等于目标安全。同样，`unsupported` 与 `not_applicable` 是两回事：前者进入分母
> 记为覆盖缺口，后者移出分母不参与评分。

（注意：代码标识符 `unsupported`、`not_applicable` 仍用反引号；被替换掉的只是
把它们连起来的符号 `→`、`≠`。）
