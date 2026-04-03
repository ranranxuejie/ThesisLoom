# ThesisLoom 使用指南（Web 驱动版）

ThesisLoom 用于自动生成论文草稿，并支持检索、研究空白生成、审稿改稿循环与断点续跑。

当前版本已去掉流程中的命令行交互，统一通过 Web 页面驱动关键动作。

## 0. 本次更新（2026-03）

- 提示词模板改为英文单栈：仅保留 `en` 模板分支，`language` 字段继续用于约束论文输出语言，不再用于模板分支选择。
- 提示词结构重排：关键角色模板在 `<Context>` 后增加关键记忆锚点块，降低长上下文遗忘风险。
- 删除未使用模板映射：移除冗余未调用项，保留运行链路实际使用模板。
- 新增“架构审查循环”：在 `architect -> planner` 之间加入 `architecture_reviewer` 审查节点。
  - 通过规则：无 `high` 严重问题即通过。
  - 人工放行：仅中低优问题时，可在 Web 面板手动放行继续。
  - 轮次上限：默认 3 轮，超限会暂停并保留断点。

## 0.1 增强项（2026-04）

- Streamlit 控制台支持自动刷新（可调间隔），默认用于动态追踪运行状态。
- 右侧流程说明升级为“动态步骤视图 + 动作控制”双标签，展示当前状态、下一步和撰写子节进度。
- checkpoint 写入时会额外追加全量历史：
  - topic 级历史：`*_checkpoint_history.json`
  - 项目级总历史：`completed_history/workflow_state_history.json`
- 打开项目时会自动将断点状态同步到页面会话内存，减少断点重开后的显示错位。
- 预留 EXE 打包脚本：`scripts/build_exe.ps1`。

## 1. 环境准备

建议环境：

- Python 3.11+
- Conda（推荐）

```powershell
conda create -n ENV2026 python=3.11 -y
conda activate ENV2026
pip install requests rich
```

## 2. 启动方式

在项目根目录执行：

```powershell
python main.py
```

启动后：

- 工作流后台自动启动
- Web 控制台地址：`http://127.0.0.1:8765`

## 3. 输入配置

配置文件读取路径：

- `inputs/inputs.json`

`inputs/inputs.json` 推荐字段示例：

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

## 4. 哪些输入是必要的

必要（必须有）：

- `inputs/existing_material.md`：实验材料与结果，核心输入

建议（强烈推荐）：

- `inputs/write_requests.md`：用户自定义写作/审稿要求

可选（没有也可以运行）：

- `topic`：可留空，系统可在缺省场景下继续流程
- `inputs/existing_sections.md`
- `inputs/related_works.md`（可先自动检索再人工补充）
- 标题相关内容（非必须）

## 5. Web 交互动作

工作流在关键节点会进入“待处理动作”，在页面里直接点击或填写即可：

- 是否自动生成标题
- 是否执行文献检索
- 检索后确认继续（用于人工补充 related works）
- 进入审稿前确认（可指定加载要求文件）
- 架构审查中低优问题人工放行（可选）

页面支持文件预览：

- `related_works.md`
- `revision_requests.md`

## 6. 审稿阶段人工改稿指令

新增文件：`inputs/revision_requests.md`

推荐格式：

```markdown
### GLOBAL
- 全局改稿要求

### SUB 2.1
- 只针对 2.1 小节的改稿要求

### SUB 3.2
- 只针对 3.2 小节的改稿要求
```

说明：

- `GLOBAL` 对所有改稿项生效
- `SUB x.y` 只对对应小节生效
- 模型在 rewrite 阶段会把这些人工指令与审稿建议合并使用

## 7. 断点机制

状态与断点文件位于：

- `completed_history/*_checkpoint.json`
- `completed_history/*_checkpoint_history.json`（同一主题全量历史）
- `completed_history/workflow_state_history.json`（项目全量历史）

关键状态包括：

- `workflow_phase`
- `current_node`
- `pending_action`
- `last_checkpoint_reason`
- `current_major_chapter_id`
- `current_sub_chapter_id`

页面行为补充：

- 打开项目后会尝试把最新 checkpoint 快照恢复到 Web 会话内存，保证界面状态与断点一致。

## 8. 常见问题

1. Web 页看到“待处理动作”但流程不前进
- 需要在页面动作区提交对应操作（按钮/输入）

2. 检索结果不足
- 增大 `paper_search_limit`
- 检查 `topic` 是否过于泛化
- 人工补充 `inputs/related_works.md`

3. 审稿改稿没有按预期修改
- 检查 `inputs/revision_requests.md` 的 `### SUB x.y` 标注是否与实际小节 ID 一致
- 检查 `inputs/write_requests.md` 是否为空

## 9. 额外说明

- 研究空白输出文件路径已统一为 `inputs/research_gaps.md`
- `ark_api_key` 已支持从 inputs 配置读取（并兼容环境变量）
- 若仅看监控，也可单独运行：

```powershell
python state_dashboard.py
```

## 10. 打包为 EXE（预留方案）

已提供打包脚本（Windows PowerShell）：

```powershell
./scripts/build_exe.ps1
```

默认产物：

- `dist/ThesisLoom/ThesisLoom.exe`（onedir）

若需要单文件：

```powershell
./scripts/build_exe.ps1 -OneFile
```

单文件产物：

- `dist/ThesisLoom.exe`

说明：

- 主程序已预留 frozen 运行路径（打包后可直接启动 Streamlit 控制台）。
- 首次打包会自动安装/升级 `pyinstaller`。
- 打包后默认以窗口模式启动；也可通过参数切换：

```powershell
./dist/ThesisLoom/ThesisLoom.exe --ui-mode browser
```

## 11. 生成安装程序（Setup）

已新增 Inno Setup 安装脚本，可将 `ThesisLoom.exe` 与 `_internal` 目录一起打包成安装程序。

先确保已完成 EXE 构建：

```powershell
./scripts/build_exe.ps1
```

再生成安装包：

```powershell
./scripts/build_setup.ps1
```

默认产物：

- `dist/installer/ThesisLoomSetup.exe`

如果 Inno Setup 不在默认安装目录，可指定编译器路径：

```powershell
./scripts/build_setup.ps1 -InnoCompiler "C:/Program Files (x86)/Inno Setup 6/ISCC.exe"
```
