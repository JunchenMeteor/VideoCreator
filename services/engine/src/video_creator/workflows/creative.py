"""Gate0 creative crew; fixed-input results are committed to the business ledger."""

from __future__ import annotations

import contextvars
import json

from crewai import Agent, Crew, Process, Task

from video_creator.application.engine import EngineService, canonical, digest
from video_creator.application.executor import OperationExecutor
from video_creator.domain.contracts import (
    CreativeProposal,
    CreativeRevision,
    LeaseGrant,
)
from video_creator.domain.errors import EngineError
from video_creator.workflows.attempt_control import current_attempt
from video_creator.workflows.controlled_llm import ControlledTextLLM
from video_creator.workflows.delegation_audit import (
    ACTIVE_AUDIT,
    AuditedManager,
    successful_production_reuse,
    successful_reuse,
)

_ACTIVE_TASK: contextvars.ContextVar[Task | None] = contextvars.ContextVar(
    "creative_task", default=None
)


def require_real_delegation(output):
    audit = ACTIVE_AUDIT.get()
    try:
        proposal = output.pydantic or CreativeProposal.model_validate_json(output.raw)
        valid, refs = successful_reuse(proposal, audit or [])
    except ValueError:
        valid, refs = False, []
    if not valid:
        return (
            False,
            "Use actual Delegate work to coworker for 洞察师 and 编剧. Require successful specialist JSON results; final insight and candidates must reuse those exact outputs. Attempts, questions and error strings are insufficient.",
        )
    audit.append({"kind": "final_reuse", "status": "verified", "refs": refs})
    return True, output


def require_production_delegation(output):
    audit = ACTIVE_AUDIT.get()
    try:
        proposal = output.pydantic or CreativeProposal.model_validate_json(output.raw)
        valid, refs = successful_production_reuse(proposal, audit or [])
    except (ValueError, TypeError, KeyError):
        valid, refs = False, []
    if not valid:
        return False, "Actually delegate to all six roles. Reuse exact insight/candidates and director IDs/sources, sound narration, picture visuals/camera and edit durations from completed original specialist responses."
    audit.append({"kind": "production_reuse", "status": "verified", "refs": refs})
    return True, output


