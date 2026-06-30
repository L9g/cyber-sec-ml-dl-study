---
name: marimo-pytest-conftest
description: >
  Use when `pytest notebooks/*.py` fails with ModuleNotFoundError or
  FileNotFoundError even though `python notebooks/nb.py` works fine, or
  when a marimo notebook's import cell raises "No module named 'config'"
  only under pytest.  The root cause is mo.notebook_dir() returning CWD
  (not the notebook's directory) in pytest mode, so sys.path.append(...parent)
  points to the wrong directory.  Fix: add a conftest.py to the notebooks/
  directory that sets sys.path before any cell runs.
---

# marimo notebook 在 pytest 下 import 失败

## 症状（怎么认出来）

- `python notebooks/nb.py` 正常；`pytest notebooks/nb.py` 报
  `ModuleNotFoundError: No module named 'config'`（或项目内其他模块）。
- 错误堆栈指向 import cell 里的 `from config import ...` 这一行。
- import cell 里有 `sys.path.append(str(mo.notebook_dir().parent))`。

## 根因（一句话）

`mo.notebook_dir()` 在 **`pytest` 模式下退化为进程 CWD**，不是 notebook
文件所在目录。

| 启动方式 | `mo.notebook_dir()` 返回 |
|---|---|
| `python notebooks/nb.py` | notebook 所在目录（如 `…/01-honest-nids/notebooks`） |
| `marimo run/edit nb.py` | notebook 所在目录 ✅ |
| `pytest notebooks/nb.py` | 进程 CWD（如 `…/01-honest-nids`）❌ |

结果：`.parent` 再偏移一层，`sys.path` 里进了 workspace root 而非项目根，
`config.py` 当然找不到。

## 修法：在 `notebooks/` 加 `conftest.py`（一劳永逸）

```python
# notebooks/conftest.py
import sys
from pathlib import Path

# mo.notebook_dir() degrades to CWD in pytest mode, so its .parent points
# to the workspace root instead of the project root.  Add the project root
# here so that `config` and `src` are importable regardless of invocation.
sys.path.insert(0, str(Path(__file__).parent.parent))
```

pytest 在收集任何测试之前先加载 `conftest.py`，`Path(__file__)` 是
`conftest.py` 自身的路径（不受 CWD 影响），`.parent.parent` 稳定指向
项目根。此后 import cell 里的 `from config import ...` 就能找到了。

**不需要改 notebook 里任何 cell。**

## 为什么不直接在 import cell 里用 `__file__`

marimo cell 是函数体，`__file__` 是模块级变量，**在 cell 函数内部不可见**。
`mo.notebook_dir()` 是 marimo 提供的替代，但 pytest 下它拿不到运行时上下文，
只能 fallback 到 CWD。`conftest.py` 绕过这个限制，且对目录下所有 notebook
一次性生效。

## 验证

```bash
# 冒烟（应 exit 0）
python notebooks/nb.py

# 断言（应全 passed，无 ModuleNotFoundError，无 skipped）
pytest notebooks/nb.py -v
```

`N passed, 0 skipped` 才算真修好——`skipped` 可能是别的 import 失败后
`pytest.skip` 吞掉错误（呼应 gotchas #5）。

## 真实案例（本作品集）

`01-honest-nids/notebooks/conftest.py`（2026-06-29 加）：
历史上 nb02/nb04 的 pytest 都因此报 `No module named 'config'`；
加完 conftest 后 nb02 4 passed、nb04 3 passed（-k p6 skipped 是数据文件
缺失的预期 skip，不是 import 问题）。
