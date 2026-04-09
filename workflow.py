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
    node_architecture_review,
    node_planner,
    node_chapter_header,
    node_chapter_opening,
    node_writer,
    node_overall_review,
    node_major_review,
    node_rewrite,
)
import json
import os
import re
import time
import glob
from datetime import datetime
from threading import Event
from typing import Any, Dict, Optional
from core.project_paths import project_path, absolute_path_in_project


def _action_file() -> str:
    return project_path("completed_history", "workflow_actions.json")


def _runtime_file() -> str:
    return project_path("completed_history", "workflow_runtime.json")


def _events_file() -> str:
    return project_path("completed_history", "workflow_events.jsonl")


def _metrics_file() -> str:
    return project_path("completed_history", "workflow_metrics.json")


class WorkflowStopRequested(Exception):
    pass


def _read_metrics() -> Dict[str, Any]:
    metrics_file = _metrics_file()
    if not os.path.exists(metrics_file):
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
        with open(metrics_file, "r", encoding="utf-8") as f:
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
    metrics_file = _metrics_file()
    os.makedirs(os.path.dirname(metrics_file), exist_ok=True)
    data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(metrics_file, "w", encoding="utf-8") as f:
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
    runtime_file = _runtime_file()
    os.makedirs(os.path.dirname(runtime_file), exist_ok=True)
    with open(runtime_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _append_event(level: str, message: str, **extra: Any) -> None:
    payload: Dict[str, Any] = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "level": str(level),
        "message": str(message),
    }
    payload.update(extra)
    events_file = _events_file()
    os.makedirs(os.path.dirname(events_file), exist_ok=True)
    with open(events_file, "a", encoding="utf-8") as f:
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


def _to_project_abs(path: str) -> str:
    raw = str(path or "").strip()
    if not raw:
        return raw
    normalized = raw.replace("\\", "/")
    if normalized.startswith("/") or (":" in normalized) or (".." in normalized):
        return raw
    return absolute_path_in_project(normalized)


