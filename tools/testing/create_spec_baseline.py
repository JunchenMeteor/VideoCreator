"""Snapshot read-only specification coverage. Does not evaluate product completion."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
from pathlib import Path

GATE0_IDS = [
    "G0-ENV", "G0-ORCH", "G0-REVIEW", "G0-LEDGER", "G0-BOUNDARY",
    "G0-MEDIA", "G0-ALIGN", "G0-DESKTOP", "G0-LINUX", "G0-CONTRACT", "G0-UI",
]
CHECKS = {
    "FR01": "AC01/02/13；免注册、目录、诊断、另实例恢复",
    "FR02": "AC24/MM11；实际能力连接、路由、明确目的地",
    "FR03": "AC13/MM04；导入哈希/来源/权利、路径边界",
    "FR04": "AC21/MM01/08；仅目标资料，真实模型洞察/3候选",
    "FR05": "R1参考设定版本；R2真实角色/声音一致性增强",
    "FR06": "AC21；结构分镜含画面/旁白/动作/运镜/时长/路线",
    "FR07": "AC07/17/MM02/03；真实旁白、混音、字幕、两画幅",
    "FR08": "AC04/22/MM11；第三镜头局改、旧资产/调用数不变",
    "FR09": "AC03；真实图片及异步视频提交/查询/下载/校验",
    "FR10": "R1≥3新生成动画镜头；R2参考一致性真实样本",
    "FR11": "AC05/06/20/MM07；去重、lease/fencing、崩溃、预算",
    "FR12": "AC08/13/17/MM02/04；固定包、export/reference",
    "FR13": "AC10/16/MM01；一次HTTP/MCP、断线继续、受控嵌入",
    "FR14": "AC11/12；Linux原生headless、实例身份/成员权限",
    "FR15": "AC09/CM01—05；真实官方账号/订阅/额度/Gateway",
    "FR16": "CM06；抖音、小红书分别实际授权与作品回执",
    "FR17": "R2冻结音色克隆/口型/高阶时间线/资源包，真实样本",
    "FR18": "后续范围；不得自动扩大本次R1/R2",
    "FR19": "AC18/19/MM04—06；精确来源及新选题匹配分别测",
    "FR20": "AC21/23/MM09/10；平台/赛道洞察、来源缺口不造指标",
    "FR21": "AC22/24/MM08/11；指导版本/定位修订/模型协同",
}
OWNER = {
    "FR01": "集成/后端", "FR02": "后端/Agent媒体/前端",
    "FR03": "后端/前端", "FR04": "Agent媒体/前端", "FR05": "Agent媒体/后端/前端",
    "FR06": "Agent媒体/后端/前端", "FR07": "Agent媒体/集成",
    "FR08": "后端/Agent媒体/前端", "FR09": "Agent媒体/后端",
    "FR10": "Agent媒体/后端/前端", "FR11": "后端/集成",
    "FR12": "后端/Agent媒体/集成", "FR13": "后端/集成/前端",
    "FR14": "后端/集成", "FR15": "后端/前端", "FR16": "后端/前端",
    "FR17": "Agent媒体/后端/前端/集成", "FR18": "不派发",
    "FR19": "后端/Agent媒体", "FR20": "Agent媒体/后端", "FR21": "Agent媒体/后端/前端",
}


def snapshot(spec_dir: Path, target_dir: Path) -> dict:
    files = sorted(p for p in spec_dir.glob("*.md") if re.match(r"^(0[1-9]|10|11)-", p.name))
    if len(files) != 11:
        raise ValueError(f"Expected 11 specifications; found {len(files)}")
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    requirements = []
    for path in files:
        for line in path.read_text(encoding="utf-8").splitlines():
            match = re.match(r"\|\s*((?:FR|AC|MM|CM)\d{2})\s*\|\s*(.*?)\s*\|", line)
            if not match:
                continue
            req_id, statement = match.groups()
            if any(item["id"] == req_id for item in requirements):
                raise ValueError(f"Duplicate requirement {req_id}")
            if req_id == "FR18":
                phases = []
            elif req_id in {"FR15", "FR16", "FR17", "AC09"} or req_id.startswith("CM"):
                phases = ["R2"]
            else:
                phases = ["R1", "R2"]
            requirements.append({
                "id": req_id, "source": path.name, "statement": statement,
                "required_phases": phases, "status": "not_run",
                "check": CHECKS.get(req_id, statement),
                "implementation_owners": OWNER.get(req_id, "按关联FR；测试开发维护测试；独立验收判定"),
                "minimum_evidence_kind": "real",
            })
    counts = {prefix: sum(item["id"].startswith(prefix) for item in requirements) for prefix in ("FR", "AC", "MM", "CM")}
    if counts != {"FR": 21, "AC": 24, "MM": 11, "CM": 8}:
        raise ValueError(f"Specification coverage differs: {counts}")
    baseline = {
        "schema_version": "1.0", "criteria_version": "0.1-candidate",
        "freeze_status": "pending_independent_review",
        "source_sha256": hashes, "counts": counts,
        "product_test_baseline": {"executed": 0, "passed": 0, "skipped": 0},
        "gate0_criteria": GATE0_IDS, "requirements": requirements,
        "thresholds_pending_gate0_measurement": {
            "alignment_utterance_p95_ms": 200, "retrieval_precision_min": "0.90",
            "retrieval_topics_min": 30, "retrieval_candidates_min": 60,
            "source_exact_version_preservation": "1.00", "api_metadata_p95_ms": 500,
            "ui_shots": 50, "animation_generated_shots_min": 3,
        },
        "snapshot_runtime": {"python": platform.python_version(), "platform": platform.platform()},
    }
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "BASELINE.json").write_text(json.dumps(baseline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    lines = ["# FR/AC/MM/CM逐项追踪 v0.1候选", "", "来源、标准状态及哈希见BASELINE.json。全部尚未实现验收通过；不是完成百分比。R2仍回归全部适用R1项。FR05/FR10增强和FR17能力需架构冻结供应商/样本后细化，不能省略。", "", "| ID | 范围 | 原始要求 | 验证/归属 |", "| --- | --- | --- | --- |"]
    for item in requirements:
        phase = "/".join(item["required_phases"]) or "后续，排除本次"
        lines.append(f"| {item['id']} | {phase} | {item['statement']} | {item['check']}；{item['implementation_owners']} |")
    lines += ["", "真实/模拟分开报告；状态/故障的模拟通过不意味着对应真实创作、安装、付款或发布通过。冻结后新增测试可扩展覆盖，降低阈值或删除用例须独立评审保留旧版及原失败；必需项skip=0。", ""]
    (target_dir / "TRACEABILITY.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return {"counts": counts, "product_tests_executed": 0, "freeze_status": baseline["freeze_status"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec-dir", type=Path, required=True)
    parser.add_argument("--target-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(snapshot(args.spec_dir, args.target_dir), ensure_ascii=False))
