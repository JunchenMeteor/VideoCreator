"""Original strong setup sources. None is a JSON ticket or a bool authority."""

from dataclasses import dataclass


@dataclass(frozen=True, eq=False, repr=False)
class AcceptedOwnerSetupSource:
    journal: object
    _service: object
    _engine: object
    _epoch: object
    _thread_id: int
    _preparation: object


@dataclass(frozen=True, eq=False, repr=False)
class OwnerActionConfirmationSource:
    accepted: AcceptedOwnerSetupSource
    step: object
    final_command_sha256: str
    _service: object
    _epoch: object
    _thread_id: int


@dataclass(frozen=True, eq=False, repr=False)
class OwnerSetupGoalSource:
    accepted: AcceptedOwnerSetupSource
    draft_origin: object
    goal: object
    idempotency_key: str
    accepted_setup_ref: object
    registered: object
    planned_ids: tuple[str, str, str, str, str]
    _service: object
    _engine: object
    _daily: object
    _epoch: object
    _thread_id: int
