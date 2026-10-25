//! Trusted native supervision primitives; not a renderer or process plugin API.
pub mod resource_pins;
pub mod platform;
pub mod supervisor;
pub mod load_policy;
mod windows_native_sources;
#[cfg(windows)]
pub mod resource_authority;
pub mod native_startup;
pub mod native_installation;
pub(crate) mod qualification_record;
#[cfg(any(target_os = "linux", target_os = "macos"))]
pub mod posix_identity;
#[cfg(any(target_os = "linux", target_os = "macos"))]
pub mod posix_authority;
