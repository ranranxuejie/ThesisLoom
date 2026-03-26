# ThesisLoom 使用指南（从 0 到可运行）

本项目用于自动化生成论文草稿，并支持断点续跑、审稿改稿循环、文献检索与研究空白生成。

## 1. 环境准备

### 1.1 Python 与 Conda

建议环境：

- Python 3.11+
- Conda（推荐）

示例（Windows PowerShell）：

```powershell
conda create -n ENV2026 python=3.11 -y
conda activate ENV2026
```

### 1.2 安装依赖

项目没有固定 `requirements.txt` 时，可先安装最小依赖：

```powershell
pip install requests rich
```

说明：

- `requests`：OpenAlex 文献检索。
- `rich`：终端 Dashboard（可选但推荐）。

## 2. 项目结构与输入文件

核心目录：

- `workflow.py`：主工作流入口。
- `core/`：节点、状态、提示词等核心逻辑。
- `inputs/`：输入配置与素材。
- `completed_history/`：历史产物与 checkpoint。
- `outputs/`：阶段输出（如 `research_gaps.md`）。
- `state_dashboard.py`：状态看板（Web + 终端模式）。

必须关注的输入：

- `inputs/inputs_safe.json`（优先读取）
- `inputs/inputs.json`（回退读取）
- `inputs/existing_material.md`
- `inputs/existing_sections.md`
- `inputs/user_requirements.md`

提示：

- 工作流会优先读取 `inputs/inputs_safe.json`。
- 如果不存在，会自动回退到 `inputs/inputs.json`。

## 3. 参数配置

### 3.1 配置文件选择逻辑

工作流读取顺序：

1. `inputs/inputs_safe.json`
2. `inputs_safe.json`
3. `inputs.json`
4. `inputs/inputs.json`

推荐只维护 `inputs/inputs_safe.json`（更安全，避免误提交敏感信息）。

### 3.2 推荐最小配置示例

文件：`inputs/inputs_safe.json`

```json
{
  "model": "gemini-3-pro",
  "base_url": "",
  "model_api_key": "",
  "topic": "基于动态强化学习的城市交通信号自适应控制",
  "language": "中文",
  "paper_search_limit": 20,
  "openalex_api_key": "",
  "enable_paper_search": true,
  "related_works_path": "inputs/related_works.md",
  "research_gap_output_path": "outputs/research_gaps.md",
  "research_gaps_refs_dir": "inputs/research_gaps",
  "max_review_rounds": 3
}
```

## 4. 从头运行流程

在项目根目录执行：

```powershell
python workflow.py
```

### 4.1 运行中的关键交互

1. 断点恢复：
- 检测到 checkpoint 时会询问是否继续。

2. 检索阶段：
- 若启用检索，会生成/更新 `related_works.md`。
- 系统会暂停，要求你先补充 `related_works.md`，再输入 `y` 继续。

3. 审稿前自定义要求：
- 进入审稿前会询问是否加载自定义修改建议。
- 默认文件是 `inputs/user_requirements.md`。
- 你可指定其他 `inputs/*.md` 文件。

## 5. 断点与恢复机制

系统会把状态保存到：

- `completed_history/*_checkpoint.json`

当前版本已细化记录以下恢复信息：

- `workflow_phase`
- `current_node`
- `current_major_chapter_id`
- `current_sub_chapter_id`
- `last_checkpoint_reason`
- `last_checkpoint_time`
- `resume_count`

因此重启后可以更准确地从中间位置继续。

## 6. 状态看板（Dashboard）

### 6.1 Web 看板

```powershell
python state_dashboard.py
```

打开：

- `http://127.0.0.1:8765`

特性：

- 每 2 秒自动刷新（可暂停/恢复）
- 显示运行阶段、当前节点、审稿轮次
- 显示总词数、总字符数、自定义要求长度
- 显示检索词预览与章节词数分布

### 6.2 Rich 终端看板

```powershell
python state_dashboard.py --terminal
```

特性：

- 终端实时刷新
- 带图标的关键状态面板
- 适合服务器或纯终端场景

## 7. 常见问题

### 7.1 运行时报缺少 guidance/review 文件

请确认以下文件存在：

- `inputs/guidance/overall_guidance.md`
- `inputs/review/overall_review.md`

### 7.2 检索结果为空

可检查：

- `topic` 是否过于空泛
- 网络是否可访问 OpenAlex
- `paper_search_limit` 是否过小

并可手动补充：

- `inputs/related_works.md`

### 7.3 看板无法启动

- Web 模式：检查 8765 端口是否占用。
- 终端模式：若报 rich 缺失，执行 `pip install rich`。

## 8. 一组可直接复制的命令

```powershell
conda create -n ENV2026 python=3.11 -y
conda activate ENV2026
pip install requests rich
python workflow.py
python state_dashboard.py
python state_dashboard.py --terminal
```

## 9. 建议工作流

1. 先填好 `inputs/inputs_safe.json` 与素材 md 文件。
2. 运行 `python workflow.py`。
3. 检索后手动补充 `inputs/related_works.md`。
4. 在审稿前填写 `inputs/user_requirements.md`（例如：只改方法和实验部分，减少冗余）。
5. 用 Dashboard 跟踪状态，直至最终版本输出。
