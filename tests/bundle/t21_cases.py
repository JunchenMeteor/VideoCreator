"""Complete inherited 68-ID dispatch, not an assertion of runtime readiness.

Only Test modules are imported, lazily after an approved actual context exists.
The criterion and original case objects are not rewritten by this registry.
"""
from __future__ import annotations

import importlib

# (id, Test module, actual driver, keyword parameters, prerequisite groups)
CASE_ROWS = (
    ("T15-01", "t21_media_cases", "default_outputs", {}, ("service",)),
    ("T15-02", "t21_media_cases", "full_media_decode", {}, ("full_bundle", "actual_AV_review")),
    ("T15-03", "t21_media_cases", "manifest_bytes", {}, ("full_bundle",)),
    ("T15-04", "t21_media_cases", "strict_materials", {}, ("full_bundle", "invalid_materials")),
    ("T15-05", "t21_media_cases", "transcript_input", {}, ("full_bundle", "ASR")),
    ("T15-06", "t21_media_cases", "audio_corpus", {}, ("ASR", "human_corpus")),
    ("T15-07", "t21_media_cases", "decoded_provenance", {}, ("ASR", "media_decode")),
    ("T15-08", "t21_media_cases", "corrupt_asr_adapter", {}, ("ASR", "ordinary_lease", "controlled_injection")),
    ("T15-09", "t21_media_cases", "missing_alignment_policy", {}, ("service",)),
    ("T15-10", "t21_media_cases", "independent_precision", {}, ("real_preparation", "qualified_human_reference")),
    ("T15-11", "t21_media_cases", "independent_precision", {"case_id": "T15-11"}, ("real_preparation", "qualified_human_reference", "precision_fault_role")),
    ("T15-12", "t21_media_cases", "real_word_degradation_guard", {}, ("full_bundle", "explicit_degradation_approval", "degradation_fault_role")),
    ("T15-13", "t21_media_cases", "subtitle_mapping", {}, ("full_bundle", "independent_mapping")),
    ("T15-14", "t21_media_cases", "subtitle_mapping", {"case_id": "T15-14"}, ("full_bundle", "independent_mapping")),
    ("T15-15", "t21_media_cases", "subtitle_mapping", {"case_id": "T15-15"}, ("full_bundle", "independent_mapping")),
    ("T15-16", "t21_media_cases", "semantic_sources", {}, ("full_bundle", "independent_semantics")),
    ("T15-17", "t21_media_cases", "semantic_sources", {"case_id": "T15-17"}, ("full_bundle", "independent_semantics")),
    ("T15-18", "t21_media_cases", "semantic_sources", {"case_id": "T15-18"}, ("full_bundle", "independent_semantics", "actual_frame_decode")),
    ("T15-19", "t21_media_cases", "independent_retrieval", {}, ("MM05_corpus", "actual_retrieval_API")),
    ("T15-20", "t21_bundle_cases", "immutable_expiring_revision", {}, ("full_bundle", "real_rights_expiry")),
    ("T15-21", "t21_bundle_cases", "principal_payload_boundary", {}, ("full_bundle", "real_HTTP")),
    ("T15-22", "t21_bundle_cases", "pre_content_authorization", {}, ("full_bundle", "real_HTTP")),
    ("T15-23", "t21_bundle_cases", "real_grant_expiry_revoke", {}, ("full_bundle", "real_recipient", "real_rights")),
    ("T15-24", "t21_bundle_cases", "real_rights_limit", {}, ("full_bundle", "real_rights")),
    ("T15-25", "t21_bundle_cases", "unsettled_no_publish", {}, ("real_preparation", "real_uncertain_operation")),
    ("T15-26", "t21_bundle_cases", "actual_cancel_deadline", {}, ("ASR", "native_job", "cleanup_unknown_fault_role")),
    ("T15-27", "t21_bundle_cases", "actual_publish_crash", {}, ("real_preparation", "native_job", "publisher_fault_role")),
    ("T15-28", "t21_bundle_cases", "actual_publish_crash", {"case_id": "T15-28"}, ("real_preparation", "native_job", "publisher_fault_role")),
    ("T15-29", "t21_bundle_cases", "concurrent_bundle_commands", {}, ("service", "concurrent_publisher_fault_role")),
    ("T15-30", "t21_bundle_cases", "actual_export", {}, ("full_bundle", "real_rights")),
    ("T15-31", "t21_bundle_cases", "actual_export", {"case_id": "T15-31", "projection": True}, ("full_bundle", "real_rights")),
    ("T15-32", "t21_bundle_cases", "malicious_archives", {}, ("malicious_ZIP", "real_import_service")),
    ("T15-33", "t21_bundle_cases", "malicious_archives", {"case_id": "T15-33"}, ("limit_ZIP", "real_import_service")),
    ("T15-34", "t21_bundle_cases", "second_instance_import", {}, ("full_bundle", "second_instance")),
    ("T15-35", "t21_bundle_cases", "second_instance_import", {"case_id": "T15-35"}, ("full_bundle", "second_instance")),
    ("T15-36", "t21_bundle_cases", "actual_contract_transports", {}, ("real_HTTP", "real_stdio_MCP", "SDK")),
    ("T15-37", "t21_bundle_cases", "autonomous_once", {}, ("W14_autonomous_upstream", "real_HTTP", "independent_orchestration_audit")),
    ("T15-38", "t21_bundle_cases", "real_three_os", {}, ("independent_installed_three_OS", "actual_AV_review")),
    ("V03-01", "t21_v03_cases", "fixed_request_versions", {}, ("service", "fixed_v03_policy")),
    ("V03-02", "t21_v03_cases", "three_scopes_null", {}, ("qualified_full_bundle",)),
    ("V03-03", "t21_v03_cases", "actual_qualification_scope", {}, ("actual_qualification", "real_execution_identity")),
    ("V03-04", "t21_v03_cases", "real_untrusted_install_refusal", {}, ("service", "real_signed_documents")),
    ("V03-05", "t21_v03_cases", "signed_revoke_during_publish", {}, ("real_revocation", "writer_order_fault_role")),
    ("V03-06", "t21_v03_cases", "registry_restart_backup", {}, ("real_revocation", "backup_fault_role")),
    ("V03-07", "t21_v03_cases", "actual_max_N", {}, ("independent_actual_benchmark",)),
    ("V03-08", "t21_v03_cases", "actual_max_N", {"case_id": "V03-08"}, ("independent_actual_benchmark", "all_population_counterexamples")),
    ("V03-09", "t21_v03_cases", "real_allocation_persistence", {}, ("real_preparation", "allocation_restart_fault_role")),
    ("V03-10", "t21_v03_cases", "allocation_old_fence", {}, ("real_preparation", "real_lease_wallclock")),
    ("V03-11", "t21_v03_cases", "actual_material_dag", {}, ("measured_full_bundle", "actual_stage_journal")),
    ("V03-12", "t21_v03_cases", "real_qualified_unmeasured", {}, ("qualified_full_bundle", "W14_autonomous_upstream")),
    ("V03-13", "t21_v03_cases", "actual_correction", {}, ("corrected_full_bundle", "independent_ancestor_mapping", "old_report_fault_role")),
    ("V03-14", "t21_v03_cases", "benchmark_license_export", {}, ("qualified_full_bundle", "benchmark_license")),
    ("V03-15", "t21_v03_cases", "full_projection_closure", {}, ("qualified_full_bundle", "real_rights")),
    ("V03-16", "t21_v03_cases", "imported_trust_no_inheritance", {}, ("qualified_full_bundle", "second_instance", "actual_local_recognition")),
    ("V03-17", "t21_v03_cases", "real_schema_migration", {}, ("real_schema4_backup", "migration_fault_role")),
    ("V03-18", "t21_v03_cases", "real_transports_detached", {}, ("W14_autonomous_upstream", "persistent_worker", "real_stdio_MCP")),
    ("V03-19", "t21_v03_cases", "actual_all_runtime_materials", {}, ("qualified_full_bundle", "ASR", "independent_semantics", "actual_frame_decode")),
    ("V03-20", "t21_v03_cases", "independent_method_and_MM05", {}, ("independent_actual_benchmark", "MM05_corpus", "independent_installed_three_OS")),
    ("REF-01", "t21_reference_cases", "reference_unique_dispatch", {}, ("actual_reference_preparation",)),
    ("REF-02", "t21_reference_cases", "reference_original_audio_units", {}, ("actual_reference_preparation", "actual_media_clock", "independent_reference_units")),
    ("REF-03", "t21_reference_cases", "actual_listener_arbitration", {}, ("actual_reference_preparation", "real_listener_arbitration")),
    ("REF-04", "t21_reference_cases", "issuer_scope_current", {}, ("actual_reference_preparation", "actual_issuer_scope")),
    ("REF-05", "t21_reference_cases", "actual_three_hash_layers", {}, ("actual_reference_preparation", "actual_issuer_scope")),
    ("REF-06", "t21_reference_cases", "signed_prediction_copy_refused", {}, ("actual_reference_preparation", "genuinely_signed_adversarial_reference")),
    ("REF-07", "t21_reference_cases", "actual_reference_dag", {}, ("measured_full_bundle", "actual_stage_journal")),
    ("REF-08", "t21_reference_cases", "actual_reference_export", {}, ("measured_full_bundle", "real_listener_rights")),
    ("REF-09", "t21_reference_cases", "actual_reference_origin_import", {}, ("measured_full_bundle", "second_instance")),
    ("REF-10", "t21_reference_cases", "actual_null_or_strict_wait", {}, ("qualified_full_bundle", "strict_missing_reference")),
)


def dispatch(ctx, case_id):
    rows = [row for row in CASE_ROWS if row[0] == case_id]
    assert len(rows) == 1, "unknown or duplicate inherited case ID"
    _, module_name, function_name, kwargs, _ = rows[0]
    driver = getattr(importlib.import_module(module_name), function_name)
    return driver(ctx, **kwargs)
