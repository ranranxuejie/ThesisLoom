# ThesisLoom Release Notes

- 日期: 2026-04-16
- Tag: v0.2.1
- 发布类型: Desktop（Tauri + Local Python Backend）

## 本版摘要

- 版本号升级到 v0.2.1，前端显示和 Tauri 元数据保持一致。
- 顶部全局暂停/自动审批控制可在任意页面直接操作。
- 默认启动状态固定为暂停，必须手动点击后才会继续流程。
- Release 版重新打包为 MSI，可直接用于桌面安装分发。
- 输入页已将图片描述列表独立为下方 3 列卡片区，并统一其他 tab 卡片为无边框样式，非必填项括号文案统一为（可选）。
- 动作提交在后端短暂离线时会自动尝试恢复并重试，避免“执行检索/跳过”点击无效。
- 修复豆包调用的 API Key 优先级：优先读取当前项目 inputs 配置，避免被旧环境变量覆盖导致 401。
- 新增 Anthropic 格式调用兼容（/v1/messages）并支持前端按供应商自定义 base_url。
- 修复 Anthropic 兼容网关在仅 system 输入时可能返回 400 的问题，改为发送非空 user 消息提升兼容性。
- 修复 LLM 重试断点恢复在 pre_research 阶段误跳到 drafting 的问题，避免旧 outline/文件回填导致状态错乱。
- 新增 LLM 等待/失败/重试/成功的事件日志输出，前端日志可实时看到“等待模型返回”状态。
- README 新增“本地源码运行（无需打包）”章节，补充 Python+Vite 与 Tauri dev 的最小启动步骤。
- 统一 Workflow 详细日志格式并补充 phase/node/重试等上下文，同时将豆包、Base URL、Anthropic 的模型选择固定为指定白名单且 Base URL 预置测试地址与 API Key。
- OpenRouter 模型白名单更新为 z-ai/glm-5.1、x-ai/grok-4.20-multi-agent、anthropic/claude-opus-4.6，并新增基于 OpenRouter 价格表的 USD token 成本统计与前端展示。
- 输出页新增“图片规划节点结果”板块，流程页增加运行态动画反馈（运行波形、节点完成闪动、当前步骤扫描）。

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
