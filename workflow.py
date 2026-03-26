from core.state import (
    PaperWriterState,
    resolve_inputs_path,
    build_output_paths,
    save_markdown_snapshot,
    save_versioned_snapshot,
    save_state_checkpoint,
    load_state_checkpoint,
)
from core.nodes import (
    node_search_paper,
    node_research_gaps,
    node_architect,
    node_planner,
    node_chapter_header,
    node_writer,
    node_overall_review,
    node_major_review,
    node_rewrite,
)
import json
import os
import re

os.makedirs("completed_history", exist_ok=True)
initial_inputs = json.load(open(resolve_inputs_path(), "r", encoding="utf-8-sig"))
temp_state = PaperWriterState(initial_inputs)
output_path, checkpoint_path = build_output_paths(
    temp_state.model,
    temp_state.topic,
    temp_state.get_prompt_language(),
)


def _checkpoint(state: PaperWriterState, reason: str, node: str = "", major_id: str = "", sub_id: str = "") -> None:
    state.mark_progress(node=node, reason=reason, major_id=major_id, sub_id=sub_id)
    save_state_checkpoint(state, checkpoint_path)


def _read_text(path: str) -> str:
    if not path or (not os.path.exists(path)):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def _maybe_apply_review_requirements(state: PaperWriterState) -> None:
    print("| 审稿前可加载自定义修改建议文件（默认: inputs/user_requirements.md）")
    apply_req = input("| 是否加载/刷新该文件内容到 user_requirements？(y/n): ").strip().lower()
    if apply_req not in ("y", "yes", "是"):
        return

    req_path = input("| 输入文件路径（直接回车使用默认）: ").strip() or "inputs/user_requirements.md"
    if not os.path.exists(req_path):
        with open(req_path, "w", encoding="utf-8") as f:
            f.write("# 审稿前自定义修改建议\n\n请写下你希望重点修改或审查的内容。\n")
        print(f"| 未找到文件，已自动创建模板: {req_path}")
        confirm = input("| 请编辑后再输入 y 继续加载（其他键跳过）: ").strip().lower()
        if confirm not in ("y", "yes", "是"):
            return

    content = _read_text(req_path)
    if not content:
        print(f"| [WARN] 文件为空，跳过加载: {req_path}")
        return

    state.user_requirements = content
    print(f"| 已加载自定义要求: {req_path} (长度: {len(content)} 字符)")

if os.path.exists(checkpoint_path):
    resume = input(f"检测到断点文件 {checkpoint_path}，是否继续断点？(y/n): ").strip().lower()
    if resume in ("y", "yes", "是"):
        checkpoint_data = load_state_checkpoint(checkpoint_path)
        state = PaperWriterState(checkpoint_data, input_from_md=False)
        state.resume_count = int(getattr(state, "resume_count", 0)) + 1
        _checkpoint(state, reason="resume_from_checkpoint", node="resume")
        print(f"[OK] 已从断点恢复，当前阶段：{state.workflow_phase}")
    else:
        state = temp_state
else:
    state = temp_state

# 迁移逻辑：旧断点默认从 drafting 开始，新流程在缺少 research_gaps 时先进入前置阶段
if state.workflow_phase == "drafting" and not str(getattr(state, "research_gaps", "")).strip():
    state.workflow_phase = "pre_research"
    _checkpoint(state, reason="migrate_to_pre_research", node="phase_migration")

if state.workflow_phase == "pre_research":
    if state.enable_paper_search is None:
        need_search = input("是否需要先检索相关文献？(y/n): ").strip().lower()
        state.enable_paper_search = need_search in ("y", "yes", "是")
        _checkpoint(state, reason="set_enable_paper_search", node="pre_research")

    if state.enable_paper_search:
        related_works_exists = os.path.exists(state.related_works_path) and os.path.getsize(state.related_works_path) > 0
        if not related_works_exists:
            state = node_search_paper(state)
            _checkpoint(state, reason="node_search_paper_done", node="node_search_paper")

        print(f"| 文献检索已完成，请先补充 {state.related_works_path}")
        continue_now = input("| 完成补充后按 y 继续生成 research_gaps.md (其他键暂停): ").strip().lower()
        if continue_now not in ("y", "yes", "是"):
            print(f"| 已暂停。可稍后重新运行并从断点继续：{checkpoint_path}")
            raise SystemExit(0)
        state.wait_for_manual_related_works = False
        _checkpoint(state, reason="manual_related_works_confirmed", node="pre_research")

    state = node_research_gaps(state)
    state.workflow_phase = "drafting"
    _checkpoint(state, reason="node_research_gaps_done", node="node_research_gaps")

