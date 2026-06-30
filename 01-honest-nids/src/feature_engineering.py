"""特征泄漏 / 捷径学习策略（项目一智力核心）。

把每个特征分到一个 policy，落地为 feature_policy_matrix.csv（见阅读清单 §6）。
对应 Arp 陷阱 P3 (data snooping) / P4 (spurious correlations)。

针对 NetFlow-v3 统一系列（`sarhan2021standardfeature` 扩展到 53 特征）的列名。
"""
from __future__ import annotations

import pandas as pd

# NetFlow-v3 里直接编码「身份/环境」的列——跨数据集不可迁移，且常成捷径或直接泄漏。
# 诚实版必须在 Step 2 移除它们，只保留可泛化的 flow 统计特征。
NETFLOW_IDENTITY_FEATURES = [
    "IPV4_SRC_ADDR",
    "IPV4_DST_ADDR",
    "L4_SRC_PORT",
    "L4_DST_PORT",
]

# v3 新增的绝对时间戳——编码的是「哪个数据集、哪段时间采集」，不是流量本身的行为。
# 跨数据集训练/测试时不可迁移（各数据集时间范围不重叠），作为特征会引入环境标识泄漏。
# ⚠️ 这两列在 temporal_split 里用于排序，排序后需从特征中剔除（temporal_split 内部已处理）；
#    LODO / model_scan 里不做 temporal split，应在 prep() 时通过 extra 参数一并删除。
NETFLOW_ABSOLUTE_TIMESTAMP_FEATURES = [
    "FLOW_START_MILLISECONDS",
    "FLOW_END_MILLISECONDS",
]

# 标签列（不同发行版命名略有差异，加载后统一）。
NETFLOW_LABEL_COLS = ["Label", "Attack"]

# 特征 policy 取值（写进 data_card / feature_policy_matrix.csv 的 policy 列）。
POLICY_INFERENCE_SAFE = "inference-safe"
POLICY_ENVIRONMENT_SPECIFIC = "environment-specific"
POLICY_SUSPECTED_SHORTCUT = "suspected-shortcut"
POLICY_DIRECT_LEAKAGE = "direct-leakage"
POLICY_PRIVACY_SENSITIVE = "privacy-sensitive"


def classify_netflow_feature(col: str) -> str:
    """给 NetFlow 列一个初始 policy 建议（人工再复核，不是自动真理）。"""
    if col in ("IPV4_SRC_ADDR", "IPV4_DST_ADDR"):
        # IP 在实验室数据里常和标签强耦合（攻击机固定 IP）→ 环境捷径 + PII
        return POLICY_PRIVACY_SENSITIVE
    if col in ("L4_SRC_PORT", "L4_DST_PORT"):
        # 端口可直接暴露攻击类型（如固定攻击服务端口）→ 捷径
        return POLICY_SUSPECTED_SHORTCUT
    return POLICY_INFERENCE_SAFE


def build_feature_policy_matrix(columns: list[str]) -> pd.DataFrame:
    """对全部列生成初始 policy 表，供人工复核后存成 feature_policy_matrix.csv。"""
    feature_cols = [c for c in columns if c not in NETFLOW_LABEL_COLS]
    return pd.DataFrame(
        {
            "feature": feature_cols,
            "policy": [classify_netflow_feature(c) for c in feature_cols],
            "reviewed": False,  # 人工复核后置 True
            "note": "",
        }
    )


def drop_leakage_features(
    df: pd.DataFrame, extra: list[str] | None = None
) -> pd.DataFrame:
    """Step 2 诚实重做：移除身份/环境泄漏特征，只留可泛化的 flow 统计特征。"""
    drop = [c for c in NETFLOW_IDENTITY_FEATURES if c in df.columns]
    if extra:
        drop += [c for c in extra if c in df.columns]
    return df.drop(columns=drop)
