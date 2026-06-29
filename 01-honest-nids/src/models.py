"""模型注册表——P6 多算法基线/鲁棒性扫描（Arp P6 + 复现 Layeghy A2「所有模型一起崩」）。

用途：把 §2 的「LightGBM 跨数据集崩塌」升级为「**换什么模型都一起崩**」。
这回答 Arp P6（inappropriate baseline）与一个常见面试追问——
「换个更强/更弱的模型会不会不一样？」——答案：失败的根因是评估/数据，不是模型容量。

四个模型按复杂度递增：
- **SingleFeature(stump)**：depth-1 决策树，自动选**单个最强特征**做一刀切。
  Arp P6 的核心——连 1 个特征都能在合成 benchmark 上逼近满分，说明复杂模型的高分
  不是检测能力的证明，而是数据本身平凡可分（呼应视角8）。
- **LogReg**：线性基线（Layeghy 2024 八模型之一）。
- **MLP**：小型神经网络，代表「DL 也不例外」（吃 IAT/flow 统计特征）。无 torch 依赖，
  用 sklearn MLPClassifier 保持 MVP 档依赖精简。
- **LightGBM**：与 §1/§2/§3 同配置的梯度提升树（对照锚点）。

**前处理差异本身是发现**：树模型(LightGBM)原生容忍 inf/NaN；线性/NN/sklearn 决策树
都不容忍（NF-v3 的 rate 类特征含 inf，UNSW 500K 实测 ~3.8 万 inf + 1.3 万 NaN）。
故非 LightGBM 模型统一加 inf→NaN + 中位数插补；LogReg/MLP 再加标准化。
"""
from __future__ import annotations

from collections import OrderedDict

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler
from sklearn.tree import DecisionTreeClassifier

from config import SEED


def _inf_to_nan(A):
    """把 ±inf 替成 NaN，交给下游 imputer 统一处理（树模型如 LightGBM 不需要这步）。"""
    return np.where(np.isinf(A), np.nan, A)


def _clean_step():
    return ("clean", FunctionTransformer(_inf_to_nan, feature_names_out="one-to-one"))


def _impute_step():
    return ("impute", SimpleImputer(strategy="median"))


def build_models() -> "OrderedDict[str, object]":
    """返回有序 {名称: sklearn 兼容 estimator}（均实现 predict_proba）。

    顺序按复杂度递增，方便表格从「单特征基线」读到「梯度提升树」。
    LightGBM 延迟导入，避免在仅用其它模型时强依赖。
    """
    from lightgbm import LGBMClassifier

    models: "OrderedDict[str, object]" = OrderedDict()

    # 单特征一刀切——Arp P6 的 inappropriate-baseline 反例
    models["SingleFeature(stump)"] = Pipeline(
        [_clean_step(), _impute_step(),
         ("clf", DecisionTreeClassifier(max_depth=1, random_state=SEED))]
    )

    # 线性基线（需标准化）
    models["LogReg"] = Pipeline(
        [_clean_step(), _impute_step(), ("scale", StandardScaler()),
         ("clf", LogisticRegression(max_iter=200))]
    )

    # 小型神经网络——「DL 也不例外」（需标准化；early_stopping 控时）
    models["MLP"] = Pipeline(
        [_clean_step(), _impute_step(), ("scale", StandardScaler()),
         ("clf", MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=60,
                               early_stopping=True, random_state=SEED))]
    )

    # 梯度提升树——与 §1/§2/§3 同配置的对照锚点（原生容忍 inf/NaN，不加前处理）
    models["LightGBM"] = LGBMClassifier(random_state=SEED, n_jobs=-1, verbose=-1)

    return models
