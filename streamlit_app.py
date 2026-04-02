import json
import os
from typing import Any, Dict

import streamlit as st

from state_dashboard import (
    EDITABLE_INPUT_FILES,
    _read_inputs_payload,
    _read_state_snapshot,
    _write_action,
    _write_inputs_payload,
)


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


def _build_stage_rows(state: Dict[str, Any]) -> list[Dict[str, Any]]:
    phase = str(state.get("workflow_phase", "idle"))
    current_node = str(state.get("current_node", ""))
    order = [
        ("idle", "初始化"),
        ("pre_research", "检索前准备"),
        ("drafting", "正文写作"),
        ("review_pending", "等待进入审稿"),
        ("reviewing", "审稿与重写"),
        ("done", "完成"),
    ]
    phase_idx = -1
    for idx, item in enumerate(order):
        if item[0] == phase:
            phase_idx = idx
            break

    rows = []
    for idx, (key, name) in enumerate(order):
        done_mark = "✅" if (phase_idx >= idx and phase_idx >= 0) else "⬜"
        is_current = "👉" if key == phase else ""
        rows.append(
            {
                "完成": done_mark,
                "阶段": name,
                "phase_key": key,
                "当前": is_current,
                "节点": current_node if key == phase else "",
            }
        )
    return rows


def _render_center_editor() -> None:
    st.subheader("输入修改与展示")
    options = ["inputs.json"] + EDITABLE_INPUT_FILES
    selected = st.selectbox("选择可编辑文件", options=options, index=0)

    state_key = f"editor::{selected}"
    if state_key not in st.session_state:
        if selected == "inputs.json":
            payload = _read_inputs_payload()
            st.session_state[state_key] = str(payload.get("raw", "{}")) if payload.get("ok") else "{}"
        else:
            st.session_state[state_key] = _read_text(selected)

    content = st.text_area("内容", value=st.session_state[state_key], height=420, key=f"textarea::{selected}")

    col_save, col_start = st.columns(2)
    if col_save.button("保存", width="stretch"):
        if selected == "inputs.json":
            result = _write_inputs_payload(content)
        else:
            result = _write_text(selected, content)
        if result.get("ok"):
            st.success(f"保存成功: {selected}")
            st.session_state[state_key] = content
        else:
            st.error(f"保存失败: {result.get('message', 'unknown')}")

    if col_start.button("保存并开始工作流", width="stretch", type="primary"):
        if selected == "inputs.json":
            result = _write_inputs_payload(content)
        else:
            result = _write_text(selected, content)
        if result.get("ok"):
            _write_action({"action": "confirm_inputs_ready"})
            st.success("已保存并提交 confirm_inputs_ready")
        else:
            st.error(f"保存失败: {result.get('message', 'unknown')}")


def _render_actions_and_logs(state: Dict[str, Any]) -> None:
    st.subheader("阶段进度 / 用户动作")
    stage_rows = _build_stage_rows(state)
    st.dataframe(stage_rows, width="stretch", hide_index=True)

    wm = state.get("workflow_metrics", {}) or {}
    totals = wm.get("totals", {}) if isinstance(wm, dict) else {}
    c1, c2 = st.columns(2)
    c1.metric("Step Calls", int(totals.get("step_calls", 0) or 0))
    c2.metric("Step Seconds", float(totals.get("total_step_seconds", 0.0) or 0.0))

    pending_action = str(state.get("pending_action", ""))
    pending_message = str(state.get("pending_action_message", ""))
    runtime_status = str(state.get("runtime_status", "")).strip().lower()
    runtime_message = str(state.get("runtime_message", ""))

    if pending_action:
        st.error(f"必须处理动作后才能继续: {pending_action}")
        st.caption(pending_message or "-")

        if pending_action == "set_enable_search":
            c1, c2 = st.columns(2)
            if c1.button("执行检索并继续", type="primary", width="stretch"):
                _write_action({"action": "set_enable_search", "value": True})
                st.success("已提交 set_enable_search=True")
            if c2.button("跳过检索并继续", width="stretch"):
                _write_action({"action": "set_enable_search", "value": False})
                st.success("已提交 set_enable_search=False")

        elif pending_action == "set_enable_auto_title":
            c1, c2 = st.columns(2)
            if c1.button("开启自动生成标题并继续", type="primary", width="stretch"):
                _write_action({"action": "set_enable_auto_title", "value": True})
                st.success("已提交 set_enable_auto_title=True")
            if c2.button("关闭自动生成标题并继续", width="stretch"):
                _write_action({"action": "set_enable_auto_title", "value": False})
                st.success("已提交 set_enable_auto_title=False")

        elif pending_action == "confirm_related_works":
            if st.button("我已补充 related_works，继续", type="primary", width="stretch"):
                _write_action({"action": "confirm_related_works"})
                st.success("已提交 confirm_related_works")

        elif pending_action == "enter_reviewing":
            load_requirements = st.checkbox("加载自定义要求文件", value=True)
            req_path = st.text_input("requirements_path", value="inputs/user_requirements.md")
            manual_path = st.text_input("manual_revision_path", value="inputs/revision_requests.md")
            if st.button("确认进入审稿并继续", type="primary", width="stretch"):
                _write_action({
                    "action": "enter_reviewing",
                    "load_requirements": bool(load_requirements),
                    "requirements_path": req_path.strip() or "inputs/user_requirements.md",
                    "manual_revision_path": manual_path.strip() or "inputs/revision_requests.md",
                })
                st.success("已提交 enter_reviewing")

        elif pending_action == "confirm_inputs_ready":
            if st.button("输入已准备完成，继续", type="primary", width="stretch"):
                _write_action({"action": "confirm_inputs_ready"})
                st.success("已提交 confirm_inputs_ready")
    else:
        if runtime_status in {"paused", "waiting_action"} and "LLM" in runtime_message.upper():
            st.warning(runtime_message)
            if st.button("继续重试（从断点续跑）", type="primary", width="stretch"):
                _write_action({"action": "retry_after_llm_failure"})
                st.success("已提交 retry_after_llm_failure")
        else:
            st.success("当前无待处理动作")


def main() -> None:
    st.set_page_config(
        page_title="ThesisLoom Streamlit Console",
        page_icon="🧠",
        layout="wide",
    )

    st.markdown(
        """
        <style>
          .stApp {
            background: radial-gradient(circle at 10% 0%, #eaf8f1 0%, #f2f7f5 45%, #e2f2f8 100%);
          }
          .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("ThesisLoom Human-in-the-Loop Streamlit Console")
    st.caption("左侧流程与指标，中间输入编辑，右侧动作与日志")

    state = _read_state_snapshot()
    topic_line = (state.get("topic") or state.get("inputs_topic") or "(empty topic)")

    top1, top2, top3, top4 = st.columns([2.2, 1.2, 1.2, 1.2])
    top1.info(f"Topic: {topic_line}")
    top2.info(f"Phase: {state.get('workflow_phase', '-')}")
    top3.info(f"Runtime: {state.get('runtime_status', '-')}")
    top4.info(f"Server: {state.get('server_time', '-')}")

    if st.button("刷新", width="stretch"):
        st.rerun()

    left, center, right = st.columns([1.05, 1.3, 1.2])
    with left:
        _render_paper_outputs_panel(state)
        _render_pipeline_outputs_panel(state)
    with center:
        _render_center_editor()
    with right:
        _render_actions_and_logs(state)


if __name__ == "__main__":
    main()
