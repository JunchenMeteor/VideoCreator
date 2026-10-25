"""Separate copy-scope restore floor; never overwrites the production/alignment floor."""

from typing import Literal

from pydantic import Field

from video_creator.application.production_management import (
    ProductionAuthorizationControl,
)
from video_creator.domain import contracts as c


class _LocalCopyControlDocument(c.Contract):
    format: Literal['local-copy-input-control-v1'] = 'local-copy-input-control-v1'
    instance_id: c.Identifier
    minimum_revision: int = Field(ge=0, le=9_223_372_036_854_775_807, strict=True)
    pending_request_sha256: c.Sha256 | None = None


class LocalCopyInputControl(ProductionAuthorizationControl):
    """Same actual lock/reserve/fsync/complete implementation, distinct fixed identity."""
    _filename = 'LocalCopyInputControl.json'
    _document_type = _LocalCopyControlDocument
