"""Private installation-qualification floor; no qualification admission here.

The fixed qualified source must perform admission and registry writes. This
control only reuses the original reserve/fsync/complete crash-floor mechanism;
neither constructing it nor its serialized document approves an installation.
"""

from typing import Literal

from pydantic import Field

from video_creator.application.production_management import (
    ProductionAuthorizationControl,
)
from video_creator.domain import contracts as c


class _InstallationQualificationControlDocument(c.Contract):
    format: Literal['installation-qualification-control-v1'] = (
        'installation-qualification-control-v1'
    )
    namespace: Literal['installation-qualification'] = 'installation-qualification'
    instance_id: c.Identifier
    minimum_revision: int = Field(ge=0, le=9_223_372_036_854_775_807, strict=True)
    pending_request_sha256: c.Sha256 | None = None


class InstallationQualificationControl(ProductionAuthorizationControl):
    """Distinct retained floor in the existing control framework.

    Admission must come from the original trusted verifier/registry source,
    never a production-management capability or an Owner approval boolean.
    The existing SQLite revision range remains signed 64-bit. Wire uint64
    registry revisions above that range cannot be persisted by this format.
    """

    _filename = 'InstallationQualificationControl.json'
    _document_type = _InstallationQualificationControlDocument