if state.workflow_phase == "drafting":
    _checkpoint(state, reason="enter_drafting_phase", node="drafting")
    state = node_architect(state)
    _checkpoint(state, reason="node_architect_done", node="node_architect")
    if not isinstance(state.outline, list):
        raise RuntimeError("architect 未返回章节列表，请检查模型输出格式。")

    # Guardrail: prevent malformed giant outlines from breaking the pipeline.
    if len(state.outline) > 12:
        print(f"[WARN] 架构输出章节数异常({len(state.outline)})，已自动截断到前12个大章节。")
        state.outline = state.outline[:12]

    writing_queue = sorted(state.outline, key=lambda x: x["writing_order"])

    for major_chapter in writing_queue:
        major_id = str(major_chapter.get("major_chapter_id", "")).strip()
        _checkpoint(state, reason="enter_major_chapter", node="major_loop", major_id=major_id, sub_id="")
        print(f"\n==================================================")
        print(f"[RUN] 进入大章节: {major_chapter['major_title']} (优先级: {major_chapter['writing_order']})")
        print(f"==================================================")

        state = node_planner(state, major_chapter)
        _checkpoint(state, reason="node_planner_done", node="node_planner", major_id=major_id, sub_id="")
        state = node_chapter_header(state, major_chapter)
        _checkpoint(state, reason="node_chapter_header_done", node="node_chapter_header", major_id=major_id, sub_id="")
        for sub_section in major_chapter.get("sub_sections", []):
            sub_id = str(sub_section.get("sub_chapter_id", "")).strip()
            _checkpoint(state, reason="before_node_writer", node="node_writer", major_id=major_id, sub_id=sub_id)
            state = node_writer(state, major_chapter, sub_section)
            save_markdown_snapshot(state, output_path)
            _checkpoint(state, reason="node_writer_done", node="node_writer", major_id=major_id, sub_id=sub_id)

    state.workflow_phase = "review_pending"
    state.current_major_chapter_id = ""
    state.current_sub_chapter_id = ""
    draft_snapshot = save_versioned_snapshot(state, output_path, "draft_initial")
    _checkpoint(state, reason="draft_initial_saved", node="drafting_completed")
    print(f"| 初稿快照已保存: {draft_snapshot}")
    print("[OK] 所有章节初稿完成，已保存断点。")

if state.workflow_phase == "review_pending":
    _maybe_apply_review_requirements(state)
    _checkpoint(state, reason="review_requirements_checked", node="review_pending")
    proceed = input("初稿已完成，是否进入审稿-改稿循环？(y/n): ").strip().lower()
    if proceed not in ("y", "yes", "是"):
        print(f"[PAUSE] 已暂停。可稍后重新运行并从断点继续：{checkpoint_path}")
        raise SystemExit(0)
    state.workflow_phase = "reviewing"
    _checkpoint(state, reason="enter_reviewing_phase", node="reviewing")

if state.workflow_phase == "reviewing":
    print("[RUN] 开始审稿阶段")
    for _ in range(state.max_review_rounds):
        _checkpoint(state, reason="before_overall_review", node="node_overall_review")
        state = node_overall_review(state)
        _checkpoint(state, reason="node_overall_review_done", node="node_overall_review")
        state = node_major_review(state)
        _checkpoint(state, reason="node_major_review_done", node="node_major_review")

        safe_topic = re.sub(r'[\\/*?:"<>|]', '', state.topic).replace(" ", "_")
        review_report_path = f"completed_history/review_round_{state.review_round}_{safe_topic}.json"
        with open(review_report_path, "w", encoding="utf-8") as f:
            json.dump({
                "round": state.review_round,
                "passed": state.passed,
                "summary": state.review_summary,
                "major_review_plans": state.major_review_plans,
                "sections_to_revise": state.reviewed_sections,
            }, f, ensure_ascii=False, indent=2)

        if state.passed:
            state.workflow_phase = "done"
            final_snapshot = save_versioned_snapshot(state, output_path, f"final_round_{state.review_round}")
            _checkpoint(state, reason="review_passed_final_saved", node="done")
            print(f"| 终稿快照已保存: {final_snapshot}")
            print("[OK] 所有章节审稿通过")
            break

        if not state.reviewed_sections:
            print("[WARN] 审稿未通过但未返回可重写小节，提前结束循环以避免空转。")
            no_rewrite_snapshot = save_versioned_snapshot(state, output_path, f"review_round_{state.review_round}_no_rewrite")
            print(f"| 审稿快照已保存: {no_rewrite_snapshot}")
            _checkpoint(state, reason="no_rewrite_sections_break", node="reviewing")
            break

        for sub_section in state.reviewed_sections:
            sub_id = str(sub_section.get("sub_chapter_id", "")).strip()
            _checkpoint(state, reason="before_node_rewrite", node="node_rewrite", sub_id=sub_id)
            state = node_rewrite(state, sub_section)
            print(f"[OK] 子节 {sub_section['sub_chapter_id']} 重写完成")
            _checkpoint(state, reason="node_rewrite_done", node="node_rewrite", sub_id=sub_id)

        round_snapshot = save_versioned_snapshot(state, output_path, f"rewrite_round_{state.review_round}")
        _checkpoint(state, reason="rewrite_round_snapshot_saved", node="reviewing")
        print(f"| 改稿快照已保存: {round_snapshot}")
        print("[OK] 所有章节重写完成")
    else:
        print(f"[WARN] 达到最大审稿轮数 {state.max_review_rounds}，请人工复核。")