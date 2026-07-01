"""项目级配置：固定随机种子与路径（结果可复现，见主文档 6.1）。

与项目一 01-honest-nids/config.py 同模具。MVP 档只用 numpy/random；
升到 GNN（Reference-grade）时再在 seed_everything 扩展 torch。
"""
from pathlib import Path

SEED = 42

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
RESULTS_DIR = ROOT / "results"
EXPERIMENTS_CSV = RESULTS_DIR / "experiments.csv"

# Elliptic / Elliptic++ 固定事实（来源见 data/README.md）
N_TIME_STEPS = 49          # 交易图时间步
# 标签编码（Elliptic 原始约定）：1=illicit, 2=licit, 3/unknown=未标注
LABEL_ILLICIT = 1
LABEL_LICIT = 2
LABEL_UNKNOWN = 3


def seed_everything(seed: int = SEED) -> None:
    """统一设种子。MVP 只需 numpy/random；加 GNN 时再扩展 torch。"""
    import os
    import random

    import numpy as np

    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
