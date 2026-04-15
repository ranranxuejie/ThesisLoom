# ThesisLoom Desktop UI（Tauri + React）

## 1. 组件定位

desktop_ui 是 ThesisLoom 的桌面前端与壳层，职责如下：

- 提供项目管理、输入编辑、流程动作确认、状态可视化。
- 通过 Tauri 启动本地 Python 后端 sidecar（ThesisLoomBackend）。
- 通过 HTTP API 与后端通信，不直接承载工作流逻辑。

后端工作流主链路：

- pre_research -> drafting -> review_pending -> reviewing -> done
- drafting 内部包含 architecture、planning、writer 等细粒度节点。

## 2. 前端调用 API

- GET /api/state：读取实时状态、运行态与断点快照。
- GET/POST /api/inputs：读取/保存输入参数。
- GET /api/logs：查看关键日志/详细日志。
- POST /api/action：提交待处理动作（例如继续、放行、重试）。
- GET/POST /api/input-file：编辑输入资料文件。
- GET /api/projects、POST /api/project/open、POST /api/project/trash。
- POST /api/project/open-folder：打开当前项目文件夹。

## 3. 本地开发

在仓库根目录执行：

```powershell
cd desktop_ui
npm install
npm run tauri dev
```

默认后端地址：

- http://127.0.0.1:18765

## 4. MSI 构建方法（推荐）

推荐从仓库根目录使用统一脚本构建，自动处理后端 sidecar + 前端打包：

```powershell
# 先确保 Rust cargo 在 PATH（否则可能报: failed to get cargo metadata: program not found）
$env:Path = "C:\Users\Administrator\.cargo\bin;$env:Path"

.\scripts\build_setup.ps1 -PythonExe ".venv\Scripts\python.exe"
```

常用参数：

```powershell
# 仅前端有改动时，跳过后端重打包
.\scripts\build_setup.ps1 -PythonExe ".venv\Scripts\python.exe" -SkipBackend

# 切换后端打包模式（默认 onefile）
.\scripts\build_setup.ps1 -PythonExe ".venv\Scripts\python.exe" -BackendMode onedir

# 启用可选 TLS 后端（体积会变大）
.\scripts\build_setup.ps1 -PythonExe ".venv\Scripts\python.exe" -IncludeOptionalTlsBackends
```

MSI 产物路径：

- desktop_ui/src-tauri/target/release/bundle/msi/

## 5. 仅构建 MSI（高级）

如果你已确认 sidecar 是最新版本，也可以只跑 Tauri：

```powershell
cd desktop_ui
npm run tauri build -- --bundles msi
```

## 6. 运行注意事项

- 关闭桌面应用时，后端会自动回收。
- 发布版请优先使用 demo 模板输入，不要把个人项目或私有模型配置打入安装包。