def _consume_action(expected_action: str) -> Dict[str, Any] | None:
    action_file = _action_file()
    if not os.path.exists(action_file):
        return None
    try:
        with open(action_file, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception:
        return None

    if str(payload.get("action", "")).strip() != expected_action:
        return None

    try:
        os.remove(action_file)
    except Exception:
        pass
    return payload


def _latest_project_checkpoint_path() -> str:
    files = glob.glob(project_path("completed_history", "*_checkpoint.json"))
    if not files:
        return ""
    files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return files[0]


_AUTO_APPLY_ACTIONS = {
    "confirm_inputs_ready",
    "set_enable_auto_title",
    "set_enable_search",
    "confirm_related_works",
    "enter_reviewing",
    "set_architecture_force_continue",
}


def _normalize_action_payload(action_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {"action": str(action_name).strip()}

    if action_name in {"set_enable_auto_title", "set_enable_search", "set_architecture_force_continue"}:
        normalized["value"] = bool(payload.get("value", False))
    elif action_name == "enter_reviewing":
        normalized["load_requirements"] = bool(payload.get("load_requirements", True))
        req_path = str(payload.get("requirements_path", "inputs/write_requests.md") or "").strip() or "inputs/write_requests.md"
        manual_path = str(payload.get("manual_revision_path", "inputs/revision_requests.md") or "").strip() or "inputs/revision_requests.md"
        normalized["requirements_path"] = req_path
        normalized["manual_revision_path"] = manual_path

    return normalized


def _remember_action_choice(state: PaperWriterState, action_name: str, payload: Dict[str, Any], source: str) -> None:
    normalized = _normalize_action_payload(action_name, payload)
    preferences = getattr(state, "action_preferences", {})
    if not isinstance(preferences, dict):
        preferences = {}
    preferences[action_name] = dict(normalized)
    state.action_preferences = preferences

    history = getattr(state, "action_history", [])
    if not isinstance(history, list):
        history = []
    history.append(
        {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": str(source or "unknown"),
            **normalized,
        }
    )
    state.action_history = history[-200:]


def _recall_action_choice(state: PaperWriterState, action_name: str) -> Dict[str, Any] | None:
    if action_name not in _AUTO_APPLY_ACTIONS:
        return None
    if not bool(getattr(state, "auto_apply_saved_actions", True)):
        return None

    preferences = getattr(state, "action_preferences", {})
    if not isinstance(preferences, dict):
        return None

    raw_payload = preferences.get(action_name)
    if not isinstance(raw_payload, dict):
        return None

    payload = _normalize_action_payload(action_name, raw_payload)
    if str(payload.get("action", "")).strip() != action_name:
        return None
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
    remembered_action = _recall_action_choice(state, action_name)
    if remembered_action is not None:
        state.pending_action = ""
        state.pending_action_message = ""
        _checkpoint(state, checkpoint_path, reason=f"action_{action_name}_auto_reused", node=node)
        _write_runtime_status("running", f"已自动应用历史动作: {action_name}", node=node, interaction_mode=interaction_mode)
        _append_event("key", f"自动应用历史动作: {action_name}", node=node, interaction_mode=interaction_mode)
        return remembered_action

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
            req_path = input("| 自定义要求文件路径(默认 inputs/write_requests.md): ").strip() or "inputs/write_requests.md"
            action = {
                "action": action_name,
                "load_requirements": load_req,
                "requirements_path": req_path,
            }
        elif action_name == "set_architecture_force_continue":
            raw = input("| 架构仅剩中低优问题，是否人工放行继续？[y/N]: ").strip().lower()
            action = {"action": action_name, "value": raw in {"y", "yes", "1", "true"}}
        elif action_name == "confirm_next_review_round":
            raw = input("| 是否进入下一轮审稿？[Y/n]: ").strip().lower()
            action = {"action": action_name, "continue": raw not in {"n", "no", "0", "false"}}
        else:
            input("| 按回车继续...")
            action = {"action": action_name}

        _remember_action_choice(state, action_name=action_name, payload=action, source="cli")
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
            _remember_action_choice(state, action_name=action_name, payload=action, source="web")
            state.pending_action = ""
            state.pending_action_message = ""
            _checkpoint(state, checkpoint_path, reason=f"action_{action_name}_received", node=node)
            _write_runtime_status("running", f"已接收动作: {action_name}", node=node, interaction_mode=interaction_mode)
            _append_event("key", f"已接收动作: {action_name}", node=node, interaction_mode=interaction_mode)
            return action
        time.sleep(poll_seconds)


def _apply_requirements_from_file(state: PaperWriterState, path: str) -> None:
    text = _read_text(_to_project_abs(path))
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


def _major_sub_sections(major: Dict[str, Any]) -> list[Dict[str, Any]]:
    return [x for x in ((major or {}).get("sub_sections", []) or []) if isinstance(x, dict)]


def _major_has_planner_cache(major: Dict[str, Any]) -> bool:
    if bool((major or {}).get("planner_done", False)):
        return True

    planned_count = 0
    for sub in _major_sub_sections(major):
        routing = sub.get("context_routing", {})
        blueprints = sub.get("paragraph_blueprints", [])
        guidance_key = str(sub.get("selected_guidance_key", "")).strip()
        guidance_reason = str(sub.get("guidance_reason", "")).strip()

        has_plan = (
            (isinstance(routing, dict) and bool(routing))
            or (isinstance(blueprints, list) and bool(blueprints))
            or bool(guidance_key)
            or bool(guidance_reason)
        )
        if has_plan:
            planned_count += 1

    return planned_count > 0


def _major_has_header_cache(major: Dict[str, Any]) -> bool:
    major_id = str((major or {}).get("major_chapter_id", "")).strip()
    if major_id == "0":
        return True
    if bool((major or {}).get("chapter_header_ready", False)):
        return True
    title = str((major or {}).get("chapter_header_title", "")).strip()
    lead = str((major or {}).get("chapter_header_lead", "")).strip()
    return bool(title or lead)


def _major_has_opening_cache(major: Dict[str, Any]) -> bool:
    major_id = str((major or {}).get("major_chapter_id", "")).strip()
    if major_id == "0":
        return True
    if bool((major or {}).get("chapter_opening_ready", False)):
        return True
    opening = str((major or {}).get("chapter_opening_markdown", "")).strip()
    return bool(opening)


def _build_drafting_next_steps(outline: list[dict], done_sub_ids: set[str]) -> list[dict]:
    rows: list[dict] = []
    order_index = 0
    writing_queue = sorted(outline or [], key=lambda x: int((x or {}).get("writing_order", 999) or 999))

    for major in writing_queue:
        if not isinstance(major, dict):
            continue
        major_id = str(major.get("major_chapter_id", "")).strip()
        major_title = str(major.get("major_title", "")).strip()
        sub_sections = [x for x in (major.get("sub_sections", []) or []) if isinstance(x, dict)]

        for sub in sub_sections:
            sub_id = str(sub.get("sub_chapter_id", "")).strip()
            if not sub_id:
                continue
            order_index += 1
            rows.append(
                {
                    "phase": "drafting",
                    "order": order_index,
                    "major_chapter_id": major_id,
                    "major_title": major_title,
                    "sub_chapter_id": sub_id,
                    "sub_title": str(sub.get("sub_title", "")).strip(),
                    "status": "done" if sub_id in done_sub_ids else "todo",
                    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
    return rows


def _refresh_drafting_next_steps(state: PaperWriterState, done_sub_ids: set[str]) -> None:
    outline = _coerce_outline_list(getattr(state, "outline", []))
    state.next_steps_plan = _build_drafting_next_steps(outline, done_sub_ids)
    state.next_steps_updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _mark_drafting_step_done(state: PaperWriterState, sub_id: str) -> None:
    target = str(sub_id or "").strip()
    if not target:
        return

    changed = False
    rows = getattr(state, "next_steps_plan", [])
    if not isinstance(rows, list):
        rows = []

    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("sub_chapter_id", "")).strip() != target:
            continue
        if str(row.get("status", "")).strip() != "done":
            row["status"] = "done"
            changed = True
        row["updated_at"] = now_text

    if changed:
        state.next_steps_updated_at = now_text


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


def _coerce_outline_list(raw: Any) -> list[Dict[str, Any]]:
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]

    if isinstance(raw, dict):
        for key in ["outline", "architect_outline", "architecture_outline", "paper_outline", "chapters", "data"]:
            value = raw.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]

    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        for candidate in [text, text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()]:
            if not candidate:
                continue
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, list):
                    return [x for x in parsed if isinstance(x, dict)]
                if isinstance(parsed, dict):
                    for key in ["outline", "architect_outline", "architecture_outline", "paper_outline", "chapters", "data"]:
                        value = parsed.get(key)
                        if isinstance(value, list):
                            return [x for x in value if isinstance(x, dict)]
            except Exception:
                continue

    return []