class CreativeCrew:
    def __init__(
        self,
        engine: EngineService,
        production_id: str,
        lease: LeaseGrant,
        *,
        subject: str = "local-user",
        route_id: str = "deepseek-validation",
        production_roles: bool = False,
    ):
        self.engine, self.production_id, self.lease = engine, production_id, lease
        self.subject, self.route_id = subject, route_id
        self.production_roles = production_roles
        self.llm = None
        self.delegations = []

    def proposal(self) -> CreativeRevision:
        current_attempt().check()
        request = self.engine.get_request(self.lease)
        step_key, revision_id = "creative-proposal", "proposal." + self.lease.run_id
        step = self.engine.begin_step(self.lease, step_key, digest(canonical(request)))
        # A domain revision can survive the later Step/Flow save crash windows.
        # Consult execution facts first, never use graph state as billing truth.
        revisions = self.engine.creative_revisions(self.subject, self.production_id)
        saved = next(
            (revision for revision in revisions if revision.revision_id == revision_id),
            None,
        )
        if saved is not None:
            if self.production_roles:
                body = saved.body
                valid = False
                try:
                    self.delegations = body["production_delegation_audit"]
                    proposal = CreativeProposal.model_validate(body["proposal"])
                    valid, _ = successful_production_reuse(proposal, self.delegations)
                except (KeyError, TypeError, ValueError):
                    pass
                if not valid:
                    raise EngineError("creative_delegation_provenance_missing", "Original production-role provenance must be resolved without rerunning old model attempts.", 409)
            if step["status"] != "succeeded":
                result = {"revision_id": revision_id}
                if self.production_roles:
                    result["production_delegation_audit"] = self.delegations
                self.engine.complete_step(
                    self.lease, step_key, result_json=result
                )
            return saved
        if step["status"] == "succeeded":
            raise EngineError(
                "creative_revision_missing",
                "Committed creative step is missing its fixed revision.",
                409,
            )
        llm = ControlledTextLLM(
            self.engine,
            OperationExecutor(self.engine),
            self.lease,
            step_key,
            self.route_id,
            max_calls=16,
        )
        self.llm = llm

        def role(name, goal, backstory):
            return Agent(
                role=name,
                goal=goal,
                backstory=backstory,
                llm=llm,
                allow_delegation=False,
                max_iter=6,
                max_retry_limit=0,
                respect_context_window=False,
                verbose=False,
            )

        insight = role(
            "洞察师",
            "依据给定资料分析目标、受众及可制作方向，区分事实、推断及来源缺口。",
            "你只使用本次提供的资料，不虚构平台样本、播放指标或研究结果。",
        )
        writer = role(
            "编剧",
            "形成三个不同且简洁的中文剧本候选，保留已确认事实。",
            "你写适合口播的语言，不擅自改变资料事实。",
        )
        director = role(
            "导演",
            "基于推荐剧本形成三个有稳定ID的镜头，含画面、旁白、运镜及微秒时长。",
            "你负责创作判断与分镜，不代替用户批准，不生成shell。",
        )
        agents = [insight, writer, director]
        if self.production_roles:
            agents.extend([
                role("声音导演", "逐镜头确定自然中文旁白，返三个StoryboardShot。", "只调整narration，保shot-1/2/3顺序和事实；不批准声音许可或冒实际合成。"),
                role("画面导演", "逐镜头确定可拍/可生成画面与运镜，返三个StoryboardShot。", "只负责visual/camera，区分口播与基础动画，不任意shell/path或冒已生成素材。"),
                role("剪辑导演", "依据旁白、画面与主旨安排节奏和整数微秒时长，返三个StoryboardShot。", "只负责duration_us，保稳定shot IDs，不以规划时长冒实际解码或ASR坐标。"),
            ])
        manager = AuditedManager(
            role="执行统筹",
            goal="真实委派专业角色，并组合洞察、三候选和三镜头方案。",
            backstory="你协调洞察师、编剧、导演。至少分别向洞察师与编剧委派一次，再汇总符合JSON Schema的成果。",
            llm=llm,
            allow_delegation=True,
            max_iter=12,
            max_retry_limit=0,
            respect_context_window=False,
            verbose=False,
        )
        facts = [
            fact
            for source in request.source_bindings
            for fact in source.confirmed_facts
        ]
        payload = {
            "goal": request.goal,
            "source_text": request.inputs.source_text,
            "source_bindings": [
                binding.model_dump(mode="json") for binding in request.source_bindings
            ],
            "preserved_facts": facts,
        }
        description = (
            "只依据以下目标资料自主完成洞察、Brief、三个剧本候选，并推荐一个候选及三个分镜。"
            "未授权联网，source_gaps应明确平台样本/历史数据未提供，不编造热度。"
            "original_goal必须逐字等于输入goal，preserved_facts必须逐字保留给定事实，"
            "所有角色产物只是创作方案，不宣称已生成音视频或已获人工批准。"
            "镜头ID使用shot-1/shot-2/shot-3，时长是整数微秒。source_refs仅引用输入中存在的资料证据。"
            "你必须使用委派工具组织专业协作。最终答案只输出符合下列JSON Schema的JSON，不包含Markdown。\n"
            + json.dumps(payload, ensure_ascii=False)
            + "\nJSON Schema:\n"
            + json.dumps(CreativeProposal.model_json_schema(), ensure_ascii=False)
        )
        if self.production_roles:
            description += "\n必须真正委派六角色。最终shots字段shot_id/source_refs取导演，narration取声音导演，visual/camera取画面导演，duration_us取剪辑导演，逐字复用实际专业产物。当前制作profile为25fps，各镜头duration_us为40000倍数且不超过15000000。所有角色返既有Schema，不虚构Observation或自行批准。"
        task = Task(
            description=description,
            expected_output="符合CreativeProposal的JSON，三个候选及三个镜头，事实完整、来源缺口明确。",
            output_pydantic=CreativeProposal,
            guardrail=require_production_delegation if self.production_roles else require_real_delegation,
            guardrail_max_retries=1,
        )

        crew = Crew(
            agents=agents,
            tasks=[task],
            process=Process.hierarchical,
            manager_agent=manager,
            verbose=False,
            memory=False,
            cache=False,
            tracing=False,
        )
        token = _ACTIVE_TASK.set(task)
        audit_records = []
        audit_token = ACTIVE_AUDIT.set(audit_records)
        try:
            output = crew.kickoff()
        finally:
            _ACTIVE_TASK.reset(token)
            ACTIVE_AUDIT.reset(audit_token)
            self.delegations = [
                {
                    "count": task.delegations,
                    "used_tools": task.used_tools,
                    "processed_by_agents": sorted(task.processed_by_agents),
                }
            ]
            self.delegations.extend(audit_records)
        proposal = output.pydantic or CreativeProposal.model_validate_json(output.raw)
        current_attempt().check()
        if proposal.insight.original_goal != request.goal or tuple(
            proposal.insight.preserved_facts
        ) != tuple(facts):
            raise EngineError(
                "creative_constraint_failed",
                "Creative output changed the original goal or preserved facts.",
                422,
            )
        if tuple(shot.shot_id for shot in proposal.shots) != (
            "shot-1",
            "shot-2",
            "shot-3",
        ):
            raise EngineError(
                "creative_constraint_failed",
                "Creative output did not preserve stable shot identities.",
                422,
            )
        revision = self.engine.commit_creative_revision(
            self.lease,
            CreativeRevision(
                revision_id=revision_id,
                kind="plan",
                body={"proposal": proposal.model_dump(mode="json"), "production_delegation_audit": self.delegations}
                     if self.production_roles else proposal.model_dump(mode="json"),
            ),
        )
        result = {"revision_id": revision.revision_id}
        if self.production_roles:
            result["production_delegation_audit"] = self.delegations
        self.engine.complete_step(self.lease, step_key, result_json=result)
        return revision
