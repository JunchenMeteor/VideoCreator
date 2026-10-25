"""UNAPPLIED native-only facts startup candidate; never import/run this copy."""

import json
import sys

from video_creator.application.native_goal_facts_startup import (
    native_pending_goal_store,
)
from video_creator.application.native_installation import (
    NativeOwnerServices,
    connect_native_installation,
)
from video_creator.application.owner_services import assemble_owner_services
from video_creator.cli.native_startup_record import NativeStartupRecord
from video_creator.domain.errors import EngineError
from video_creator.infrastructure.held_authority import _json


def _factory(record, locator_bytes):
    def assemble(*, engine, bundle, role, registered_runtime, for_management):
        context = record.context
        if (for_management is not False or engine.instance_id != context.instance_id
                or role != context.role or bundle.engine is not engine
                or role == 'worker' and (registered_runtime is None
                    or registered_runtime.engine is not engine or registered_runtime.bundle is not bundle
                    or registered_runtime.installation_resource_identity != (
                        context.registration_sha256, context.resource_manifest_sha256, context.runtime_manifest_sha256))
                or role != 'worker' and registered_runtime is not None):
            raise EngineError('native_startup_binding_denied', 'Native startup differs from the actual instance or fixed role', 403)
        owner = bundle.principals.owner_subject
        authority, build = connect_native_installation(locator_bytes=locator_bytes, context=context,
            installed_native_image=record.installed_native_image,
            installed_native_image_sha256=record.installed_native_image_sha256)
        store, current = None, None
        try:
            # The helper authenticates complete independent stored source facts
            # before any writer. It never creates a current execution identity.
            store = native_pending_goal_store(engine=engine, bundle=bundle, record=record, authority=authority)
            current = store.current(owner, role, record)
            services = assemble_owner_services(engine, owner, bundle=bundle, for_management=False,
                installation_authority=authority, installation_session_guard=authority,
                execution_registration=store.original_projection(current),
                native_registration_store=store, native_current_registration=current,
                owner_setup_bootstrap=store.bootstrap)
            return NativeOwnerServices(services, authority.connection, authority, build)
        except BaseException as failure:
            # Both original retained resources are attempted. Unknown I/O/close
            # ownership stays with their existing holders; original failure wins.
            for owned in (authority, build):
                try:
                    owned.close()
                except BaseException as cleanup:  # noqa: BLE001 -- both retained closes attempted; original failure re-raised
                    failure.add_note('Native startup cleanup also failed: ' + type(cleanup).__name__)
            if store is not None and current is not None:
                try:
                    store.release(current)
                except BaseException as cleanup:  # noqa: BLE001 -- release cannot replace the original failure
                    failure.add_note('Original current release also failed: ' + type(cleanup).__name__)
            raise
    return assemble


def main(*, startup_record: bytes, locator_bytes: bytes) -> int:
    try:
        record = NativeStartupRecord.parse(startup_record)
        locator = _json(locator_bytes)
        if (type(locator) is not dict or locator.get('instance_id') != record.context.instance_id
                or locator.get('role') != record.context.role):
            raise EngineError('native_startup_binding_denied', 'Private locator differs from the fixed startup identity', 403)
        from video_creator.cli.main import main as engine_main

        return engine_main(installed_service_factory=_factory(record, locator_bytes))
    except EngineError as error:
        print(json.dumps({'code': error.code, 'message': error.message}), file=sys.stderr)
        return 1


def _qualified_factory(record, locator_bytes):
    def assemble(*, engine, bundle, role, registered_runtime, for_management):
        context = record.context
        if (for_management is not False or engine.instance_id != context.instance_id
                or role != context.role or bundle.engine is not engine
                or role == 'worker' and (registered_runtime is None
                    or registered_runtime.engine is not engine or registered_runtime.bundle is not bundle
                    or registered_runtime.installation_resource_identity != (
                        context.registration_sha256, context.resource_manifest_sha256, context.runtime_manifest_sha256))
                or role != 'worker' and registered_runtime is not None):
            raise EngineError('native_startup_binding_denied', 'Native startup differs from the actual instance or fixed role', 403)
        from video_creator.application.native_installation import connect_qualified_native_installation

        owner = bundle.principals.owner_subject
        authority, build = connect_qualified_native_installation(engine=engine, bundle=bundle, locator_bytes=locator_bytes, context=context,
            installed_native_image=record.installed_native_image,
            installed_native_image_sha256=record.installed_native_image_sha256)
        store, current = None, None
        try:
            # The helper authenticates complete independent stored source facts
            # before any writer. It never creates a current execution identity.
            store = native_pending_goal_store(engine=engine, bundle=bundle, record=record, authority=authority)
            current = store.current(owner, role, record)
            services = assemble_owner_services(engine, owner, bundle=bundle, for_management=False,
                installation_authority=authority, installation_session_guard=authority,
                execution_registration=store.original_projection(current),
                native_registration_store=store, native_current_registration=current,
                owner_setup_bootstrap=store.bootstrap)
            return NativeOwnerServices(services, authority.connection, authority, build)
        except BaseException as failure:
            # Both original retained resources are attempted. Unknown I/O/close
            # ownership stays with their existing holders; original failure wins.
            for owned in (authority, build):
                try:
                    owned.close()
                except BaseException as cleanup:  # noqa: BLE001 -- both retained closes attempted; original failure re-raised
                    failure.add_note('Native startup cleanup also failed: ' + type(cleanup).__name__)
            if store is not None and current is not None:
                try:
                    store.release(current)
                except BaseException as cleanup:  # noqa: BLE001 -- release cannot replace the original failure
                    failure.add_note('Original current release also failed: ' + type(cleanup).__name__)
            raise
    return assemble


def main_qualified(*, startup_record: bytes, locator_bytes: bytes) -> int:
    try:
        record = NativeStartupRecord.parse(startup_record)
        locator = _json(locator_bytes)
        if (type(locator) is not dict or locator.get('instance_id') != record.context.instance_id
                or locator.get('role') != record.context.role):
            raise EngineError('native_startup_binding_denied', 'Private locator differs from the fixed startup identity', 403)
        from video_creator.cli.main import main as engine_main

        return engine_main(installed_service_factory=_qualified_factory(record, locator_bytes))
    except EngineError as error:
        print(json.dumps({'code': error.code, 'message': error.message}), file=sys.stderr)
        return 1