def _outline_sub_id_set(state: PaperWriterState) -> set[str]:
    result: set[str] = set()
    outline = _coerce_outline_list(getattr(state, "outline", []))
    for major in outline:
        sub_sections = (major or {}).get("sub_sections", []) or []
        for sub in sub_sections:
            if not isinstance(sub, dict):
                continue
            sub_id = str(sub.get("sub_chapter_id", "")).strip()
            if sub_id:
                result.add(sub_id)
    return result


def _infer_resume_phase(state: PaperWriterState) -> str:
    current_phase = str(getattr(state, "workflow_phase", "") or "").strip().lower()
    if current_phase == "done":
        return "done"

    outline_sub_ids = _outline_sub_id_set(state)
    completed_sub_ids = _completed_sub_id_set(state)
    draft_is_complete = bool(completed_sub_ids) and (
        (not outline_sub_ids) or outline_sub_ids.issubset(completed_sub_ids)
    )

    review_round = int(getattr(state, "review_round", 0) or 0)
    reviewed_sections = getattr(state, "reviewed_sections", []) or []
    rewrite_done_sub_ids = getattr(state, "rewrite_done_sub_ids", []) or []
    has_review_markers = current_phase == "reviewing" or review_round > 0 or bool(reviewed_sections) or bool(rewrite_done_sub_ids)
    if has_review_markers and draft_is_complete:
        return "reviewing"

    if current_phase == "review_pending":
        if draft_is_complete:
            return "review_pending"
        return "drafting"

    if completed_sub_ids:
        if draft_is_complete:
            return "review_pending"
        return "drafting"

    if draft_is_complete:
        return "review_pending"

    outline = _coerce_outline_list(getattr(state, "outline", []))
    if outline:
        return "drafting"

    has_research_gaps = bool(str(getattr(state, "research_gaps", "") or "").strip())
    if has_research_gaps or bool(getattr(state, "pre_done_research_gaps", False)):
        return "drafting"

    pending_action = str(getattr(state, "pending_action", "") or "").strip()
    if pending_action == "enter_reviewing":
        if draft_is_complete:
            return "review_pending"
        return "drafting"

    pending_phase_map = {
        "confirm_inputs_ready": "pre_research",
        "set_enable_auto_title": "pre_research",
        "set_enable_search": "pre_research",
        "confirm_related_works": "pre_research",
        "set_architecture_force_continue": "drafting",
    }
    if pending_action in pending_phase_map:
        return pending_phase_map[pending_action]

    return "pre_research"


