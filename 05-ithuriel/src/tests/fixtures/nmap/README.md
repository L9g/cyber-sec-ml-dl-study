# nmap fixtures（slice 3 / ADR-0013）

冻结的 `nmap -oX` 输出，用于主动探测切片（CE-UK-FW-01）。**手写代表性输出**——slice 3 fixture-first、
**MockBackend 绝不调 subprocess/socket、零真实网络 I/O**。

地址用 **RFC 5737 文档地址 `192.0.2.10`**（保证即便误接真实网络也不命中真实主机）。Finding 只裁定
**synthetic target/fixture**，**不对 fixture 中地址作任何现实安全声明**（assurance_level=none）。

| fixture | 内容 | 用途 |
|---|---|---|
| `open_22_443.xml` | 192.0.2.10：22/tcp open(ssh)、80 closed、443 open(https) | pass/fail/inconclusive 矩阵（配不同 DeclaredService inventory） |
| `malformed.xml` | 非 well-formed XML（截断） | 解析失败 → inconclusive |

裁定规则（`fw01-exposed-services-justified/v1`）：`observed ⊆ declared-and-justified → pass` /
`存在未声明开放端口 → fail` / `无 justification inventory → inconclusive`。⭐ nmap 只证 `identified`、
证不了 `justified` —— 需 target-scoped `DeclaredService` 清单，**parser 内不写静态 allowed-port 列表**。
