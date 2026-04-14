#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::Serialize;
use std::net::{TcpStream, ToSocketAddrs};
#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};
use tauri::Manager;
use tauri::State;

#[derive(Default)]
struct BackendState {
    child: Mutex<Option<Child>>,
    last_error: Mutex<Option<String>>,
    last_backend_command: Mutex<Option<String>>,
    last_workspace_root: Mutex<Option<String>>,
    sidecar_hint: Mutex<Option<String>>,
}

impl Drop for BackendState {
    fn drop(&mut self) {
        if let Ok(mut guard) = self.child.lock() {
            let _ = stop_child_process(&mut guard);
        }
    }
}

#[derive(Serialize)]
struct BackendStatus {
    running: bool,
    pid: Option<u32>,
    message: String,
    workspace_root: String,
    python_path: String,
}

fn detect_workspace_root(explicit_root: Option<String>) -> Result<PathBuf, String> {
    if let Some(raw) = explicit_root {
        let trimmed = raw.trim();
        if !trimmed.is_empty() {
            let candidate = PathBuf::from(trimmed);
            if candidate.exists() {
                return Ok(candidate);
            }
            return Err(format!("workspace_root 不存在: {}", candidate.display()));
        }
    }

    let cwd = std::env::current_dir().map_err(|e| format!("读取当前目录失败: {e}"))?;
    let mut candidates = vec![cwd.clone()];
    if let Some(parent) = cwd.parent() {
        candidates.push(parent.to_path_buf());
    }
    if let Some(grandparent) = cwd.parent().and_then(|p| p.parent()) {
        candidates.push(grandparent.to_path_buf());
    }

    for path in candidates {
        let has_backend_api = path.join("backend_api.py").exists() || path.join("state_dashboard.py").exists();
        if path.join("workflow.py").exists() && has_backend_api {
            return Ok(path);
        }
    }

    Err("无法自动定位工作区根目录，请在前端传入 workspace_root".to_string())
}

fn resolve_workspace_root(explicit_root: Option<String>) -> Option<PathBuf> {
    detect_workspace_root(explicit_root).ok()
}

fn workspace_display(path: Option<PathBuf>) -> String {
    if let Some(p) = path {
        return p.display().to_string();
    }
    if let Ok(cwd) = std::env::current_dir() {
        return cwd.display().to_string();
    }
    String::new()
}

fn push_candidate(candidates: &mut Vec<String>, candidate: String) {
    let value = candidate.trim().to_string();
    if value.is_empty() {
        return;
    }
    if candidates.iter().any(|x| x.eq_ignore_ascii_case(&value)) {
        return;
    }
    candidates.push(value);
}

fn collect_backend_exe_candidates(workspace: Option<&Path>) -> Vec<String> {
    let mut candidates: Vec<String> = Vec::new();

    if let Ok(value) = std::env::var("THESISLOOM_BACKEND_EXE") {
        push_candidate(&mut candidates, value);
    }

    if let Some(root) = workspace {
        for path in [
            root.join("dist").join("ThesisLoomBackend").join("ThesisLoomBackend.exe"),
            root.join("desktop_ui").join("src-tauri").join("bin").join("ThesisLoomBackend-x86_64-pc-windows-msvc.exe"),
            root.join("desktop_ui").join("src-tauri").join("bin").join("ThesisLoomBackend.exe"),
        ] {
            if path.exists() {
                push_candidate(&mut candidates, path.display().to_string());
            }
        }
    }

    if let Ok(current_exe) = std::env::current_exe() {
        if let Some(exe_dir) = current_exe.parent() {
            for path in [
                exe_dir.join("ThesisLoomBackend.exe"),
                exe_dir.join("ThesisLoomBackend-x86_64-pc-windows-msvc.exe"),
                exe_dir.join("ThesisLoomBackend").join("ThesisLoomBackend.exe"),
                exe_dir.join("resources").join("ThesisLoomBackend.exe"),
                exe_dir.join("resources").join("ThesisLoomBackend-x86_64-pc-windows-msvc.exe"),
            ] {
                if path.exists() {
                    push_candidate(&mut candidates, path.display().to_string());
                }
            }

            if let Some(parent) = exe_dir.parent() {
                for path in [
                    parent.join("Resources").join("ThesisLoomBackend.exe"),
                    parent.join("Resources").join("ThesisLoomBackend-x86_64-pc-windows-msvc.exe"),
                    parent.join("resources").join("ThesisLoomBackend.exe"),
                    parent.join("resources").join("ThesisLoomBackend-x86_64-pc-windows-msvc.exe"),
                ] {
                    if path.exists() {
                        push_candidate(&mut candidates, path.display().to_string());
                    }
                }
            }
        }
    }

    candidates
}