def _repair_resume_state(state: PaperWriterState) -> list[str]:
    notes: list[str] = []

    normalized_outline = _coerce_outline_list(getattr(state, "outline", []))
    raw_outline = getattr(state, "outline", [])
    if normalized_outline:
        if (not isinstance(raw_outline, list)) or (len(normalized_outline) != len(raw_outline)):
            state.outline = normalized_outline
            notes.append("outline_normalized")
    elif isinstance(raw_outline, list):
        cleaned = [x for x in raw_outline if isinstance(x, dict)]
        if len(cleaned) != len(raw_outline):
            state.outline = cleaned
            notes.append("outline_cleaned")

    has_valid_topic = str(getattr(state, "topic", "") or "").strip().lower() not in {"", "auto_title_pending", "未提供", "none", "n/a", "null"}
    if has_valid_topic and state.enable_auto_title is None:
        state.enable_auto_title = False
        if not bool(getattr(state, "pre_done_title", False)):
            state.pre_done_title = True
        notes.append("auto_title_state_repaired")

    remembered_auto_title = _recall_action_choice(state, "set_enable_auto_title")
    if state.enable_auto_title is None and isinstance(remembered_auto_title, dict) and ("value" in remembered_auto_title):
        state.enable_auto_title = bool(remembered_auto_title.get("value", False))
        notes.append("enable_auto_title_restored_from_memory")
    if (state.enable_auto_title is False) and (not bool(getattr(state, "pre_done_title", False))):
        state.pre_done_title = True
        notes.append("auto_title_marked_done_by_choice")

    queries = getattr(state, "search_queries", []) or []
    if isinstance(queries, list) and queries and (not bool(getattr(state, "pre_done_query_builder", False))):
        state.pre_done_query_builder = True
        notes.append("query_builder_marked_done")

    remembered_search = _recall_action_choice(state, "set_enable_search")
    if state.enable_paper_search is None and isinstance(remembered_search, dict) and ("value" in remembered_search):
        state.enable_paper_search = bool(remembered_search.get("value", False))
        notes.append("enable_search_restored_from_memory")

    if state.enable_paper_search is None and bool(getattr(state, "pre_done_query_builder", False)):
        state.enable_paper_search = True
        notes.append("enable_search_inferred_true")

    related_works_text = str(getattr(state, "related_works_summary", "") or "").strip()
    if not related_works_text:
        related_works_path = str(getattr(state, "related_works_path", "") or "").strip()
        if related_works_path and os.path.exists(related_works_path):
            related_works_text = _read_text(related_works_path)
            if related_works_text:
                state.related_works_summary = related_works_text
                notes.append("related_works_summary_restored")

    if bool(state.enable_paper_search) and related_works_text and (not bool(getattr(state, "pre_done_paper_search", False))):
        state.pre_done_paper_search = True
        notes.append("paper_search_marked_done")

    remembered_related_confirm = _recall_action_choice(state, "confirm_related_works")
    if (
        (not bool(getattr(state, "pre_done_related_confirm", False)))
        and (remembered_related_confirm is not None)
        and (bool(getattr(state, "pre_done_paper_search", False)) or bool(related_works_text))
    ):
        state.pre_done_related_confirm = True
        state.wait_for_manual_related_works = False
        notes.append("related_works_confirm_restored_from_memory")

    research_gaps_text = str(getattr(state, "research_gaps", "") or "").strip()
    if not research_gaps_text:
        rg_file = str(getattr(state, "research_gap_output_path", "") or "").strip()
        if rg_file and os.path.exists(rg_file) and os.path.getsize(rg_file) > 0:
            state.research_gaps = _read_text(rg_file)
            research_gaps_text = str(getattr(state, "research_gaps", "") or "").strip()
            if research_gaps_text:
                notes.append("research_gaps_restored_from_file")

    if research_gaps_text and (not bool(getattr(state, "pre_done_research_gaps", False))):
        state.pre_done_research_gaps = True
        notes.append("research_gaps_marked_done")

    completed_sub_ids = _completed_sub_id_set(state)
    has_drafting_progress = bool(completed_sub_ids)
    if has_drafting_progress and state.enable_paper_search is None:
        if isinstance(remembered_search, dict) and ("value" in remembered_search):
            state.enable_paper_search = bool(remembered_search.get("value", False))
            notes.append("enable_search_restored_from_memory_drafting")
        else:
            state.enable_paper_search = bool(
                bool(getattr(state, "pre_done_query_builder", False))
                or bool(getattr(state, "pre_done_paper_search", False))
                or bool(related_works_text)
            )
            notes.append("enable_search_inferred_from_drafting_progress")

    if has_drafting_progress and (not bool(getattr(state, "pre_done_related_confirm", False))):
        state.pre_done_related_confirm = True
        notes.append("related_works_confirm_marked_done")

    pending_action = str(getattr(state, "pending_action", "") or "").strip()
    if pending_action in {"confirm_inputs_ready", "set_enable_auto_title", "set_enable_search", "confirm_related_works"}:
        if has_drafting_progress or bool(normalized_outline) or bool(research_gaps_text):
            state.pending_action = ""
            state.pending_action_message = ""
            notes.append("stale_pending_action_cleared")
            pending_action = ""

    remembered_arch_force_continue = _recall_action_choice(state, "set_architecture_force_continue")
    if (
        normalized_outline
        and (not bool(getattr(state, "architecture_force_continue", False)))
        and isinstance(remembered_arch_force_continue, dict)
        and bool(remembered_arch_force_continue.get("value", False))
    ):
        state.architecture_force_continue = True
        state.architecture_passed = True
        notes.append("architecture_force_continue_restored_from_memory")

    if normalized_outline and (not bool(getattr(state, "architecture_passed", False))) and pending_action != "set_architecture_force_continue":
        state.architecture_passed = True
        notes.append("architecture_passed_inferred")

    inferred_phase = _infer_resume_phase(state)
    old_phase = str(getattr(state, "workflow_phase", "") or "").strip()
    if inferred_phase and inferred_phase != old_phase:
        state.workflow_phase = inferred_phase
        notes.append(f"phase:{old_phase}->{inferred_phase}")

    return notes


