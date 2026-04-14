# ThesisLoom Release Notes

- 日期: 2026-04-10
- Tag: v0.1.0
- 发布类型: Desktop（Tauri + Local Python Backend）

## 本版摘要

- 主链路切换为桌面端，后端 sidecar 自动拉起/自动回收。
- 工作流恢复与动作交互稳定性提升，减少陈旧动作与恢复错位。
- 流程视图与输入输出文案优化，面向非技术用户更易理解。
- MSI 一体化打包可用，默认 demo-only 且包体瘦身。

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
