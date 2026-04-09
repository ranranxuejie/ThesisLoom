import json
import os
import importlib
import time
from html import escape
from pathlib import Path
from typing import Any, Dict

import streamlit as st

from state_dashboard import (
    get_editable_input_display_files,
    list_available_projects,
    get_current_project_name,
    open_or_create_project,
    open_or_create_project_by_folder,
    _read_inputs_payload,
    _read_state_snapshot,
    _write_action,
    _write_inputs_payload,
)
from core.project_paths import absolute_path_in_project, get_active_project_root

try:
    st_autorefresh = getattr(importlib.import_module("streamlit_autorefresh"), "st_autorefresh", None)
except Exception:
    st_autorefresh = None


FLOW_STEPS = [
    {
        "key": "preparation",
        "title": "准备阶段",
        "description": "确认主题、模型参数与基础输入是否完整。",
    },
    {
        "key": "literature_review",
        "title": "文献综述阶段",
        "description": "完成检索、补充 related_works 并生成 research_gaps。",
    },
    {
        "key": "drafting",
        "title": "章节计划与撰写",
        "description": "按大纲生成章节正文并持续落盘。",
    },
    {
        "key": "review_pending",
        "title": "审稿准备",
        "description": "确认进入审稿前的人机协作参数。",
    },
    {
        "key": "reviewing",
        "title": "审稿与重写",
        "description": "每完成一轮审稿后手动确认是否进入下一轮。",
    },
    {
        "key": "done",
        "title": "流程完成",
        "description": "终稿产出完成，可导出或切换项目。",
    },
]

FLOW_PHASE_MAP = {
    "idle": "preparation",
    "drafting": "drafting",
    "review_pending": "review_pending",
    "reviewing": "reviewing",
    "done": "done",
}

PREPARATION_NODES = {
    "",
    "pre_start",
    "pre_research",
    "node_title_builder",
}

LITERATURE_REVIEW_NODES = {
    "node_search_query_builder",
    "node_search_paper",
    "node_research_gaps",
}

START_REQUIRED_TEXT_FIELDS = {
    "topic": "topic",
    "model": "model",
    "language": "language",
}

NODE_LABELS = {
    "pre_start": "前置确认",
    "pre_research": "前置准备",
    "node_title_builder": "标题生成",
    "node_search_query_builder": "检索词生成",
    "node_search_paper": "文献检索",
    "node_research_gaps": "研究空白生成",
    "node_architect": "架构生成",
    "node_architecture_review": "架构审查",
    "node_planner": "章节规划",
    "node_chapter_header": "章节标题",
    "node_chapter_opening": "章节总起",
    "node_writer": "正文撰写",
    "node_overall_review": "总审稿",
    "node_major_review": "章节审稿",
    "node_rewrite": "章节重写",
    "reviewing": "审稿阶段",
    "resume": "断点恢复",
}

PENDING_ACTION_LABELS = {
    "confirm_inputs_ready": "确认输入已准备",
    "set_enable_auto_title": "是否自动生成标题",
    "set_enable_search": "是否执行文献检索",
    "confirm_related_works": "确认已补充 related_works",
    "enter_reviewing": "确认进入审稿阶段",
    "set_architecture_force_continue": "架构人工放行",
    "retry_after_llm_failure": "失败后继续重试",
    "confirm_next_review_round": "确认进入下一轮审稿",
}


def _read_text(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _write_text(path: str, content: str) -> Dict[str, Any]:
    try:
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"ok": True, "path": path}
    except Exception as e:
        return {"ok": False, "message": str(e)}


def _pick_folder_via_dialog(initial_dir: str = "") -> str:
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askdirectory(
            initialdir=initial_dir or str(Path.cwd()),
            title="选择 ThesisLoom 项目文件夹",
        )
        root.destroy()
        return str(selected or "")
    except Exception as e:
        st.error(f"无法打开文件夹选择器: {e}")
        return ""


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _pause_auto_refresh(seconds: float = 2.5) -> None:
    hold_seconds = max(0.5, float(seconds))
    st.session_state["ui_pause_refresh_until"] = time.time() + hold_seconds


def _is_auto_refresh_paused() -> bool:
    try:
        until = float(st.session_state.get("ui_pause_refresh_until", 0.0) or 0.0)
    except Exception:
        until = 0.0
    return time.time() < until


def _submit_action(payload: Dict[str, Any], success_text: str, pause_seconds: float = 2.5) -> bool:
    _pause_auto_refresh(pause_seconds)
    try:
        _write_action(payload)
    except Exception as e:
        st.error(f"动作提交失败: {e}")
        return False
    st.success(success_text)
    st.rerun()
    return True


