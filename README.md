# ThesisLoom 使用指南（Web 驱动版）

ThesisLoom 用于自动生成论文草稿，并支持检索、研究空白生成、审稿改稿循环与断点续跑。

当前版本已去掉流程中的命令行交互，统一通过 Web 页面驱动关键动作。

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

配置文件读取优先级：

1. `inputs/inputs_safe.json`
2. `inputs_safe.json`
3. `inputs.json`
4. `inputs/inputs.json`

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
  "model_api_key": "",
  "manual_revision_path": "inputs/revision_requests.md"
}
```

## 4. 哪些输入是必要的

必要（必须有）：

- `inputs/existing_material.md`：实验材料与结果，核心输入

建议（强烈推荐）：

- `inputs/user_requirements.md`：用户自定义写作/审稿要求

可选（没有也可以运行）：

- `topic`：可留空，系统可在缺省场景下继续流程
- `inputs/existing_sections.md`
- `inputs/related_works.md`（可先自动检索再人工补充）
- 标题相关内容（非必须）

## 5. Web 交互动作

工作流在关键节点会进入“待处理动作”，在页面里直接点击或填写即可：

- 是否执行文献检索
- 检索后确认继续（用于人工补充 related works）
- 进入审稿前确认（可指定加载要求文件）

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

关键状态包括：

- `workflow_phase`
- `current_node`
- `pending_action`
- `last_checkpoint_reason`
- `current_major_chapter_id`
- `current_sub_chapter_id`

## 8. 常见问题

1. Web 页看到“待处理动作”但流程不前进
- 需要在页面动作区提交对应操作（按钮/输入）

2. 检索结果不足
- 增大 `paper_search_limit`
- 检查 `topic` 是否过于泛化
- 人工补充 `inputs/related_works.md`

3. 审稿改稿没有按预期修改
- 检查 `inputs/revision_requests.md` 的 `### SUB x.y` 标注是否与实际小节 ID 一致
- 检查 `inputs/user_requirements.md` 是否为空

## 9. 额外说明

- 已停止对 `inputs/research_gaps/` 目录的自动依赖与自动创建
- `ark_api_key` 已支持从 inputs 配置读取（并兼容环境变量）
- 若仅看监控，也可单独运行：

```powershell
python state_dashboard.py
```