fn collect_python_candidates(requested: Option<String>, workspace: &Path) -> Vec<String> {
    let mut candidates: Vec<String> = Vec::new();

    if let Some(value) = requested {
        push_candidate(&mut candidates, value);
    }

    if let Ok(value) = std::env::var("THESISLOOM_PYTHON") {
        push_candidate(&mut candidates, value);
    }

    for path in [
        workspace.join(".venv").join("Scripts").join("pythonw.exe"),
        workspace.join(".venv").join("Scripts").join("python.exe"),
        workspace.join("venv").join("Scripts").join("pythonw.exe"),
        workspace.join("venv").join("Scripts").join("python.exe"),
    ] {
        if path.exists() {
            push_candidate(&mut candidates, path.display().to_string());
        }
    }

    push_candidate(&mut candidates, "pythonw".to_string());
    push_candidate(&mut candidates, "python".to_string());
    candidates
}

fn apply_hidden_spawn_flags(command: &mut Command) {
    #[cfg(target_os = "windows")]
    {
        const CREATE_NO_WINDOW: u32 = 0x08000000;
        command.creation_flags(CREATE_NO_WINDOW);
    }
}

fn wait_for_port(host: &str, port: u16, timeout: Duration) -> bool {
    let deadline = Instant::now() + timeout;
    while Instant::now() < deadline {
        if let Ok(addrs) = (host, port).to_socket_addrs() {
            for addr in addrs {
                if TcpStream::connect_timeout(&addr, Duration::from_millis(260)).is_ok() {
                    return true;
                }
            }
        }
        thread::sleep(Duration::from_millis(220));
    }
    false
}

fn try_start_with_backend_exe(exe_path: &str, host: &str, port: u16) -> Result<Child, String> {
    let exe = PathBuf::from(exe_path);
    if !exe.exists() {
        return Err(format!("sidecar 不存在: {}", exe.display()));
    }

    let mut command = Command::new(&exe);
    if let Some(parent) = exe.parent() {
        command.current_dir(parent);
    }

    command
        .arg("--host")
        .arg(host)
        .arg("--port")
        .arg(port.to_string())
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null());
    apply_hidden_spawn_flags(&mut command);

    let mut child = command
        .spawn()
        .map_err(|e| format!("无法启动 sidecar: {e}"))?;

    thread::sleep(Duration::from_millis(1100));
    match child.try_wait() {
        Ok(None) => Ok(child),
        Ok(Some(status)) => Err(format!("sidecar 进程立即退出: {status}")),
        Err(e) => Err(format!("读取 sidecar 子进程状态失败: {e}")),
    }
}

fn try_start_with_python(
    python: &str,
    workspace: &Path,
    host: &str,
    port: u16,
) -> Result<Child, String> {
    let mut command = Command::new(python);
    command
        .current_dir(workspace)
        .arg("desktop_backend.py")
        .arg("--host")
        .arg(host)
        .arg("--port")
        .arg(port.to_string())
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null());
    apply_hidden_spawn_flags(&mut command);

    let mut child = command
        .spawn()
        .map_err(|e| format!("无法启动进程: {e}"))?;

    // Wait briefly to detect immediate crash.
    thread::sleep(Duration::from_millis(1100));
    match child.try_wait() {
        Ok(None) => Ok(child),
        Ok(Some(status)) => Err(format!("进程立即退出: {status}")),
        Err(e) => Err(format!("读取子进程状态失败: {e}")),
    }
}