def _safe_name(text: str) -> str:
    return "".join(ch for ch in str(text or "") if ch not in '\\/*?:"<>|').replace(" ", "_")


def _score_resume_checkpoint(path: str, model: str, topic: str) -> tuple[int, float]:
    score = 0
    mtime = 0.0
    try:
        mtime = float(os.path.getmtime(path))
    except Exception:
        mtime = 0.0

    filename = os.path.basename(str(path or "")).lower()
    safe_model = _safe_name(model).lower()
    safe_topic = _safe_name(topic if str(topic or "").strip() else "auto_title_pending").lower()
    if safe_model and safe_model in filename:
        score += 15
    if safe_topic and safe_topic in filename:
        score += 12

    try:
        payload = load_state_checkpoint(path)
    except Exception:
        return score, mtime

    phase = str(payload.get("workflow_phase", "")).strip().lower()
    if phase == "done":
        score += 80
    elif phase in {"reviewing", "review_pending"}:
        score += 60
    elif phase == "drafting":
        score += 45
    elif phase == "pre_research":
        score += 15

    outline = _coerce_outline_list(payload.get("outline", []))
    if outline:
        score += 80

    completed = payload.get("completed_sections", []) or []
    if isinstance(completed, list):
        score += min(60, len([x for x in completed if isinstance(x, dict)]) * 6)

    if bool(payload.get("architecture_passed", False)):
        score += 20

    queries = payload.get("search_queries", []) or []
    if isinstance(queries, list) and queries:
        score += 8

    return score, mtime


def _select_best_resume_checkpoint(default_checkpoint: str, model: str, topic: str, prompt_language: str) -> str:
    candidates: list[str] = []
    seen: set[str] = set()

    def _add(path: str) -> None:
        p = str(path or "").strip()
        if (not p) or (not os.path.exists(p)):
            return
        norm = os.path.normcase(os.path.normpath(p))
        if norm in seen:
            return
        seen.add(norm)
        candidates.append(p)

    _add(default_checkpoint)

    try:
        _add(find_latest_checkpoint_for_resume(model, prompt_language))
    except Exception:
        pass

    safe_topic = _safe_name(topic if str(topic or "").strip() else "auto_title_pending")
    safe_lang = _safe_name(prompt_language)
    topic_pattern = project_path("completed_history", f"*_{safe_topic}_{safe_lang}_checkpoint.json")
    for p in sorted(glob.glob(topic_pattern), key=lambda x: os.path.getmtime(x), reverse=True)[:8]:
        _add(p)

    any_pattern = project_path("completed_history", "*_checkpoint.json")
    for p in sorted(glob.glob(any_pattern), key=lambda x: os.path.getmtime(x), reverse=True)[:5]:
        _add(p)

    if not candidates:
        return default_checkpoint

    best = max(candidates, key=lambda p: _score_resume_checkpoint(p, model=model, topic=topic))
    return best


