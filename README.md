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
注意：不要将 API 密钥等敏感信息提交到版本库；可将 `inputs/inputs.json` 加入 `.gitignore` 或使用环境变量注入。

#### `inputs/inputs.json` 字段说明

- `topic`: 要生成或检索的研究主题或论文标题提示（例："基于强化学习的城市交通信号优化"）。
- `language`: 输出语言（例：`"English"` 或 `"中文"`）。
- `model`: 使用的模型标识（例：`"doubao-seed-2-0-pro-260215"`, `"gpt-5.2"` 等）。
- `max_review_rounds`: 最大审稿/自我修正轮次（整数，默认 3）。
- `paper_search_limit`: 检索时每次请求的论文数量上限（整数，例如 20-50）。
- `openalex_api_key`: 可选，OpenAlex 的 API key，用于加速/提高检索配额；没有则留空。
- `ark_api_key`: 可选，第三方检索或付费服务的 API key（如果项目集成了额外检索源则填写）。
- `base_url`: 可选，模型或检索服务的自定义基地址（例如私有部署时填写）。
- `model_api_key`: 模型服务的 API key（必填或可选取决于所用模型提供商）。

小建议：先填写 `topic`、`language`、`paper_search_limit` 和 `model` 来进行一次检索与初始草稿生成，检索结果出来后再补全 `inputs/related_works.md` 与 `inputs/user_requirements.md`，以保证后续审稿循环更精确。

## 2. 项目结构与输入文件

核心目录：

- `workflow.py`：主工作流入口。
- `core/`：节点、状态、提示词等核心逻辑。
- `inputs/`：输入配置与素材。
- `completed_history/`：历史产物与 checkpoint。
- `outputs/`：阶段输出（如 `research_gaps.md`）。
- `state_dashboard.py`：状态看板（Web + 终端模式）。

必须关注的输入：

- `inputs/inputs.json`
- `inputs/existing_material.md`
- `inputs/existing_sections.md`
- `inputs/user_requirements.md`

提示：

- 工作流默认读取 `inputs/inputs.json`。普通用户只需维护 `inputs/inputs.json` 即可。

## 3. 参数配置

### 3.1 配置文件选择逻辑

工作流默认读取 `inputs/inputs.json`。普通用户只需维护 `inputs/inputs.json` 即可；请不要将 API 密钥等敏感信息提交到版本库。

### 3.2 推荐最小配置示例

首选：维护 `inputs/inputs_safe.json`（将敏感密钥保存在此文件中且不要提交到版本库）。若未提供，系统会回退读取 `inputs/inputs.json`。

回退配置示例（反映当前仓库中 `inputs/inputs.json` 的字段）：

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

注意：不要将 API 密钥等敏感信息提交到版本库；可将 `inputs/inputs.json` 加入 `.gitignore` 或使用环境变量注入。

### 3.3 填写各 Markdown 文件的快速指南

- `inputs/existing_material.md`：粘贴已有论文草稿、笔记或实验记录。用章节标题分隔（如 `# 方法`、`# 实验`），便于自动合并。
- `inputs/existing_sections.md`：列出已有章节标题与短描述；指出哪些章节可复用或需要重写。
- `inputs/user_requirements.md`：明确审稿/修改指令（例如：只修改方法与结果、控制总字数、强调创新点）。写成要点列表，越具体越好。
- `inputs/related_works.md`：手工补充或修订检索阶段生成的文献摘要、关键引用和每篇文献的要点（用于生成 research_gaps）。
- `inputs/guidance/*.md`：对每个章节提供写作指南（风格、目标字数、核心要点），例如 `introduction_guidance.md` 给出引言的要点与推荐结构。
- `inputs/review/*.md`：提供审稿模板或示例审稿意见（便于自动审稿轮次应用统一标准）。

小贴士：先把 `inputs/inputs_safe.json` 里的 `topic`、`language`、`paper_search_limit` 填好，再运行一次检索，随后补充 `inputs/related_works.md`，最后完善 `user_requirements.md` 用于审稿循环。

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
