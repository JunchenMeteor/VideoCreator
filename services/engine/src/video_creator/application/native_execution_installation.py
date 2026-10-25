"""Trusted retained installation observation ABI, separate from qualification."""

from dataclasses import dataclass, field
from typing import Protocol

from video_creator.application.owner_bootstrap import OwnerBindingRecord
from video_creator.domain.native_execution_registration import NativeInstallationInputs


@dataclass(frozen=True, eq=False, repr=False)
class RetainedNativeInstallation:
    """Original adapter observation and strong owner of both actual held guards.

    Construction/types do not authenticate facts. The one trusted installation
    adapter must track this exact object and validate every original handle.
    """
    installation: NativeInstallationInputs
    instance_id: str
    owner_subject: str
    owner_binding_generation: int
    owner_binding_action_id: str
    authentication_binding_id: str
    os_subject: str
    directory_device: int
    directory_inode: int
    observed_at_us: int
    _issuer: object = field(repr=False)
    _held_owner: object = field(repr=False)


class NativeExecutionInstallationObserver(Protocol):
    def observe(self, installation: NativeInstallationInputs, *, owner_binding: OwnerBindingRecord) -> RetainedNativeInstallation:
        """Outside writer: real OS Owner/protected host/full payload/receipt bytes.

        Track original objects before first OS contact; retain actual build and
        payload guards, complete full files and original external build receipt.
        Do not trust locator/task SHA, imply publisher trust or qualify resources.
        """
        ...

    def assert_current(self, observation: RetainedNativeInstallation) -> None:
        """Outside writer: current original dual guards and actual bytes/RPC."""
        ...

    def assert_local_current(self, observation: RetainedNativeInstallation) -> None:
        """Short writer: original issued object/epoch invalidation only, no I/O."""
        ...

    def close(self, observation: RetainedNativeInstallation | None) -> None:
        """Release only after real original held ownership completion.

        None means observe did not return; adapter still owns any pre-contact
        retained resources. An exception/unknown completion retains ownership;
        no reconnect, fresh handle or numeric close retry may be invented here.
        """
        ...
