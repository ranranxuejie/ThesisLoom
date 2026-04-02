from core.state import (
    PaperWriterState,
    resolve_inputs_path,
    build_output_paths,
    load_topic_from_inputs_json,
    find_latest_checkpoint_for_resume,
    output_path_from_checkpoint,
    migrate_paths_after_topic_update,
    save_markdown_snapshot,
    save_versioned_snapshot,
    save_state_checkpoint,
    load_state_checkpoint,
)
from core.nodes import (
    node_title_builder,
    node_search_query_builder,
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
import time
from datetime import datetime
from threading import Event
from typing import Any, Dict, Optional


ACTION_FILE = "completed_history/workflow_actions.json"
RUNTIME_FILE = "completed_history/workflow_runtime.json"
EVENTS_FILE = "completed_history/workflow_events.jsonl"
METRICS_FILE = "completed_history/workflow_metrics.json"


class WorkflowStopRequested(Exception):
    pass


def _read_metrics() -> Dict[str, Any]:
    if not os.path.exists(METRICS_FILE):
        return {
            "updated_at": "",
            "workflow_started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "totals": {
                "step_calls": 0,
                "total_step_seconds": 0.0,
            },
            "steps": {},
        }
    try:
        with open(METRICS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("steps", {})
            data.setdefault("totals", {"step_calls": 0, "total_step_seconds": 0.0})
            return data
    except Exception:
        pass
    return {
        "updated_at": "",
        "workflow_started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "totals": {
            "step_calls": 0,
            "total_step_seconds": 0.0,
        },
        "steps": {},
    }