def _sync_inputs_to_memory(inputs_data: Dict[str, Any]) -> None:
    project_name = get_current_project_name()
    mem_key = _state_memory_key(project_name)
    cached = st.session_state.get(mem_key)
    merged = dict(cached) if isinstance(cached, dict) else {}

    topic = str(inputs_data.get("topic", "")).strip()
    model = str(inputs_data.get("model", "")).strip()
    language = str(inputs_data.get("language", "")).strip()

    merged["inputs_topic"] = topic
    merged["inputs_model"] = model
    merged["inputs_language"] = language

    runtime_status = str(merged.get("runtime_status", "")).strip().lower()
    workflow_phase = str(merged.get("workflow_phase", "")).strip().lower()
    pending_action = str(merged.get("pending_action", "")).strip()
    safe_status = {"", "unknown", "stopped", "failed", "done", "idle"}
    if (runtime_status in safe_status) or (workflow_phase in {"", "idle"}) or (pending_action == "confirm_inputs_ready"):
        merged["topic"] = topic
        merged["model"] = model
        merged["language"] = language

    st.session_state[mem_key] = merged


def _validate_inputs_for_start(inputs_data: Dict[str, Any], state_snapshot: Dict[str, Any]) -> list[str]:
    errors: list[str] = []

    for key, label in START_REQUIRED_TEXT_FIELDS.items():
        value = str(inputs_data.get(key, "")).strip()
        if not value:
            errors.append(f"必填项未填写: {label}")

    language = str(inputs_data.get("language", "")).strip()
    if language and language not in {"English", "Chinese"}:
        errors.append("language 仅支持 English 或 Chinese")

    max_review_rounds = _safe_int(inputs_data.get("max_review_rounds", 0), 0)
    if max_review_rounds < 1:
        errors.append("max_review_rounds 必须大于等于 1")

    paper_search_limit = _safe_int(inputs_data.get("paper_search_limit", 0), 0)
    if paper_search_limit < 1:
        errors.append("paper_search_limit 必须大于等于 1")

    has_checkpoint = bool(state_snapshot.get("has_checkpoint"))
    auto_resume = bool(inputs_data.get("auto_resume", False))
    if has_checkpoint and auto_resume:
        checkpoint_model = str(state_snapshot.get("model", "")).strip()
        input_model = str(inputs_data.get("model", "")).strip()
        if checkpoint_model and input_model and (checkpoint_model != input_model):
            errors.append(
                f"检测到断点模型为 {checkpoint_model}，当前输入模型为 {input_model}。"
                "若要使用新模型，请先关闭 auto_resume 或切换到新项目。"
            )

    return errors


def _state_memory_key(project_name: str) -> str:
    safe_name = str(project_name or "default").strip() or "default"
    return f"workflow_state_memory::{safe_name}"


