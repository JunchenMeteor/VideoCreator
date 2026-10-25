fn main() {
    tauri_build::try_build(
        tauri_build::Attributes::new().app_manifest(
            tauri_build::AppManifest::new().commands(&[
                "get_engine_session","engine_request_open","engine_upload_chunk",
                "engine_upload_finish","engine_response_head","engine_response_read",
                "engine_request_abort","engine_request_release",
                "owner_setup_prepare","owner_setup_present","owner_setup_status","owner_setup_abort",
            ]),
        ),
    )
    .expect("native_build_configuration_invalid");
}
