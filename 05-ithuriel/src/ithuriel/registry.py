"""控制注册表加载器（档 3，ADR-0008）——差异化层「标准→ontology」半边首次落码。

**只读消费** profile（`docs/UK_Region_Profile_v0.2.yaml`）里已声明的控制实例 + standards 注册表：
解析 → 校验 schema 不变量（standards_ref.source 不悬空，见 `models.Registry`）→ 供 derive 解析元数据。
**不建** capability/plugin 匹配（profile GATE-2 明确 defer plugin→capability）、**不改** profile/ontology YAML。

路径锚定到文件、非 CWD（[[anchor-paths-to-file-not-cwd]]）。加载结果缓存（profile 是静态数据）。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from ithuriel.models import Registry

# src/ithuriel/registry.py → parents[2] = 项目根；profile 在 docs/ 下。
_PROFILE = Path(__file__).resolve().parents[2] / "docs" / "UK_Region_Profile_v0.2.yaml"
DEFAULT_CONTROL_ID = "AI-AGENT-PI-01"   # D8 唯一在用控制（PI 探针）


def load_registry(profile_path: Path | str | None = None) -> Registry:
    """读 profile YAML → 校验过的 Registry。standards + controls + planned_ai_controls 合并。

    校验（standards_ref.source 不悬空）在 `Registry` 的 model_validator 里，悬空 → ValueError。
    """
    path = Path(profile_path) if profile_path else _PROFILE
    data = yaml.safe_load(path.read_text())
    # standards 注册表在 `profile:` 下；controls/planned_ai_controls 在顶层。
    std_list = (data.get("profile") or {}).get("standards") or data.get("standards") or []
    standards = {s["id"]: s for s in std_list}
    controls: dict[str, dict] = {}
    for group in ("controls", "planned_ai_controls"):
        for c in data.get(group, []):
            controls[c["id"]] = c
    return Registry(standards=standards, controls=controls)


@lru_cache(maxsize=1)
def _cached_registry() -> Registry:
    return load_registry()


def default_control():
    """D8 在用控制（AI-AGENT-PI-01）的解析定义；缓存（profile 静态）。"""
    return _cached_registry().controls[DEFAULT_CONTROL_ID]


def control(control_id: str):
    """按 id 取解析后的控制定义（slice 2 起多控制：如 CE-UK-FW-03）；缓存。"""
    return _cached_registry().controls[control_id]


def referenced_standards(control_id: str = DEFAULT_CONTROL_ID):
    """该控制引用到的 standards 子集（审计闭环：Finding→control_id→source→StandardEntry）。"""
    return _cached_registry().referenced_standards(control_id)
