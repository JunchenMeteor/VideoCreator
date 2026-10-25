/* Generated from unique fixed OpenAPI by openapi-typescript@7.13.0. Do not edit. */
export interface paths {
    "/api/v1/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health */
        get: operations["health_api_v1_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Projects */
        get: operations["projects_api_v1_projects_get"];
        put?: never;
        /** Project Create */
        post: operations["project_create_api_v1_projects_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/projects/{project_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Project Get */
        get: operations["project_get_api_v1_projects__project_id__get"];
        /** Project Update */
        put: operations["project_update_api_v1_projects__project_id__put"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/productions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Production List */
        get: operations["production_list_api_v1_productions_get"];
        put?: never;
        /**
         * Production Create
         * @description Accept a production or recover its original receipt by replaying the saved request and Idempotency-Key. The key is scoped to this installation and the currently authenticated subject. For acceptances recorded by this implementation, the same canonical Pydantic input returns the immutable original ProductionAccepted with HTTP 202, including its original Run and acceptance-time status, even after feedback creates a new Run. JSON whitespace, object-key order and serializer-equivalent omitted defaults do not change canonical input. Different canonical input with the same key returns idempotency_conflict/409 and never replaces that receipt. Historical acceptances without a receipt journal retain their original event-bound Run identity and return that Run's current status; their original returned status is unavailable. Invalid or inconsistent acceptance records return acceptance_record_invalid/422, never a new production. Current credential, operation, purpose and project permissions are required on every replay. A revoked or expired credential or denied scope cannot recover a receipt, and its error does not prove that a prior request was never accepted. Replaying a committed acceptance does not resume execution, approve a revision, resolve unknown provider acceptance/cost, create an Operation or reset a budget. First acceptance commits the production, original Run, event and receipt in one transaction; replay after an uncommitted failure may perform that first acceptance. Use status_path to read current production progress; the acceptance snapshot is not current execution permission. Task-list similarity is not recovery evidence.
         */
        post: operations["production_create_api_v1_productions_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/project-goals": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Create Project Goal
         * @description Accept one canonical Goal under an actual previously installed bounded Owner creation delegation. Creates the real Project, exact child scope and original Production/Run atomically. Same authenticated principal, key and canonical Goal replay the immutable original receipt; a different Goal conflicts. Disconnect does not cancel production. A locator, ordinary token or Goal never installs a delegation or resource qualification.
         */
        post: operations["create_project_goal"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/project-goals/receipt-lookup": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Lookup Project Goal Receipt
         * @description Read the original authenticated principal/key/canonical Goal association without accepting, recovering or reserving production.
         */
        post: operations["lookup_project_goal_receipt"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/productions/{production_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Production Get */
        get: operations["production_get_api_v1_productions__production_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/productions/{production_id}/cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Production Cancel */
        post: operations["production_cancel_api_v1_productions__production_id__cancel_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/productions/{production_id}/revisions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Production Revisions */
        get: operations["production_revisions_api_v1_productions__production_id__revisions_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/runs/{run_id}/decisions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Decision Submit */
        post: operations["decision_submit_api_v1_runs__run_id__decisions_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/runs/{run_id}/pause": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Run Pause */
        post: operations["run_pause_api_v1_runs__run_id__pause_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/runs/{run_id}/resume": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Run Resume */
        post: operations["run_resume_api_v1_runs__run_id__resume_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/runs/{run_id}/events": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Run Events */
        get: operations["run_events_api_v1_runs__run_id__events_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/assets/staging": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Asset Stage */
        post: operations["asset_stage_api_v1_assets_staging_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/assets/import": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Asset Import */
        post: operations["asset_import_api_v1_assets_import_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/assets/{asset_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Asset Get */
        get: operations["asset_get_api_v1_assets__asset_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/assets/{asset_id}/content": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Asset Content */
        get: operations["asset_content_api_v1_assets__asset_id__content_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/assets/{asset_id}/content/metadata": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Asset Content Metadata */
        get: operations["asset_content_metadata_api_v1_assets__asset_id__content_metadata_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/bundles/{revision_id}/manifest": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Bundle Get */
        get: operations["bundle_get_api_v1_bundles__revision_id__manifest_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/bundles/{revision_id}/manifest/metadata": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Bundle Manifest Metadata */
        get: operations["bundle_manifest_metadata_api_v1_bundles__revision_id__manifest_metadata_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/bundles/{revision_id}/artifacts/{artifact_id}/content": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Bundle Content */
        get: operations["bundle_content_api_v1_bundles__revision_id__artifacts__artifact_id__content_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/bundles/{revision_id}/artifacts/{artifact_id}/content/metadata": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Bundle Artifact Metadata */
        get: operations["bundle_artifact_metadata_api_v1_bundles__revision_id__artifacts__artifact_id__content_metadata_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/bundles/{revision_id}/semantic-segments": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Bundle Semantic */
        get: operations["bundle_semantic_api_v1_bundles__revision_id__semantic_segments_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/bundles/{revision_id}/exports": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Bundle Export */
        post: operations["bundle_export_api_v1_bundles__revision_id__exports_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/bundle-exports/{export_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Bundle Export Status */
        get: operations["bundle_export_status_api_v1_bundle_exports__export_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/bundle-exports/{export_id}/content": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Bundle Export Content */
        get: operations["bundle_export_content_api_v1_bundle_exports__export_id__content_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/bundle-exports/{export_id}/content/metadata": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Bundle Export Metadata */
        get: operations["bundle_export_metadata_api_v1_bundle_exports__export_id__content_metadata_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/bundles/{revision_id}/grants": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Bundle Grant */
        post: operations["bundle_grant_api_v1_bundles__revision_id__grants_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/bundle-grants/{grant_id}/revoke": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Bundle Revoke */
        post: operations["bundle_revoke_api_v1_bundle_grants__grant_id__revoke_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/bundle-imports": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Bundle Import */
        post: operations["bundle_import_api_v1_bundle_imports_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/bundle-imports/{import_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Bundle Import Get */
        get: operations["bundle_import_get_api_v1_bundle_imports__import_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/bundle-imports/{import_id}/manifest": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Bundle Import Manifest */
        get: operations["bundle_import_manifest_api_v1_bundle_imports__import_id__manifest_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/bundle-imports/{import_id}/manifest/metadata": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Bundle Import Manifest Metadata */
        get: operations["bundle_import_manifest_metadata_api_v1_bundle_imports__import_id__manifest_metadata_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/bundle-imports/{import_id}/artifacts/{artifact_id}/content": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Bundle Import Content */
        get: operations["bundle_import_content_api_v1_bundle_imports__import_id__artifacts__artifact_id__content_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/bundle-imports/{import_id}/artifacts/{artifact_id}/content/metadata": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Bundle Import Artifact Metadata */
        get: operations["bundle_import_artifact_metadata_api_v1_bundle_imports__import_id__artifacts__artifact_id__content_metadata_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/bundle-imports/{import_id}/exports": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Bundle Import Export */
        post: operations["bundle_import_export_api_v1_bundle_imports__import_id__exports_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/local-copy-input-scopes/preview": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Local Copy Scope Preview */
        post: operations["local_copy_scope_preview_api_v1_local_copy_input_scopes_preview_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/local-copy-input-scopes/install": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Local Copy Scope Install */
        post: operations["local_copy_scope_install_api_v1_local_copy_input_scopes_install_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/local-copy-input-scopes/select": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Local Copy Scope Select */
        post: operations["local_copy_scope_select_api_v1_local_copy_input_scopes_select_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/local-copy-input-scopes/revoke": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Local Copy Scope Revoke */
        post: operations["local_copy_scope_revoke_api_v1_local_copy_input_scopes_revoke_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/local-copy-input-scopes/{scope_id}/revisions/{revision}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Local Copy Scope Get */
        get: operations["local_copy_scope_get_api_v1_local_copy_input_scopes__scope_id__revisions__revision__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/local-copy-input-scopes/bind-request": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Local Copy Scope Bind */
        post: operations["local_copy_scope_bind_api_v1_local_copy_input_scopes_bind_request_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AlignmentApplicability */
        AlignmentApplicability: {
            /** Languages */
            languages: string[];
            /** Input Media Types */
            input_media_types: string[];
            /** Transformations */
            transformations: string[];
            /** Maximum Duration Us */
            maximum_duration_us: number;
            /**
             * Units
             * @enum {string}
             */
            units: "utterance" | "word";
        };
        /** AlignmentExecutionIdentity */
        AlignmentExecutionIdentity: {
            /** Method Id */
            method_id: string;
            /** Tool */
            tool: string;
            /** Tool Version */
            tool_version: string;
            /** Model Id */
            model_id: string;
            /** Model File Sha256 */
            model_file_sha256: {
                [key: string]: string;
            };
            /** Resource Manifest Sha256 */
            resource_manifest_sha256: string;
            /** Configuration Sha256 */
            configuration_sha256: string;
            /** Compute Type */
            compute_type: string;
            /** Device */
            device: string;
            /** Operating System */
            operating_system: string;
            /** Architecture */
            architecture: string;
        };
        /** ApprovalRef */
        ApprovalRef: {
            /** Run Id */
            run_id: string;
            /** Idempotency Key */
            idempotency_key: string;
            /** Target Revision Id */
            target_revision_id: string;
            /** Decision Sha256 */
            decision_sha256: string;
        };
        /** ArtifactSpec */
        ArtifactSpec: {
            /** Duration Us */
            duration_us?: number | null;
            /** Width */
            width?: number | null;
            /** Height */
            height?: number | null;
            audio_clock?: components["schemas"]["AudioClock"] | null;
        };
        /** AssetCandidate */
        AssetCandidate: {
            /** Staging Id */
            staging_id: string;
            /** Sha256 */
            sha256: string;
            /** Size */
            size: number;
            /** Media Type */
            media_type: string;
            /** Source */
            source: string;
            /** Rights */
            rights: string;
        };
        /** AssetContentLocator */
        AssetContentLocator: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "asset";
            /** Asset Id */
            asset_id: string;
        };
        /** AssetRecord */
        AssetRecord: {
            /** Asset Id */
            asset_id: string;
            /** Sha256 */
            sha256: string;
            /** Size */
            size: number;
            /** Media Type */
            media_type: string;
            /** Source */
            source: string;
            /** Rights */
            rights: string;
            probe: components["schemas"]["MediaProbe"];
        };
        /** AudioClock */
        AudioClock: {
            /** Sample Rate */
            sample_rate: number;
            /** Decoded Sample Count */
            decoded_sample_count: number;
            /**
             * Stream Index
             * @default 0
             */
            stream_index: number;
            /** Timebase Num */
            timebase_num?: number | null;
            /** Timebase Den */
            timebase_den?: number | null;
            /** Origin Pts */
            origin_pts?: number | null;
        };
        /** AudioMappingPiece */
        AudioMappingPiece: {
            /** Piece Id */
            piece_id: string;
            source_track: components["schemas"]["AudioTrackRef"];
            source_range: components["schemas"]["MediaRange"];
            timeline_range: components["schemas"]["MediaRange"];
            /**
             * Playback Rate Num
             * @default 1
             */
            playback_rate_num: number;
            /**
             * Playback Rate Den
             * @default 1
             */
            playback_rate_den: number;
            /** Source Sample Start */
            source_sample_start?: number | null;
            /** Source Sample End */
            source_sample_end?: number | null;
            /** Source Pts Start */
            source_pts_start?: number | null;
            /** Source Pts End */
            source_pts_end?: number | null;
            /** Source Timebase Num */
            source_timebase_num?: number | null;
            /** Source Timebase Den */
            source_timebase_den?: number | null;
            /**
             * Transformation
             * @enum {string}
             */
            transformation: "crop" | "place" | "resample" | "time_stretch" | "encode";
            /**
             * Rounding Policy
             * @default half_up_us
             * @constant
             */
            rounding_policy: "half_up_us";
            /**
             * Start Rounding Error Us
             * @default 0
             */
            start_rounding_error_us: string;
            /**
             * End Rounding Error Us
             * @default 0
             */
            end_rounding_error_us: string;
            /** Method Ref */
            method_ref: string;
        };
        /** AudioTimelineMapping */
        AudioTimelineMapping: {
            /** Mapping Revision Id */
            mapping_revision_id: string;
            /** Target Video Asset Id */
            target_video_asset_id: string;
            target_track: components["schemas"]["AudioTrackRef"];
            /**
             * Target Coordinate
             * @default work_timeline
             * @constant
             */
            target_coordinate: "work_timeline";
            /** Timeline Duration Us */
            timeline_duration_us: number;
            /** Pieces */
            pieces: components["schemas"]["AudioMappingPiece"][];
            /** Encoding Origin Offset Us */
            encoding_origin_offset_us?: number | null;
            /** Method Ref */
            method_ref: string;
            /** Content Sha256 */
            content_sha256: string;
        };
        /** AudioTrackRef */
        AudioTrackRef: {
            /** Asset Id */
            asset_id: string;
            /** Sha256 */
            sha256: string;
            /** Stream Index */
            stream_index: number;
            /**
             * Kind
             * @enum {string}
             */
            kind: "narration" | "mix_master" | "video_encoded" | "dialogue" | "music" | "effects";
            /** Intrinsic Duration Us */
            intrinsic_duration_us: number;
            clock: components["schemas"]["AudioClock"];
            /** Method Ref */
            method_ref: string;
        };
        /** Automation */
        Automation: {
            /**
             * Mode
             * @default interactive
             * @enum {string}
             */
            mode: "interactive" | "unattended";
            /**
             * Max Revision Cycles
             * @default 2
             */
            max_revision_cycles: number;
        };
        /** BindLocalCopyInputScope */
        BindLocalCopyInputScope: {
            scope_ref: components["schemas"]["LocalCopyInputScopeRef"];
            /** Production Id */
            production_id: string;
            /** Run Id */
            run_id: string;
            /** Request Revision Id */
            request_revision_id: string;
            /** Request Sha256 */
            request_sha256: string;
        };
        /** BundleArtifact */
        BundleArtifact: {
            /** Artifact Id */
            artifact_id: string;
            /** Asset Id */
            asset_id?: string | null;
            /** Material Id */
            material_id?: string | null;
            /** Sha256 */
            sha256: string;
            /** Size */
            size: number;
            /** Media Type */
            media_type: string;
            /** Relative Path */
            relative_path: string;
            /** Roles */
            roles: string[];
            /**
             * Dependency Artifact Ids
             * @default []
             */
            dependency_artifact_ids: string[];
            /** Method Ref */
            method_ref: string;
            /** Rights Ref */
            rights_ref: string;
            spec?: components["schemas"]["ArtifactSpec"];
        };
        /** BundleArtifactContentLocator */
        BundleArtifactContentLocator: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "bundle_artifact";
            bundle_ref: components["schemas"]["BundleRef"];
            /** Artifact Id */
            artifact_id: string;
        };
        /** BundleExportAccepted */
        BundleExportAccepted: {
            /** Export Id */
            export_id: string;
            bundle_ref: components["schemas"]["BundleRef"];
            /**
             * Delivery Profile
             * @enum {string}
             */
            delivery_profile: "full" | "projection";
            /**
             * Status
             * @enum {string}
             */
            status: "queued" | "building" | "ready" | "failed";
            /** Input Sha256 */
            input_sha256: string;
            /** Status Path */
            status_path: string;
            /** Archive Sha256 */
            archive_sha256?: string | null;
            /** Size */
            size?: number | null;
            /** Content Path */
            content_path?: string | null;
            /** Error Code */
            error_code?: string | null;
        };
        /** BundleExportRequest */
        BundleExportRequest: {
            /**
             * Delivery Profile
             * @default full
             * @enum {string}
             */
            delivery_profile: "full" | "projection";
            /**
             * Format
             * @default zip
             * @constant
             */
            format: "zip";
            /**
             * Artifact Ids
             * @default []
             */
            artifact_ids: string[];
            /**
             * Purpose
             * @default export
             * @enum {string}
             */
            purpose: "playback" | "export" | "rag_index" | "derivative" | "commercial_use" | "standalone_audio" | "redistribution";
        };
        /** BundleGrantRequest */
        BundleGrantRequest: {
            /** Recipient Id */
            recipient_id: string;
            /** Artifact Ids */
            artifact_ids: string[];
            /**
             * Allow Semantic Text
             * @default false
             */
            allow_semantic_text: boolean;
            /** Purposes */
            purposes: ("playback" | "export" | "rag_index" | "derivative" | "commercial_use" | "standalone_audio" | "redistribution")[];
            /** Expires At Us */
            expires_at_us: number;
        };
        /** BundleImportReceipt */
        BundleImportReceipt: {
            /** Import Id */
            import_id: string;
            /** Local Instance Id */
            local_instance_id: string;
            /** Project Id */
            project_id: string;
            origin_bundle_ref: components["schemas"]["BundleRef"];
            /**
             * Status
             * @default ready
             * @constant
             */
            status: "ready";
            /** Status Path */
            status_path: string;
            /** Manifest Path */
            manifest_path: string;
            /**
             * Index State
             * @default not_built
             * @enum {string}
             */
            index_state: "not_built" | "ready" | "failed";
        };
        /** BundleImportReceiptV03 */
        BundleImportReceiptV03: {
            /** Import Id */
            import_id: string;
            /** Local Instance Id */
            local_instance_id: string;
            /** Project Id */
            project_id: string;
            origin_bundle_ref: components["schemas"]["BundleRef"];
            /**
             * Status
             * @default ready
             * @constant
             */
            status: "ready";
            /** Status Path */
            status_path: string;
            /** Manifest Path */
            manifest_path: string;
            /**
             * Index State
             * @default not_built
             * @enum {string}
             */
            index_state: "not_built" | "ready" | "failed";
            /**
             * Evidence Trust Status
             * @default origin_snapshot_only
             * @enum {string}
             */
            evidence_trust_status: "origin_snapshot_only" | "locally_recognized_current";
            /**
             * Execution Qualification Inherited
             * @default false
             * @constant
             */
            execution_qualification_inherited: false;
        };
        /** BundleImportRequest */
        BundleImportRequest: {
            /** Staging Id */
            staging_id: string;
            /** Archive Sha256 */
            archive_sha256: string;
            expected_origin_ref: components["schemas"]["BundleRef"];
            /** Project Id */
            project_id: string;
        };
        /** BundleManifest */
        BundleManifest: {
            /**
             * Schema Version
             * @default 0.2.0-candidate
             * @constant
             */
            schema_version: "0.2.0-candidate";
            /**
             * Bundle Format Version
             * @default 1
             * @constant
             */
            bundle_format_version: 1;
            /** Instance Id */
            instance_id: string;
            /** Bundle Id */
            bundle_id: string;
            /** Bundle Revision Id */
            bundle_revision_id: string;
            /** Project Id */
            project_id: string;
            /** Production Id */
            production_id: string;
            /** Run Id */
            run_id: string;
            /** Request Revision Id */
            request_revision_id: string;
            /** Request Sha256 */
            request_sha256: string;
            /** Workflow Version */
            workflow_version: string;
            /** Created At Us */
            created_at_us: number;
            /** Timeline Duration Us */
            timeline_duration_us: number;
            /** Creative Revision Refs */
            creative_revision_refs: components["schemas"]["RevisionRef"][];
            /** Approval Refs */
            approval_refs: components["schemas"]["ApprovalRef"][];
            /**
             * Feedback Revision Refs
             * @default []
             */
            feedback_revision_refs: components["schemas"]["RevisionRef"][];
            /** Source Refs */
            source_refs: components["schemas"]["BundleSourceRef"][];
            /** Requested Outputs */
            requested_outputs: ("video" | "narration_audio" | "mixed_audio" | "approved_script" | "actual_transcript" | "subtitles" | "semantic_manifest" | "rag_chunks")[];
            /** Outputs */
            outputs: components["schemas"]["BundleOutput"][];
            /** Artifacts */
            artifacts: components["schemas"]["BundleArtifact"][];
            /** Audio Mappings */
            audio_mappings: components["schemas"]["AudioTimelineMapping"][];
            /** Methods */
            methods: components["schemas"]["MethodEvidence"][];
            /** Rights */
            rights: components["schemas"]["RightsSnapshot"][];
            quality_ref: components["schemas"]["RevisionRef"];
        };
        /** BundleManifestContentLocator */
        BundleManifestContentLocator: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "bundle_manifest";
            bundle_ref: components["schemas"]["BundleRef"];
        };
        /** BundleManifestV03 */
        BundleManifestV03: {
            /**
             * Schema Version
             * @constant
             */
            schema_version: "0.3.0-candidate";
            /**
             * Bundle Format Version
             * @default 1
             * @constant
             */
            bundle_format_version: 1;
            /** Instance Id */
            instance_id: string;
            /** Bundle Id */
            bundle_id: string;
            /** Bundle Revision Id */
            bundle_revision_id: string;
            /** Project Id */
            project_id: string;
            /** Production Id */
            production_id: string;
            /** Run Id */
            run_id: string;
            /** Request Revision Id */
            request_revision_id: string;
            /** Request Sha256 */
            request_sha256: string;
            /** Workflow Version */
            workflow_version: string;
            /** Created At Us */
            created_at_us: number;
            /** Timeline Duration Us */
            timeline_duration_us: number;
            /** Creative Revision Refs */
            creative_revision_refs: components["schemas"]["RevisionRef"][];
            /** Approval Refs */
            approval_refs: components["schemas"]["ApprovalRef"][];
            /**
             * Feedback Revision Refs
             * @default []
             */
            feedback_revision_refs: components["schemas"]["RevisionRef"][];
            /** Source Refs */
            source_refs: components["schemas"]["BundleSourceRef"][];
            /** Requested Outputs */
            requested_outputs: ("video" | "narration_audio" | "mixed_audio" | "approved_script" | "actual_transcript" | "subtitles" | "semantic_manifest" | "rag_chunks")[];
            /** Outputs */
            outputs: components["schemas"]["BundleOutput"][];
            /** Artifacts */
            artifacts: components["schemas"]["BundleArtifact"][];
            /** Audio Mappings */
            audio_mappings: components["schemas"]["AudioTimelineMapping"][];
            /** Methods */
            methods: components["schemas"]["MethodEvidence"][];
            /** Rights */
            rights: components["schemas"]["RightsSnapshot"][];
            quality_ref: components["schemas"]["RevisionRef"];
            evidence_policy_revision_ref: components["schemas"]["EvidencePolicyRevisionRef"];
            qualification_ref: components["schemas"]["MethodQualificationRef"];
            /**
             * Benchmark Binding
             * @enum {string}
             */
            benchmark_binding: "embedded_full_report" | "provenance_reference";
            /** Benchmark Document Artifact Id */
            benchmark_document_artifact_id: string;
            /** Policy Document Artifact Id */
            policy_document_artifact_id: string;
            /** Qualification Document Artifact Id */
            qualification_document_artifact_id: string;
            /** Work Validation Document Artifact Id */
            work_validation_document_artifact_id: string;
        };
        /** BundleOutput */
        BundleOutput: {
            /**
             * Role
             * @enum {string}
             */
            role: "video" | "narration_audio" | "mixed_audio" | "approved_script" | "actual_transcript" | "subtitles" | "semantic_manifest" | "rag_chunks";
            /** Artifact Ids */
            artifact_ids: string[];
            /**
             * Status
             * @default present
             * @constant
             */
            status: "present";
            /**
             * Provenance Revision Refs
             * @default []
             */
            provenance_revision_refs: components["schemas"]["RevisionRef"][];
        };
        /** BundleRef */
        BundleRef: {
            /** Instance Id */
            instance_id: string;
            /** Bundle Id */
            bundle_id: string;
            /** Bundle Revision Id */
            bundle_revision_id: string;
            /**
             * Schema Version
             * @default 0.2.0-candidate
             */
            schema_version: string;
            /** Manifest Sha256 */
            manifest_sha256: string;
        };
        /** BundleReferenceGrant */
        BundleReferenceGrant: {
            /** Grant Id */
            grant_id: string;
            bundle_ref: components["schemas"]["BundleRef"];
            /** Project Id */
            project_id: string;
            /** Recipient Id */
            recipient_id: string;
            /** Artifact Ids */
            artifact_ids: string[];
            /** Allow Semantic Text */
            allow_semantic_text: boolean;
            /** Purposes */
            purposes: ("playback" | "export" | "rag_index" | "derivative" | "commercial_use" | "standalone_audio" | "redistribution")[];
            /** Created At Us */
            created_at_us: number;
            /** Expires At Us */
            expires_at_us: number;
            /** Revoked At Us */
            revoked_at_us?: number | null;
        };
        /** BundleSourceRef */
        BundleSourceRef: {
            /** System */
            system: string;
            /** Namespace */
            namespace: string;
            /** Article Id */
            article_id?: string | null;
            /** Article Revision */
            article_revision?: string | null;
            /** Topic Id */
            topic_id?: string | null;
            /** Topic Revision */
            topic_revision?: string | null;
            /**
             * Paragraph Ids
             * @default []
             */
            paragraph_ids: string[];
            /**
             * Fact Refs
             * @default []
             */
            fact_refs: components["schemas"]["SourceFactRef"][];
            /**
             * Input Asset Ids
             * @default []
             */
            input_asset_ids: string[];
            /**
             * Binding Kind
             * @enum {string}
             */
            binding_kind: "provided_input" | "researched_source";
            /**
             * Evidence Refs
             * @default []
             */
            evidence_refs: string[];
            /** Retrieved At Us */
            retrieved_at_us?: number | null;
            /** Valid Until Us */
            valid_until_us?: number | null;
        };
        /** ContentRequestPurpose */
        ContentRequestPurpose: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "content_request";
            /**
             * Purpose
             * @enum {string}
             */
            purpose: "playback" | "export" | "rag_index" | "derivative" | "commercial_use" | "standalone_audio" | "redistribution";
        };
        /** CreativeBriefInput */
        CreativeBriefInput: {
            /**
             * Language
             * @default zh-CN
             */
            language: string;
            /** Target Duration Us */
            target_duration_us?: number | null;
            /**
             * Aspect Ratio
             * @default 9:16
             * @enum {string}
             */
            aspect_ratio: "9:16" | "16:9";
            /** Guidance */
            guidance?: string | null;
        };
        /** CreativeRevision */
        CreativeRevision: {
            /** Revision Id */
            revision_id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "insight" | "brief" | "plan" | "script" | "storyboard" | "quality";
            /** Parent Revision Id */
            parent_revision_id?: string | null;
            /**
             * Input Revision Refs
             * @default []
             */
            input_revision_refs: string[];
            body: components["schemas"]["JsonValue"];
        };
        /** DailyProjectAuthorizationRef */
        DailyProjectAuthorizationRef: {
            /** Authorization Id */
            authorization_id: string;
            /** Revision */
            revision: number;
            /** Content Sha256 */
            content_sha256: string;
        };
        /**
         * DeliveryContentMetadata
         * @description A current authorized fact snapshot, never a transferable access ticket.
         */
        DeliveryContentMetadata: {
            /**
             * Schema Kind
             * @default delivery_content_metadata
             * @constant
             */
            schema_kind: "delivery_content_metadata";
            /**
             * Schema Version
             * @default 0.1.0-candidate
             * @constant
             */
            schema_version: "0.1.0-candidate";
            /** Local Instance Id */
            local_instance_id: string;
            /** Locator */
            locator: components["schemas"]["AssetContentLocator"] | components["schemas"]["BundleManifestContentLocator"] | components["schemas"]["BundleArtifactContentLocator"] | components["schemas"]["ExportArchiveContentLocator"] | components["schemas"]["ImportManifestContentLocator"] | components["schemas"]["ImportArtifactContentLocator"];
            /**
             * State
             * @default ready
             * @constant
             */
            state: "ready";
            /** Sha256 */
            sha256: string;
            /** Size */
            size: number;
            /** Media Type */
            media_type: string;
            /** Purpose Binding */
            purpose_binding: components["schemas"]["InstallationOwnerPurpose"] | components["schemas"]["ContentRequestPurpose"] | components["schemas"]["ExportJournalPurpose"];
            /** Checked At Us */
            checked_at_us: number;
            /** Authorization Expires At Us */
            authorization_expires_at_us: number | null;
        };
        /** DeliveryRequirements */
        DeliveryRequirements: {
            /**
             * Alignment Requirement
             * @default utterance_verified
             * @enum {string}
             */
            alignment_requirement: "utterance_verified" | "word_verified";
            /**
             * Allowed Degradations
             * @default []
             */
            allowed_degradations: "word_estimate_with_declared_gap"[];
        };
        /** DeliveryRequirementsV03 */
        DeliveryRequirementsV03: {
            /**
             * Alignment Requirement
             * @enum {string}
             */
            alignment_requirement: "utterance_verified" | "word_verified";
            /**
             * Allowed Degradations
             * @default []
             */
            allowed_degradations: "word_estimate_with_declared_gap"[];
            /**
             * Alignment Evidence Policy
             * @enum {string}
             */
            alignment_evidence_policy: "strict_reference_v1" | "qualified_method_runtime_v1";
            evidence_policy_revision_ref: components["schemas"]["EvidencePolicyRevisionRef"];
        };
        /** ErrorEnvelope */
        ErrorEnvelope: {
            /** Code */
            code: string;
            /** Message */
            message: string;
            /**
             * Retryability
             * @enum {string}
             */
            retryability: "never" | "safe" | "reconcile";
            /** Request Id */
            request_id: string;
        };
        /** EventEnvelope */
        EventEnvelope: {
            /** Event Id */
            event_id: string;
            /** Sequence */
            sequence: number;
            /** Production Id */
            production_id: string;
            /** Run Id */
            run_id: string;
            /** Event Type */
            event_type: string;
            /** Occurred At Us */
            occurred_at_us: number;
            status: components["schemas"]["RunStatus"];
            /** Entity Revision Id */
            entity_revision_id?: string | null;
        };
        /** EvidencePolicyRevisionRef */
        EvidencePolicyRevisionRef: {
            /** Policy Id */
            policy_id: string;
            /** Revision */
            revision: number;
            /** Content Sha256 */
            content_sha256: string;
        };
        /** EvidenceReportRef */
        EvidenceReportRef: {
            /** Report Id */
            report_id: string;
            /**
             * Schema Version
             * @constant
             */
            schema_version: "0.3.0-candidate";
            /**
             * Evaluation Scope
             * @enum {string}
             */
            evaluation_scope: "capability_benchmark" | "work_runtime_validation" | "per_work_reference_measurement";
            /** Content Sha256 */
            content_sha256: string;
        };
        /** ExecutionPolicy */
        "ExecutionPolicy-Input": {
            /**
             * Version
             * @default local-default-v1
             */
            version: string;
            /**
             * Allowed Provider Routes
             * @default []
             */
            allowed_provider_routes: string[];
            /**
             * External Transfer Allowed
             * @default false
             */
            external_transfer_allowed: boolean;
            max_cost?: components["schemas"]["Money-Input"];
            /** Budget Group Id */
            budget_group_id?: string | null;
        };
        /** ExecutionPolicy */
        "ExecutionPolicy-Output": {
            /**
             * Version
             * @default local-default-v1
             */
            version: string;
            /**
             * Allowed Provider Routes
             * @default []
             */
            allowed_provider_routes: string[];
            /**
             * External Transfer Allowed
             * @default false
             */
            external_transfer_allowed: boolean;
            max_cost?: components["schemas"]["Money-Output"];
            /** Budget Group Id */
            budget_group_id?: string | null;
        };
        /** ExportArchiveContentLocator */
        ExportArchiveContentLocator: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "export_archive";
            /** Export Id */
            export_id: string;
            /** Source */
            source: components["schemas"]["LocalBundleExportSource"] | components["schemas"]["LocalImportExportSource"];
            /** Input Sha256 */
            input_sha256: string;
            /**
             * Delivery Profile
             * @enum {string}
             */
            delivery_profile: "full" | "projection";
            /** Artifact Ids */
            artifact_ids: string[];
        };
        /** ExportJournalPurpose */
        ExportJournalPurpose: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "export_journal";
            /**
             * Purpose
             * @enum {string}
             */
            purpose: "playback" | "export" | "rag_index" | "derivative" | "commercial_use" | "standalone_audio" | "redistribution";
        };
        /** FeedbackRevision */
        FeedbackRevision: {
            /** Feedback Id */
            feedback_id: string;
            /** Previous Run Id */
            previous_run_id: string;
            /** New Run Id */
            new_run_id: string;
            /** Target Revision Id */
            target_revision_id: string;
            /** Instruction Text */
            instruction_text: string;
            /** Preserved Constraints */
            preserved_constraints: string[];
        };
        /** FrameEvidenceRef */
        FrameEvidenceRef: {
            /** Video Asset Id */
            video_asset_id: string;
            /** Video Sha256 */
            video_sha256: string;
            /** At Us */
            at_us: number;
            /** Actual Pts */
            actual_pts?: number | null;
            /** Timebase Num */
            timebase_num?: number | null;
            /** Timebase Den */
            timebase_den?: number | null;
            /** Decoded Frame Sha256 */
            decoded_frame_sha256: string;
            /** Pixel Format */
            pixel_format: string;
            /** Width */
            width: number;
            /** Height */
            height: number;
            /** Decoder Method Ref */
            decoder_method_ref: string;
            /** Frame Artifact Id */
            frame_artifact_id?: string | null;
            /**
             * Limitations
             * @default []
             */
            limitations: string[];
        };
        /** ImportArtifactContentLocator */
        ImportArtifactContentLocator: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "import_artifact";
            /** Import Id */
            import_id: string;
            origin_bundle_ref: components["schemas"]["BundleRef"];
            /** Artifact Id */
            artifact_id: string;
        };
        /** ImportManifestContentLocator */
        ImportManifestContentLocator: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "import_manifest";
            /** Import Id */
            import_id: string;
            origin_bundle_ref: components["schemas"]["BundleRef"];
        };
        /** InstallLocalCopyInputScope */
        InstallLocalCopyInputScope: {
            scope: components["schemas"]["LocalCopyInputScope-Input"];
            previous_ref?: components["schemas"]["LocalCopyInputScopeRef"] | null;
        };
        /** InstallationOwnerPurpose */
        InstallationOwnerPurpose: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "installation_owner";
        };
        /** InstanceHealth */
        InstanceHealth: {
            /** Instance Id */
            instance_id: string;
            /**
             * Schema Version
             * @default 0.2.0-candidate
             */
            schema_version: string;
            /** Engine Version */
            engine_version: string;
            /**
             * Mode
             * @default local
             * @constant
             */
            mode: "local";
            /** Worker Connected */
            worker_connected: boolean;
        };
        JsonValue: unknown;
        /** LocalBundleExportSource */
        LocalBundleExportSource: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "local_bundle";
            bundle_ref: components["schemas"]["BundleRef"];
        };
        /** LocalCopyAssetLocator */
        LocalCopyAssetLocator: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "asset";
            /** Asset Id */
            asset_id: string;
        };
        /** LocalCopyDependencyEdge */
        "LocalCopyDependencyEdge-Input": {
            source: components["schemas"]["LocalCopyMemberRef"];
            target: components["schemas"]["LocalCopyMemberRef"];
            /**
             * Kind
             * @enum {string}
             */
            kind: "artifact_dependency" | "license_dependency" | "authorization_proof" | "correction_origin";
        };
        /** LocalCopyDependencyEdge */
        "LocalCopyDependencyEdge-Output": {
            source: components["schemas"]["LocalCopyMemberRef"];
            target: components["schemas"]["LocalCopyMemberRef"];
            /**
             * Kind
             * @enum {string}
             */
            kind: "artifact_dependency" | "license_dependency" | "authorization_proof" | "correction_origin";
        };
        /** LocalCopyInputActionReceipt */
        LocalCopyInputActionReceipt: {
            /**
             * Kind
             * @default local_copy_input_action
             * @constant
             */
            kind: "local_copy_input_action";
            /**
             * Version
             * @default 0.1.0-candidate
             * @constant
             */
            version: "0.1.0-candidate";
            /** Action Id */
            action_id: string;
            /** Instance Id */
            instance_id: string;
            /** Administrator Id */
            administrator_id: string;
            /** Authentication Binding Id */
            authentication_binding_id: string;
            /**
             * Authentication Source
             * @enum {string}
             */
            authentication_source: "native_owner_session" | "headless_administrator";
            /** Owner Subject */
            owner_subject: string;
            /** Destination Project Id */
            destination_project_id: string;
            /**
             * Action
             * @enum {string}
             */
            action: "create" | "replace" | "select" | "revoke" | "bind_request";
            scope_ref: components["schemas"]["LocalCopyInputScopeRef"];
            /** Idempotency Key */
            idempotency_key: string;
            /** Request Sha256 */
            request_sha256: string;
            /** Authorized At Us */
            authorized_at_us: number;
            /** Registry Revision */
            registry_revision: number;
            /** Reason */
            reason?: string | null;
            target?: components["schemas"]["BindLocalCopyInputScope"] | null;
        };
        /** LocalCopyInputScope */
        "LocalCopyInputScope-Input": {
            /**
             * Kind
             * @default local_copy_input_scope
             * @constant
             */
            kind: "local_copy_input_scope";
            /**
             * Version
             * @default 0.1.0-candidate
             * @constant
             */
            version: "0.1.0-candidate";
            /** Scope Id */
            scope_id: string;
            /** Revision */
            revision: number;
            /** Instance Id */
            instance_id: string;
            /** Owner Subject */
            owner_subject: string;
            /** Destination Project Id */
            destination_project_id: string;
            /** Executing Principal Ids */
            executing_principal_ids: string[];
            /** Registration Sha256 */
            registration_sha256: string;
            policy_ref: components["schemas"]["ProductionPolicyRef"];
            /** Valid From Us */
            valid_from_us: number;
            /** Expires At Us */
            expires_at_us: number;
            source_set: components["schemas"]["LocalCopySourceSet-Input"];
            /** Source Set Sha256 */
            source_set_sha256: string;
        };
        /** LocalCopyInputScope */
        "LocalCopyInputScope-Output": {
            /**
             * Kind
             * @default local_copy_input_scope
             * @constant
             */
            kind: "local_copy_input_scope";
            /**
             * Version
             * @default 0.1.0-candidate
             * @constant
             */
            version: "0.1.0-candidate";
            /** Scope Id */
            scope_id: string;
            /** Revision */
            revision: number;
            /** Instance Id */
            instance_id: string;
            /** Owner Subject */
            owner_subject: string;
            /** Destination Project Id */
            destination_project_id: string;
            /** Executing Principal Ids */
            executing_principal_ids: string[];
            /** Registration Sha256 */
            registration_sha256: string;
            policy_ref: components["schemas"]["ProductionPolicyRef"];
            /** Valid From Us */
            valid_from_us: number;
            /** Expires At Us */
            expires_at_us: number;
            source_set: components["schemas"]["LocalCopySourceSet-Output"];
            /** Source Set Sha256 */
            source_set_sha256: string;
        };
        /** LocalCopyInputScopeRecord */
        LocalCopyInputScopeRecord: {
            scope_ref: components["schemas"]["LocalCopyInputScopeRef"];
            scope: components["schemas"]["LocalCopyInputScope-Output"];
            installation_action: components["schemas"]["LocalCopyInputActionReceipt"];
            /** Current */
            current: boolean;
            /** Revoked */
            revoked: boolean;
            revocation_action?: components["schemas"]["LocalCopyInputActionReceipt"] | null;
        };
        /** LocalCopyInputScopeRef */
        LocalCopyInputScopeRef: {
            /** Scope Id */
            scope_id: string;
            /** Revision */
            revision: number;
            /** Content Sha256 */
            content_sha256: string;
        };
        /** LocalCopyMaterialLocator */
        LocalCopyMaterialLocator: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "material";
            /** Material Id */
            material_id: string;
        };
        /** LocalCopyMemberRef */
        LocalCopyMemberRef: {
            bundle_ref: components["schemas"]["BundleRef"];
            /** Artifact Id */
            artifact_id: string;
        };
        /** LocalCopyRequestedRoot */
        LocalCopyRequestedRoot: {
            bundle_ref: components["schemas"]["BundleRef"];
            /** Artifact Id */
            artifact_id: string;
            /**
             * Handling
             * @enum {string}
             */
            handling: "verify_only" | "copy_into_delivery";
            /** Required Uses */
            required_uses: ("playback" | "export" | "rag_index" | "derivative" | "commercial_use" | "standalone_audio" | "redistribution")[];
        };
        /** LocalCopySourceItem */
        LocalCopySourceItem: {
            bundle_ref: components["schemas"]["BundleRef"];
            /** Artifact Id */
            artifact_id: string;
            /**
             * Kind
             * @default local_bundle_artifact
             * @constant
             */
            kind: "local_bundle_artifact";
            /** Source Instance Id */
            source_instance_id: string;
            /** Source Project Id */
            source_project_id: string;
            /** Source Production Id */
            source_production_id: string;
            /** Locator */
            locator: components["schemas"]["LocalCopyMaterialLocator"] | components["schemas"]["LocalCopyAssetLocator"];
            /** Sha256 */
            sha256: string;
            /** Size */
            size: number;
            /** Media Type */
            media_type: string;
            /** Roles */
            roles: string[];
            /** Rights Id */
            rights_id: string;
            /** Rights Sha256 */
            rights_sha256: string;
            /**
             * Handling
             * @enum {string}
             */
            handling: "verify_only" | "copy_into_delivery";
            /** Required Uses */
            required_uses: ("playback" | "export" | "rag_index" | "derivative" | "commercial_use" | "standalone_audio" | "redistribution")[];
        };
        /**
         * LocalCopySourceSet
         * @description Ordered full source identities; no include-future-dependencies permission.
         */
        "LocalCopySourceSet-Input": {
            /** Items */
            items: components["schemas"]["LocalCopySourceItem"][];
            /** Roots */
            roots: components["schemas"]["LocalCopyMemberRef"][];
            /** Edges */
            edges: components["schemas"]["LocalCopyDependencyEdge-Input"][];
        };
        /**
         * LocalCopySourceSet
         * @description Ordered full source identities; no include-future-dependencies permission.
         */
        "LocalCopySourceSet-Output": {
            /** Items */
            items: components["schemas"]["LocalCopySourceItem"][];
            /** Roots */
            roots: components["schemas"]["LocalCopyMemberRef"][];
            /** Edges */
            edges: components["schemas"]["LocalCopyDependencyEdge-Output"][];
        };
        /** LocalImportExportSource */
        LocalImportExportSource: {
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            kind: "local_import";
            /** Import Id */
            import_id: string;
            origin_bundle_ref: components["schemas"]["BundleRef"];
        };
        /** MediaProbe */
        MediaProbe: {
            /** Media Type */
            media_type: string;
            /** Duration Us */
            duration_us?: number | null;
            /**
             * Has Video
             * @default false
             */
            has_video: boolean;
            /**
             * Has Audio
             * @default false
             */
            has_audio: boolean;
            /** Width */
            width?: number | null;
            /** Height */
            height?: number | null;
            /** Tool Version */
            tool_version: string;
            /** Decoded */
            decoded: boolean;
        };
        /** MediaRange */
        MediaRange: {
            /** Start Us */
            start_us: number;
            /** End Us */
            end_us: number;
        };
        /** MethodEvidence */
        MethodEvidence: {
            /** Method Id */
            method_id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "observed" | "model_inference" | "user_provided" | "derived";
            /** Tool Name */
            tool_name: string;
            /** Tool Version */
            tool_version: string;
            /** Build Revision */
            build_revision?: string | null;
            /** Model Repository */
            model_repository?: string | null;
            /** Model Revision */
            model_revision?: string | null;
            /** Resource Manifest Sha256 */
            resource_manifest_sha256?: string | null;
            /**
             * Operation Ids
             * @default []
             */
            operation_ids: string[];
            /**
             * Input Artifact Ids
             * @default []
             */
            input_artifact_ids: string[];
            /** Config Sha256 */
            config_sha256: string;
            /**
             * Evidence Artifact Ids
             * @default []
             */
            evidence_artifact_ids: string[];
            /**
             * Limitations
             * @default []
             */
            limitations: string[];
        };
        /** MethodQualificationRef */
        MethodQualificationRef: {
            /** Qualification Id */
            qualification_id: string;
            /** Revision */
            revision: number;
            /** Profile Id */
            profile_id: string;
            /** Profile Revision */
            profile_revision: number;
            /** Profile Sha256 */
            profile_sha256: string;
            execution_identity: components["schemas"]["AlignmentExecutionIdentity"];
            applicability: components["schemas"]["AlignmentApplicability"];
            benchmark_report_ref: components["schemas"]["EvidenceReportRef"];
            /**
             * Criterion Version Ref
             * @constant
             */
            criterion_version_ref: "alignment-unit-max-p95-200ms-v1";
            /** Authority Ref */
            authority_ref: string;
            /** Issuer */
            issuer: string;
            /** Approval Refs */
            approval_refs: string[];
            /** Valid From Us */
            valid_from_us: number;
            /** Expires At Us */
            expires_at_us: number;
            /** Content Sha256 */
            content_sha256: string;
        };
        /** Money */
        "Money-Input": {
            /**
             * Currency
             * @default CNY
             * @constant
             */
            currency: "CNY";
            /** Amount */
            amount: number | string;
        };
        /** Money */
        "Money-Output": {
            /**
             * Currency
             * @default CNY
             * @constant
             */
            currency: "CNY";
            /** Amount */
            amount: string;
        };
        /** OperationSummary */
        OperationSummary: {
            /** Operation Id */
            operation_id: string;
            /** Status */
            status: string;
            /**
             * Cost Status
             * @enum {string}
             */
            cost_status: "unknown" | "known";
            actual_cost: components["schemas"]["Money-Output"] | null;
            /** Cost Evidence */
            cost_evidence: string;
            /** External Id */
            external_id: string | null;
        };
        /**
         * PreviewLocalCopyInputScope
         * @description Owner chooses finite roots; trusted service resolves their complete proof closure.
         */
        PreviewLocalCopyInputScope: {
            /** Scope Id */
            scope_id: string;
            /** Revision */
            revision: number;
            /** Instance Id */
            instance_id: string;
            /** Destination Project Id */
            destination_project_id: string;
            /** Executing Principal Ids */
            executing_principal_ids: string[];
            /** Registration Sha256 */
            registration_sha256: string;
            policy_ref: components["schemas"]["ProductionPolicyRef"];
            /** Valid From Us */
            valid_from_us: number;
            /** Expires At Us */
            expires_at_us: number;
            /** Roots */
            roots: components["schemas"]["LocalCopyRequestedRoot"][];
        };
        /** ProductionAccepted */
        ProductionAccepted: {
            /**
             * Schema Version
             * @default 0.2.0-candidate
             */
            schema_version: string;
            /** Instance Id */
            instance_id: string;
            /** Production Id */
            production_id: string;
            /** Run Id */
            run_id: string;
            /** Project Id */
            project_id: string;
            /** Request Revision Id */
            request_revision_id: string;
            status: components["schemas"]["RunStatus"];
            /** Status Path */
            status_path: string;
            /** Events Path */
            events_path: string;
        };
        /** ProductionCost */
        ProductionCost: {
            spent: components["schemas"]["Money-Output"];
            reserved: components["schemas"]["Money-Output"];
        };
        /** ProductionDetail */
        ProductionDetail: {
            /**
             * Schema Version
             * @default 0.2.0-candidate
             */
            schema_version: string;
            /** Instance Id */
            instance_id: string;
            /** Production Id */
            production_id: string;
            /** Run Id */
            run_id: string;
            /** Project Id */
            project_id: string;
            /** Request Revision Id */
            request_revision_id: string;
            status: components["schemas"]["RunStatus"];
            /** Status Path */
            status_path: string;
            /** Events Path */
            events_path: string;
            /** Request */
            request: components["schemas"]["ProductionRequest-Output"] | components["schemas"]["ProductionRequestV03-Output"];
            cost: components["schemas"]["ProductionCost"];
            /** Operations */
            operations: components["schemas"]["OperationSummary"][];
            /** Revision Cycles */
            revision_cycles: number;
            bundle_ref?: components["schemas"]["BundleRef"] | null;
        };
        /** ProductionInputs */
        ProductionInputs: {
            /**
             * Source Text
             * @default
             */
            source_text: string;
            /**
             * Asset Ids
             * @default []
             */
            asset_ids: string[];
        };
        /** ProductionPolicyRef */
        ProductionPolicyRef: {
            /** Policy Id */
            policy_id: string;
            /** Revision */
            revision: number;
            /** Content Sha256 */
            content_sha256: string;
        };
        /** ProductionRequest */
        "ProductionRequest-Input": {
            /** Request Format Version */
            request_format_version?: "0.2.0-candidate" | null;
            delivery_requirements?: components["schemas"]["DeliveryRequirements"] | null;
            /** Goal */
            goal: string;
            inputs?: components["schemas"]["ProductionInputs"];
            /** Project Id */
            project_id?: string | null;
            /**
             * Source Bindings
             * @default []
             */
            source_bindings: components["schemas"]["SourceBinding"][];
            brief?: components["schemas"]["CreativeBriefInput"] | null;
            automation?: components["schemas"]["Automation"];
            policy?: components["schemas"]["ExecutionPolicy-Input"];
            /**
             * Outputs
             * @default [
             *       "video",
             *       "narration_audio",
             *       "mixed_audio",
             *       "approved_script",
             *       "actual_transcript",
             *       "subtitles",
             *       "semantic_manifest",
             *       "rag_chunks"
             *     ]
             */
            outputs: ("video" | "narration_audio" | "mixed_audio" | "approved_script" | "actual_transcript" | "subtitles" | "semantic_manifest" | "rag_chunks")[];
            /**
             * Delivery
             * @default reference
             * @enum {string}
             */
            delivery: "reference" | "export";
        };
        /** ProductionRequest */
        "ProductionRequest-Output": {
            /** Request Format Version */
            request_format_version?: "0.2.0-candidate" | null;
            delivery_requirements?: components["schemas"]["DeliveryRequirements"] | null;
            /** Goal */
            goal: string;
            inputs?: components["schemas"]["ProductionInputs"];
            /** Project Id */
            project_id?: string | null;
            /**
             * Source Bindings
             * @default []
             */
            source_bindings: components["schemas"]["SourceBinding"][];
            brief?: components["schemas"]["CreativeBriefInput"] | null;
            automation?: components["schemas"]["Automation"];
            policy?: components["schemas"]["ExecutionPolicy-Output"];
            /**
             * Outputs
             * @default [
             *       "video",
             *       "narration_audio",
             *       "mixed_audio",
             *       "approved_script",
             *       "actual_transcript",
             *       "subtitles",
             *       "semantic_manifest",
             *       "rag_chunks"
             *     ]
             */
            outputs: ("video" | "narration_audio" | "mixed_audio" | "approved_script" | "actual_transcript" | "subtitles" | "semantic_manifest" | "rag_chunks")[];
            /**
             * Delivery
             * @default reference
             * @enum {string}
             */
            delivery: "reference" | "export";
        };
        /** ProductionRequestV03 */
        "ProductionRequestV03-Input": {
            /**
             * Request Format Version
             * @constant
             */
            request_format_version: "0.3.0-candidate";
            delivery_requirements?: components["schemas"]["DeliveryRequirementsV03"] | null;
            /** Goal */
            goal: string;
            inputs?: components["schemas"]["ProductionInputs"];
            /** Project Id */
            project_id?: string | null;
            /**
             * Source Bindings
             * @default []
             */
            source_bindings: components["schemas"]["SourceBinding"][];
            brief?: components["schemas"]["CreativeBriefInput"] | null;
            automation?: components["schemas"]["Automation"];
            policy?: components["schemas"]["ExecutionPolicy-Input"];
            /**
             * Outputs
             * @default [
             *       "video",
             *       "narration_audio",
             *       "mixed_audio",
             *       "approved_script",
             *       "actual_transcript",
             *       "subtitles",
             *       "semantic_manifest",
             *       "rag_chunks"
             *     ]
             */
            outputs: ("video" | "narration_audio" | "mixed_audio" | "approved_script" | "actual_transcript" | "subtitles" | "semantic_manifest" | "rag_chunks")[];
            /**
             * Delivery
             * @default reference
             * @enum {string}
             */
            delivery: "reference" | "export";
        };
        /** ProductionRequestV03 */
        "ProductionRequestV03-Output": {
            /**
             * Request Format Version
             * @constant
             */
            request_format_version: "0.3.0-candidate";
            delivery_requirements?: components["schemas"]["DeliveryRequirementsV03"] | null;
            /** Goal */
            goal: string;
            inputs?: components["schemas"]["ProductionInputs"];
            /** Project Id */
            project_id?: string | null;
            /**
             * Source Bindings
             * @default []
             */
            source_bindings: components["schemas"]["SourceBinding"][];
            brief?: components["schemas"]["CreativeBriefInput"] | null;
            automation?: components["schemas"]["Automation"];
            policy?: components["schemas"]["ExecutionPolicy-Output"];
            /**
             * Outputs
             * @default [
             *       "video",
             *       "narration_audio",
             *       "mixed_audio",
             *       "approved_script",
             *       "actual_transcript",
             *       "subtitles",
             *       "semantic_manifest",
             *       "rag_chunks"
             *     ]
             */
            outputs: ("video" | "narration_audio" | "mixed_audio" | "approved_script" | "actual_transcript" | "subtitles" | "semantic_manifest" | "rag_chunks")[];
            /**
             * Delivery
             * @default reference
             * @enum {string}
             */
            delivery: "reference" | "export";
        };
        /** ProjectDraft */
        ProjectDraft: {
            /**
             * Name
             * @default 未命名项目
             */
            name: string;
            /**
             * Goal
             * @default
             */
            goal: string;
            /**
             * Source Text
             * @default
             */
            source_text: string;
            /** Project Id */
            project_id: string;
            /** Revision */
            revision: number;
            /** Saved At Us */
            saved_at_us: number;
        };
        /** ProjectGoalAccepted */
        ProjectGoalAccepted: {
            /**
             * Format
             * @default project-goal-accepted-v1
             * @constant
             */
            format: "project-goal-accepted-v1";
            /** Instance Id */
            instance_id: string;
            /** Project Id */
            project_id: string;
            /** Production Id */
            production_id: string;
            /** Run Id */
            run_id: string;
            derivation_ref: components["schemas"]["ProjectScopeDerivationRef"];
            /** Goal Sha256 */
            goal_sha256: string;
            production: components["schemas"]["ProductionAccepted"];
        };
        /** ProjectGoalInput */
        ProjectGoalInput: {
            /**
             * Format
             * @default project-goal-input-v1
             * @constant
             */
            format: "project-goal-input-v1";
            /**
             * Name
             * @default 未命名项目
             */
            name: string;
            /** Goal */
            goal: string;
            inputs?: components["schemas"]["ProductionInputs"];
            /**
             * Source Bindings
             * @default []
             */
            source_bindings: components["schemas"]["SourceBinding"][];
            brief?: components["schemas"]["CreativeBriefInput"];
            /**
             * Delivery
             * @default reference
             * @enum {string}
             */
            delivery: "reference" | "export";
            creation_authorization_ref?: components["schemas"]["DailyProjectAuthorizationRef"] | null;
        };
        /** ProjectGoalReceiptAbsentV1 */
        ProjectGoalReceiptAbsentV1: {
            /**
             * Format
             * @constant
             */
            format: "project-goal-receipt-association-v1";
            /** Instance Id */
            instance_id: string;
            /** Principal Id */
            principal_id: string;
            /**
             * Original Scope
             * @constant
             */
            original_scope: "project.goal.accept";
            /** Idempotency Key */
            idempotency_key: string;
            /** Goal Sha256 */
            goal_sha256: string;
            /**
             * Canonicalization Id
             * @constant
             */
            canonicalization_id: "project-goal-pydantic-json-v1";
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            state: "absent";
        };
        /** ProjectGoalReceiptAcceptedV1 */
        ProjectGoalReceiptAcceptedV1: {
            /**
             * Format
             * @constant
             */
            format: "project-goal-receipt-association-v1";
            /** Instance Id */
            instance_id: string;
            /** Principal Id */
            principal_id: string;
            /**
             * Original Scope
             * @constant
             */
            original_scope: "project.goal.accept";
            /** Idempotency Key */
            idempotency_key: string;
            /** Goal Sha256 */
            goal_sha256: string;
            /**
             * Canonicalization Id
             * @constant
             */
            canonicalization_id: "project-goal-pydantic-json-v1";
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            state: "accepted";
            receipt: components["schemas"]["ProjectGoalAccepted"];
        };
        /** ProjectGoalReceiptDeniedV1 */
        ProjectGoalReceiptDeniedV1: {
            /**
             * Format
             * @constant
             */
            format: "project-goal-receipt-association-v1";
            /** Instance Id */
            instance_id: string;
            /** Principal Id */
            principal_id: string;
            /**
             * Original Scope
             * @constant
             */
            original_scope: "project.goal.accept";
            /** Idempotency Key */
            idempotency_key: string;
            /** Goal Sha256 */
            goal_sha256: string;
            /**
             * Canonicalization Id
             * @constant
             */
            canonicalization_id: "project-goal-pydantic-json-v1";
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            state: "denied";
            /** Reason Code */
            reason_code: string;
            /** Resolved At Us */
            resolved_at_us: number;
        };
        /** ProjectGoalReceiptPendingV1 */
        ProjectGoalReceiptPendingV1: {
            /**
             * Format
             * @constant
             */
            format: "project-goal-receipt-association-v1";
            /** Instance Id */
            instance_id: string;
            /** Principal Id */
            principal_id: string;
            /**
             * Original Scope
             * @constant
             */
            original_scope: "project.goal.accept";
            /** Idempotency Key */
            idempotency_key: string;
            /** Goal Sha256 */
            goal_sha256: string;
            /**
             * Canonicalization Id
             * @constant
             */
            canonicalization_id: "project-goal-pydantic-json-v1";
            /**
             * @description discriminator enum property added by openapi-typescript
             * @enum {string}
             */
            state: "pending";
        };
        /** ProjectGoalReceiptQueryV1 */
        ProjectGoalReceiptQueryV1: {
            /**
             * Format
             * @constant
             */
            format: "project-goal-receipt-query-v1";
            /** Expected Instance Id */
            expected_instance_id: string;
            /** Idempotency Key */
            idempotency_key: string;
            goal: components["schemas"]["ProjectGoalInput"];
        };
        /** ProjectInput */
        ProjectInput: {
            /**
             * Name
             * @default 未命名项目
             */
            name: string;
            /**
             * Goal
             * @default
             */
            goal: string;
            /**
             * Source Text
             * @default
             */
            source_text: string;
        };
        /** ProjectScopeDerivationRef */
        ProjectScopeDerivationRef: {
            /** Derivation Id */
            derivation_id: string;
            /** Content Sha256 */
            content_sha256: string;
        };
        /** ReviewDecision */
        ReviewDecision: {
            /** Target Revision Id */
            target_revision_id: string;
            /**
             * Action
             * @enum {string}
             */
            action: "approve" | "revise" | "reject";
            /**
             * Instruction Text
             * @default
             */
            instruction_text: string;
            /**
             * Preserved Constraints
             * @default []
             */
            preserved_constraints: string[];
        };
        /** RevisionRef */
        RevisionRef: {
            /** Revision Id */
            revision_id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "insight" | "brief" | "plan" | "script" | "storyboard" | "quality" | "feedback";
            /** Content Sha256 */
            content_sha256: string;
        };
        /** RevokeLocalCopyInputScope */
        RevokeLocalCopyInputScope: {
            scope_ref: components["schemas"]["LocalCopyInputScopeRef"];
            /** Reason */
            reason: string;
        };
        /** RightsSnapshot */
        RightsSnapshot: {
            /** Rights Id */
            rights_id: string;
            /**
             * Basis
             * @enum {string}
             */
            basis: "owned" | "licensed" | "user_asserted";
            /** Holder */
            holder?: string | null;
            /** License Identifier */
            license_identifier?: string | null;
            /**
             * License Document Artifact Ids
             * @default []
             */
            license_document_artifact_ids: string[];
            /** Permitted Uses */
            permitted_uses: ("playback" | "export" | "rag_index" | "derivative" | "commercial_use" | "standalone_audio" | "redistribution")[];
            /**
             * Attribution
             * @default
             */
            attribution: string;
            /** Valid From Us */
            valid_from_us?: number | null;
            /** Expires At Us */
            expires_at_us?: number | null;
            /**
             * Platforms
             * @default []
             */
            platforms: string[];
            /**
             * Territories
             * @default []
             */
            territories: string[];
            /** Approval Ref */
            approval_ref?: string | null;
            /**
             * Limitations
             * @default []
             */
            limitations: string[];
        };
        /**
         * RunStatus
         * @enum {string}
         */
        RunStatus: "queued" | "running" | "waiting_user" | "waiting_authorization" | "waiting_provider" | "succeeded" | "failed" | "cancel_requested" | "cancelled" | "needs_reconciliation";
        /** SelectLocalCopyInputScope */
        SelectLocalCopyInputScope: {
            scope_ref: components["schemas"]["LocalCopyInputScopeRef"];
            /** Destination Project Id */
            destination_project_id: string;
            /** Executing Principal Id */
            executing_principal_id: string;
            /** Registration Sha256 */
            registration_sha256: string;
            policy_ref: components["schemas"]["ProductionPolicyRef"];
        };
        /** SemanticAudioSpan */
        SemanticAudioSpan: {
            track: components["schemas"]["AudioTrackRef"];
            intrinsic_range: components["schemas"]["MediaRange"];
            timeline_range: components["schemas"]["MediaRange"];
            /** Mapping Piece Ids */
            mapping_piece_ids: string[];
        };
        /** SemanticPage */
        SemanticPage: {
            bundle_ref: components["schemas"]["BundleRef"];
            /** Segments */
            segments: components["schemas"]["SemanticSegmentV1"][];
            /** Next Cursor */
            next_cursor?: string | null;
        };
        /** SemanticSegmentV1 */
        SemanticSegmentV1: {
            /**
             * Record Format Version
             * @default 1
             * @constant
             */
            record_format_version: 1;
            /** Segment Id */
            segment_id: string;
            /** Bundle Revision Id */
            bundle_revision_id: string;
            /** Video Asset Id */
            video_asset_id: string;
            video_range: components["schemas"]["MediaRange"];
            /** Audio Spans */
            audio_spans: components["schemas"]["SemanticAudioSpan"][];
            /** Shot Revision Ids */
            shot_revision_ids: string[];
            /** Transcript Unit Refs */
            transcript_unit_refs: string[];
            /** Speech Text */
            speech_text: string;
            /** Visual Description */
            visual_description: string;
            /** Summary */
            summary: string;
            /** Topic */
            topic: string;
            /** Main Thesis */
            main_thesis: string;
            /**
             * Keywords
             * @default []
             */
            keywords: string[];
            /**
             * Entities
             * @default []
             */
            entities: {
                [key: string]: string;
            }[];
            /**
             * Source Refs
             * @default []
             */
            source_refs: components["schemas"]["BundleSourceRef"][];
            /** Alignment Revision Id */
            alignment_revision_id: string;
            /** Field Provenance */
            field_provenance: {
                [key: string]: "observed" | "model_inference" | "user_provided" | "derived";
            };
            /** Frame Evidence Refs */
            frame_evidence_refs: components["schemas"]["FrameEvidenceRef"][];
            /** Rights Ref */
            rights_ref: string;
            /** Valid Until Us */
            valid_until_us?: number | null;
            /** Retrieval Text */
            retrieval_text: string;
            /** Content Sha256 */
            content_sha256: string;
        };
        /** SourceBinding */
        SourceBinding: {
            /** System */
            system: string;
            /** Namespace */
            namespace: string;
            /** Article Id */
            article_id?: string | null;
            /** Article Revision */
            article_revision?: string | null;
            /** Topic Id */
            topic_id?: string | null;
            /** Topic Revision */
            topic_revision?: string | null;
            /**
             * Paragraph Ids
             * @default []
             */
            paragraph_ids: string[];
            /**
             * Confirmed Facts
             * @default []
             */
            confirmed_facts: string[];
        };
        /** SourceFactRef */
        SourceFactRef: {
            /** Foreign Fact Id */
            foreign_fact_id?: string | null;
            /** Local Fact Id */
            local_fact_id?: string | null;
            /** Text */
            text: string;
            /** Source Revision */
            source_revision: string;
            /**
             * Confirmation Kind
             * @enum {string}
             */
            confirmation_kind: "caller_asserted" | "approved" | "researched_observation" | "inference";
            /** Approval Ref */
            approval_ref?: string | null;
        };
        /** StagedAsset */
        StagedAsset: {
            /** Staging Id */
            staging_id: string;
            /** Sha256 */
            sha256: string;
            /** Size */
            size: number;
            /** Media Type */
            media_type: string;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    health_api_v1_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["InstanceHealth"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    projects_api_v1_projects_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectDraft"][];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    project_create_api_v1_projects_post: {
        parameters: {
            query?: never;
            header?: {
                "Idempotency-Key"?: string | null;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProjectInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectDraft"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    project_get_api_v1_projects__project_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Quoted SHA256 for content; quoted numeric revision for project drafts. */
                    ETag?: string;
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectDraft"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    project_update_api_v1_projects__project_id__put: {
        parameters: {
            query?: never;
            header: {
                /** @description Draft numeric revision parsed as int after trimming quote characters; mismatch409. */
                "If-Match": string;
            };
            path: {
                project_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProjectInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Quoted SHA256 for content; quoted numeric revision for project drafts. */
                    ETag?: string;
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectDraft"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    production_list_api_v1_productions_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProductionAccepted"][];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    production_create_api_v1_productions_post: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProductionRequest-Input"] | components["schemas"]["ProductionRequestV03-Input"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProductionAccepted"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    create_project_goal: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProjectGoalInput"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectGoalAccepted"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    lookup_project_goal_receipt: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProjectGoalReceiptQueryV1"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual route cache directive. */
                    "Cache-Control"?: string;
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProjectGoalReceiptAcceptedV1"] | components["schemas"]["ProjectGoalReceiptPendingV1"] | components["schemas"]["ProjectGoalReceiptDeniedV1"] | components["schemas"]["ProjectGoalReceiptAbsentV1"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    production_get_api_v1_productions__production_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                production_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProductionDetail"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    production_cancel_api_v1_productions__production_id__cancel_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                production_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ProductionDetail"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    production_revisions_api_v1_productions__production_id__revisions_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                production_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CreativeRevision"][];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    decision_submit_api_v1_runs__run_id__decisions_post: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": string;
            };
            path: {
                run_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ReviewDecision"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ReviewDecision"] | components["schemas"]["FeedbackRevision"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    run_pause_api_v1_runs__run_id__pause_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                run_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    run_resume_api_v1_runs__run_id__resume_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                run_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    run_events_api_v1_runs__run_id__events_get: {
        parameters: {
            query?: {
                after_sequence?: number;
            };
            header?: {
                /** @description Response is SSE when this value contains text/event-stream; otherwise a JSON event list. */
                Accept?: string;
                /** @description Integer resume cursor; effective cursor=max(after_sequence,int(header)). Malformed400; a larger cursor yields no earlier events. */
                "Last-Event-ID"?: string;
            };
            path: {
                run_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    /** @description Actual route cache directive. */
                    "Cache-Control"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EventEnvelope"][];
                    "text/event-stream": string;
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    asset_stage_api_v1_assets_staging_post: {
        parameters: {
            query?: never;
            header?: {
                /** @description Actual staging MIME before the first semicolon; defaults application/octet-stream. Staging is not decoder or rights approval. */
                "Content-Type"?: string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "*/*": string;
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["StagedAsset"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    asset_import_api_v1_assets_import_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AssetCandidate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AssetRecord"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    asset_get_api_v1_assets__asset_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AssetRecord"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    asset_content_api_v1_assets__asset_id__content_get: {
        parameters: {
            query?: never;
            header?: {
                /** @description Starlette byte ranges; malformed400, unsatisfiable416, a supported range206. Too many ranges fall back to200. */
                Range?: string;
                /** @description Range applies only when exactly equal to the current ETag or Last-Modified; otherwise full200. */
                "If-Range"?: string;
            };
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    /** @description Actual HTTP body byte length when present; a partial length is not the full artifact size. */
                    "Content-Length"?: string;
                    /** @description Quoted SHA256 for content; quoted numeric revision for project drafts. */
                    ETag?: string;
                    /** @description FileResponse stat timestamp; not a creative revision or integrity proof. */
                    "Last-Modified"?: string;
                    /** @description Actual route cache directive. */
                    "Cache-Control"?: string;
                    /** @description bytes for FileResponse content. */
                    "Accept-Ranges"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "*/*": string;
                };
            };
            /** @description Authorized actual partial bytes; never evidence of complete file integrity. */
            206: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    /** @description Actual HTTP body byte length when present; a partial length is not the full artifact size. */
                    "Content-Length"?: string;
                    /** @description Quoted SHA256 for content; quoted numeric revision for project drafts. */
                    ETag?: string;
                    /** @description FileResponse stat timestamp; not a creative revision or integrity proof. */
                    "Last-Modified"?: string;
                    /** @description Actual route cache directive. */
                    "Cache-Control"?: string;
                    /** @description bytes for FileResponse content. */
                    "Accept-Ranges"?: string;
                    /** @description Single206 bytes start-end/size;416 bytes *\/size. Multipart206 carries its ranges within the body. */
                    "Content-Range"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "*/*": string;
                    "multipart/byteranges": string;
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unsatisfiable byte range; Starlette empty plain-text transport response. */
            416: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    /** @description Actual HTTP body byte length when present; a partial length is not the full artifact size. */
                    "Content-Length"?: string;
                    /** @description Single206 bytes start-end/size;416 bytes *\/size. Multipart206 carries its ranges within the body. */
                    "Content-Range"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    asset_content_metadata_api_v1_assets__asset_id__content_metadata_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DeliveryContentMetadata"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    bundle_get_api_v1_bundles__revision_id__manifest_get: {
        parameters: {
            query?: {
                purpose?: "playback" | "export" | "rag_index" | "derivative" | "commercial_use" | "standalone_audio" | "redistribution";
            };
            header?: {
                /** @description Starlette byte ranges; malformed400, unsatisfiable416, a supported range206. Too many ranges fall back to200. */
                Range?: string;
                /** @description Range applies only when exactly equal to the current ETag or Last-Modified; otherwise full200. */
                "If-Range"?: string;
                /** @description Only exact equality to the current quoted SHA256 ETag returns304, after authorization and integrity checks. */
                "If-None-Match"?: string;
            };
            path: {
                revision_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    /** @description Actual HTTP body byte length when present; a partial length is not the full artifact size. */
                    "Content-Length"?: string;
                    /** @description Quoted SHA256 for content; quoted numeric revision for project drafts. */
                    ETag?: string;
                    /** @description FileResponse stat timestamp; not a creative revision or integrity proof. */
                    "Last-Modified"?: string;
                    /** @description Actual route cache directive. */
                    "Cache-Control"?: string;
                    /** @description bytes for FileResponse content. */
                    "Accept-Ranges"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BundleManifest"] | components["schemas"]["BundleManifestV03"];
                };
            };
            /** @description Authorized actual partial bytes; never evidence of complete file integrity. */
            206: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    /** @description Actual HTTP body byte length when present; a partial length is not the full artifact size. */
                    "Content-Length"?: string;
                    /** @description Quoted SHA256 for content; quoted numeric revision for project drafts. */
                    ETag?: string;
                    /** @description FileResponse stat timestamp; not a creative revision or integrity proof. */
                    "Last-Modified"?: string;
                    /** @description Actual route cache directive. */
                    "Cache-Control"?: string;
                    /** @description bytes for FileResponse content. */
                    "Accept-Ranges"?: string;
                    /** @description Single206 bytes start-end/size;416 bytes *\/size. Multipart206 carries its ranges within the body. */
                    "Content-Range"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": string;
                    "multipart/byteranges": string;
                };
            };
            /** @description Authorized exact ETag match; empty body, not a full-file verification. */
            304: {
                headers: {
                    /** @description Quoted SHA256 for content; quoted numeric revision for project drafts. */
                    ETag?: string;
                    /** @description Actual route cache directive. */
                    "Cache-Control"?: string;
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unsatisfiable byte range; Starlette empty plain-text transport response. */
            416: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    /** @description Actual HTTP body byte length when present; a partial length is not the full artifact size. */
                    "Content-Length"?: string;
                    /** @description Single206 bytes start-end/size;416 bytes *\/size. Multipart206 carries its ranges within the body. */
                    "Content-Range"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    bundle_manifest_metadata_api_v1_bundles__revision_id__manifest_metadata_get: {
        parameters: {
            query?: {
                purpose?: "playback" | "export" | "rag_index" | "derivative" | "commercial_use" | "standalone_audio" | "redistribution";
            };
            header?: never;
            path: {
                revision_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DeliveryContentMetadata"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    bundle_content_api_v1_bundles__revision_id__artifacts__artifact_id__content_get: {
        parameters: {
            query?: {
                purpose?: "playback" | "export" | "rag_index" | "derivative" | "commercial_use" | "standalone_audio" | "redistribution";
            };
            header?: {
                /** @description Starlette byte ranges; malformed400, unsatisfiable416, a supported range206. Too many ranges fall back to200. */
                Range?: string;
                /** @description Range applies only when exactly equal to the current ETag or Last-Modified; otherwise full200. */
                "If-Range"?: string;
                /** @description Only exact equality to the current quoted SHA256 ETag returns304, after authorization and integrity checks. */
                "If-None-Match"?: string;
            };
            path: {
                revision_id: string;
                artifact_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    /** @description Actual HTTP body byte length when present; a partial length is not the full artifact size. */
                    "Content-Length"?: string;
                    /** @description Quoted SHA256 for content; quoted numeric revision for project drafts. */
                    ETag?: string;
                    /** @description FileResponse stat timestamp; not a creative revision or integrity proof. */
                    "Last-Modified"?: string;
                    /** @description Actual route cache directive. */
                    "Cache-Control"?: string;
                    /** @description bytes for FileResponse content. */
                    "Accept-Ranges"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "*/*": string;
                };
            };
            /** @description Authorized actual partial bytes; never evidence of complete file integrity. */
            206: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    /** @description Actual HTTP body byte length when present; a partial length is not the full artifact size. */
                    "Content-Length"?: string;
                    /** @description Quoted SHA256 for content; quoted numeric revision for project drafts. */
                    ETag?: string;
                    /** @description FileResponse stat timestamp; not a creative revision or integrity proof. */
                    "Last-Modified"?: string;
                    /** @description Actual route cache directive. */
                    "Cache-Control"?: string;
                    /** @description bytes for FileResponse content. */
                    "Accept-Ranges"?: string;
                    /** @description Single206 bytes start-end/size;416 bytes *\/size. Multipart206 carries its ranges within the body. */
                    "Content-Range"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "*/*": string;
                    "multipart/byteranges": string;
                };
            };
            /** @description Authorized exact ETag match; empty body, not a full-file verification. */
            304: {
                headers: {
                    /** @description Quoted SHA256 for content; quoted numeric revision for project drafts. */
                    ETag?: string;
                    /** @description Actual route cache directive. */
                    "Cache-Control"?: string;
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unsatisfiable byte range; Starlette empty plain-text transport response. */
            416: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    /** @description Actual HTTP body byte length when present; a partial length is not the full artifact size. */
                    "Content-Length"?: string;
                    /** @description Single206 bytes start-end/size;416 bytes *\/size. Multipart206 carries its ranges within the body. */
                    "Content-Range"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    bundle_artifact_metadata_api_v1_bundles__revision_id__artifacts__artifact_id__content_metadata_get: {
        parameters: {
            query?: {
                purpose?: "playback" | "export" | "rag_index" | "derivative" | "commercial_use" | "standalone_audio" | "redistribution";
            };
            header?: never;
            path: {
                revision_id: string;
                artifact_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DeliveryContentMetadata"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    bundle_semantic_api_v1_bundles__revision_id__semantic_segments_get: {
        parameters: {
            query?: {
                cursor?: string | null;
                limit?: number;
            };
            header?: never;
            path: {
                revision_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SemanticPage"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    bundle_export_api_v1_bundles__revision_id__exports_post: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": string;
            };
            path: {
                revision_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BundleExportRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BundleExportAccepted"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    bundle_export_status_api_v1_bundle_exports__export_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                export_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BundleExportAccepted"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    bundle_export_content_api_v1_bundle_exports__export_id__content_get: {
        parameters: {
            query?: never;
            header?: {
                /** @description Starlette byte ranges; malformed400, unsatisfiable416, a supported range206. Too many ranges fall back to200. */
                Range?: string;
                /** @description Range applies only when exactly equal to the current ETag or Last-Modified; otherwise full200. */
                "If-Range"?: string;
                /** @description Only exact equality to the current quoted SHA256 ETag returns304, after authorization and integrity checks. */
                "If-None-Match"?: string;
            };
            path: {
                export_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    /** @description Actual HTTP body byte length when present; a partial length is not the full artifact size. */
                    "Content-Length"?: string;
                    /** @description Quoted SHA256 for content; quoted numeric revision for project drafts. */
                    ETag?: string;
                    /** @description FileResponse stat timestamp; not a creative revision or integrity proof. */
                    "Last-Modified"?: string;
                    /** @description Actual route cache directive. */
                    "Cache-Control"?: string;
                    /** @description bytes for FileResponse content. */
                    "Accept-Ranges"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/zip": string;
                };
            };
            /** @description Authorized actual partial bytes; never evidence of complete file integrity. */
            206: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    /** @description Actual HTTP body byte length when present; a partial length is not the full artifact size. */
                    "Content-Length"?: string;
                    /** @description Quoted SHA256 for content; quoted numeric revision for project drafts. */
                    ETag?: string;
                    /** @description FileResponse stat timestamp; not a creative revision or integrity proof. */
                    "Last-Modified"?: string;
                    /** @description Actual route cache directive. */
                    "Cache-Control"?: string;
                    /** @description bytes for FileResponse content. */
                    "Accept-Ranges"?: string;
                    /** @description Single206 bytes start-end/size;416 bytes *\/size. Multipart206 carries its ranges within the body. */
                    "Content-Range"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/zip": string;
                    "multipart/byteranges": string;
                };
            };
            /** @description Authorized exact ETag match; empty body, not a full-file verification. */
            304: {
                headers: {
                    /** @description Quoted SHA256 for content; quoted numeric revision for project drafts. */
                    ETag?: string;
                    /** @description Actual route cache directive. */
                    "Cache-Control"?: string;
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unsatisfiable byte range; Starlette empty plain-text transport response. */
            416: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    /** @description Actual HTTP body byte length when present; a partial length is not the full artifact size. */
                    "Content-Length"?: string;
                    /** @description Single206 bytes start-end/size;416 bytes *\/size. Multipart206 carries its ranges within the body. */
                    "Content-Range"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    bundle_export_metadata_api_v1_bundle_exports__export_id__content_metadata_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                export_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DeliveryContentMetadata"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    bundle_grant_api_v1_bundles__revision_id__grants_post: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": string;
            };
            path: {
                revision_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BundleGrantRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BundleReferenceGrant"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    bundle_revoke_api_v1_bundle_grants__grant_id__revoke_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                grant_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BundleReferenceGrant"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    bundle_import_api_v1_bundle_imports_post: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BundleImportRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BundleImportReceipt"] | components["schemas"]["BundleImportReceiptV03"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    bundle_import_get_api_v1_bundle_imports__import_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                import_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BundleImportReceipt"] | components["schemas"]["BundleImportReceiptV03"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    bundle_import_manifest_api_v1_bundle_imports__import_id__manifest_get: {
        parameters: {
            query?: {
                purpose?: "playback" | "export" | "rag_index" | "derivative" | "commercial_use" | "standalone_audio" | "redistribution";
            };
            header?: {
                /** @description Starlette byte ranges; malformed400, unsatisfiable416, a supported range206. Too many ranges fall back to200. */
                Range?: string;
                /** @description Range applies only when exactly equal to the current ETag or Last-Modified; otherwise full200. */
                "If-Range"?: string;
                /** @description Only exact equality to the current quoted SHA256 ETag returns304, after authorization and integrity checks. */
                "If-None-Match"?: string;
            };
            path: {
                import_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    /** @description Actual HTTP body byte length when present; a partial length is not the full artifact size. */
                    "Content-Length"?: string;
                    /** @description Quoted SHA256 for content; quoted numeric revision for project drafts. */
                    ETag?: string;
                    /** @description FileResponse stat timestamp; not a creative revision or integrity proof. */
                    "Last-Modified"?: string;
                    /** @description Actual route cache directive. */
                    "Cache-Control"?: string;
                    /** @description bytes for FileResponse content. */
                    "Accept-Ranges"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BundleManifest"] | components["schemas"]["BundleManifestV03"];
                };
            };
            /** @description Authorized actual partial bytes; never evidence of complete file integrity. */
            206: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    /** @description Actual HTTP body byte length when present; a partial length is not the full artifact size. */
                    "Content-Length"?: string;
                    /** @description Quoted SHA256 for content; quoted numeric revision for project drafts. */
                    ETag?: string;
                    /** @description FileResponse stat timestamp; not a creative revision or integrity proof. */
                    "Last-Modified"?: string;
                    /** @description Actual route cache directive. */
                    "Cache-Control"?: string;
                    /** @description bytes for FileResponse content. */
                    "Accept-Ranges"?: string;
                    /** @description Single206 bytes start-end/size;416 bytes *\/size. Multipart206 carries its ranges within the body. */
                    "Content-Range"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": string;
                    "multipart/byteranges": string;
                };
            };
            /** @description Authorized exact ETag match; empty body, not a full-file verification. */
            304: {
                headers: {
                    /** @description Quoted SHA256 for content; quoted numeric revision for project drafts. */
                    ETag?: string;
                    /** @description Actual route cache directive. */
                    "Cache-Control"?: string;
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unsatisfiable byte range; Starlette empty plain-text transport response. */
            416: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    /** @description Actual HTTP body byte length when present; a partial length is not the full artifact size. */
                    "Content-Length"?: string;
                    /** @description Single206 bytes start-end/size;416 bytes *\/size. Multipart206 carries its ranges within the body. */
                    "Content-Range"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    bundle_import_manifest_metadata_api_v1_bundle_imports__import_id__manifest_metadata_get: {
        parameters: {
            query?: {
                purpose?: "playback" | "export" | "rag_index" | "derivative" | "commercial_use" | "standalone_audio" | "redistribution";
            };
            header?: never;
            path: {
                import_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DeliveryContentMetadata"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    bundle_import_content_api_v1_bundle_imports__import_id__artifacts__artifact_id__content_get: {
        parameters: {
            query?: {
                purpose?: "playback" | "export" | "rag_index" | "derivative" | "commercial_use" | "standalone_audio" | "redistribution";
            };
            header?: {
                /** @description Starlette byte ranges; malformed400, unsatisfiable416, a supported range206. Too many ranges fall back to200. */
                Range?: string;
                /** @description Range applies only when exactly equal to the current ETag or Last-Modified; otherwise full200. */
                "If-Range"?: string;
                /** @description Only exact equality to the current quoted SHA256 ETag returns304, after authorization and integrity checks. */
                "If-None-Match"?: string;
            };
            path: {
                import_id: string;
                artifact_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    /** @description Actual HTTP body byte length when present; a partial length is not the full artifact size. */
                    "Content-Length"?: string;
                    /** @description Quoted SHA256 for content; quoted numeric revision for project drafts. */
                    ETag?: string;
                    /** @description FileResponse stat timestamp; not a creative revision or integrity proof. */
                    "Last-Modified"?: string;
                    /** @description Actual route cache directive. */
                    "Cache-Control"?: string;
                    /** @description bytes for FileResponse content. */
                    "Accept-Ranges"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "*/*": string;
                };
            };
            /** @description Authorized actual partial bytes; never evidence of complete file integrity. */
            206: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    /** @description Actual HTTP body byte length when present; a partial length is not the full artifact size. */
                    "Content-Length"?: string;
                    /** @description Quoted SHA256 for content; quoted numeric revision for project drafts. */
                    ETag?: string;
                    /** @description FileResponse stat timestamp; not a creative revision or integrity proof. */
                    "Last-Modified"?: string;
                    /** @description Actual route cache directive. */
                    "Cache-Control"?: string;
                    /** @description bytes for FileResponse content. */
                    "Accept-Ranges"?: string;
                    /** @description Single206 bytes start-end/size;416 bytes *\/size. Multipart206 carries its ranges within the body. */
                    "Content-Range"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "*/*": string;
                    "multipart/byteranges": string;
                };
            };
            /** @description Authorized exact ETag match; empty body, not a full-file verification. */
            304: {
                headers: {
                    /** @description Quoted SHA256 for content; quoted numeric revision for project drafts. */
                    ETag?: string;
                    /** @description Actual route cache directive. */
                    "Cache-Control"?: string;
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unsatisfiable byte range; Starlette empty plain-text transport response. */
            416: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    /** @description Actual HTTP body byte length when present; a partial length is not the full artifact size. */
                    "Content-Length"?: string;
                    /** @description Single206 bytes start-end/size;416 bytes *\/size. Multipart206 carries its ranges within the body. */
                    "Content-Range"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    bundle_import_artifact_metadata_api_v1_bundle_imports__import_id__artifacts__artifact_id__content_metadata_get: {
        parameters: {
            query?: {
                purpose?: "playback" | "export" | "rag_index" | "derivative" | "commercial_use" | "standalone_audio" | "redistribution";
            };
            header?: never;
            path: {
                import_id: string;
                artifact_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DeliveryContentMetadata"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    bundle_import_export_api_v1_bundle_imports__import_id__exports_post: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": string;
            };
            path: {
                import_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BundleExportRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            202: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BundleExportAccepted"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    local_copy_scope_preview_api_v1_local_copy_input_scopes_preview_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PreviewLocalCopyInputScope"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LocalCopyInputScope-Output"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    local_copy_scope_install_api_v1_local_copy_input_scopes_install_post: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["InstallLocalCopyInputScope"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LocalCopyInputActionReceipt"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    local_copy_scope_select_api_v1_local_copy_input_scopes_select_post: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SelectLocalCopyInputScope"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LocalCopyInputActionReceipt"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    local_copy_scope_revoke_api_v1_local_copy_input_scopes_revoke_post: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RevokeLocalCopyInputScope"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LocalCopyInputActionReceipt"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    local_copy_scope_get_api_v1_local_copy_input_scopes__scope_id__revisions__revision__get: {
        parameters: {
            query: {
                content_sha256: string;
            };
            header?: never;
            path: {
                scope_id: string;
                revision: number;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LocalCopyInputScopeRecord"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    local_copy_scope_bind_api_v1_local_copy_input_scopes_bind_request_post: {
        parameters: {
            query?: never;
            header: {
                "Idempotency-Key": string;
            };
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BindLocalCopyInputScope"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LocalCopyInputActionReceipt"];
                };
            };
            /** @description Invalid domain input (JSON), or a rejected transport Host/Origin/Range (plain text) */
            400: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "text/plain": string;
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation session is invalid */
            401: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Installation permission or browser origin is denied */
            403: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Owned resource does not exist */
            404: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Version, idempotency or execution state conflicts; inspect retryability */
            409: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Asset upload exceeds the configured limit */
            413: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Identified media format or media reference is not supported by installation policy */
            415: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Request contract, content integrity or media decoding is invalid */
            422: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Required installation resource or media validator is unavailable */
            503: {
                headers: {
                    /** @description Actual response MIME, including charset/boundary when supplied. */
                    "Content-Type"?: string;
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
}
