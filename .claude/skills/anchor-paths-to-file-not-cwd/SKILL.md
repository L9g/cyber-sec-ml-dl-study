---
name: anchor-paths-to-file-not-cwd
description: >
  Use when a notebook or script throws ModuleNotFoundError or
  FileNotFoundError that appears or disappears depending on where it was
  launched from (papermill from notebooks/, marimo edit from the repo root,
  IDE, cron), or when the code contains CWD-relative paths like
  sys.path.append("..") , open("data/x.csv") , or Path("../config").
  Anchors imports and file I/O to the file's own location instead of the
  process working directory.
---

# 锚定路径到文件，而非进程 CWD

## 症状（怎么认出来）
- 同一份代码，papermill 从 `notebooks/` 跑能过，marimo `edit` 从项目根跑就
  `ModuleNotFoundError` / `FileNotFoundError`；换个目录启动 bug 就时有时无。
- 代码里出现 `sys.path.append("..")`、`open("data/...")`、`Path("../config")`
  这类**相对**路径。

## 根因（一句话）
相对路径解析的基准是**进程的当前工作目录 (CWD)**，不是源文件的位置。
启动方式不同，CWD 就不同，于是 bug 时有时无。

## 修法：把基准换成「文件自身的位置」
| 环境 | 拿到文件目录的方式 |
|---|---|
| 普通 `.py` 脚本 | `Path(__file__).resolve().parent` |
| marimo notebook | `mo.notebook_dir()`（`__file__` 不可靠） |
| Jupyter `.ipynb` | 无 `__file__`；改用 config 模块里 `Path(__file__)` 算出的绝对路径，notebook 只 import 它 |
| 项目通用 | 在 `config.py` 用 `ROOT = Path(__file__).resolve().parent` 定义所有路径，各处 import，**绝不**在散落处拼相对路径 |

## 核心原则
**别在 `config` 之外手写任何相对路径。** 把所有路径集中到一个
`config.ROOT`（用 `Path(__file__)` 锚定）派生，散落处一律 import。
单纯「记得用绝对路径」防不住下一次——集中化才能。

## 自检清单
- [ ] 代码里有没有 `".."` / 裸相对路径？
- [ ] 换一个目录启动，还跑得通吗？
- [ ] 路径是不是都从一个 `config.ROOT` 派生？

## 真实案例（本项目集）
`01-honest-nids/config.py` 已用 `Path(__file__).resolve().parent` 锚定，
数据/结果路径从未出问题；**唯独 marimo notebook 里 `sys.path.append("..")`
是漏网的散落相对路径**——papermill 从 `notebooks/` 跑时 `".."` 正好指到项目根，
marimo 从根目录跑时 `".."` 跑到上一级，于是 `No module named 'config'`。
修法：`sys.path.append(str(mo.notebook_dir().parent))`。
