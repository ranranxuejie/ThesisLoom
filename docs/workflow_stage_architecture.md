# ThesisLoom 工作流阶段架构说明（代码对齐版）

本文档面向希望深入理解 ThesisLoom 运行机制的用户与开发者。内容已按当前主线代码更新。

## 1. 全局模型

ThesisLoom 的主流程是状态机，核心阶段为：

pre_research -> drafting -> review_pending -> reviewing -> done

状态机由 workflow_phase 驱动，并通过 checkpoint + runtime + events 三类文件持续记录执行上下文。

## 2. 启动与运行控制

### 2.1 启动策略

1. workflow 启动时先写入 runtime 状态 starting。
2. 在 Web/桌面交互模式下，默认进入暂停等待，直到收到 resume_workflow 控制指令才真正开始。
3. 启动前会清理遗留 action/control 文件，避免误消费旧指令。

### 2.2 暂停与继续

1. pause_workflow：流程在安全检查点进入 paused。
2. resume_workflow：触发从 checkpoint 续跑，而不是从头重跑。
3. waiting_action、done、stopped、failed 状态下会忽略暂停指令。

### 2.3 自动续跑

1. auto_resume 固定启用。
2. 启动时会在项目内 checkpoint、候选历史 checkpoint 中选择最优恢复点。
3. 恢复后会执行状态修复与阶段重推断，避免“状态字段不一致”导致的错误分支。

## 3. 阶段详解

### 3.1 pre_research

职责：

1. 输入确认与标题策略处理。
2. 可选执行检索链路：query_builder -> search_paper -> related_works 人工确认。
3. 生成或复用 research_gaps。

关键动作：

1. set_enable_auto_title
2. set_enable_search
3. confirm_related_works

关键行为：

1. 若已有有效 topic，默认关闭自动标题并标记 pre_done_title。
2. 若已有 drafting 进度，可跳过 pre_research 并回到 drafting。
3. pre_research 结束后统一切换到 drafting。

### 3.2 drafting

职责：

1. 生成并审查论文架构（node_architect + node_architecture_review）。
2. 按大章节执行 planner/header/opening。
3. 按小节执行 node_writer，逐节落盘。

关键守卫：

1. 若已有 outline，视为架构阶段已完成，可跳过 architect。
2. 架构审查最大轮次由 max_architecture_review_rounds 控制；最后一轮可自动放行。
3. 当仅剩中低优问题，可通过 set_architecture_force_continue 人工放行。

断点恢复粒度：

1. 支持按 current_node + current_major_chapter_id + current_sub_chapter_id 精确恢复。
2. 支持跳过已完成小节、已缓存 planner/header/opening 的节点。
3. 维护 next_steps_plan 作为 drafting 过程可视化待办。

进入 review_pending 条件：

1. 必须至少生成一个正文小节。
2. 若 outline 存在，正文完成度需满足 outline 子节集合约束。

### 3.3 review_pending

职责：

1. 等待 enter_reviewing 人工确认。
2. 准备人工改稿模板文件 revision_requests。
3. 可加载 write_requests 作为审稿改写附加要求。

关键动作：

1. enter_reviewing（可携带 load_requirements、requirements_path、manual_revision_path）。

### 3.4 reviewing

每一轮固定顺序：

1. node_overall_review
2. node_major_review
3. 对 reviewed_sections 执行 node_rewrite
4. 保存轮次报告与改稿快照
5. 等待 confirm_next_review_round 决定是否继续下一轮

当前实现约束：

1. 审稿安全上限强制使用 MAX_REVIEW_ROUNDS_SAFETY_LIMIT = 20。
2. 即使 inputs 里配置了 max_review_rounds，运行时也会被安全上限覆盖。
3. 若审稿未通过但未返回可改写小节，会提前退出循环，防止空转。

结束路径：

1. passed = true：进入 done，保存 final snapshot。
2. 用户在 confirm_next_review_round 选择停止：进入 done，保留当前轮结果。
3. 达到 20 轮安全上限：停止自动循环并等待人工复核。

### 3.5 done

职责：

1. 标记流程已完成。
2. 保留最终快照、checkpoint 与事件记录。

## 4. 审稿前置守卫

当流程位于 review_pending 或 reviewing 时，系统会再次校验 drafting 完整性：

1. 若正文不完整，自动回退到 drafting。
2. 同步写入 checkpoint 与关键事件日志。

该守卫用于阻断“正文未完成就进入审稿”的异常路径。

## 5. 交互动作与 pending_action 清单

常见动作：

1. confirm_inputs_ready
2. set_enable_auto_title
3. set_enable_search
4. confirm_related_works
5. set_architecture_force_continue
6. enter_reviewing
7. confirm_next_review_round
8. retry_after_llm_failure

控制动作（非 pending_action）：

1. pause_workflow
2. resume_workflow

## 6. 运行时文件与产物

核心路径位于 completed_history：

1. *_checkpoint.json：当前可恢复状态。
2. *_checkpoint_history.json：checkpoint 元信息历史。
3. workflow_state_history.json：全局状态历史。
4. workflow_runtime.json：当前 runtime 状态（running/paused/waiting_action 等）。
5. workflow_events.jsonl：事件日志流。
6. workflow_metrics.json：节点耗时与调用统计。
7. review_round_*.json：每轮审稿报告。
8. snapshots/*：版本化正文与状态快照。

## 7. 设计取向

当前工作流的核心设计是“可恢复优先 + 人工确认优先”：

1. 默认暂停启动，避免误跑。
2. 每个关键节点落 checkpoint，保证可续。
3. 关键转移由人工动作驱动，减少失控循环。
4. 审稿阶段加入前置守卫与安全上限，优先保证结果可控。
