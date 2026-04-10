# ThesisLoom Release Notes

发布日期: 2026-04-09
版本类型: Desktop 稳定发布（Tauri + Local Python Backend）

## 亮点

- 桌面端主链路正式切换为 Tauri + React。
- Python 后端统一为本地 sidecar 运行模式，桌面端可自动拉起并在关闭时自动回收。
- 工作流恢复与动作交互稳定性大幅提升，减少“按钮点击后无响应/显示旧状态”的问题。

## 主要更新

### 1) 架构与模块

- 旧 Streamlit 前端不再作为主链路。
- 后端 API 主模块统一为 `backend_api.py`，保留兼容层以降低迁移风险。
- 桌面后端入口为 `desktop_backend.py`（工作流线程 + 本地 API 服务）。

### 2) 工作流与状态机

- 新增/增强 drafting 细粒度恢复：按 major/sub/node 级别恢复，避免 LLM 重试后回退到过粗阶段。
- 流程视图细化：architect、planner、正文撰写阶段分离展示。
- 正文撰写进度可内嵌展示到流程卡片中。
- 审稿入口约束更严格：仅在正文完成后允许进入 review_pending/reviewing。

### 3) 交互与可用性

- 动作按钮响应链路增强：提交成功后即时刷新状态与日志。
- 清理过期 pending_action 显示，避免用户看到陈旧动作按钮。
- 项目管理新增：
  - 移至回收站
  - 一键打开项目文件夹
- 输入区交互优化：
  - 必填项标注 `*`
  - 输入资料文件名去掉 `inputs/` 前缀显示
  - 部分冗余按钮与信息精简
- 侧边栏信息优化（当前项目、阶段、Tokens 使用量）。
- 修复桌面端“内容较多无法下滚”与“容器被强制等高”问题，恢复自适应高度。

### 4) 打包与发布

- 一体化打包脚本增强：`scripts/build_setup.ps1` / `scripts/build_desktop_bundle.ps1`。
- 修复打包脚本参数转发问题，提升构建稳定性。
- 后端 sidecar 默认 onefile 输出，便于分发。
- 发布包瘦身：默认排除可选 TLS 后端，减小安装包体积。
- 安装包数据安全策略：默认仅携带 demo 模板，避免打入个人项目与私有配置。
- 应用图标可嵌入安装包。

## MSI 构建（发布建议）

```powershell
# 仓库根目录执行
.\scripts\build_setup.ps1 -PythonExe ".venv/Scripts/python.exe"
```

可选参数：

```powershell
# 仅前端有改动时
.\scripts\build_setup.ps1 -PythonExe ".venv/Scripts/python.exe" -SkipBackend

# 后端打包模式切换
.\scripts\build_setup.ps1 -PythonExe ".venv/Scripts/python.exe" -BackendMode onedir

# 保留可选 TLS 后端（体积更大）
.\scripts\build_setup.ps1 -PythonExe ".venv/Scripts/python.exe" -IncludeOptionalTlsBackends
```

MSI 产物目录:

- `desktop_ui/src-tauri/target/release/bundle/msi/`

## 升级注意事项

- 旧 Streamlit 运行入口不再作为正式发布链路。
- 若历史项目来自旧版本，建议先用 demo 模板验证，再迁移私有配置。
- 若你启用 `IncludeOptionalTlsBackends`，安装包体积会显著增加。

## 已知说明

- 首次启动若本机安全策略拦截本地端口监听，请允许本地程序通信后重试。
- 若你使用自定义模型/URL/密钥，请通过运行时输入配置，不建议固化进安装包。
