# ThesisLoom 构建与打包说明

本文档记录当前仓库的构建入口、打包顺序和常见注意事项。只要是文档修改或纯说明调整，通常不需要重新打 MSI；只有代码或资源产物变化时，才需要重新打包。

## 1. 构建入口

当前推荐的总入口是：

```powershell
.\scripts\build_setup.ps1 -PythonExe ".venv\Scripts\python.exe"
```

这个脚本会依次调用：

- `scripts/build_desktop_bundle.ps1`
- `scripts/build_backend_exe.ps1`
- `npm run tauri build`

如果只改了前端、没有动后端，可跳过后端构建：

```powershell
.\scripts\build_setup.ps1 -PythonExe ".venv\Scripts\python.exe" -SkipBackend
```

## 2. 各脚本职责

### 2.1 `scripts/build_setup.ps1`

用途：

- 桌面端完整构建入口
- 适合产出 release 包和 MSI
- 只负责串联，不直接处理细节

### 2.2 `scripts/build_desktop_bundle.ps1`

用途：

- 构建后端可执行文件
- 复制 backend sidecar 到 `desktop_ui/src-tauri/bin/`
- 安装前端依赖
- 执行 `tauri build`

推荐命令：

```powershell
.\scripts\build_desktop_bundle.ps1 -PythonExe ".venv\Scripts\python.exe" -BackendMode onefile
```

如网络或环境导致 Tauri bundle 失败，脚本会自动回退到：

```powershell
npm run tauri build -- --no-bundle
```

### 2.3 `scripts/build_backend_exe.ps1`

用途：

- 单独打包后端 EXE
- 适合调试 backend 产物是否可独立运行

### 2.4 `scripts/build_exe.ps1`

用途：

- 底层 PyInstaller 封装脚本
- 用于更细粒度地验证 Python 端打包参数

## 3. 产物位置

常见产物路径如下：

- Tauri 应用：`desktop_ui/src-tauri/target/release/thesisloom_desktop.exe`
- MSI：`desktop_ui/src-tauri/target/release/bundle/msi/`
- NSIS：`desktop_ui/src-tauri/target/release/bundle/nsis/`
- 后端 sidecar：`desktop_ui/src-tauri/bin/ThesisLoomBackend-x86_64-pc-windows-msvc.exe`

## 4. 打包前检查

打包前建议确认：

- 已关闭正在运行的 `ThesisLoom`、`ThesisLoomBackend`、`thesisloom_desktop.exe`
- `.venv` 可用，且 `PythonExe` 路径正确
- `npm` 可用
- 如果需要完整 release 包，后端 sidecar 应优先使用 `onefile`

## 5. 常见失败与处理

- `WinError 5`：通常是目标 EXE 正在运行，先关掉进程再打包
- `timeout: global`：通常是 WiX 或网络问题，可先用 `--no-bundle` 出程序，再补 bundle
- sidecar 缺失：重新执行 `build_desktop_bundle.ps1`，确认 `desktop_ui/src-tauri/bin/` 下的后端 EXE 已复制成功

## 6. 推荐流程

1. 先改代码或文档
2. 如果是文档类改动，一般无需重打 MSI
3. 如果是前端/后端代码改动，先运行 `build_setup.ps1`
4. 再检查 `bundle/msi/` 是否生成目标安装包
