use std::fs;
use std::path::PathBuf;

fn ensure_sidecar_placeholder() {
    let manifest_dir = match std::env::var("CARGO_MANIFEST_DIR") {
        Ok(v) => v,
        Err(_) => return,
    };

    let sidecar = PathBuf::from(manifest_dir)
        .join("bin")
        .join("ThesisLoomBackend-x86_64-pc-windows-msvc.exe");

    if sidecar.exists() {
        return;
    }

    if let Some(parent) = sidecar.parent() {
        let _ = fs::create_dir_all(parent);
    }
    // Keep a tiny placeholder so tauri externalBin path check passes in dev checks.
    let _ = fs::write(sidecar, b"placeholder");
}

fn main() {
    ensure_sidecar_placeholder();
    tauri_build::build()
}