fn start_backend_internal(
    backend_state: &BackendState,
    host: Option<String>,
    port: Option<u16>,
    python_path: Option<String>,
    workspace_root: Option<String>,
) -> Result<BackendStatus, String> {
    let workspace = resolve_workspace_root(workspace_root);
    let host = host.unwrap_or_else(|| "127.0.0.1".to_string());
    let port = port.unwrap_or(8765);
    let fallback_workspace_root = workspace_display(workspace.clone());
    let sidecar_hint = backend_state
        .sidecar_hint
        .lock()
        .ok()
        .and_then(|x| x.clone());

    let mut child_guard = backend_state
        .child
        .lock()
        .map_err(|_| "无法获取后端状态锁".to_string())?;

    if let Some(child) = child_guard.as_mut() {
        if check_running(child)? {
            let command_path = backend_state
                .last_backend_command
                .lock()
                .ok()
                .and_then(|x| x.clone())
                .unwrap_or_else(|| "python".to_string());
            let display_workspace = backend_state
                .last_workspace_root
                .lock()
                .ok()
                .and_then(|x| x.clone())
                .unwrap_or_else(|| fallback_workspace_root.clone());

            return Ok(BackendStatus {
                running: true,
                pid: Some(child.id()),
                message: "后端已在运行，无需重复启动".to_string(),
                workspace_root: display_workspace,
                python_path: command_path,
            });
        }
        *child_guard = None;
    }

    let mut errors: Vec<String> = Vec::new();

    let mut backend_exe_candidates: Vec<String> = Vec::new();
    if let Some(candidate) = sidecar_hint {
        push_candidate(&mut backend_exe_candidates, candidate);
    }
    for candidate in collect_backend_exe_candidates(workspace.as_deref()) {
        push_candidate(&mut backend_exe_candidates, candidate);
    }

    for candidate in backend_exe_candidates {
        match try_start_with_backend_exe(&candidate, &host, port) {
            Ok(child) => {
                let pid = child.id();
                *child_guard = Some(child);

                if let Ok(mut x) = backend_state.last_error.lock() {
                    *x = None;
                }
                if let Ok(mut x) = backend_state.last_backend_command.lock() {
                    *x = Some(candidate.clone());
                }

                let exe_parent = PathBuf::from(&candidate)
                    .parent()
                    .map(|p| p.display().to_string())
                    .unwrap_or_else(|| fallback_workspace_root.clone());
                if let Ok(mut x) = backend_state.last_workspace_root.lock() {
                    *x = Some(exe_parent.clone());
                }

                let ready = wait_for_port(&host, port, Duration::from_secs(8));
                let message = if ready {
                    format!("后端 sidecar 已启动，地址 http://{host}:{port}")
                } else {
                    format!("后端 sidecar 已启动，接口预热中: http://{host}:{port}")
                };

                return Ok(BackendStatus {
                    running: true,
                    pid: Some(pid),
                    message,
                    workspace_root: exe_parent,
                    python_path: candidate,
                });
            }
            Err(err) => {
                errors.push(format!("[sidecar {candidate}] {err}"));
            }
        }
    }

    if let Some(workspace) = workspace {
        let candidates = collect_python_candidates(python_path, workspace.as_path());

        for candidate in candidates {
            match try_start_with_python(&candidate, workspace.as_path(), &host, port) {
                Ok(child) => {
                    let pid = child.id();
                    *child_guard = Some(child);
                    if let Ok(mut x) = backend_state.last_error.lock() {
                        *x = None;
                    }
                    if let Ok(mut x) = backend_state.last_backend_command.lock() {
                        *x = Some(candidate.clone());
                    }
                    if let Ok(mut x) = backend_state.last_workspace_root.lock() {
                        *x = Some(workspace.display().to_string());
                    }

                    let ready = wait_for_port(&host, port, Duration::from_secs(8));
                    let message = if ready {
                        format!("后端已启动，地址 http://{host}:{port}")
                    } else {
                        format!("后端进程已启动，接口预热中: http://{host}:{port}")
                    };

                    return Ok(BackendStatus {
                        running: true,
                        pid: Some(pid),
                        message,
                        workspace_root: workspace.display().to_string(),
                        python_path: candidate,
                    });
                }
                Err(err) => {
                    errors.push(format!("[python {candidate}] {err}"));
                }
            }
        }
    } else {
        errors.push("未识别到工作区根目录，且 sidecar 不可用".to_string());
    }

    let message = if errors.is_empty() {
        "后端启动失败：未找到可用 sidecar 或 Python".to_string()
    } else {
        format!("后端启动失败：{}", errors.join(" | "))
    };
    if let Ok(mut x) = backend_state.last_error.lock() {
        *x = Some(message.clone());
    }
    Err(message)
}

fn kill_process_tree(pid: u32) {
    #[cfg(target_os = "windows")]
    {
        let _ = Command::new("taskkill")
            .args(["/PID", &pid.to_string(), "/T", "/F"])
            .status();
    }

    #[cfg(not(target_os = "windows"))]
    {
        let _ = Command::new("kill").args(["-TERM", &pid.to_string()]).status();
    }
}

fn stop_child_process(child_slot: &mut Option<Child>) -> Option<u32> {
    if let Some(mut child) = child_slot.take() {
        let pid = child.id();
        kill_process_tree(pid);
        let _ = child.kill();
        let _ = child.wait();
        Some(pid)
    } else {
        None
    }
}

