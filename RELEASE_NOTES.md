# ThesisLoom Release Notes

- 日期: 2026-04-15
- Tag: v0.2.0
- 发布类型: Desktop（Tauri + Local Python Backend）

## 本版摘要

- 版本号升级到 v0.2.0，前端显示和 Tauri 元数据保持一致。
- 顶部全局暂停/自动审批控制可在任意页面直接操作。
- 默认启动状态固定为暂停，必须手动点击后才会继续流程。
- Release 版重新打包为 MSI，可直接用于桌面安装分发。

## 快速构建

```powershell
# 若终端找不到 cargo，请先补 PATH
$env:Path = "C:\Users\Administrator\.cargo\bin;$env:Path"

# 全量打包（后端 + 前端 + MSI）
.\scripts\build_setup.ps1 -PythonExe ".venv\Scripts\python.exe"

# 仅前端改动时
.\scripts\build_setup.ps1 -PythonExe ".venv\Scripts\python.exe" -SkipBackend
```

## 产物目录

- MSI: `desktop_ui/src-tauri/target/release/bundle/msi/`
- NSIS: `desktop_ui/src-tauri/target/release/bundle/nsis/`