def _write_metrics(data: Dict[str, Any]) -> None:
    os.makedirs("completed_history", exist_ok=True)
    data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(METRICS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _record_step_metric(step: str, node: str, duration_seconds: float, status: str = "ok", phase: str = "") -> None:
    data = _read_metrics()
    steps = data.setdefault("steps", {})
    item = steps.setdefault(
        step,
        {
            "step": step,
            "node": node,
            "count": 0,
            "success": 0,
            "failed": 0,
            "total_seconds": 0.0,
            "avg_seconds": 0.0,
            "last_seconds": 0.0,
            "last_status": "",
            "last_phase": "",
            "last_time": "",
        },
    )
    item["node"] = node
    item["count"] = int(item.get("count", 0)) + 1
    if status == "ok":
        item["success"] = int(item.get("success", 0)) + 1
    else:
        item["failed"] = int(item.get("failed", 0)) + 1
    item["total_seconds"] = round(float(item.get("total_seconds", 0.0)) + float(duration_seconds), 4)
    item["last_seconds"] = round(float(duration_seconds), 4)
    item["avg_seconds"] = round(item["total_seconds"] / max(1, int(item.get("count", 1))), 4)
    item["last_status"] = status
    item["last_phase"] = phase
    item["last_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    totals = data.setdefault("totals", {"step_calls": 0, "total_step_seconds": 0.0})
    totals["step_calls"] = int(totals.get("step_calls", 0)) + 1
    totals["total_step_seconds"] = round(float(totals.get("total_step_seconds", 0.0)) + float(duration_seconds), 4)

    _write_metrics(data)


def _timed_call(step: str, metric_node: str, phase: str, fn, *args, **kwargs):
    started = time.perf_counter()
    status = "ok"
    try:
        return fn(*args, **kwargs)
    except Exception:
        status = "failed"
        raise
    finally:
        elapsed = time.perf_counter() - started
        _record_step_metric(step=step, node=metric_node, duration_seconds=elapsed, status=status, phase=phase)
        _append_event("detail", f"metric: {step} {elapsed:.3f}s", node=metric_node, phase=phase, status=status)


def _write_runtime_status(status: str, message: str = "", **extra: Any) -> None:
    payload: Dict[str, Any] = {
        "status": str(status),
        "message": str(message),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    payload.update(extra)
    os.makedirs("completed_history", exist_ok=True)
    with open(RUNTIME_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _append_event(level: str, message: str, **extra: Any) -> None:
    payload: Dict[str, Any] = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "level": str(level),
        "message": str(message),
    }
    payload.update(extra)
    os.makedirs("completed_history", exist_ok=True)
    with open(EVENTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _check_stop(stop_event: Optional[Event]) -> None:
    if stop_event is not None and stop_event.is_set():
        raise WorkflowStopRequested("workflow stop requested")


def _checkpoint(
    state: PaperWriterState,
    checkpoint_path: str,
    reason: str,
    node: str = "",
    major_id: str = "",
    sub_id: str = "",
) -> None:
    state.runtime_checkpoint_path = str(checkpoint_path)
    state.mark_progress(node=node, reason=reason, major_id=major_id, sub_id=sub_id)
    save_state_checkpoint(state, checkpoint_path)
    _append_event(
        "detail",
        f"checkpoint: {reason}",
        node=state.current_node,
        major_id=state.current_major_chapter_id,
        sub_id=state.current_sub_chapter_id,
        phase=getattr(state, "workflow_phase", ""),
    )


def _read_text(path: str) -> str:
    if not path or (not os.path.exists(path)):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def _consume_action(expected_action: str) -> Dict[str, Any] | None:
    if not os.path.exists(ACTION_FILE):
        return None
    try:
        with open(ACTION_FILE, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception:
        return None

    if str(payload.get("action", "")).strip() != expected_action:
        return None

    try:
        os.remove(ACTION_FILE)
    except Exception:
        pass
    return payload


def _wait_for_action(
    state: PaperWriterState,
    checkpoint_path: str,
    action_name: str,
    prompt: str,
    node: str,
    interaction_mode: str = "web",
    stop_event: Optional[Event] = None,
    poll_seconds: float = 1.0,
) -> Dict[str, Any]:
    state.pending_action = action_name
    state.pending_action_message = prompt
    _checkpoint(state, checkpoint_path, reason=f"wait_{action_name}", node=node)
    _write_runtime_status("waiting_action", prompt, pending_action=action_name, node=node, interaction_mode=interaction_mode)
    _append_event("key", f"等待动作: {action_name}", node=node, interaction_mode=interaction_mode)

    if interaction_mode == "cli":
        print(f"| [CLI] {prompt}")
        if action_name == "set_enable_auto_title":
            raw = input("| 是否自动生成标题？[Y/n]: ").strip().lower()
            action = {"action": action_name, "value": raw not in {"n", "no", "0", "false"}}
        elif action_name == "set_enable_search":
            raw = input("| 是否执行文献检索？[y/N]: ").strip().lower()
            action = {"action": action_name, "value": raw in {"y", "yes", "1", "true"}}
        elif action_name == "confirm_related_works":
            input(f"| 请补充 {state.related_works_path} 后按回车继续...")
            action = {"action": action_name}
        elif action_name == "enter_reviewing":
            load_req = input("| 加载自定义要求文件？[Y/n]: ").strip().lower() not in {"n", "no", "0", "false"}
            req_path = input("| 自定义要求文件路径(默认 inputs/user_requirements.md): ").strip() or "inputs/user_requirements.md"
            manual_path = input("| 人工改稿指令文件路径(默认 inputs/revision_requests.md): ").strip() or "inputs/revision_requests.md"
            action = {
                "action": action_name,
                "load_requirements": load_req,
                "requirements_path": req_path,
                "manual_revision_path": manual_path,
            }
        else:
            input("| 按回车继续...")
            action = {"action": action_name}

        state.pending_action = ""
        state.pending_action_message = ""
        _checkpoint(state, checkpoint_path, reason=f"action_{action_name}_received", node=node)
        _write_runtime_status("running", f"已接收动作: {action_name}", node=node, interaction_mode=interaction_mode)
        _append_event("key", f"已接收动作: {action_name}", node=node, interaction_mode=interaction_mode)
        return action

    while True:
        _check_stop(stop_event)
        action = _consume_action(action_name)
        if action is not None:
            state.pending_action = ""
            state.pending_action_message = ""
            _checkpoint(state, checkpoint_path, reason=f"action_{action_name}_received", node=node)
            _write_runtime_status("running", f"已接收动作: {action_name}", node=node, interaction_mode=interaction_mode)
            _append_event("key", f"已接收动作: {action_name}", node=node, interaction_mode=interaction_mode)
            return action
        time.sleep(poll_seconds)


def _apply_requirements_from_file(state: PaperWriterState, path: str) -> None:
    text = _read_text(path)
    if text:
        state.user_requirements = text


def _completed_sub_id_set(state: PaperWriterState) -> set[str]:
    done = set()
    for sec in (getattr(state, "completed_sections", []) or []):
        sid = str((sec or {}).get("sub_chapter_id", "")).strip()
        if sid:
            done.add(sid)
    return done


def _rewrite_done_sub_id_set(state: PaperWriterState) -> set[str]:
    values = getattr(state, "rewrite_done_sub_ids", []) or []
    return {str(x).strip() for x in values if str(x).strip()}


def _ensure_manual_revision_template(path: str) -> None:
    if os.path.exists(path):
        return
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    template = (
        "# Manual Revision Instructions\n\n"
        "使用以下格式提供人工改稿建议：\n\n"
        "### GLOBAL\n"
        "- 全文要求（例如：语气更学术，减少口语表达）\n\n"
        "### SUB 2.1\n"
        "- 2.1 小节补充算法复杂度与边界条件\n\n"
        "### SUB 3.2\n"
        "- 3.2 小节增加与基线方法误差对比\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(template)


def _parse_manual_revision_notes(notes: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    current_key = ""
    blocks = str(notes or "").splitlines()

    for line in blocks:
        stripped = line.strip()
        m_global = re.match(r"^###\s*GLOBAL\s*$", stripped, flags=re.IGNORECASE)
        if m_global:
            current_key = "__global__"
            result.setdefault(current_key, "")
            continue

        m_sub = re.match(r"^###\s*SUB\s+([0-9]+\.[0-9]+)\s*$", stripped, flags=re.IGNORECASE)
        if m_sub:
            current_key = m_sub.group(1)
            result.setdefault(current_key, "")
            continue

        if current_key:
            if result[current_key]:
                result[current_key] += "\n"
            result[current_key] += line

    return {k: v.strip() for k, v in result.items() if str(v).strip()}


def _attach_manual_revision_instruction(state: PaperWriterState, review_item: Dict[str, Any]) -> Dict[str, Any]:
    sub_id = str(review_item.get("sub_chapter_id", "")).strip()
    if not sub_id:
        return review_item

    notes = _parse_manual_revision_notes(getattr(state, "manual_revision_notes", ""))
    combined = []
    if "__global__" in notes:
        combined.append(f"[GLOBAL]\n{notes['__global__']}")
    if sub_id in notes:
        combined.append(f"[SUB {sub_id}]\n{notes[sub_id]}")

    if combined:
        review_item = dict(review_item)
        review_item["manual_instruction"] = "\n\n".join(combined)
    return review_item


def _wait_for_retry_action(stop_event: Optional[Event], interaction_mode: str = "web", poll_seconds: float = 1.0) -> bool:
    if interaction_mode == "cli":
        print("| [CLI] LLM 调用失败已暂停。按回车继续重试（或 Ctrl+C 终止）。")
        input()
        return True

    _write_runtime_status(
        "waiting_action",
        "LLM 连续重试失败，等待前端点击“继续重试”。",
        interaction_mode=interaction_mode,
        pending_action="retry_after_llm_failure",
        pending_action_message="请在前端点击‘继续重试’，系统将从最近断点自动续跑。",
    )

    while True:
        _check_stop(stop_event)
        action = _consume_action("retry_after_llm_failure")
        if action is not None:
            _write_runtime_status("running", "已接收动作: retry_after_llm_failure", interaction_mode=interaction_mode)
            _append_event("key", "已接收动作: retry_after_llm_failure", interaction_mode=interaction_mode)
            return True
        time.sleep(poll_seconds)


def run_workflow(stop_event: Optional[Event] = None, interaction_mode: str = "web", force_resume: bool = False) -> None:
    interaction_mode = (interaction_mode or "web").strip().lower()
    if interaction_mode not in {"web", "cli"}:
        interaction_mode = "web"

    os.makedirs("completed_history", exist_ok=True)
    _write_runtime_status("starting", "workflow 正在启动", interaction_mode=interaction_mode)
    _append_event("key", "workflow 启动", interaction_mode=interaction_mode)

    initial_inputs = json.load(open(resolve_inputs_path(), "r", encoding="utf-8-sig"))
    temp_state = PaperWriterState(initial_inputs)
    output_path, checkpoint_path = build_output_paths(
        temp_state.model,
        temp_state.topic,
        temp_state.get_prompt_language(),
    )

    auto_resume = bool(force_resume) or bool(initial_inputs.get("auto_resume", True))
    if auto_resume and (not os.path.exists(checkpoint_path)):
        fallback_checkpoint = find_latest_checkpoint_for_resume(temp_state.model, temp_state.get_prompt_language())
        if fallback_checkpoint:
            checkpoint_path = fallback_checkpoint
            fallback_output = output_path_from_checkpoint(fallback_checkpoint)
            if fallback_output:
                output_path = fallback_output

    if os.path.exists(checkpoint_path) and auto_resume:
        checkpoint_data = load_state_checkpoint(checkpoint_path)
        state = PaperWriterState(checkpoint_data, input_from_md=False)
        state.runtime_checkpoint_path = str(checkpoint_path)
        state.resume_count = int(getattr(state, "resume_count", 0)) + 1
        _checkpoint(state, checkpoint_path, reason="resume_from_checkpoint", node="resume")
        print(f"| 已从断点恢复，当前阶段: {state.workflow_phase}")
        _write_runtime_status("running", f"已恢复到 {state.workflow_phase}", interaction_mode=interaction_mode)
        _append_event("key", f"断点恢复: {state.workflow_phase}", interaction_mode=interaction_mode)
    else:
        state = temp_state
        state.runtime_checkpoint_path = str(checkpoint_path)
        _write_runtime_status("running", "从初始输入启动", interaction_mode=interaction_mode)
        _append_event("key", "从初始输入启动", interaction_mode=interaction_mode)

    if (not os.path.exists(checkpoint_path)) and interaction_mode == "web":
        _timed_call(
            "wait_confirm_inputs_ready",
            "pre_start",
            str(getattr(state, "workflow_phase", "")),
            _wait_for_action,
            state,
            checkpoint_path,
            action_name="confirm_inputs_ready",
            prompt="请在 Web 面板编辑并保存 inputs.json，完成后点击开始工作流。",
            node="pre_start",
            interaction_mode=interaction_mode,
            stop_event=stop_event,
        )
        reloaded_inputs = json.load(open(resolve_inputs_path(), "r", encoding="utf-8-sig"))
        state.topic = str(reloaded_inputs.get("topic", state.topic)).strip()
        state.model = str(reloaded_inputs.get("model", state.model)).strip() or state.model
        state.language = str(reloaded_inputs.get("language", state.language)).strip() or state.language
        state.user_requirements = str(reloaded_inputs.get("user_requirements", state.user_requirements))
        _checkpoint(state, checkpoint_path, reason="inputs_confirmed", node="pre_start")
        _append_event("key", "inputs 已确认，开始流程", interaction_mode=interaction_mode)

    # 迁移逻辑：旧断点默认从 drafting 开始，新流程在缺少 research_gaps 时先进入前置阶段
    if state.workflow_phase == "drafting" and not str(getattr(state, "research_gaps", "")).strip():
        state.workflow_phase = "pre_research"
        _checkpoint(state, checkpoint_path, reason="migrate_to_pre_research", node="phase_migration")

    if state.workflow_phase == "pre_research":
        if str(getattr(state, "topic", "") or "").strip().lower() in {"", "auto_title_pending", "未提供", "none", "n/a", "null"}:
            topic_from_inputs = load_topic_from_inputs_json()
            if topic_from_inputs:
                state.topic = topic_from_inputs
                _checkpoint(state, checkpoint_path, reason="topic_synced_from_inputs", node="pre_research")

        has_valid_topic = str(getattr(state, "topic", "") or "").strip().lower() not in {"", "auto_title_pending", "未提供", "none", "n/a", "null"}
        if has_valid_topic and state.enable_auto_title is None:
            state.enable_auto_title = False
            state.pre_done_title = True
            _checkpoint(state, checkpoint_path, reason="auto_title_disabled_existing_topic", node="pre_research")

        if state.enable_auto_title is None:
            action = _timed_call(
                "wait_set_enable_auto_title",
                "pre_research",
                str(getattr(state, "workflow_phase", "")),
                _wait_for_action,
                state,
                checkpoint_path,
                action_name="set_enable_auto_title",
                prompt="请在 Web 面板选择是否自动生成标题。",
                node="pre_research",
                interaction_mode=interaction_mode,
                stop_event=stop_event,
            )
            state.enable_auto_title = bool(action.get("value", True))
            _checkpoint(state, checkpoint_path, reason="set_enable_auto_title", node="pre_research")

        if bool(state.enable_auto_title) and (not bool(getattr(state, "pre_done_title", False))):
            state = _timed_call(
                "node_title_builder",
                "node_title_builder",
                str(getattr(state, "workflow_phase", "")),
                node_title_builder,
                state,
            )
            state.pre_done_title = True
            _checkpoint(state, checkpoint_path, reason="node_title_builder_done", node="node_title_builder")
            try:
                output_path, checkpoint_path = migrate_paths_after_topic_update(
                    model=state.model,
                    topic=state.topic,
                    prompt_language=state.get_prompt_language(),
                    output_path=output_path,
                    checkpoint_path=checkpoint_path,
                )
                _checkpoint(state, checkpoint_path, reason="checkpoint_path_migrated_after_title", node="node_title_builder")
            except Exception as e:
                print(f"| [WARN] 标题更新后迁移断点路径失败: {e}")
        elif not bool(state.enable_auto_title):
            print("| [TitleBuilder] 已关闭自动生成标题，跳过该节点。")
            state.pre_done_title = True
            _checkpoint(state, checkpoint_path, reason="node_title_builder_skipped", node="node_title_builder")

        if state.enable_paper_search is None:
            action = _timed_call(
                "wait_set_enable_search",
                "pre_research",
                str(getattr(state, "workflow_phase", "")),
                _wait_for_action,
                state,
                checkpoint_path,
                action_name="set_enable_search",
                prompt="请在 Web 面板选择是否执行文献检索。",
                node="pre_research",
                interaction_mode=interaction_mode,
                stop_event=stop_event,
            )
            state.enable_paper_search = bool(action.get("value", True))
            _checkpoint(state, checkpoint_path, reason="set_enable_paper_search", node="pre_research")

        if state.enable_paper_search:
            if not bool(getattr(state, "pre_done_query_builder", False)):
                state = _timed_call(
                    "node_search_query_builder",
                    "node_search_query_builder",
                    str(getattr(state, "workflow_phase", "")),
                    node_search_query_builder,
                    state,
                )
                state.pre_done_query_builder = True
                _checkpoint(state, checkpoint_path, reason="node_search_query_builder_done", node="node_search_query_builder")

            if not bool(getattr(state, "pre_done_paper_search", False)):
                state = _timed_call(
                    "node_search_paper",
                    "node_search_paper",
                    str(getattr(state, "workflow_phase", "")),
                    node_search_paper,
                    state,
                )
                state.pre_done_paper_search = True
                _checkpoint(state, checkpoint_path, reason="node_search_paper_done", node="node_search_paper")

            if not bool(getattr(state, "pre_done_related_confirm", False)):
                _timed_call(
                    "wait_confirm_related_works",
                    "pre_research",
                    str(getattr(state, "workflow_phase", "")),
                    _wait_for_action,
                    state,
                    checkpoint_path,
                    action_name="confirm_related_works",
                    prompt=f"文献检索已完成。请先补充 {state.related_works_path}，然后在 Web 中点击继续。",
                    node="pre_research",
                    interaction_mode=interaction_mode,
                    stop_event=stop_event,
                )
                state.wait_for_manual_related_works = False
                state.pre_done_related_confirm = True
                _checkpoint(state, checkpoint_path, reason="manual_related_works_confirmed", node="pre_research")

        if not bool(getattr(state, "pre_done_research_gaps", False)):
            if (not bool(state.enable_paper_search)):
                rg_file = str(getattr(state, "research_gap_output_path", "") or "").strip()
                if rg_file and os.path.exists(rg_file) and os.path.getsize(rg_file) > 0:
                    state.research_gaps = _read_text(rg_file)
                    state.pre_done_research_gaps = True
                    _checkpoint(state, checkpoint_path, reason="node_research_gaps_skipped_existing_file", node="node_research_gaps")
                    print(f"| [ResearchGaps] 已跳过自动生成，复用现有文件: {rg_file}")

            if not bool(getattr(state, "pre_done_research_gaps", False)):
                state = _timed_call(
                    "node_research_gaps",
                    "node_research_gaps",
                    str(getattr(state, "workflow_phase", "")),
                    node_research_gaps,
                    state,
                )
                state.pre_done_research_gaps = True

        state.workflow_phase = "drafting"
        _checkpoint(state, checkpoint_path, reason="node_research_gaps_done", node="node_research_gaps")

    if state.workflow_phase == "drafting":
        _checkpoint(state, checkpoint_path, reason="enter_drafting_phase", node="drafting")
        state = _timed_call(
            "node_architect",
            "node_architect",
            str(getattr(state, "workflow_phase", "")),
            node_architect,
            state,
        )
        _checkpoint(state, checkpoint_path, reason="node_architect_done", node="node_architect")
        if not isinstance(state.outline, list):
            raise RuntimeError("architect 未返回章节列表，请检查模型输出格式。")

        if len(state.outline) > 12:
            print(f"| [WARN] 架构输出章节数异常({len(state.outline)})，已自动截断到前12个大章节。")
            state.outline = state.outline[:12]

        writing_queue = sorted(state.outline, key=lambda x: x["writing_order"])
        done_sub_ids = _completed_sub_id_set(state)

        for major_chapter in writing_queue:
            major_id = str(major_chapter.get("major_chapter_id", "")).strip()
            _checkpoint(state, checkpoint_path, reason="enter_major_chapter", node="major_loop", major_id=major_id, sub_id="")
            print(f"| 进入大章节: {major_chapter['major_title']} (优先级: {major_chapter['writing_order']})")

            state = _timed_call(
                "node_planner",
                "node_planner",
                str(getattr(state, "workflow_phase", "")),
                node_planner,
                state,
                major_chapter,
            )
            _checkpoint(state, checkpoint_path, reason="node_planner_done", node="node_planner", major_id=major_id, sub_id="")
            state = _timed_call(
                "node_chapter_header",
                "node_chapter_header",
                str(getattr(state, "workflow_phase", "")),
                node_chapter_header,
                state,
                major_chapter,
            )
            _checkpoint(state, checkpoint_path, reason="node_chapter_header_done", node="node_chapter_header", major_id=major_id, sub_id="")
            for sub_section in major_chapter.get("sub_sections", []):
                sub_id = str(sub_section.get("sub_chapter_id", "")).strip()
                if sub_id in done_sub_ids:
                    _append_event("key", f"跳过已完成写作子节: {sub_id}", node="node_writer")
                    continue
                _checkpoint(state, checkpoint_path, reason="before_node_writer", node="node_writer", major_id=major_id, sub_id=sub_id)
                state = _timed_call(
                    "node_writer",
                    "node_writer",
                    str(getattr(state, "workflow_phase", "")),
                    node_writer,
                    state,
                    major_chapter,
                    sub_section,
                )
                save_markdown_snapshot(state, output_path)
                _checkpoint(state, checkpoint_path, reason="node_writer_done", node="node_writer", major_id=major_id, sub_id=sub_id)
                _append_event("key", f"写作完成: {sub_id}", node="node_writer")
                done_sub_ids.add(sub_id)

        state.workflow_phase = "review_pending"
        state.current_major_chapter_id = ""
        state.current_sub_chapter_id = ""
        draft_snapshot = save_versioned_snapshot(state, output_path, "draft_initial")
        _checkpoint(state, checkpoint_path, reason="draft_initial_saved", node="drafting_completed")
        print(f"| 初稿快照已保存: {draft_snapshot}")

    if state.workflow_phase == "review_pending":
        _ensure_manual_revision_template(state.manual_revision_path)
        action = _timed_call(
            "wait_enter_reviewing",
            "review_pending",
            str(getattr(state, "workflow_phase", "")),
            _wait_for_action,
            state,
            checkpoint_path,
            action_name="enter_reviewing",
            prompt="请在 Web 面板确认是否进入审稿阶段，并可选择加载自定义修改要求文件。",
            node="review_pending",
            interaction_mode=interaction_mode,
            stop_event=stop_event,
        )

        if bool(action.get("load_requirements", True)):
            requirements_path = str(action.get("requirements_path", "inputs/user_requirements.md")).strip()
            _apply_requirements_from_file(state, requirements_path)

        manual_revision_path = str(action.get("manual_revision_path", state.manual_revision_path)).strip()
        if manual_revision_path:
            state.manual_revision_path = manual_revision_path
            _ensure_manual_revision_template(state.manual_revision_path)
            state.manual_revision_notes = _read_text(state.manual_revision_path)

        state.workflow_phase = "reviewing"
        _checkpoint(state, checkpoint_path, reason="enter_reviewing_phase", node="reviewing")

    if state.workflow_phase == "reviewing":
        print("| 开始审稿阶段")
        if not hasattr(state, "rewrite_done_sub_ids"):
            state.rewrite_done_sub_ids = []
        for _ in range(state.max_review_rounds):
            _check_stop(stop_event)
            state.manual_revision_notes = _read_text(state.manual_revision_path)
            _checkpoint(state, checkpoint_path, reason="before_overall_review", node="node_overall_review")
            state = _timed_call(
                "node_overall_review",
                "node_overall_review",
                str(getattr(state, "workflow_phase", "")),
                node_overall_review,
                state,
            )
            _checkpoint(state, checkpoint_path, reason="node_overall_review_done", node="node_overall_review")
            state = _timed_call(
                "node_major_review",
                "node_major_review",
                str(getattr(state, "workflow_phase", "")),
                node_major_review,
                state,
            )
            _checkpoint(state, checkpoint_path, reason="node_major_review_done", node="node_major_review")

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
                _checkpoint(state, checkpoint_path, reason="review_passed_final_saved", node="done")
                _write_runtime_status("done", "workflow 已完成", interaction_mode=interaction_mode)
                _append_event("key", "workflow 审稿通过并完成", interaction_mode=interaction_mode)
                print(f"| 终稿快照已保存: {final_snapshot}")
                print("| 所有章节审稿通过")
                break

            if not state.reviewed_sections:
                print("| [WARN] 审稿未通过但未返回可重写小节，提前结束循环以避免空转。")
                no_rewrite_snapshot = save_versioned_snapshot(state, output_path, f"review_round_{state.review_round}_no_rewrite")
                print(f"| 审稿快照已保存: {no_rewrite_snapshot}")
                _checkpoint(state, checkpoint_path, reason="no_rewrite_sections_break", node="reviewing")
                break

            for sub_section in state.reviewed_sections:
                _check_stop(stop_event)
                sub_id = str(sub_section.get("sub_chapter_id", "")).strip()
                done_rewrite_subs = _rewrite_done_sub_id_set(state)
                if sub_id in done_rewrite_subs:
                    _append_event("key", f"跳过已完成重写子节: {sub_id}", node="node_rewrite")
                    continue
                _checkpoint(state, checkpoint_path, reason="before_node_rewrite", node="node_rewrite", sub_id=sub_id)
                enhanced_item = _attach_manual_revision_instruction(state, sub_section)
                state = _timed_call(
                    "node_rewrite",
                    "node_rewrite",
                    str(getattr(state, "workflow_phase", "")),
                    node_rewrite,
                    state,
                    enhanced_item,
                )
                print(f"| 子节 {sub_section['sub_chapter_id']} 重写完成")
                state.rewrite_done_sub_ids = sorted(done_rewrite_subs | {sub_id})
                _checkpoint(state, checkpoint_path, reason="node_rewrite_done", node="node_rewrite", sub_id=sub_id)
                _append_event("key", f"重写完成: {sub_id}", node="node_rewrite")

            round_snapshot = save_versioned_snapshot(state, output_path, f"rewrite_round_{state.review_round}")
            state.rewrite_done_sub_ids = []
            _checkpoint(state, checkpoint_path, reason="rewrite_round_snapshot_saved", node="reviewing")
            print(f"| 改稿快照已保存: {round_snapshot}")
            print("| 所有章节重写完成")
        else:
            print(f"| [WARN] 达到最大审稿轮数 {state.max_review_rounds}，请人工复核。")
            _write_runtime_status("done", "达到最大审稿轮数，等待人工复核", interaction_mode=interaction_mode)
            _append_event("key", "达到最大审稿轮数", interaction_mode=interaction_mode)


def _run_workflow_safely(stop_event: Optional[Event] = None, interaction_mode: str = "web") -> None:
    force_resume_next = False
    while True:
        try:
            run_workflow(stop_event=stop_event, interaction_mode=interaction_mode, force_resume=force_resume_next)
            force_resume_next = False
            return
        except WorkflowStopRequested:
            _write_runtime_status("stopped", "收到停止信号并安全退出", interaction_mode=interaction_mode)
            _append_event("key", "workflow 收到停止信号并退出", interaction_mode=interaction_mode)
            print("| 工作流收到停止信号，已安全退出。")
            return
        except Exception as e:
            if "LLM_RETRY_EXHAUSTED" in str(e):
                _write_runtime_status(
                    "paused",
                    "LLM 连续重试失败，流程已暂停并保留断点；可在前端点击继续重试。",
                    interaction_mode=interaction_mode,
                )
                _append_event("key", "LLM 连续重试失败，workflow 已暂停并保留断点", interaction_mode=interaction_mode)
                print("| [PAUSE] LLM 连续重试失败，流程已暂停，等待前端继续重试。")
                _wait_for_retry_action(stop_event=stop_event, interaction_mode=interaction_mode)
                force_resume_next = True
                continue
            if "SEARCH_QUERY_BUILDER_EMPTY" in str(e):
                _write_runtime_status(
                    "paused",
                    "检索词生成失败（空结果），流程已暂停并保留断点；请补充 topic/已有材料后重启续跑。",
                    interaction_mode=interaction_mode,
                )
                _append_event("key", "检索词生成为空，workflow 已暂停并保留断点", interaction_mode=interaction_mode)
                print("| [PAUSE] 检索词生成为空，流程已暂停。")
                return
            _write_runtime_status("failed", f"workflow 异常退出: {e}", interaction_mode=interaction_mode)
            _append_event("key", f"workflow 异常退出: {e}", interaction_mode=interaction_mode)
            raise


if __name__ == "__main__":
    _run_workflow_safely()
