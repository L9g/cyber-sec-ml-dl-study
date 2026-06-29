"""项目级配置：固定随机种子与路径（结果可复现，见主文档 6.1）。"""
from pathlib import Path

SEED = 42

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"
EXPERIMENTS_CSV = RESULTS_DIR / "experiments.csv"


def seed_everything(seed: int = SEED) -> None:
    """统一设种子。MVP 只需 numpy/random；加 DL 时再扩展 torch。"""
    import os
    import random

    import numpy as np

    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