def _sync_state_snapshot_into_memory(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    project_name = str(snapshot.get("project_name", get_current_project_name()))
    mem_key = _state_memory_key(project_name)

    if bool(snapshot.get("ok")) and bool(snapshot.get("has_checkpoint")):
        copied = json.loads(json.dumps(snapshot, ensure_ascii=False))
        copied["restored_from_memory"] = True
        st.session_state[mem_key] = copied
        return copied

    cached = st.session_state.get(mem_key)
    if bool(snapshot.get("ok")) and (not bool(snapshot.get("has_checkpoint"))):
        st.session_state.pop(mem_key, None)
        return snapshot

    if isinstance(cached, dict):
        merged = dict(cached)
        runtime_keys = [
            "runtime_status",
            "runtime_message",
            "runtime_time",
            "runtime_interaction_mode",
            "server_time",
            "pending_action",
            "pending_action_message",
            "inputs_topic",
            "inputs_model",
            "inputs_language",
            "token_usage",
        ]
        for key in runtime_keys:
            if key in snapshot:
                merged[key] = snapshot.get(key)
        merged["restored_from_memory"] = True
        return merged

    return snapshot


def _resolve_flow_key(state: Dict[str, Any]) -> str:
    phase = str(state.get("workflow_phase", "idle")).strip().lower()
    current_node = str(state.get("current_node", "")).strip()
    pending_action = str(state.get("pending_action", "")).strip()
    query_count = _safe_int(state.get("search_query_count", 0), 0)
    pre_done_query_builder = bool(state.get("pre_done_query_builder", False))
    pre_done_paper_search = bool(state.get("pre_done_paper_search", False))

    if phase in {"idle", "pre_research"}:
        if pending_action == "confirm_related_works":
            return "literature_review"
        if current_node in LITERATURE_REVIEW_NODES:
            return "literature_review"
        if pre_done_query_builder or pre_done_paper_search or query_count > 0:
            return "literature_review"
        if current_node in PREPARATION_NODES:
            return "preparation"
        return "preparation"

    return FLOW_PHASE_MAP.get(phase, "preparation")


def _resolve_flow_index(flow_key: str) -> int:
    for idx, step in enumerate(FLOW_STEPS):
        if step["key"] == flow_key:
            return idx
    return 0


def _friendly_node_name(node: str) -> str:
    raw = str(node or "").strip()
    if not raw:
        return "-"
    return NODE_LABELS.get(raw, raw)


def _friendly_pending_action_name(action: str) -> str:
    raw = str(action or "").strip()
    if not raw:
        return "-"
    return PENDING_ACTION_LABELS.get(raw, raw)


def _derive_runtime_status_text(state: Dict[str, Any]) -> str:
    pending_action = str(state.get("pending_action", "")).strip()
    if pending_action:
        return f"等待用户操作：{_friendly_pending_action_name(pending_action)}"

    runtime_status = str(state.get("runtime_status", "")).strip().lower()
    runtime_message = str(state.get("runtime_message", "")).strip()
    current_node = str(state.get("current_node", "")).strip()

    if runtime_status in {"running", "starting"}:
        if current_node:
            return f"大模型输出中：{_friendly_node_name(current_node)}"
        return "工作流执行中"
    if runtime_status in {"waiting_action", "paused"}:
        return runtime_message or "流程暂停，等待用户动作"
    if runtime_status == "done":
        return "流程已完成"
    if runtime_status == "failed":
        return runtime_message or "流程执行失败"

    return runtime_message or "等待工作流启动"


def _derive_next_step_text(state: Dict[str, Any], step_key: str) -> str:
    pending_action = str(state.get("pending_action", "")).strip()
    current_sub_id = str(state.get("current_sub_chapter_id", "")).strip()
    pending_rewrite_count = _safe_int(state.get("pending_rewrite_count", 0), 0)

    if pending_action:
        return f"处理动作：{_friendly_pending_action_name(pending_action)}"

    if step_key == "preparation":
        return "确认参数与输入素材后进入文献综述阶段"
    if step_key == "literature_review":
        return "完成检索与综述后进入章节计划与撰写"
    if step_key == "drafting":
        if current_sub_id:
            return f"继续推进小节 {current_sub_id}"
        return "完成全部小节后进入审稿准备"
    if step_key == "review_pending":
        return "确认审稿参数后进入审稿与重写"
    if step_key == "reviewing":
        if pending_rewrite_count > 0:
            return f"继续重写剩余 {pending_rewrite_count} 个待改小节"
        return "等待审稿结论并检查是否通过"
    if step_key == "done":
        return "可导出终稿、切换项目或发起新任务"

    return "等待下一步"


def _build_drafting_detail_rows(state: Dict[str, Any]) -> list[Dict[str, str]]:
    outputs = state.get("paper_outputs", []) or []
    normalized = []
    for row in outputs:
        if not isinstance(row, dict):
            continue
        sub_id = str(row.get("sub_chapter_id", "")).strip()
        if not sub_id:
            continue
        normalized.append(
            {
                "sub_id": sub_id,
                "order": _safe_int(row.get("actual_order_index", 0), 0),
            }
        )

    normalized.sort(key=lambda x: (x["order"], x["sub_id"]))
    recent_completed = normalized[-4:]
    rows: list[Dict[str, str]] = [
        {
            "label": f"撰写 {x['sub_id']}",
            "status": "done",
            "detail": "已完成",
        }
        for x in recent_completed
    ]

    completed_ids = {x["sub_id"] for x in normalized}
    current_sub_id = str(state.get("current_sub_chapter_id", "")).strip()
    current_node = str(state.get("current_node", "")).strip()
    runtime_status = str(state.get("runtime_status", "")).strip().lower()
    writing_nodes = {
        "node_writer",
        "node_rewrite",
        "node_chapter_opening",
        "node_chapter_header",
    }
    if current_sub_id and (current_sub_id not in completed_ids):
        detail = "大模型输出中..." if (runtime_status in {"running", "starting"} and current_node in writing_nodes) else "等待调度"
        rows.append(
            {
                "label": f"撰写 {current_sub_id}",
                "status": "current",
                "detail": detail,
            }
        )

    if not rows:
        rows.append({"label": "等待章节计划生成", "status": "todo", "detail": "尚未开始"})

    return rows[-5:]


def _render_flow_status_panel(state: Dict[str, Any]) -> None:
    flow_key = _resolve_flow_key(state)
    current_idx = _resolve_flow_index(flow_key)
    runtime_text = _derive_runtime_status_text(state)

    progress_value = min(1.0, max(0.0, (current_idx + 1) / max(1, len(FLOW_STEPS))))
    st.progress(progress_value)
    st.caption(f"当前节点: {_friendly_node_name(state.get('current_node', ''))}")

    st.markdown(
        """
        <style>
          .tl-flow-wrap {
            border: 1px solid #d9e7f2;
            border-radius: 14px;
            background: linear-gradient(160deg, #fbfdff 0%, #f2f8fc 60%, #eef7ff 100%);
            padding: 10px;
          }
          .tl-step {
            display: grid;
            grid-template-columns: 34px 1fr;
            gap: 8px;
            padding: 10px;
            border: 1px solid #dbe7f2;
            border-radius: 12px;
            background: #ffffffd9;
            margin-bottom: 8px;
          }
          .tl-step.done {
            border-color: #bee3cf;
            background: #f3faf5;
          }
          .tl-step.current {
            border-color: #86b7d7;
            background: #ebf5ff;
            box-shadow: 0 0 0 1px #d0e7f8 inset;
          }
          .tl-marker {
            width: 26px;
            height: 26px;
            border-radius: 999px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            color: #1f2937;
            background: #e5edf4;
            margin-top: 2px;
          }
          .tl-step.done .tl-marker {
            background: #c6f0d8;
            color: #0f766e;
          }
          .tl-step.current .tl-marker {
            background: #cde8ff;
            color: #0c4a6e;
            animation: tlPulse 1.1s ease-in-out infinite;
          }
          .tl-title-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
          }
          .tl-title {
            font-weight: 700;
            color: #1f2937;
          }
          .tl-status {
            font-size: 12px;
            color: #35516a;
            background: #e5eef7;
            border-radius: 999px;
            padding: 2px 8px;
          }
          .tl-line {
            color: #334155;
            font-size: 13px;
            margin-top: 4px;
          }
          .tl-desc {
            color: #64748b;
            font-size: 12px;
            margin-top: 4px;
          }
          .tl-sub-list {
            margin-top: 6px;
            border-top: 1px dashed #c5d9ea;
            padding-top: 6px;
          }
          .tl-sub-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
            font-size: 12px;
            color: #334155;
            padding: 2px 0;
          }
          .tl-sub-row.done em {
            color: #0f766e;
          }
          .tl-sub-row.current em {
            color: #0369a1;
            font-style: normal;
            font-weight: 700;
          }
          .tl-sub-row.todo em {
            color: #9ca3af;
          }
          @keyframes tlPulse {
            0% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.35); }
            100% { box-shadow: 0 0 0 8px rgba(59, 130, 246, 0.0); }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

    html_parts = ["<div class='tl-flow-wrap'>"]
    for idx, step in enumerate(FLOW_STEPS):
        if flow_key == "done":
            status_key = "done"
        elif idx < current_idx:
            status_key = "done"
        elif idx == current_idx:
            status_key = "current"
        else:
            status_key = "todo"

        marker = {"done": "✓", "current": "▶", "todo": "○"}[status_key]
        status_text = {"done": "已完成", "current": "进行中", "todo": "待开始"}[status_key]
        current_line = runtime_text if status_key == "current" else ("已达成阶段目标" if status_key == "done" else "等待上一阶段完成")
        next_line = _derive_next_step_text(state, step["key"])

        html_parts.append(f"<div class='tl-step {status_key}'>")
        html_parts.append(f"<div class='tl-marker'>{marker}</div>")
        html_parts.append("<div>")
        html_parts.append("<div class='tl-title-row'>")
        html_parts.append(f"<div class='tl-title'>{escape(step['title'])}</div>")
        html_parts.append(f"<div class='tl-status'>{escape(status_text)}</div>")
        html_parts.append("</div>")
        html_parts.append(f"<div class='tl-line'>当前状态：{escape(current_line)}</div>")
        html_parts.append(f"<div class='tl-line'>下一步：{escape(next_line)}</div>")
        html_parts.append(f"<div class='tl-desc'>说明：{escape(step['description'])}</div>")

        if step["key"] == "drafting" and status_key in {"done", "current"}:
            details = _build_drafting_detail_rows(state)
            detail_html = "".join(
                f"<div class='tl-sub-row {escape(item['status'])}'><span>{escape(item['label'])}</span><em>{escape(item['detail'])}</em></div>"
                for item in details
            )
            html_parts.append(f"<div class='tl-sub-list'>{detail_html}</div>")

        html_parts.append("</div>")
        html_parts.append("</div>")
    html_parts.append("</div>")

    st.markdown("".join(html_parts), unsafe_allow_html=True)


def _render_inputs_form() -> None:
    payload = _read_inputs_payload()
    if not payload.get("ok"):
        st.error(f"读取 inputs.json 失败: {payload.get('message', 'unknown')}")
        return

    data = payload.get("data", {}) if isinstance(payload.get("data", {}), dict) else {}
    st.caption(f"当前文件: {payload.get('path', '-')}")

    with st.form("inputs_form", clear_on_submit=False):
        topic = st.text_area("topic", value=str(data.get("topic", "")), height=110)
        language = st.selectbox("language", options=["English", "Chinese"], index=0 if str(data.get("language", "English")) == "English" else 1)
        model = st.text_input("model", value=str(data.get("model", "")))

        c1, c2 = st.columns(2)
        max_review_rounds = c1.number_input("max_review_rounds", min_value=1, max_value=20, value=int(data.get("max_review_rounds", 3) or 3), step=1)
        paper_search_limit = c2.number_input("paper_search_limit", min_value=1, max_value=200, value=int(data.get("paper_search_limit", 30) or 30), step=1)

        openalex_api_key = st.text_input("openalex_api_key", value=str(data.get("openalex_api_key", "")))
        ark_api_key = st.text_input("ark_api_key", value=str(data.get("ark_api_key", "")))
        base_url = st.text_input("base_url", value=str(data.get("base_url", "")))
        model_api_key = st.text_input("model_api_key", value=str(data.get("model_api_key", "")))
        auto_resume = st.checkbox("auto_resume", value=bool(data.get("auto_resume", False)))

        extra = {}
        known = {
            "topic", "language", "model", "max_review_rounds", "paper_search_limit",
            "openalex_api_key", "ark_api_key", "base_url", "model_api_key",
            "auto_resume",
        }
        for k, v in data.items():
            if k not in known:
                extra[k] = v

        extra_json = st.text_area(
            "其他字段（JSON 对象，可选）",
            value=json.dumps(extra, ensure_ascii=False, indent=2),
            height=130,
        )

        save_btn = st.form_submit_button("保存 inputs（表单）", type="primary")
        start_btn = st.form_submit_button("保存并开始工作流")

    if not (save_btn or start_btn):
        return

    _pause_auto_refresh(3.0)

    try:
        extra_obj = json.loads(extra_json.strip() or "{}")
        if not isinstance(extra_obj, dict):
            st.error("其他字段必须是 JSON 对象")
            return
    except Exception as e:
        st.error(f"其他字段 JSON 解析失败: {e}")
        return

    new_data: Dict[str, Any] = {
        "topic": topic,
        "language": language,
        "model": model,
        "max_review_rounds": int(max_review_rounds),
        "paper_search_limit": int(paper_search_limit),
        "openalex_api_key": openalex_api_key,
        "ark_api_key": ark_api_key,
        "base_url": base_url,
        "model_api_key": model_api_key,
        "auto_resume": bool(auto_resume),
    }
    new_data.update(extra_obj)

    result = _write_inputs_payload(json.dumps(new_data, ensure_ascii=False, indent=2))
    if not result.get("ok"):
        st.error(f"保存失败: {result.get('message', 'unknown')}")
        return

    _sync_inputs_to_memory(new_data)
    st.success("inputs.json 已保存")

    if start_btn:
        state_snapshot = _read_state_snapshot()
        errors = _validate_inputs_for_start(new_data, state_snapshot)
        if errors:
            st.error("检测到必填项或启动条件未满足，已阻止启动工作流。")
            for msg in errors:
                st.warning(msg)
            return

        _submit_action({"action": "confirm_inputs_ready"}, "已提交 confirm_inputs_ready", pause_seconds=3.0)


def _render_paper_outputs_panel(state: Dict[str, Any]) -> None:
    st.subheader("论文输出（可折叠）")
    outputs = state.get("paper_outputs", []) or []
    if not outputs:
        st.info("当前还没有正文输出。")
        return

    for row in outputs:
        sid = str(row.get("sub_chapter_id", ""))
        title = str(row.get("title", "")).strip() or "Untitled"
        major = str(row.get("major_title", "")).strip()
        order_idx = int(row.get("actual_order_index", 0) or 0)
        content = str(row.get("content", ""))
        label = f"[{order_idx}] {sid} {title}"
        if major:
            label = f"[{order_idx}] {major} / {sid} {title}"
        with st.expander(label, expanded=False):
            st.markdown(content if content else "(empty)")


def _render_pipeline_outputs_panel(state: Dict[str, Any]) -> None:
    st.subheader("架构/规划/审稿输出")

    with st.expander("检索词输出（Search Query Builder）", expanded=False):
        search_queries = state.get("search_queries", []) or []
        if search_queries:
            st.write(f"共 {len(search_queries)} 条")
            st.json(search_queries)
        else:
            st.info("暂无检索词输出")

    architect_outline = state.get("architect_outline", []) or []
    with st.expander("架构输出（Architect）", expanded=False):
        if architect_outline:
            rows = []
            for x in architect_outline:
                if not isinstance(x, dict):
                    continue
                rows.append({
                    "major_id": x.get("major_chapter_id", ""),
                    "major_title": x.get("major_title", ""),
                    "writing_order": x.get("writing_order", ""),
                    "sub_sections": len(x.get("sub_sections", []) or []),
                })
            st.dataframe(rows, width="stretch", hide_index=True)
            st.json(architect_outline)
        else:
            st.info("暂无架构输出")

    planner_outputs = state.get("planner_outputs", []) or []
    with st.expander("规划输出（Planner）", expanded=False):
        if planner_outputs:
            st.dataframe(planner_outputs, width="stretch", hide_index=True)
        else:
            st.info("暂无规划输出")

    with st.expander("总审稿输出（Overall Review）", expanded=False):
        summary = str(state.get("overall_review_summary", "") or "").strip()
        plans = state.get("overall_review_plans", []) or []
        st.markdown(summary if summary else "(no summary)")
        if plans:
            st.json(plans)
        else:
            st.info("暂无总审稿计划")

    with st.expander("章节审稿输出（Major Review）", expanded=False):
        items = state.get("major_review_items", []) or []
        if items:
            st.json(items)
        else:
            st.info("暂无章节审稿条目")


def _render_center_editor() -> None:
    st.subheader("输入修改与展示")
    options = ["inputs.json"] + get_editable_input_display_files()
    selected = st.selectbox("选择可编辑文件", options=options, index=0)

    if selected == "inputs.json":
        _render_inputs_form()
        return

    project_name = get_current_project_name()
    abs_path = absolute_path_in_project(selected)
    st.caption(f"当前项目: {project_name} | 文件: {abs_path}")

    state_key = f"editor::{project_name}::{selected}"
    if state_key not in st.session_state:
        st.session_state[state_key] = _read_text(abs_path)

    content = st.text_area("内容", value=st.session_state[state_key], height=420, key=f"textarea::{project_name}::{selected}")

    col_save, col_start = st.columns(2)
    if col_save.button("保存", width="stretch"):
        _pause_auto_refresh(2.5)
        result = _write_text(abs_path, content)
        if result.get("ok"):
            st.success(f"保存成功: {selected}")
            st.session_state[state_key] = content
        else:
            st.error(f"保存失败: {result.get('message', 'unknown')}")

    if col_start.button("保存并开始工作流", width="stretch", type="primary"):
        _pause_auto_refresh(3.0)
        result = _write_text(abs_path, content)
        if result.get("ok"):
            payload = _read_inputs_payload()
            if (not payload.get("ok")) or (not isinstance(payload.get("data"), dict)):
                st.error("无法读取 inputs.json，已阻止启动工作流。")
                return

            current_inputs = payload.get("data", {})
            state_snapshot = _read_state_snapshot()
            errors = _validate_inputs_for_start(current_inputs, state_snapshot)
            if errors:
                st.error("检测到必填项或启动条件未满足，已阻止启动工作流。")
                for msg in errors:
                    st.warning(msg)
                return

            _submit_action({"action": "confirm_inputs_ready"}, "已保存并提交 confirm_inputs_ready", pause_seconds=3.0)
        else:
            st.error(f"保存失败: {result.get('message', 'unknown')}")


def _render_actions_and_logs(state: Dict[str, Any], panel_mode: str = "tabs") -> None:
    st.subheader("流程状态中心")

    def _render_flow_view() -> None:
        _render_flow_status_panel(state)
        if state.get("restored_from_memory"):
            st.caption("已将断点状态恢复到会话内存，界面与断点状态保持一致。")

        wm = state.get("workflow_metrics", {}) or {}
        totals = wm.get("totals", {}) if isinstance(wm, dict) else {}
        c1, c2 = st.columns(2)
        c1.metric("Step Calls", int(totals.get("step_calls", 0) or 0))
        c2.metric("Step Seconds", f"{float(totals.get('total_step_seconds', 0.0) or 0.0):.1f}")

        # Token usage display
        tu = state.get("token_usage", {}) or {}
        total_input_tokens = int(tu.get("total_input_tokens", 0) or 0)
        total_output_tokens = int(tu.get("total_output_tokens", 0) or 0)
        tc1, tc2 = st.columns(2)
        tc1.metric("📊 总输入 Tokens", f"{total_input_tokens:,}")
        tc2.metric("📊 总输出 Tokens", f"{total_output_tokens:,}")

        current_hint = _derive_runtime_status_text(state)
        pending_name = _friendly_pending_action_name(state.get("pending_action", ""))
        st.info(f"当前状态: {current_hint}")
        st.caption(f"待处理动作: {pending_name}")

    def _render_action_view() -> None:
        pending_action = str(state.get("pending_action", ""))
        pending_message = str(state.get("pending_action_message", ""))
        runtime_status = str(state.get("runtime_status", "")).strip().lower()
        runtime_message = str(state.get("runtime_message", ""))

        if pending_action:
            st.error(f"必须处理动作后才能继续: {_friendly_pending_action_name(pending_action)}")
            st.caption(pending_message or "-")

            if pending_action == "set_enable_search":
                c1, c2 = st.columns(2)
                if c1.button("执行检索并继续", type="primary", width="stretch"):
                    _submit_action({"action": "set_enable_search", "value": True}, "已提交 set_enable_search=True")
                if c2.button("跳过检索并继续", width="stretch"):
                    _submit_action({"action": "set_enable_search", "value": False}, "已提交 set_enable_search=False")

            elif pending_action == "set_enable_auto_title":
                c1, c2 = st.columns(2)
                if c1.button("开启自动生成标题并继续", type="primary", width="stretch"):
                    _submit_action({"action": "set_enable_auto_title", "value": True}, "已提交 set_enable_auto_title=True")
                if c2.button("关闭自动生成标题并继续", width="stretch"):
                    _submit_action({"action": "set_enable_auto_title", "value": False}, "已提交 set_enable_auto_title=False")

            elif pending_action == "confirm_related_works":
                if st.button("我已补充 related_works，继续", type="primary", width="stretch"):
                    _submit_action({"action": "confirm_related_works"}, "已提交 confirm_related_works")

            elif pending_action == "enter_reviewing":
                load_requirements = st.checkbox("加载自定义要求文件", value=True)
                req_path = st.text_input("requirements_path", value="inputs/write_requests.md")
                if st.button("确认进入审稿并继续", type="primary", width="stretch"):
                    _submit_action(
                        {
                            "action": "enter_reviewing",
                            "load_requirements": bool(load_requirements),
                            "requirements_path": req_path.strip() or "inputs/write_requests.md",
                        },
                        "已提交 enter_reviewing",
                    )

            elif pending_action == "confirm_inputs_ready":
                if st.button("输入已准备完成，继续", type="primary", width="stretch"):
                    _submit_action({"action": "confirm_inputs_ready"}, "已提交 confirm_inputs_ready")

            elif pending_action == "set_architecture_force_continue":
                c1, c2 = st.columns(2)
                if c1.button("人工放行继续到规划", type="primary", width="stretch"):
                    _submit_action({"action": "set_architecture_force_continue", "value": True}, "已提交 set_architecture_force_continue=True")
                if c2.button("不放行，继续架构修订", width="stretch"):
                    _submit_action({"action": "set_architecture_force_continue", "value": False}, "已提交 set_architecture_force_continue=False")
        else:
            if runtime_status in {"paused", "waiting_action"} and "LLM" in runtime_message.upper():
                st.warning(runtime_message)
                if st.button("继续重试（从断点续跑）", type="primary", width="stretch"):
                    _submit_action({"action": "retry_after_llm_failure"}, "已提交 retry_after_llm_failure")
            else:
                st.success("当前无待处理动作")

            if pending_action == "confirm_next_review_round":
                review_round = _safe_int(state.get("review_round", 0), 0)
                max_rounds = _safe_int(state.get("max_review_rounds", 3), 3)
                st.info(f"当前已完成第 {review_round} 轮审稿/重写，最大轮次: {max_rounds}")
                c1, c2 = st.columns(2)
                if c1.button("确认进入下一轮审稿", type="primary", width="stretch"):
                    _submit_action({"action": "confirm_next_review_round", "continue": True}, "已确认进入下一轮审稿")
                if c2.button("停止审稿，保留当前结果", width="stretch"):
                    _submit_action({"action": "confirm_next_review_round", "continue": False}, "已停止审稿循环")

        with st.expander("已记录动作偏好与历史", expanded=False):
            prefs = state.get("action_preferences", {}) or {}
            history = state.get("action_history", []) or []
            auto_apply = bool(state.get("auto_apply_saved_actions", True))
            st.caption(f"自动复用动作选择: {'开启' if auto_apply else '关闭'}")

            if isinstance(prefs, dict) and prefs:
                st.json(prefs)
            else:
                st.info("当前没有已记录的动作偏好。")

            if isinstance(history, list) and history:
                rows = [x for x in history if isinstance(x, dict)][-15:]
                rows.reverse()
                st.dataframe(rows, width="stretch", hide_index=True)
            else:
                st.info("当前没有动作历史记录。")

    panel_key = str(panel_mode or "tabs").strip().lower()
    if panel_key == "action_top":
        _render_action_view()
        st.divider()
        _render_flow_view()
        return
    if panel_key == "flow_top":
        _render_flow_view()
        st.divider()
        _render_action_view()
        return

    flow_tab, action_tab = st.tabs(["流程视图", "动作控制"])
    with flow_tab:
        _render_flow_view()
    with action_tab:
        _render_action_view()


def main() -> None:
    st.set_page_config(
        page_title="ThesisLoom Streamlit Console",
        page_icon="🧠",
        layout="wide",
    )

    st.markdown(
        """
        <style>
                    :root {
                        color-scheme: light !important;
                    }
          .stApp {
            background: radial-gradient(circle at 10% 0%, #eaf8f1 0%, #f2f7f5 45%, #e2f2f8 100%);
          }
                    html, body, [data-testid="stAppViewContainer"] {
                        color: #111827 !important;
                    }
                    [data-testid="stMarkdownContainer"], [data-testid="stCaptionContainer"], label {
                        color: #1f2937 !important;
                    }
                    .stTextInput input,
                    .stTextArea textarea,
                    .stNumberInput input {
                        color: #111827 !important;
                        background: #ffffff !important;
                        border-color: #c9d6e3 !important;
                    }
                    div[data-baseweb="select"] * {
                        color: #111827 !important;
                    }
                    button[role="tab"] {
                        color: #1f2937 !important;
                    }
                    button[role="tab"][aria-selected="true"] {
                        background: #dbeafe !important;
                        color: #0f172a !important;
                    }
                    [data-testid="stAlert"] {
                        color: #111827 !important;
                    }
                    header[data-testid="stHeader"] {
                        visibility: hidden;
                        height: 0;
                    }
                    div[data-testid="stToolbar"] {
                        visibility: hidden;
                        height: 0;
                        position: fixed;
                    }
                    div[data-testid="stDecoration"] {
                        display: none;
                    }
          .block-container {
                        padding-top: 0.25rem;
            padding-bottom: 1rem;
          }
                    h1 {
                        margin-top: 0 !important;
                        padding-top: 0 !important;
                        margin-bottom: 0.25rem !important;
                    }
                    .tl-main-caption {
                        margin-top: 0 !important;
                        margin-bottom: 0.35rem !important;
                    }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("ThesisLoom Human-in-the-Loop Streamlit Console")
    st.markdown("<div class='tl-main-caption'>固定布局：左侧输入/输出标签页，右侧流程状态中心常驻（动作控制在上）。</div>", unsafe_allow_html=True)

    with st.expander("项目管理", expanded=True):
        current_project = get_current_project_name()
        c1, c2 = st.columns([1.2, 1.8])
        all_projects = list_available_projects()
        if current_project not in all_projects:
            all_projects = [current_project] + all_projects

        selected_project = c1.selectbox("打开已有项目", options=all_projects, index=max(0, all_projects.index(current_project)))
        new_project_name = c2.text_input("新建项目名称", value="")

        b1, b2 = st.columns(2)
        if b1.button("打开项目", width="stretch"):
            _pause_auto_refresh(2.5)
            result = open_or_create_project(selected_project)
            if result.get("ok"):
                restored = _sync_state_snapshot_into_memory(_read_state_snapshot())
                if restored.get("has_checkpoint"):
                    st.success(f"已打开项目: {result.get('project_name')}（已从断点恢复状态）")
                else:
                    st.success(f"已打开项目: {result.get('project_name')}")
                st.rerun()
            else:
                st.error(result.get("message", "打开项目失败"))

        if b2.button("新建并打开项目", width="stretch", type="primary"):
            _pause_auto_refresh(2.5)
            if not str(new_project_name).strip():
                st.error("请输入项目名称")
            else:
                result = open_or_create_project(new_project_name)
                if result.get("ok"):
                    restored = _sync_state_snapshot_into_memory(_read_state_snapshot())
                    if restored.get("has_checkpoint"):
                        st.success(f"已创建并打开项目: {result.get('project_name')}（已加载断点状态）")
                    else:
                        st.success(f"已创建并打开项目: {result.get('project_name')}")
                    st.rerun()
                else:
                    st.error(result.get("message", "创建项目失败"))

        st.divider()
        st.caption("可直接选择任意文件夹作为项目根目录（用于切换项目）。")
        folder_path_key = "project_folder_picker_path"
        if folder_path_key not in st.session_state:
            st.session_state[folder_path_key] = str(get_active_project_root())

        st.text_input("项目文件夹路径", key=folder_path_key)
        folder_alias = st.text_input("项目显示名称（可选）", value="")
        fc1, fc2 = st.columns(2)

        if fc1.button("浏览文件夹", width="stretch"):
            selected_folder = _pick_folder_via_dialog(str(st.session_state.get(folder_path_key, "")))
            if selected_folder:
                st.session_state[folder_path_key] = selected_folder
                st.rerun()

        if fc2.button("使用该文件夹作为项目", width="stretch"):
            _pause_auto_refresh(2.5)
            folder_path = str(st.session_state.get(folder_path_key, "")).strip()
            result = open_or_create_project_by_folder(folder_path, project_name=folder_alias)
            if result.get("ok"):
                restored = _sync_state_snapshot_into_memory(_read_state_snapshot())
                if restored.get("has_checkpoint"):
                    st.success(f"已切换到文件夹项目: {result.get('project_name')}（已加载断点状态）")
                else:
                    st.success(f"已切换到文件夹项目: {result.get('project_name')}")
                st.rerun()
            else:
                st.error(result.get("message", "切换文件夹项目失败"))

        st.caption(f"当前项目目录: {get_active_project_root()}")

    state = _sync_state_snapshot_into_memory(_read_state_snapshot())
    topic_line = (state.get("topic") or state.get("inputs_topic") or "(empty topic)")

    top1, top2, top3, top4 = st.columns([2.2, 1.2, 1.2, 1.2])
    top1.info(f"Topic: {topic_line}")
    top2.info(f"Phase: {state.get('workflow_phase', '-')}")
    top3.info(f"Runtime: {state.get('runtime_status', '-')}")
    top4.info(f"Server: {state.get('server_time', '-')}")

    ctl1, ctl2 = st.columns([2.2, 1.0])
    ctl1.caption("页面固定为 1Hz 自动刷新（动作提交后会短暂停止自动刷新以保护交互）。")
    if ctl2.button("手动刷新", width="stretch"):
        st.rerun()

    paused_refresh = _is_auto_refresh_paused()
    if paused_refresh:
        remain = max(0.0, float(st.session_state.get("ui_pause_refresh_until", 0.0) or 0.0) - time.time())
        st.caption(f"自动刷新已临时暂停，预计 {remain:.1f} 秒后恢复。")

    if not paused_refresh:
        interval_ms = 1000
        if st_autorefresh is not None:
            st_autorefresh(interval=interval_ms, key=f"streamlit_auto_refresh::{get_current_project_name()}")
        else:
            # Reliable fallback: use meta refresh instead of script injection
            st.markdown(
                f'<meta http-equiv="refresh" content="{max(1, interval_ms // 1000)}">',
                unsafe_allow_html=True,
            )

    if state.get("restored_from_memory"):
        st.caption("断点状态已同步到会话内存。")

    left_col, right_col = st.columns([1.55, 1.45])
    with left_col:
        input_tab, output_tab = st.tabs(["输入", "输出"])
        with input_tab:
            _render_center_editor()
        with output_tab:
            out1, out2 = st.tabs(["论文输出", "架构与审稿输出"])
            with out1:
                _render_paper_outputs_panel(state)
            with out2:
                _render_pipeline_outputs_panel(state)

    with right_col:
        _render_actions_and_logs(state, panel_mode="action_top")


if __name__ == "__main__":
    main()
