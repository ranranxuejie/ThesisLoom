# ThesisLoom 工作流阶段架构说明

本文档用于维护当前工作流阶段定义，明确每个阶段的职责、触发条件、输入与输出，并给出后续优化方向。

## 1. 总体状态机

当前工作流阶段由 `workflow_phase` 驱动，状态转移如下：

- pre_research -> drafting -> review_pending -> reviewing -> done

断点通过 `completed_history/*_checkpoint.json` 恢复。

## 2. 阶段职责与触发条件

### 2.1 pre_research（前置研究准备）

- 主要职责
  - 是否启用文献检索（`enable_paper_search`）
  - 执行检索词生成节点 `node_search_query_builder`
  - 执行文献检索节点 `node_search_paper`
  - 支持人工补充 `inputs/related_works.md`
  - 执行研究空白分析节点 `node_research_gaps`
- 触发条件
  - 初始运行默认进入该阶段
  - 旧断点在 `drafting` 且 `research_gaps` 为空时，迁移回该阶段
- 输入
  - `topic`, `language`, `user_requirements`
  - `existing_material`
  - 文献检索相关配置：`paper_search_limit`, `openalex_api_key`
  - `related_works_path`, `research_gaps_refs_dir`
- 输出
  - `related_works_summary`
  - `research_gaps`
  - 阶段切换到 `drafting`

### 2.2 drafting（写作生成）

- 主要职责
  - 架构节点 `node_architect` 生成章节大纲（支持保底 IMRaD）
  - 规划节点 `node_planner` 为每个大章节生成路由与段落蓝图
  - 章节头节点 `node_chapter_header` 生成专用章节标题与总起句
  - 写作节点 `node_writer` 逐小节生成正文并线性落盘
- 触发条件
  - `workflow_phase == "drafting"`
- 输入
  - `research_gaps`, `existing_material`, `existing_sections`
  - `writing_guidance_library`（含 `overall_guidance`）
  - 上一阶段产物（文献综述与研究空白）
- 输出
  - `outline`
  - `completed_sections`
  - 快照文件 `completed_history/*.md`
  - 阶段切换到 `review_pending`

### 2.3 review_pending（审稿前确认）

- 主要职责
  - 等待用户确认是否进入审稿改稿循环
- 触发条件
  - drafting 全部章节初稿完成后进入
- 输入
  - `completed_sections`
- 输出
  - 用户确认后切换到 `reviewing`
  - 若用户拒绝则保持断点并退出

### 2.4 reviewing（审稿与改写循环）

- 主要职责
  - 总审稿节点 `node_overall_review` 生成大章节审稿计划
  - 大章节审稿节点 `node_major_review` 生成待改写小节列表
  - 重写节点 `node_rewrite` 定向改写
  - 每轮生成审稿报告 `completed_history/review_round_*.json`
- 触发条件
  - 用户在 `review_pending` 确认进入审稿
- 输入
  - `completed_sections`
  - `review_guidance_library`（含 `overall_review`）
  - `max_review_rounds`
- 输出
  - `review_summary`, `major_review_plans`, `reviewed_sections`
  - 改写后快照与断点
  - 通过则进入 `done`；未通过但达最大轮次则停在 reviewing 并人工复核

### 2.5 done（完成）

- 主要职责
  - 标记流程完成
- 触发条件
  - 审稿轮次内 `state.passed == True`
- 输入
  - 审稿循环通过结果
- 输出
  - `workflow_phase = "done"`

## 3. 节点 I/O 摘要

### 3.1 node_search_query_builder

- 输入
  - `topic`, `existing_sections`, `existing_material`, `research_gaps`, `user_requirements`
- 输出
  - `search_queries`（4-8 条检索词句）
- 目标
  - 通过 LLM 生成不过宽也不过窄的高质量检索词句，作为文献检索输入

### 3.2 node_search_paper

- 输入
  - `topic`, `existing_material`, `user_requirements`
  - `paper_search_limit`
  - `openalex_api_key`
- 输出
  - `related_works_summary`
  - `related_works_path` 文件
- 当前检索策略
  - 数据源：仅 OpenAlex
  - 执行方式：遍历 `search_queries`，逐词检索并聚合去重，直到达到 `paper_search_limit`
  - 请求频率：不再施加全局 1 req/s 限制
  - 摘要提取：优先 `abstract_inverted_index`，缺失时回退 `abstract`
  - 写入方式：直接落盘原始论文清单（含摘要），不经过 LLM 总结

### 3.3 node_research_gaps

- 输入
  - `related_works_summary` + `research_gaps_refs_dir`
- 输出
  - `research_gaps`
  - `research_gap_output_path` 文件

### 3.4 node_architect

- 输入
  - `topic`, `existing_material`, `existing_sections`, `research_gaps`, `overall_guidance`
- 输出
  - `outline`
  - 当 LLM 结构化返回失败时使用保底 IMRaD 大纲

### 3.5 node_planner

- 输入
  - 当前大章节信息 + 全局 `outline` + guidance 目录
- 输出
  - 每个小节 `context_routing`、`paragraph_blueprints`、`selected_guidance_key`

### 3.6 node_chapter_header

- 输入
  - 当前大章节信息（`major_chapter_id`, `major_title`, `major_purpose`, `sub_sections`）
  - `topic`, `research_gaps`, `existing_material`, `user_requirements`
- 输出
  - `chapter_header_title`, `chapter_header_lead`
- 审稿与改写联动
  - `node_major_review` 增加章节标题/总起句专审
  - `node_rewrite` 支持 `item_type=chapter_header` 的定向重写

### 3.7 node_writer

- 输入
  - 当前小节蓝图 + 路由后的前文与材料
- 输出
  - `completed_sections` 追加新草稿
  - 小节 `draft_content`

### 3.8 node_overall_review / node_major_review / node_rewrite

- 输入
  - `completed_sections` + review 规则
- 输出
  - 审稿计划、待改写清单、改写后正文

## 4. 当前已知风险与优化点

- 风险 1：LLM 空响应导致局部内容质量波动
  - 现状：已通过安全调用和保底分支避免直接崩溃
- 风险 2：审稿结构化输出不稳定
  - 现状：已在总审稿和大章节审稿提供默认回退

## 5. 已落地能力（章节标题与总起句专项）

当前已实现：

- `node_chapter_header` 在 drafting 阶段（planner 后、writer 前）生成专用章节标题与总起句。
- `node_writer` 在每个大章节首个小节写作时，强制注入章节标题与总起句，保持格式一致。
- `node_major_review` 增加章节标题/总起句专审。
- `node_rewrite` 增加 `item_type=chapter_header` 分支，支持对章节标题与总起句定向重写。

该改造已实现“标题层”和“正文层”解耦，能够提升版式控制、审稿可解释性与改写精度。
