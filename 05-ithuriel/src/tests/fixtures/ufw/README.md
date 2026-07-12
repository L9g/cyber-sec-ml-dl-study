# UFW config-inspection fixtures（slice 2 / ADR-0012）

冻结的 `ufw status verbose` 输出，用于确定性 config-inspection 切片（CE-UK-FW-03 default-deny）。

**溯源**：手写的**代表性**输出（非真实主机采集——slice 2 fixture-first、不做 `sudo ufw` 特权调用）。
规范化调用意图 = `LC_ALL=C ufw status verbose`（钉进 evidence，避免本地化破坏解析）。真实主机执行器
+ 特权授权留 slice 3。

| fixture | Status | Default incoming | 期望裁定 |
|---|---|---|---|
| `deny_active.txt` | active | deny | **pass** |
| `allow_active.txt` | active | allow | **fail**（severity Medium） |
| `inactive.txt` | inactive | — | **inconclusive**（sole_authority=True → fail） |
| `truncated_active.txt` | active | 缺 Default 行 | **inconclusive** |
| `unknown_format.txt` | 无 Status 行 | — | **inconclusive** |

`inactive→inconclusive` 是**认识论纪律**：UFW 未激活推不出主机无 default-deny（可能 nftables/云 SG
在执行）；仅当 TargetSnapshot 声明 UFW 为唯一权威执行面才可判 fail。与 AI 切片「bare ASR=0→
inconclusive 非 pass」同源。
