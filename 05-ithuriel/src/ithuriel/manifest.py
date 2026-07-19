"""AssessmentManifest（桶 B，ADR-0019）——评估前钉死的『声明控制集』当覆盖率分母。

搭档 milestone P0 #1：`CoverageLedger` 的分母此前来自**传入的 report 集合**，可被输入选择做高
（少传一份 report，未评估的控制就从分母消失、覆盖率虚高）。本层引入一个**在结果之前就承诺、
内容寻址钉死**的评估清单：分母改由声明控制集播种；声明了却无 report 的控制归 `not_assessed`
（进分母、非 pass），不再隐形。钉死的 `manifest_hash` 让「声明」先于「结果」且可审计，事后调分母
会改变 hash、暴露。

**纯差异化层对象、不改 `ontology_schema.yaml`**（同 ledger/report/claim，新枚举先落 pydantic）。
声明的控制必须在 registry 注册（非悬空声明，echo `Registry` 的 standards_ref.source 不悬空不变量）。

**本切片刻意不建**：target 级部分评估（声明 3 主机却只跑 2 → 那 1 台算 not_assessed）是自然的下一步
细化，需要 report↔target 匹配机器；守「一个切片一个新变量」，先只在**控制级**播种分母（某声明控制
有 ≥1 report 即算已评估）。`targets` 字段留形不留逻辑，等真实摩擦逼出 target 级核对再接。
"""
from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from ithuriel.models import content_hash


class DeclaredControl(BaseModel):
    """评估清单里的一条声明：承诺要评估的控制（+ 可选期望 target）。"""
    control_id: str
    # 期望覆盖的 target id（可选）。空 = 控制级声明：有 ≥1 report 即算已评估。target 级核对延后（见模块串）。
    targets: list[str] = Field(default_factory=list)


class AssessmentManifest(BaseModel):
    """评估前承诺的声明控制集。分母 = declared；`manifest_hash` 把声明钉死在结果之前。"""
    profile_id: str
    declared: list[DeclaredControl]
    manifest_hash: str = ""              # 内容寻址派生（见 validator）；钉死声明、事后改分母会改 hash

    @model_validator(mode="after")
    def _validate_and_hash(self) -> "AssessmentManifest":
        if not self.declared:
            raise ValueError("AssessmentManifest.declared 不得为空（空声明无分母意义）")
        ids = [d.control_id for d in self.declared]
        if len(ids) != len(set(ids)):
            raise ValueError("AssessmentManifest.declared 有重复 control_id（一控制声明一次）")
        if not self.manifest_hash:
            # 稳定序列化 → 同声明同 hash（与 report/finding 的内容寻址同纪律）。
            self.manifest_hash = content_hash(
                {"profile_id": self.profile_id,
                 "declared": sorted(
                     ({"control_id": d.control_id, "targets": sorted(d.targets)} for d in self.declared),
                     key=lambda x: x["control_id"])},
                prefix="mfst:")
        return self

    def control_ids(self) -> set[str]:
        return {d.control_id for d in self.declared}
