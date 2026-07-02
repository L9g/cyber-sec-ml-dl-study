---
name: keep-bash-simple-trust-notifications
description: >
  Use when about to run a shell command to CHECK ON a background task you
  already started (tail/ps/pgrep/grep on a log or process to see if it
  finished), or when composing a Bash command that chains steps with ; &&
  || pipes or wraps a $(...) command substitution. Two rules: (1) don't
  poll harness-tracked background tasks — they notify you on completion, so
  polling is wasted work; (2) keep read-only/diagnostic commands as single
  simple commands so they match the allowlist and don't force the user to
  approve a permission prompt. Prevents both needless actions and needlessly
  un-allowlistable commands.
---

# 少写命令、写简单命令(别 poll、别堆 `$()`)

两条纪律,都是为了**别制造多余的、或复杂到要用户授权的 Bash 调用**。

## 规则 1 · 不要 poll harness 追踪的后台任务
`run_in_background` 的命令、后台跑的 pytest/训练——**完成时 harness 会自动通知你**。
所以主动去 `tail 日志 / ps / pgrep` 探活,是在 poll 一个「会自己叫你」的东西 = **纯浪费**。

- **该做**:发起后台任务 → **停下来等通知**,不探活。
- **例外**:只有 harness **追踪不到**的外部状态(CI 跑批、远程队列、部署)才值得有节制地查,
  且间隔要匹配那个状态的变化速度,不要 60 秒猛戳。

## 规则 2 · 只读/诊断用「单条简单命令」,不堆复合与命令替换
把 `tail`、`ps`、`pgrep`、`grep` 用 `;` / `&&` / `||` / 管道 串成一长条、再套 `$(...)`,有两个坏处:
1. **逼用户授权**:前缀白名单(`Bash(tail *)` 等)只能覆盖**简单命令**;一旦是复合命令、尤其含
   `$(...)` **命令替换**(里面能藏任意命令),权限系统会**额外审查、覆盖不了整条** → 弹授权。
   这是**合理**的安全边界——**别靠加权限去绕它**,靠写简单命令。
2. **难读难审、出错难定位**:一条干五件事,哪段挂了看不出来。

- **该做**:一条命令**只干一件事**;要看多个东西就**分多条**发(可在同一轮并行发多个 Bash 调用)。
- 真要 pipeline 时:确保**每一段都在白名单**、且**不含 `$(...)`**;否则拆开。

## 真实教训(本项目)
探 pytest 是否跑完,曾写成:
```bash
tail -6 nb09_pytest.log 2>/dev/null; echo "---"; ps -eo pid,etime | grep -q "$(pgrep -f '[p]ytest notebooks/09' | head -1)" && echo 跑 || echo 停
```
双重错:(a) pytest 是后台任务、**会自动通知**,这条根本不必跑(违规则 1);
(b) `;` 复合 + `$(pgrep …)` 命令替换 → **逼用户授权**(违规则 2)。
正解:要么**什么都不做、等通知**;要么就单条 `tail -6 nb09_pytest.log`。

## 自检清单
- [ ] 这个命令是在 poll 一个**会自动通知我**的后台任务吗?→ 删掉,等通知。
- [ ] 命令里有 `$(...)`,或多个 `;` / `&&` / `||` / `|` 串联吗?→ 能拆就拆成单条。
- [ ] 拆不开的 pipeline,**每一段**都在项目 allow 白名单、且无命令替换吗?否则会弹授权。
