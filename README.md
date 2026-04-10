# ThesisLoom 使用指南（Desktop + Local Backend）

ThesisLoom 是一个论文写作工作流系统，包含：

- Python 后端：流程编排、断点恢复、审稿改稿循环
- Tauri + React 桌面端：可视化状态、动作确认、输入编辑

当前主链路已不再使用 Streamlit。桌面端启动时会自动拉起后端，关闭桌面端时会自动回收后端进程。

## 0. 项目结构总览

核心目录：

- core/: 状态定义、节点实现、模型调用与项目路径管理
- workflow.py: 主状态机（pre_research/drafting/review_pending/reviewing）
- backend_api.py: HTTP API 实现（桌面端唯一后端入口）
- desktop_backend.py: 启动器（API 服务 + workflow 线程）
- desktop_ui/: Tauri + React 前端与安装包工程
- scripts/: 后端/桌面端打包脚本
- projects/: 项目工作目录（输入、断点、输出、日志）
- history/legacy_frontend/: 旧 Streamlit 历史快照（不参与主链路）

运行关系：

1. Tauri 桌面端拉起 sidecar（ThesisLoomBackend）。
2. sidecar 内启动 `desktop_backend.py`，提供 API 并运行工作流。
3. 前端按轮询 + 动作提交驱动人机协作流程。

## 1. 快速开始

### 1.1 环境准备

推荐：Python 3.11+ + venv

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
```

### 1.2 启动桌面端（推荐）

```powershell
cd desktop_ui
npm install
npm run tauri dev
```

桌面端默认连接：

- 后端地址：http://127.0.0.1:8765
- 后端入口：desktop_backend.py（由 Tauri 自动启动）

### 1.3 仅启动后端（调试用）

```powershell
python desktop_backend.py --host 127.0.0.1 --port 8765 --interaction web
```

兼容入口：

- main.py 已改为兼容代理，内部等价调用 desktop_backend.py。

## 2. 工作流阶段

主状态机：

- pre_research -> drafting -> review_pending -> reviewing -> done

关键约束：

- review_pending/reviewing 仅能在正文（drafting）完整后进入。
- 若检测到正文未完整，会自动回退到 drafting 继续写作。

## 3. 输入文件与配置

核心配置：

- inputs/inputs.json

常用输入文件：

- inputs/existing_material.md（必要）
- inputs/existing_sections.md（可选）
- inputs/related_works.md（可选，可人工补充）
- inputs/revision_requests.md（审稿改稿指令）
- inputs/write_requests.md（全局写作偏好）

示例配置：

```json
{
  "topic": "",
  "language": "English",
  "model": "doubao-seed-2-0-pro-260215",
  "max_review_rounds": 3,
  "paper_search_limit": 30,
  "openalex_api_key": "",
  "ark_api_key": "",
  "base_url": "",
  "model_api_key": ""
}
```

## 4. 断点与产物

关键目录：

- completed_history/*_checkpoint.json
- completed_history/*_checkpoint_history.json
- completed_history/workflow_state_history.json
- completed_history/review_round_*.json

常见状态字段：

- workflow_phase
- current_node
- pending_action
- current_major_chapter_id
- current_sub_chapter_id

## 5. 打包与发布

### 5.1 一体化打包（推荐）

```powershell
./scripts/build_desktop_bundle.ps1
```

默认行为：

- 打包后端 sidecar（ThesisLoomBackend）
- 复制到 desktop_ui/src-tauri/bin
- 构建 Tauri 桌面程序及安装包
- 默认启用体积优化：排除可选 TLS 后端（OpenSSL/cryptography）

可选参数：

```powershell
# 跳过后端重打包
./scripts/build_desktop_bundle.ps1 -SkipBackend

# 后端 onedir
./scripts/build_desktop_bundle.ps1 -BackendMode onedir

# 保留可选 TLS 后端（体积更大）
./scripts/build_desktop_bundle.ps1 -IncludeOptionalTlsBackends
```

### 5.2 仅构建 MSI

```powershell
# 先确保 Rust cargo 在 PATH（否则可能报: failed to get cargo metadata: program not found）
$env:Path = "C:\Users\Administrator\.cargo\bin;$env:Path"

# 推荐：在仓库根目录触发，统一走脚本（后端 + 前端 + MSI）
.\scripts\build_setup.ps1 -PythonExe ".venv\Scripts\python.exe"

# 若仅前端改动，跳过后端重打包
.\scripts\build_setup.ps1 -PythonExe ".venv\Scripts\python.exe" -SkipBackend

# 仅触发 Tauri msi（需确保 sidecar 已是最新）
cd desktop_ui
npm run tauri build -- --bundles msi
```

MSI 输出目录：

- `desktop_ui/src-tauri/target/release/bundle/msi`

发布建议：

- 仅打包 demo 模板项目，避免把个人项目数据、私有模型配置、私有 base_url 写入安装包。

### 5.3 兼容脚本说明

- scripts/build_exe.ps1 已改为兼容入口，会转调 scripts/build_desktop_bundle.ps1。
- 不再维护旧 Streamlit 打包链路。

## 6. 模块命名变更

当前主模块：

- backend_api.py：后端 HTTP API 实现

兼容模块：

- state_dashboard.py：仅保留兼容导入（shim）

## 7. Legacy 说明

Streamlit 前端已移出主运行链路，历史快照保留在：

- history/legacy_frontend/streamlit_app_legacy.py

streamlit_app.py 仅保留弃用提示，不再执行旧前端。
