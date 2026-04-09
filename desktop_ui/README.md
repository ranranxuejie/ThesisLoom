# ThesisLoom Desktop UI (Tauri + React)

## 目标

- 使用 Tauri + React 重构原有控制台 UI。
- 复用现有 Python 工作流与状态接口（`backend_api.py`）。
- 通过 `desktop_backend.py` 启动 workflow + dashboard（默认 `127.0.0.1:8765`）。

## 开发启动

在仓库根目录下：

```powershell
cd desktop_ui
npm install
npm run tauri dev
```

## 构建

```powershell
cd desktop_ui
npm run tauri build
```

## 关键说明

- 前端通过 HTTP 调用现有 API：
  - `GET /api/state`
  - `GET/POST /api/inputs`
  - `GET /api/logs`
  - `POST /api/action`
  - `GET/POST /api/input-file`
- Tauri Rust 命令负责启动与停止 `desktop_backend.py`。
- 若 Python 不在 PATH，可在前端或 Rust 命令参数中传入 `python_path`。
