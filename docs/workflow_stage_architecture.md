# ThesisLoom 工作流阶段架构说明（当前主线）

本文档描述当前生产链路下的阶段定义、进入条件和关键约束。

## 1. 总览

工作流由 workflow_phase 驱动：

- pre_research -> drafting -> review_pending -> reviewing -> done

断点恢复来源：

- completed_history/*_checkpoint.json

## 2. 阶段说明

### 2.1 pre_research

职责：

- 处理前置输入确认
- 生成检索词（node_search_query_builder）
- 执行文献检索（node_search_paper）
- 生成人工可补充的 related works
- 生成 research gaps（node_research_gaps）

主要产物：

- related_works_summary
- research_gaps

完成后进入 drafting。

### 2.2 drafting

职责：

- 章节架构生成（node_architect）
- 架构审查循环（node_architecture_review）
- 大章节规划（node_planner）
- 章节标题与总起（node_chapter_header）
- 章节开篇段（node_chapter_opening）
- 小节正文写作（node_writer）

断点续写能力：

- 支持按 major/sub chapter 粒度恢复
- 若已有 architect/planner/header/opening 产物，会自动跳过对应节点

进入 review_pending 的前置条件：

- 至少产出正文
- 且写作子节完成度满足 outline 要求

### 2.3 review_pending

职责：

- 等待用户确认是否进入审稿循环
- 可加载/更新人工改稿要求文件

确认后切换到 reviewing。

### 2.4 reviewing

职责：

- 总审稿（node_overall_review）
- 大章节审稿（node_major_review）
- 定向改写（node_rewrite）
- 每轮保存 review_round 报告与改稿快照

支持行为：

- 每轮结束后人工确认是否进入下一轮
- 用户可中途停止并保留当前轮结果

结束条件：

- 审稿通过：进入 done
- 达到 max_review_rounds：停止自动循环，等待人工复核

### 2.5 done

职责：

- 标记流程完成
- 保留最终快照与状态

## 3. 审稿前置守卫（关键变更）

当前版本已增加强约束：

- 当 workflow_phase 处于 review_pending/reviewing 时，系统会再次校验正文完成度。
- 若正文不完整，会自动回退到 drafting，并写入 checkpoint 与事件日志。

这避免了“正文未写完就进入审稿循环”的异常路径。

## 4. 断点恢复策略

关键点：

- auto_resume 在当前主线固定启用
- 系统会根据 checkpoint、pending_action、已完成章节、review 标记共同推断恢复阶段
- 若检测到阶段与数据不一致，会执行安全回退（例如回退到 drafting）

## 5. 主要交互动作（Web/API）

常见 pending_action：

- confirm_inputs_ready
- set_enable_auto_title
- set_enable_search
- confirm_related_works
- set_architecture_force_continue
- enter_reviewing
- confirm_next_review_round

## 6. 后端与 UI 关系

当前主链路：

- desktop_backend.py 启动 workflow + backend_api
- Tauri 前端通过 /api/* 与后端通信
- 桌面端关闭时，会自动回收后端子进程

兼容关系：

- state_dashboard.py 保留为 shim，实际实现已迁移到 backend_api.py。