fn stop_backend_child(state: &BackendState) {
    if let Ok(mut guard) = state.child.lock() {
        let _ = stop_child_process(&mut guard);
    }
}

fn check_running(child: &mut Child) -> Result<bool, String> {
    match child.try_wait() {
        Ok(None) => Ok(true),
        Ok(Some(_status)) => Ok(false),
        Err(e) => Err(format!("检查后端进程状态失败: {e}")),
    }
}

#[tauri::command]
fn backend_status(state: State<BackendState>, workspace_root: Option<String>) -> Result<BackendStatus, String> {
    let fallback_workspace = workspace_display(resolve_workspace_root(workspace_root));
    let mut guard = state
        .child
        .lock()
        .map_err(|_| "无法获取后端状态锁".to_string())?;

    if let Some(child) = guard.as_mut() {
        if check_running(child)? {
            let command_path = state
                .last_backend_command
                .lock()
                .ok()
                .and_then(|x| x.clone())
                .unwrap_or_else(|| "python".to_string());
            let workspace = state
                .last_workspace_root
                .lock()
                .ok()
                .and_then(|x| x.clone())
                .unwrap_or_else(|| fallback_workspace.clone());

            return Ok(BackendStatus {
                running: true,
                pid: Some(child.id()),
                message: "后端运行中".to_string(),
                workspace_root: workspace,
                python_path: command_path,
            });
        }
        *guard = None;
    }

    let last_error = state
        .last_error
        .lock()
        .ok()
        .and_then(|x| x.clone())
        .unwrap_or_default();
    let last_command = state
        .last_backend_command
        .lock()
        .ok()
        .and_then(|x| x.clone())
        .unwrap_or_else(|| "python".to_string());
    let last_workspace = state
        .last_workspace_root
        .lock()
        .ok()
        .and_then(|x| x.clone())
        .unwrap_or_else(|| fallback_workspace.clone());

    let message = if last_error.is_empty() {
        "后端未运行".to_string()
    } else {
        format!("后端未运行: {last_error}")
    };

    Ok(BackendStatus {
        running: false,
        pid: None,
        message,
        workspace_root: last_workspace,
        python_path: last_command,
    })
}

#[tauri::command]
fn start_backend(
    state: State<BackendState>,
    host: Option<String>,
    port: Option<u16>,
    python_path: Option<String>,
    workspace_root: Option<String>,
) -> Result<BackendStatus, String> {
    start_backend_internal(&state, host, port, python_path, workspace_root)
}

#[tauri::command]
fn stop_backend(state: State<BackendState>, workspace_root: Option<String>) -> Result<BackendStatus, String> {
    let fallback_workspace = workspace_display(resolve_workspace_root(workspace_root));
    let mut guard = state
        .child
        .lock()
        .map_err(|_| "无法获取后端状态锁".to_string())?;

    let stopped = stop_child_process(&mut guard);

    if let Ok(mut x) = state.last_error.lock() {
        *x = Some("后端已手动停止".to_string());
    }

    let command_path = state
        .last_backend_command
        .lock()
        .ok()
        .and_then(|x| x.clone())
        .unwrap_or_else(|| "python".to_string());
    let workspace = state
        .last_workspace_root
        .lock()
        .ok()
        .and_then(|x| x.clone())
        .unwrap_or_else(|| fallback_workspace.clone());

    Ok(BackendStatus {
        running: false,
        pid: stopped,
        message: "后端已停止".to_string(),
        workspace_root: workspace,
        python_path: command_path,
    })
}

fn main() {
    tauri::Builder::default()
        .manage(BackendState::default())
        .setup(|app| {
            let state = app.state::<BackendState>();

            let sidecar_name = if cfg!(target_os = "windows") {
                "ThesisLoomBackend-x86_64-pc-windows-msvc.exe"
            } else {
                "ThesisLoomBackend"
            };

            if let Ok(resource_dir) = app.path().resource_dir() {
                let bundled_sidecar = resource_dir.join(sidecar_name);
                if bundled_sidecar.exists() {
                    if let Ok(mut hint) = state.sidecar_hint.lock() {
                        *hint = Some(bundled_sidecar.display().to_string());
                    }
                }
            }

            if let Err(err) = start_backend_internal(
                &state,
                Some("127.0.0.1".to_string()),
                Some(8765),
                None,
                None,
            ) {
                eprintln!("[auto-start] backend start failed: {err}");
            }
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { .. } = event {
                let state = window.state::<BackendState>();
                stop_backend_child(&state);
            }
        })
        .invoke_handler(tauri::generate_handler![backend_status, start_backend, stop_backend])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
