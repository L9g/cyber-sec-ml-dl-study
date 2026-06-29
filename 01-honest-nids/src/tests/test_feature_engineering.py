"""feature_engineering.py 的确定性单元测试——泄漏特征 policy 与剔除契约。"""
import pandas as pd

from src import feature_engineering as fe


def test_drop_leakage_removes_ip_and_ports_keeps_flow_stats():
    df = pd.DataFrame(
        {
            "IPV4_SRC_ADDR": ["10.0.0.1"],
            "IPV4_DST_ADDR": ["10.0.0.2"],
            "L4_SRC_PORT": [1234],
            "L4_DST_PORT": [80],
            "IN_BYTES": [500],
            "Label": [1],
        }
    )
    out = fe.drop_leakage_features(df)
    for leaked in ["IPV4_SRC_ADDR", "IPV4_DST_ADDR", "L4_SRC_PORT", "L4_DST_PORT"]:
        assert leaked not in out.columns
    assert "IN_BYTES" in out.columns  # 可泛化流统计特征保留
    assert "Label" in out.columns


def test_drop_leakage_extra_columns():
    df = pd.DataFrame({"IN_BYTES": [1], "FLOW_START_MILLISECONDS": [99], "Label": [0]})
    out = fe.drop_leakage_features(df, extra=["FLOW_START_MILLISECONDS"])
    assert "FLOW_START_MILLISECONDS" not in out.columns
    assert "IN_BYTES" in out.columns


def test_drop_leakage_is_noop_when_absent():
    """已无身份列（如 v2 镜像）时不报错、不动其他列。"""
    df = pd.DataFrame({"IN_BYTES": [1], "Label": [0]})
    out = fe.drop_leakage_features(df)
    assert list(out.columns) == ["IN_BYTES", "Label"]


def test_classify_netflow_feature_policies():
    assert fe.classify_netflow_feature("IPV4_SRC_ADDR") == fe.POLICY_PRIVACY_SENSITIVE
    assert fe.classify_netflow_feature("IPV4_DST_ADDR") == fe.POLICY_PRIVACY_SENSITIVE
    assert fe.classify_netflow_feature("L4_SRC_PORT") == fe.POLICY_SUSPECTED_SHORTCUT
    assert fe.classify_netflow_feature("IN_BYTES") == fe.POLICY_INFERENCE_SAFE


def test_policy_matrix_excludes_label_columns():
    cols = ["IN_BYTES", "IPV4_SRC_ADDR", "Label", "Attack"]
    m = fe.build_feature_policy_matrix(cols)
    assert set(m["feature"]) == {"IN_BYTES", "IPV4_SRC_ADDR"}
    assert (~m["reviewed"]).all()  # 默认未人工复核
