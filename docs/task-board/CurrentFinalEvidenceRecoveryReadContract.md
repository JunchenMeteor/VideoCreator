# Current final-evidence recovery: authenticated read and repair contract

Status: QUEUED, original Architecture only, activate after an actual slot is released. This supplements ADR0051 without changing frozen Early source or authorizing runtime effects.

## Fixed inputs

Read workspace/project AGENTS and specifications 01–11 already governing this task. Preserve full R1 and continuous R2 scope.

- ADR0051 `docs/decisions/0051-current-production-final-evidence-continuation.md`, SHA a76d1fbf921a4d72d096d2df4ab82d5034d9662acc3a9f78bb08006534c6e6d3.
- `AgentMedia/MediaCurrentFinalEvidenceConsumption/RecoveryPortsGap.md`, SHA 012daeb0212ea668c4767dcaf00eba07a1790cfca7281ac66e3f34f56a2a7ab1; JSON SHA 42768aead29ab8b39f51e1f83d4db98c50cf7e354e7c9f082846cc0905e95767 under the fixed process root.
- Stopped Backend Early domain SHA c568d3c728d38f7ef513331c9cf3e385e13e63802fd702845430553c4152124d and application SHA 081f7d0318f36d4ba0b88feaf2a7bb4c160a55224e6899cc7ada568d0bc1e0e9, from Backend/CurrentFinalEvidenceImplementation/EarlySources and exact EarlySourceIndex.
- Original stopped BundleService, EngineService and bundle models at exact source paths and hashes listed by RecoveryPortsGap. Never inspect Backend live writes as fixed inputs.

## Required decision

Audit existing recover_preparation/read_material/material_allocation/read_step and existing operation settlement and candidate persistence APIs. Explicitly identify reusable existing calls before approving new interfaces. Approve a minimal Backend-owned sole private type and service-held port supplement only for genuinely missing facts. ResolvedEvidencePolicy remains the actual registry object, not an arbitrary recovery DTO.

Specify authenticated restoration of original complete intent and allocations; immutable saved candidate Manifest bytes/file SHA or authenticated absence; pre-candidate persisted assembly context if required; original settled Operation and secret-free original ASR validation context; strict independent reference/listener/arbitration source closure with original bytes, source/license authority and grammar; and finite affected-subset repair dispatch with original admission, rights, budget, fence, unknown-state guards and controlled preparation lineage.

All reads enforce original Run/binding/preparation/intent and current ordinary lease/fence, source access and byte identities. Never derive original expected ASR values from result, guess an Operation ID, invoke prepare_operation to recover identity, rerun ASR/masters to replace missing facts, or use published AccessContext APIs as unpublished preparation access. Ready materials and original candidates remain immutable. A saved incomplete candidate does not authorize publication. Repair allowed_action is not an execution permit; affected repair must use original registered executor and shared limits.

Give exact signatures, state/error semantics, persistence and crash boundaries, source ownership, concrete Backend/Media consumption order and independent tests. Initial production and genuine same-Run continuation/repair must both converge through the original full verifier and publisher. Permanent missing-assessment stubs are not completion. Preserve strict reference requirements and explicit qualified 0.3 semantics, both real authority checks, actual P95 failures, lease/fence and fee/ASR constraints.

## Writes and evidence

Architecture writes only project AGENTS/requirements/architecture/decisions/commercial/reuse-manifest as permitted, and its own process evidence. No Backend, Media, tests, runtime, database, native tools, provider calls, keys, fees or installation. Choose next unused ADR name without overwriting another frozen decision. Freeze the approved contract and ordinary input identities; deliver full Handoff MD/JSON, actual command terminals and reader release to Root. Backend implements sole types and persistence; Media consumes; Test tests; original Review and Acceptance remain independent.
