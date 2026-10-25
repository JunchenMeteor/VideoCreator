//! Library-only view of the actual trusted source/lifetime consumers.
//! No desktop main, build.rs, facts EXE, renderer commands or test fixtures.
#[path = "../../../../apps/desktop/src-tauri/src/resource_pins.rs"]
pub mod resource_pins;
#[path = "../../../../apps/desktop/src-tauri/src/platform.rs"]
pub mod platform;
#[path = "../../../../apps/desktop/src-tauri/src/load_policy.rs"]
pub mod load_policy;
#[path = "../../../../apps/desktop/src-tauri/src/windows_native_sources.rs"]
mod windows_native_sources;
