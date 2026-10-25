"""Real refusals of the development installation host (ADR0077 sections 2 and 6).

Every case here is a real child process run against the frozen installation slice:
the argv, raw stdout/stderr bytes and exit code are preserved under the evidence
directory. Nothing in this module edits product source: the "engine code changed"
cases run a byte-edited *scratch copy* of `services/engine/src/video_creator`, which
is exactly what the host hashes.

Only the two unattended cases are process-internal seams (clearly marked): the dev
API/worker cannot be started without a real Owner binding, so their refusal is
exercised directly on the development host's own guards.

Actual observed codes on 2026-10-25 (see the task evidence and COMMANDS.md):
`development_installation_denied`, `development_registration_changed`,
`development_registration_profile_unsupported`, `development_code_changed` (API),
`production_code_changed` (worker, see the dedicated test), `development_installation_unavailable`,
`owner_interactive_confirmation_required`, `owner_restore_refresh_required`.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import time
from pathlib import Path

import local_chain_support as support
import pytest
from conftest import require_absent_owner_binding

MISSING_FLAGS = ('registration', 'registration-sha256', 'expires')
MISSING_FLAG_TEXT = {
    'registration': '--development-registration',
    'registration-sha256': '--development-registration-sha256',
    'expires': '--development-expires-at',
}


def assert_no_listener(result) -> None:
    """A refused development start never binds or prints ready."""
    stdout = result.stdout_text()
    assert '"ready"' not in stdout and 'event": "ready' not in stdout, (
        f'a refused start announced readiness:\n{stdout}\nstderr={result.stderr_text()}')


@pytest.mark.parametrize('omitted', MISSING_FLAGS)
def test_missing_development_argument_exits_2(evidence, installation, omitted) -> None:
    argv = support.dev_host_arguments('serve-dev', omit=(omitted,))
    result = support.run_probe(f'missing-argument-{omitted}', argv, evidence,
                               env=support.dev_environment(None))
    assert result.exit_code == 2, (
        f'expected argparse usage exit 2, got {result.exit_code}\nargv={argv}\n'
        f'stdout={result.stdout_text()}\nstderr={result.stderr_text()}')
    assert MISSING_FLAG_TEXT[omitted] in result.stderr_text()
    assert 'required' in result.stderr_text()
    assert_no_listener(result)


def test_missing_environment_is_denied(evidence, installation) -> None:
    argv = support.dev_host_arguments('serve-dev')
    environment = support.base_environment({'VIDEO_CREATOR_API_TOKEN': support.new_token()})
    result = support.run_probe('environment-missing', argv, evidence, env=environment)
    assert result.exit_code == 1
    assert result.error_code() == 'development_installation_denied', (
        f'actual code={result.error_code()!r}\nstderr={result.stderr_text()}')
    assert 'VIDEO_CREATOR_DEVELOPMENT_INSTALLATION' in result.stderr_text()
    assert_no_listener(result)


def test_mismatched_environment_is_denied(evidence, installation, owner) -> None:
    argv = support.dev_host_arguments('serve-dev')
    environment = support.dev_environment(owner.get('instance_id', 'instance-not-this-one'))
    environment[support.DEV_ENVIRONMENT] = owner.get('instance_id', 'instance-x') + '-wrong'
    result = support.run_probe('environment-mismatch', argv, evidence, env=environment)
    assert result.exit_code == 1
    assert result.error_code() == 'development_installation_denied'
    assert_no_listener(result)


def test_frozen_artifact_simulation_is_unavailable(evidence, installation, owner) -> None:
    """`sys.frozen` is the only difference from the real entry point; args are complete."""
    argv = support.dev_host_arguments('serve-dev')
    shim = (
        'import sys\n'
        'sys.frozen = True\n'
        'from video_creator.cli.development_host import main\n'
        'raise SystemExit(main(sys.argv[1:]))\n'
    )
    environment = support.dev_environment(owner['instance_id'])
    result = support.run_probe('frozen-simulated', [support.PYTHON, '-c', shim, *argv[3:]],
                               evidence, env=environment)
    assert result.exit_code == 1, (
        f'a frozen artifact must be refused, got exit {result.exit_code}\n'
        f'stdout={result.stdout_text()}\nstderr={result.stderr_text()}')
    assert result.error_code() == 'development_installation_unavailable', (
        f'actual code={result.error_code()!r}\nstderr={result.stderr_text()}')
    assert_no_listener(result)


def test_pinned_registration_sha_mismatch_is_registration_changed(evidence, installation, owner) -> None:
    argv = support.dev_host_arguments('serve-dev', registration_sha256='0' * 64)
    result = support.run_probe('registration-pinned-sha-mismatch', argv, evidence,
                               env=support.dev_environment(owner['instance_id']))
    assert result.exit_code == 1
    assert result.error_code() == 'development_registration_changed', (
        f'actual code={result.error_code()!r}\nstderr={result.stderr_text()}')
    assert_no_listener(result)


def test_non_local_profile_registration_is_unsupported(evidence, installation, owner) -> None:
    """A v2-format file is refused with the ADR0077 section 6 profile code."""
    folder = Path(evidence) / 'v2-registration'
    folder.mkdir(parents=True, exist_ok=True)
    payload = support.registration_payload()
    payload['format'] = 'registered-media-config-v2'
    registration = folder / 'Registration.json'
    registration.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n',
                            encoding='utf-8', newline='\n')
    argv = support.dev_host_arguments('serve-dev', registration=registration,
                                      registration_sha256=support.sha256_file(registration),
                                      ffmpeg=None, ffprobe=None)
    result = support.run_probe('registration-v2-profile', argv, evidence,
                               env=support.dev_environment(owner['instance_id']))
    assert result.exit_code == 1
    assert result.error_code() == 'development_registration_profile_unsupported', (
        f'actual code={result.error_code()!r}\nstderr={result.stderr_text()}')
    assert_no_listener(result)


@pytest.fixture(scope='session')
def drifted_engine(evidence, installation) -> dict:
    """A scratch engine package with one real byte edit; the checkout is untouched.

    Only the engine source is copied (into the OS temp directory, removed at the end
    of the session). The registration and the bundled ffmpeg/ffprobe stay the real
    frozen artifacts, so the refusal can only come from the edited engine bytes: the
    process imports the scratch package while the real registration still declares
    the checkout hashes.
    """
    root = Path(tempfile.mkdtemp(prefix='vc-local-chain-drift-'))
    (root / 'src').mkdir(parents=True)
    package = root / 'src' / 'video_creator'
    shutil.copytree(support.ENGINE_SRC / 'video_creator', package,
                    ignore=shutil.ignore_patterns('__pycache__'))
    edited = package / 'domain' / 'errors.py'
    edit = b'# development-code-change fixture: one real edit\n'
    digest_before = support.sha256_file(edited)
    edited.write_bytes(edited.read_bytes() + b'\n' + edit)
    facts = {
        'scratch_root': str(root),
        'scratch_removed_after_session': True,
        'edited_file_relative_path': 'src/video_creator/domain/errors.py',
        'appended_bytes': '\n' + edit.decode('utf-8'),
        'sha256_before': digest_before,
        'sha256_after': support.sha256_file(edited),
        'registration': str(support.REGISTRATION),
        'registration_sha256': support.registration_sha256(),
        'ffmpeg': str(support.FFMPEG),
        'ffprobe': str(support.FFPROBE),
        'note': ('scratch copy of services/engine/src/video_creator with one appended comment '
                 'on PYTHONPATH; the real registration and bundled media tools are unchanged '
                 'and the product checkout was never edited'),
    }
    support.write_json(Path(evidence) / 'drifted-engine.json', facts)
    yield {
        'root': root,
        'src': root / 'src',
        'registration': support.REGISTRATION,
        'registration_sha256': facts['registration_sha256'],
        'ffmpeg': support.FFMPEG,
        'ffprobe': support.FFPROBE,
        'edited_file': edited,
        'sha256_before': digest_before,
        'sha256_after': facts['sha256_after'],
    }
    shutil.rmtree(root, ignore_errors=True)


def test_edited_engine_copy_on_serve_dev_is_code_changed(evidence, installation, owner,
                                                        drifted_engine) -> None:
    assert drifted_engine['sha256_before'] != drifted_engine['sha256_after']
    argv = support.dev_host_arguments(
        'serve-dev',
        registration=drifted_engine['registration'],
        registration_sha256=drifted_engine['registration_sha256'],
        ffmpeg=drifted_engine['ffmpeg'], ffprobe=drifted_engine['ffprobe'])
    environment = support.dev_environment(owner['instance_id'])
    environment['PYTHONPATH'] = str(drifted_engine['src'])
    result = support.run_probe('engine-drift-serve-dev', argv, evidence, env=environment)
    assert result.exit_code == 1, (
        f'edited engine bytes must refuse the dev API host, got exit {result.exit_code}\n'
        f'stdout={result.stdout_text()}\nstderr={result.stderr_text()}')
    assert result.error_code() == 'development_code_changed', (
        f'actual code={result.error_code()!r}\nstderr={result.stderr_text()}')
    assert_no_listener(result)


def test_edited_engine_copy_on_worker_dev_fails_fast(evidence, installation, owner,
                                                    drifted_engine) -> None:
    """The worker refuses drifted engine bytes before any resource wait.

    The registered worker constructs `RegisteredMediaRuntime` before the development
    factory, so the observed code is the production `production_code_changed`, not
    ADR0077 section 2's `development_code_changed`. Both are hard failures; this test
    pins the actual behaviour so a future change is visible. The invariant the task
    requires - never parked as `resource_not_ready` - is asserted directly.
    """
    argv = support.dev_host_arguments(
        'worker-dev',
        registration=drifted_engine['registration'],
        registration_sha256=drifted_engine['registration_sha256'],
        max_seconds=60)
    environment = support.dev_environment(owner['instance_id'])
    environment['PYTHONPATH'] = str(drifted_engine['src'])
    result = support.run_probe('engine-drift-worker-dev', argv, evidence, env=environment)
    assert result.exit_code == 1, (
        f'edited engine bytes must refuse the dev worker, got exit {result.exit_code}\n'
        f'stdout={result.stdout_text()}\nstderr={result.stderr_text()}')
    combined = result.combined()
    assert 'resource_not_ready' not in combined, (
        'drifted development code must not be parked as a retryable resource wait')
    assert 'worker_ready' not in combined
    code = result.error_code()
    assert code in {'development_code_changed', 'production_code_changed'}, (
        f'unexpected refusal code={code!r}\nstderr={result.stderr_text()}')
    assert code == 'production_code_changed', (
        'the registered worker rejects drifted bytes in RegisteredMediaRuntime; '
        f'observed {code!r}. Update ADR0077 section 2 or the worker order if this changed.\n'
        f'stderr={result.stderr_text()}')


def test_serve_dev_without_owner_binding_is_restore_refresh_required(evidence, installation, owner) -> None:
    require_absent_owner_binding(owner)
    argv = support.dev_host_arguments('serve-dev', port=0)
    result = support.run_probe('serve-dev-without-owner-binding', argv, evidence,
                               env=support.dev_environment(owner['instance_id']))
    assert result.exit_code == 1, (
        f'expected the Owner gate to refuse, got exit {result.exit_code}\n'
        f'stdout={result.stdout_text()}\nstderr={result.stderr_text()}')
    assert result.error_code() == 'owner_restore_refresh_required', (
        f'actual code={result.error_code()!r}\nstderr={result.stderr_text()}')
    assert 'Owner Control directory' in result.stderr_text()
    assert_no_listener(result)


def test_worker_dev_without_owner_binding_is_restore_refresh_required(evidence, installation, owner) -> None:
    require_absent_owner_binding(owner)
    argv = support.dev_host_arguments('worker-dev', max_seconds=60)
    result = support.run_probe('worker-dev-without-owner-binding', argv, evidence,
                               env=support.dev_environment(owner['instance_id']))
    assert result.exit_code == 1, (
        f'expected the Owner gate to refuse, got exit {result.exit_code}\n'
        f'stdout={result.stdout_text()}\nstderr={result.stderr_text()}')
    assert result.error_code() == 'owner_restore_refresh_required', (
        f'actual code={result.error_code()!r}\nstderr={result.stderr_text()}')
    assert_no_listener(result)


def test_worker_dev_requires_existing_instance_without_creating_one(evidence, installation, owner) -> None:
    """`worker-dev` refuses a data dir with no instance and does not create it."""
    empty = Path(tempfile.mkdtemp(prefix='vc-local-chain-empty-'))
    argv = support.dev_host_arguments('worker-dev', data_dir=empty, max_seconds=60)
    result = support.run_probe('worker-dev-missing-instance', argv, evidence,
                               env=support.dev_environment(owner['instance_id']))
    assert result.exit_code == 1
    assert result.error_code() == 'development_installation_denied', (
        f'actual code={result.error_code()!r}\nstderr={result.stderr_text()}')
    assert not (empty / 'Metadata.sqlite').exists(), (
        'a refused worker-dev must not create an instance database as a side effect')


def test_owner_init_without_tty_is_refused_and_creates_no_binding(evidence, installation, owner) -> None:
    """The mandatory Owner gate: headless `owner-init` cannot create a binding.

    The command runs with stdin closed, so `confirm_local_action` cannot read the
    literal authorization. The suite never types that answer and never patches
    `isatty`; it only records the refusal and re-reads the binding afterwards.
    """
    require_absent_owner_binding(owner)
    action_key = f'chain-owner-init-nontty-{int(time.time())}'
    argv = [str(support.PYTHON), '-m', 'video_creator.cli.main', 'owner-init',
            '--data-dir', str(support.instance()),
            '--action', 'initialize', '--action-key', action_key,
            '--owner-subject', 'local-user',
            '--project-id', support.project_id(),
            '--expires-at', support.expires_at(days=6)]
    result = support.run_probe('owner-init-without-tty', argv, evidence,
                               env=support.base_environment())
    assert result.exit_code == 1, (
        f'headless owner-init must be refused, got exit {result.exit_code}\n'
        f'stdout={result.stdout_text()}\nstderr={result.stderr_text()}')
    assert result.error_code() == 'owner_interactive_confirmation_required', (
        f'actual code={result.error_code()!r}\nstderr={result.stderr_text()}')
    after = support.owner_state(evidence, name='owner-state-after-owner-init-attempt')
    assert after['owner_active'] is False and after['owner_initialized'] is False, (
        'a refused headless owner-init must not create an Owner binding: '
        + json.dumps(after, ensure_ascii=False, sort_keys=True))


def test_unattended_production_is_refused_by_development_guards(evidence, installation) -> None:
    """Process-internal seam: the dev host refuses unattended before the policy branch.

    This is not an HTTP observation. `serve-dev`/`worker-dev` cannot start without a
    real Owner binding, so the refusal is exercised on the host's own guards.
    """
    result = support.run_probe_module('unattended-guards', ['unattended-guards'], evidence,
                                      env=support.base_environment())
    assert result.exit_code == 0, f'probe failed: {result.stderr_text()}'
    payload = result.json_payloads()[-1]
    support.write_json(Path(evidence) / 'unattended-guards.json', payload)
    for key in ('require_interactive_unattended', 'acceptance_unattended',
                'execution_unattended', 'goal_creation'):
        observed = payload[key]
        assert observed['outcome'] == 'error', f'{key} was not refused: {observed}'
        assert observed['code'] == 'development_mode_unsupported', f'{key}: {observed}'
        assert observed['status_code'] == 422, f'{key}: {observed}'
    assert payload['require_interactive_interactive']['outcome'] == 'accepted'
    assert payload['acceptance_original_calls_after_unattended'] == 0, (
        'an unattended acceptance must not reach the original create_production')
    assert payload['acceptance_interactive']['outcome'] == 'accepted'
    assert payload['execution_original_calls_after_unattended'] == 0, (
        'an unattended execution must not reach the original runtime.invoke')
