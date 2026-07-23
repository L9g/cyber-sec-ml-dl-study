"""把 runner 的离线自检接进常规验证流程（pytest）。

P1 之后，纯逻辑不变量已迁进 test_calendar_*/test_governance_* 直接单测；runner 的 `--self-test`
保留为**集成/glue 层**冒烟：fixture 注入、reachability control 经真实 AgentDojo pipeline、
EmissionRecorder、证据 artifact 往返、ADR-0022 git 授权链。这里以子进程跑它并断言退出码为 0，
使它在 `pytest` 里必被执行，且失败会让 CI 变红。子进程环境清空所有 *_API_KEY 以同时坐实「无 key 依赖」。
"""
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNNER = PROJECT_ROOT / "scripts" / "run_calendar_probe.py"


def test_runner_self_test_passes_offline_and_returns_zero():
    assert RUNNER.is_file()
    # 清掉可能存在的 provider key，坐实自检无网络/计费依赖
    env = {k: v for k, v in os.environ.items()
           if not (k.endswith("_API_KEY") or k.endswith("_KEY"))}
    proc = subprocess.run(
        [sys.executable, str(RUNNER), "--self-test"],
        cwd=str(PROJECT_ROOT), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300,
    )
    assert proc.returncode == 0, proc.stdout.decode("utf-8", "replace")[-3000:]