def run_workflow(stop_event: Optional[Event] = None, interaction_mode: str = "web", force_resume: bool = False) -> None:
    interaction_mode = (interaction_mode or "web").strip().lower()
    if interaction_mode not in {"web", "cli"}:
        interaction_mode = "web"

    os.makedirs(project_path("completed_history"), exist_ok=True)
    _write_runtime_status("starting", "workflow 正在启动", interaction_mode=interaction_mode)
    _append_event("key", "workflow 启动", interaction_mode=interaction_mode)

    initial_inputs = json.load(open(resolve_inputs_path(), "r", encoding="utf-8-sig"))
    temp_state = PaperWriterState(initial_inputs)
    output_path, checkpoint_path = build_output_paths(
        temp_state.model,
        temp_state.topic,
        temp_state.get_prompt_language(),
    )

    auto_resume = True
    if auto_resume:
        if force_resume:
            selected_checkpoint = _latest_project_checkpoint_path() or checkpoint_path
        else:
            selected_checkpoint = _select_best_resume_checkpoint(
                default_checkpoint=checkpoint_path,
                model=temp_state.model,
                topic=temp_state.topic,
                prompt_language=temp_state.get_prompt_language(),
            )
        if selected_checkpoint and os.path.exists(selected_checkpoint):
            checkpoint_path = selected_checkpoint
            fallback_output = output_path_from_checkpoint(selected_checkpoint)
            if fallback_output:
                output_path = fallback_output

    if os.path.exists(checkpoint_path) and auto_resume:
        checkpoint_data = load_state_checkpoint(checkpoint_path)
        state = PaperWriterState(checkpoint_data, input_from_md=False)
        state.runtime_checkpoint_path = str(checkpoint_path)
        state.resume_count = int(getattr(state, "resume_count", 0)) + 1
        resume_notes = _repair_resume_state(state)
        _checkpoint(state, checkpoint_path, reason="resume_from_checkpoint", node="resume")
        if resume_notes:
            _append_event(
                "key",
                f"断点修复: {', '.join(resume_notes)}",
                node="resume",
                phase=str(getattr(state, "workflow_phase", "")),
                interaction_mode=interaction_mode,
            )
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
        state.user_requirements = str(reloaded_inputs.get("write_requests", reloaded_inputs.get("user_requirements", state.user_requirements)))
        _checkpoint(state, checkpoint_path, reason="inputs_confirmed", node="pre_start")
        _append_event("key", "inputs 已确认，开始流程", interaction_mode=interaction_mode)

    # 迁移逻辑：旧断点默认从 drafting 开始，新流程在缺少 research_gaps 且无架构/写作进度时先进入前置阶段
    if (
        state.workflow_phase == "drafting"
        and (not str(getattr(state, "research_gaps", "")).strip())
        and (not _coerce_outline_list(getattr(state, "outline", [])))
        and (not _completed_sub_id_set(state))
    ):
        state.workflow_phase = "pre_research"
        _checkpoint(state, checkpoint_path, reason="migrate_to_pre_research", node="phase_migration")

    if state.workflow_phase == "pre_research":
        if _completed_sub_id_set(state):
            if state.enable_auto_title is None:
                state.enable_auto_title = False
            state.pre_done_title = True
            if state.enable_paper_search is None:
                remembered_search = _recall_action_choice(state, "set_enable_search")
                if isinstance(remembered_search, dict) and ("value" in remembered_search):
                    state.enable_paper_search = bool(remembered_search.get("value", False))
                else:
                    state.enable_paper_search = False
            state.pre_done_query_builder = bool(getattr(state, "pre_done_query_builder", False))
            state.pre_done_paper_search = bool(getattr(state, "pre_done_paper_search", False))
            state.pre_done_related_confirm = True
            state.pre_done_research_gaps = True
            state.workflow_phase = "drafting"
            _checkpoint(state, checkpoint_path, reason="skip_pre_research_existing_drafting_progress", node="pre_research")

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

    if state.workflow_phase in {"review_pending", "reviewing"}:
        completed_sub_ids_for_review = _completed_sub_id_set(state)
        outline_sub_ids_for_review = _outline_sub_id_set(state)
        draft_complete_for_review = bool(completed_sub_ids_for_review) and (
            (not outline_sub_ids_for_review) or outline_sub_ids_for_review.issubset(completed_sub_ids_for_review)
        )
        if not draft_complete_for_review:
            state.workflow_phase = "drafting"
            _checkpoint(state, checkpoint_path, reason="review_phase_guard_redirect_to_drafting", node="drafting")
            _append_event(
                "key",
                "审稿前置校验未通过，已返回 drafting 继续完成正文",
                node="drafting",
                interaction_mode=interaction_mode,
            )

    if state.workflow_phase == "drafting":
        _checkpoint(state, checkpoint_path, reason="enter_drafting_phase", node="drafting")
        state.architecture_force_continue = bool(getattr(state, "architecture_force_continue", False))

        # Determine if architect needs to run:
        # If outline already exists, treat architecture as completed and continue downstream.
        existing_outline = _coerce_outline_list(getattr(state, "outline", []))
        has_existing_outline = bool(existing_outline)
        existing_sections_count = len(_completed_sub_id_set(state))

        if has_existing_outline:
            if not bool(getattr(state, "architecture_passed", False)):
                state.architecture_passed = True
                _checkpoint(state, checkpoint_path, reason="architecture_passed_via_existing_outline", node="drafting")
            print(
                f"| [Resume] 检测到已有 architect 结果({len(existing_outline)} 章节)，"
                f"已完成小节 {existing_sections_count} 个，跳过架构师阶段"
            )
        elif not bool(getattr(state, "architecture_passed", False)):
            max_rounds = int(getattr(state, "max_architecture_review_rounds", 3))
            for i in range(max_rounds):
                _check_stop(stop_event)
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

                if not bool(getattr(state, "architecture_review_enabled", True)):
                    state.architecture_passed = True
                    break

                # 如果是最后一次生成架构，则自动跳过审稿并放行
                if i == max_rounds - 1:
                    state.architecture_passed = True
                    print(f"| [架构通过] 达到最大重写轮次({max_rounds})，最后一次生成的架构无需再审核，自动跳过审核环节并采纳。")
                    _write_runtime_status("running", "生成最后一次架构，跳过审核自动采纳", interaction_mode=interaction_mode)
                    _checkpoint(state, checkpoint_path, reason="architecture_auto_passed_final_round", node="drafting")
                    break

                state = _timed_call(
                    "node_architecture_review",
                    "node_architecture_review",
                    str(getattr(state, "workflow_phase", "")),
                    node_architecture_review,
                    state,
                )
                _checkpoint(state, checkpoint_path, reason="node_architecture_review_done", node="node_architecture_review")
                if bool(getattr(state, "architecture_passed", False)):
                    break

                issues = getattr(state, "architecture_issues", []) or []
                has_high = any(
                    str((item or {}).get("severity", "")).strip().lower() == "high"
                    for item in issues
                    if isinstance(item, dict)
                )
                if (not has_high) and interaction_mode in {"web", "cli"}:
                    action = _timed_call(
                        "wait_set_architecture_force_continue",
                        "drafting",
                        str(getattr(state, "workflow_phase", "")),
                        _wait_for_action,
                        state,
                        checkpoint_path,
                        action_name="set_architecture_force_continue",
                        prompt="架构审查未通过，但仅存在中低优问题。是否人工放行继续到规划阶段？",
                        node="drafting",
                        interaction_mode=interaction_mode,
                        stop_event=stop_event,
                    )
                    if bool(action.get("value", False)):
                        state.architecture_force_continue = True
                        state.architecture_passed = True
                        _checkpoint(state, checkpoint_path, reason="architecture_force_continue", node="drafting")
                        break
            if not bool(getattr(state, "architecture_passed", False)):
                _write_runtime_status(
                    "paused",
                    "架构审查在最大轮次内未通过，请根据改进建议调整输入后续跑。",
                    interaction_mode=interaction_mode,
                )
                _append_event("key", "架构审查未通过并暂停", interaction_mode=interaction_mode)
                raise RuntimeError("ARCHITECTURE_REVIEW_NOT_PASSED")

        state.outline = _coerce_outline_list(getattr(state, "outline", []))
        if len(state.outline) > 12:
            print(f"| [WARN] 架构输出章节数异常({len(state.outline)})，已自动截断到前12个大章节。")
            state.outline = state.outline[:12]

        writing_queue = sorted(state.outline, key=lambda x: int((x or {}).get("writing_order", 999) or 999))
        done_sub_ids = _completed_sub_id_set(state)
        _refresh_drafting_next_steps(state, done_sub_ids)
        _checkpoint(state, checkpoint_path, reason="drafting_next_steps_planned", node="drafting")

        # Determine the checkpoint resume position for granular resume within drafting
        resume_node = str(getattr(state, "current_node", "")).strip()
        resume_major_id = str(getattr(state, "current_major_chapter_id", "")).strip()
        resume_sub_id = str(getattr(state, "current_sub_chapter_id", "")).strip()

        for major_chapter in writing_queue:
            major_id = str(major_chapter.get("major_chapter_id", "")).strip()
            sub_sections = [x for x in (major_chapter.get("sub_sections", []) or []) if isinstance(x, dict)]
            pending_sub_sections = [
                x for x in sub_sections
                if str(x.get("sub_chapter_id", "")).strip() not in done_sub_ids
            ]
            if not pending_sub_sections:
                _append_event("key", f"跳过已完成大章节: {major_id}", node="major_loop")
                continue

            _checkpoint(state, checkpoint_path, reason="enter_major_chapter", node="major_loop", major_id=major_id, sub_id="")
            print(
                f"| 进入大章节: {major_chapter.get('major_title', '')} "
                f"(优先级: {major_chapter.get('writing_order', 999)})"
            )

            # Granular skip and resume:
            # - If this chapter already has completed sub-sections, setup nodes were done before.
            # - If checkpoint shows we were already inside planner/header/opening/writer for this chapter,
            #   skip already-finished setup nodes and continue from the precise stuck step.
            chapter_done_subs = {
                str(x.get("sub_chapter_id", "")).strip()
                for x in sub_sections
                if str(x.get("sub_chapter_id", "")).strip() in done_sub_ids
            }
            planner_cached = _major_has_planner_cache(major_chapter)
            header_cached = _major_has_header_cache(major_chapter)
            opening_cached = _major_has_opening_cache(major_chapter)

            if planner_cached and (not bool(major_chapter.get("planner_done", False))):
                major_chapter["planner_done"] = True
            if header_cached and (not bool(major_chapter.get("chapter_header_ready", False))):
                major_chapter["chapter_header_ready"] = True
            if opening_cached and (not bool(major_chapter.get("chapter_opening_ready", False))):
                major_chapter["chapter_opening_ready"] = True

            is_resume_major = bool(resume_major_id) and (resume_major_id == major_id)
            resume_node_for_major = resume_node if is_resume_major else ""

            planner_done = bool(chapter_done_subs) or planner_cached
            header_done = bool(chapter_done_subs) or header_cached
            opening_done = bool(chapter_done_subs) or opening_cached

            if resume_node_for_major == "node_planner":
                planner_done = True
            elif resume_node_for_major == "node_chapter_header":
                planner_done = True
                header_done = True
            elif resume_node_for_major in {"node_chapter_opening", "node_writer"}:
                planner_done = True
                header_done = True
                opening_done = True

            if planner_done and header_done and opening_done:
                if chapter_done_subs:
                    print(f"| [Resume] 大章节 {major_id} 已有 {len(chapter_done_subs)} 个已完成小节，跳过 planner/header/opening")
                elif resume_node_for_major:
                    print(f"| [Resume] 大章节 {major_id} 从断点节点 {resume_node_for_major} 继续，跳过已完成 setup 节点")
                else:
                    print(f"| [Resume] 大章节 {major_id} 检测到已有 planner/header/opening 缓存，直接进入写作子节")

            if not planner_done:
                state = _timed_call(
                    "node_planner",
                    "node_planner",
                    str(getattr(state, "workflow_phase", "")),
                    node_planner,
                    state,
                    major_chapter,
                )
                major_chapter["planner_done"] = True
                _checkpoint(state, checkpoint_path, reason="node_planner_done", node="node_planner", major_id=major_id, sub_id="")

            if not header_done:
                state = _timed_call(
                    "node_chapter_header",
                    "node_chapter_header",
                    str(getattr(state, "workflow_phase", "")),
                    node_chapter_header,
                    state,
                    major_chapter,
                )
                major_chapter["chapter_header_ready"] = True
                _checkpoint(state, checkpoint_path, reason="node_chapter_header_done", node="node_chapter_header", major_id=major_id, sub_id="")

            if not opening_done:
                state = _timed_call(
                    "node_chapter_opening",
                    "node_chapter_opening",
                    str(getattr(state, "workflow_phase", "")),
                    node_chapter_opening,
                    state,
                    major_chapter,
                )
                major_chapter["chapter_opening_ready"] = True
                _checkpoint(state, checkpoint_path, reason="node_chapter_opening_done", node="node_chapter_opening", major_id=major_id, sub_id="")

            if is_resume_major and resume_sub_id:
                resume_anchor_idx = -1
                for idx_resume, sec in enumerate(pending_sub_sections):
                    if str(sec.get("sub_chapter_id", "")).strip() == resume_sub_id:
                        resume_anchor_idx = idx_resume
                        break
                if resume_anchor_idx > 0:
                    skipped = pending_sub_sections[:resume_anchor_idx]
                    pending_sub_sections = pending_sub_sections[resume_anchor_idx:]
                    print(f"| [Resume] 大章节 {major_id} 按断点子节 {resume_sub_id} 继续，跳过 {len(skipped)} 个已在断点前的小节")

            for sub_section in pending_sub_sections:
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
                done_sub_ids.add(sub_id)
                _mark_drafting_step_done(state, sub_id)
                _checkpoint(state, checkpoint_path, reason="node_writer_done", node="node_writer", major_id=major_id, sub_id=sub_id)
                _append_event("key", f"写作完成: {sub_id}", node="node_writer")

        # Safety guard: only move to review_pending if at least one section was written
        if not _completed_sub_id_set(state):
            print("| [ERROR] drafting 阶段未生成任何正文小节，无法进入审稿。请检查大纲和写作流程。")
            _write_runtime_status("error", "drafting 阶段未生成任何正文，无法进入审稿", interaction_mode=interaction_mode)
            _append_event("key", "drafting 阶段未生成正文", interaction_mode=interaction_mode)
            _checkpoint(state, checkpoint_path, reason="drafting_no_content_error", node="drafting")
            raise RuntimeError("DRAFTING_NO_CONTENT: 正文写稿阶段未生成任何内容，无法进入审稿。")

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
            requirements_path = _to_project_abs(str(action.get("requirements_path", "inputs/write_requests.md")).strip())
            _apply_requirements_from_file(state, requirements_path)

        manual_revision_path = _to_project_abs(str(action.get("manual_revision_path", state.manual_revision_path)).strip())
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
            review_report_path = project_path("completed_history", f"review_round_{state.review_round}_{safe_topic}.json")
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

            # Manual confirmation: wait for user to decide whether to continue to next round
            action = _timed_call(
                "wait_confirm_next_review_round",
                "reviewing",
                str(getattr(state, "workflow_phase", "")),
                _wait_for_action,
                state,
                checkpoint_path,
                action_name="confirm_next_review_round",
                prompt=f"第 {state.review_round} 轮审稿/重写已完成。请确认是否进入下一轮审稿，或停止并保留当前结果。",
                node="reviewing",
                interaction_mode=interaction_mode,
                stop_event=stop_event,
            )

            should_continue = bool(action.get("continue", True))
            if not should_continue:
                print(f"| 用户选择停止审稿，保留第 {state.review_round} 轮结果")
                _write_runtime_status("done", f"用户停止审稿，保留第 {state.review_round} 轮结果", interaction_mode=interaction_mode)
                _append_event("key", f"用户停止审稿，保留第 {state.review_round} 轮结果", interaction_mode=interaction_mode)
                state.workflow_phase = "done"
                _checkpoint(state, checkpoint_path, reason="user_stopped_review", node="done")
                break
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
