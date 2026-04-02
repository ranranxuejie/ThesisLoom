import glob
import json
import os
import re
import sys
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from core.state import resolve_inputs_path

try:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
except Exception:
    Console = None
    Live = None
    Panel = None
    Table = None


HOST = "127.0.0.1"
PORT = 8765
ACTION_FILE = "completed_history/workflow_actions.json"
RUNTIME_FILE = "completed_history/workflow_runtime.json"
EVENTS_FILE = "completed_history/workflow_events.jsonl"
METRICS_FILE = "completed_history/workflow_metrics.json"
EDITABLE_INPUT_FILES = [
  "inputs/existing_material.md",
  "inputs/existing_sections.md",
  "inputs/related_works.md",
  "inputs/revision_requests.md",
  "inputs/user_requirements.md",
]


def _latest_checkpoint_path() -> str:
    files = glob.glob("completed_history/*_checkpoint.json")
    if not files:
        return ""
    files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return files[0]


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _sub_id_sort_key(sub_id: str) -> tuple:
    text = str(sub_id or "").strip()
    parts = text.split(".")
    key = []
    for p in parts:
        if p.isdigit():
            key.append((0, int(p)))
        else:
            key.append((1, p))
    return tuple(key)


def _count_mixed_words(text: str) -> int:
    txt = str(text or "")
    en_tokens = re.findall(r"[A-Za-z0-9_]+", txt)
    zh_chars = re.findall(r"[\u4e00-\u9fff]", txt)
    return len(en_tokens) + len(zh_chars)


def _is_safe_rel_path(path: str) -> bool:
    p = str(path or "").strip().replace("\\", "/")
    if not p:
        return False
    if p.startswith("/") or ":" in p or ".." in p:
        return False
    return True


def _is_allowed_editable_input_file(path: str) -> bool:
    p = str(path or "").strip().replace("\\", "/")
    return p in EDITABLE_INPUT_FILES


def _write_action(payload: dict) -> None:
    os.makedirs("completed_history", exist_ok=True)
    with open(ACTION_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _read_inputs_payload() -> dict:
    path = resolve_inputs_path()
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            raw = f.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception as e:
        return {"ok": False, "path": path, "raw": "", "data": {}, "message": str(e)}
    return {"ok": True, "path": path, "raw": raw, "data": data}


def _write_inputs_payload(text: str) -> dict:
    path = resolve_inputs_path()
    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            return {"ok": False, "message": "inputs.json 根节点必须是对象"}
    except Exception as e:
        return {"ok": False, "message": f"JSON 解析失败: {e}"}

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except Exception as e:
        return {"ok": False, "message": f"写入失败: {e}"}
    return {"ok": True, "path": path, "data": data}


def _read_workflow_logs(mode: str, limit: int) -> list[dict]:
    if not os.path.exists(EVENTS_FILE):
        return []
    rows: list[dict] = []
    try:
        with open(EVENTS_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return []

    for line in lines[-max(1, limit):]:
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except Exception:
            continue
        level = str(item.get("level", "detail"))
        if mode == "key" and level != "key":
            continue
        rows.append(item)
    return rows[-max(1, limit):]


def _read_metrics_snapshot() -> dict:
    if not os.path.exists(METRICS_FILE):
        return {"steps": {}, "totals": {"step_calls": 0, "total_step_seconds": 0.0}, "top_steps": []}
    try:
        with open(METRICS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        steps = data.get("steps", {}) if isinstance(data, dict) else {}
        totals = data.get("totals", {}) if isinstance(data, dict) else {}
        step_items = []
        if isinstance(steps, dict):
            for name, item in steps.items():
                if not isinstance(item, dict):
                    continue
                row = {
                    "step": str(item.get("step", name)),
                    "count": _safe_int(item.get("count", 0), 0),
                    "avg_seconds": float(item.get("avg_seconds", 0.0) or 0.0),
                    "last_seconds": float(item.get("last_seconds", 0.0) or 0.0),
                    "failed": _safe_int(item.get("failed", 0), 0),
                }
                step_items.append(row)
        step_items.sort(key=lambda x: x.get("avg_seconds", 0.0), reverse=True)
        return {
            "steps": steps,
            "totals": {
                "step_calls": _safe_int(totals.get("step_calls", 0), 0),
                "total_step_seconds": float(totals.get("total_step_seconds", 0.0) or 0.0),
            },
            "top_steps": step_items[:8],
        }
    except Exception:
        return {"steps": {}, "totals": {"step_calls": 0, "total_step_seconds": 0.0}, "top_steps": []}


def _read_runtime_snapshot() -> dict:
    payload = {
        "runtime_status": "unknown",
        "runtime_message": "未检测到 workflow 运行态文件",
        "runtime_time": "-",
        "runtime_interaction_mode": "-",
    }
    if not os.path.exists(RUNTIME_FILE):
        return payload
    try:
        with open(RUNTIME_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return {
            "runtime_status": str(raw.get("status", "unknown")),
            "runtime_message": str(raw.get("message", "")),
            "runtime_time": str(raw.get("time", "-")),
            "runtime_interaction_mode": str(raw.get("interaction_mode", "-")),
        }
    except Exception as e:
        payload["runtime_message"] = f"读取 runtime 失败: {e}"
        return payload


def _read_fallback_inputs() -> tuple[str, str, str]:
    topic = ""
    model = ""
    language = "English"
    try:
        with open(resolve_inputs_path(), "r", encoding="utf-8-sig") as f:
            raw = json.load(f)
        topic = str(raw.get("topic", "")).strip()
        model = str(raw.get("model", "")).strip()
        language = str(raw.get("language", "English")).strip() or "English"
    except Exception:
        pass
    return topic, model, language


def _read_state_snapshot() -> dict:
    runtime = _read_runtime_snapshot()
    metrics = _read_metrics_snapshot()
    checkpoint = _latest_checkpoint_path()
    fallback_topic, fallback_model, fallback_language = _read_fallback_inputs()
    inputs_meta = _read_inputs_payload()
    inputs_path = str(inputs_meta.get("path", resolve_inputs_path()))
    inputs_data = inputs_meta.get("data", {}) if isinstance(inputs_meta.get("data", {}), dict) else {}

    if not checkpoint:
        return {
            "ok": True,
            "has_checkpoint": False,
            "message": "尚未检测到 checkpoint 文件。",
            "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "topic": fallback_topic,
            "model": fallback_model,
            "language": fallback_language,
            "inputs_path": inputs_path,
            "inputs_topic": str(inputs_data.get("topic", fallback_topic)),
            "inputs_model": str(inputs_data.get("model", fallback_model)),
            "inputs_language": str(inputs_data.get("language", fallback_language)),
            "workflow_phase": "idle",
            "pending_action": "",
            "pending_action_message": "",
            "paper_outputs": [],
            "workflow_metrics": metrics,
            **runtime,
        }

    try:
        with open(checkpoint, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception as e:
        return {
            "ok": False,
            "has_checkpoint": True,
            "checkpoint_path": checkpoint,
            "message": f"读取 checkpoint 失败: {e}",
            "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            **runtime,
        }

    completed_sections = data.get("completed_sections", []) or []
    reviewed_sections = data.get("reviewed_sections", []) or []
    outline = data.get("outline", [])
    major_count = len(outline) if isinstance(outline, list) else 0
    total_chars = sum(len(str((sec or {}).get("content", ""))) for sec in completed_sections)
    total_words = sum(_count_mixed_words(str((sec or {}).get("content", ""))) for sec in completed_sections)

    by_major = {}
    for sec in completed_sections:
        sub_id = str(sec.get("sub_chapter_id", ""))
        major = sub_id.split(".")[0] if "." in sub_id else "?"
        by_major[major] = by_major.get(major, 0) + _count_mixed_words(str(sec.get("content", "")))
    top_majors = sorted(by_major.items(), key=lambda x: x[1], reverse=True)[:3]

    paper_outputs = []
    for sec in completed_sections:
      if not isinstance(sec, dict):
        continue
      paper_outputs.append(
        {
          "sub_chapter_id": str(sec.get("sub_chapter_id", "")),
          "title": str(sec.get("title", "")),
          "major_title": str(sec.get("major_title", "")),
          "actual_order_index": _safe_int(sec.get("actual_order_index", 0), 0),
          "content": str(sec.get("content", "")),
        }
      )
    paper_outputs.sort(key=lambda x: _sub_id_sort_key(x.get("sub_chapter_id", "")))

    planner_outputs = []
    if isinstance(outline, list):
      for major in outline:
        if not isinstance(major, dict):
          continue
        major_id = str(major.get("major_chapter_id", ""))
        major_title = str(major.get("major_title", ""))
        for sub in (major.get("sub_sections", []) or []):
          if not isinstance(sub, dict):
            continue
          planner_outputs.append({
            "major_chapter_id": major_id,
            "major_title": major_title,
            "sub_chapter_id": str(sub.get("sub_chapter_id", "")),
            "sub_title": str(sub.get("sub_title", "")),
            "selected_guidance_key": str(sub.get("selected_guidance_key", "")),
            "guidance_reason": str(sub.get("guidance_reason", "")),
            "paragraph_blueprints_count": len(sub.get("paragraph_blueprints", []) or []),
            "context_routing": sub.get("context_routing", {}),
          })

    return {
        "ok": True,
        "has_checkpoint": True,
        "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "checkpoint_path": checkpoint,
        "checkpoint_mtime": datetime.fromtimestamp(os.path.getmtime(checkpoint)).strftime("%Y-%m-%d %H:%M:%S"),
        "topic": str(data.get("topic", "")),
        "model": str(data.get("model", "")),
        "language": str(data.get("language", "")),
        "inputs_path": inputs_path,
        "inputs_topic": str(inputs_data.get("topic", fallback_topic)),
        "inputs_model": str(inputs_data.get("model", fallback_model)),
        "inputs_language": str(inputs_data.get("language", fallback_language)),
        "workflow_phase": str(data.get("workflow_phase", "unknown")),
        "review_round": _safe_int(data.get("review_round", 0), 0),
        "max_review_rounds": _safe_int(data.get("max_review_rounds", 0), 0),
        "passed": bool(data.get("passed", False)),
        "major_chapter_count": major_count,
        "completed_section_count": len(completed_sections),
        "pending_rewrite_count": len(reviewed_sections),
        "paper_search_limit": _safe_int(data.get("paper_search_limit", 0), 0),
        "search_query_count": len(data.get("search_queries", []) or []),
        "search_queries": data.get("search_queries", []) or [],
        "current_node": str(data.get("current_node", "")),
        "current_major_chapter_id": str(data.get("current_major_chapter_id", "")),
        "current_sub_chapter_id": str(data.get("current_sub_chapter_id", "")),
        "last_checkpoint_reason": str(data.get("last_checkpoint_reason", "")),
        "last_checkpoint_time": str(data.get("last_checkpoint_time", "")),
        "resume_count": _safe_int(data.get("resume_count", 0), 0),
        "user_requirements_size": len(str(data.get("user_requirements", ""))),
        "manual_revision_path": str(data.get("manual_revision_path", "inputs/revision_requests.md")),
        "pending_action": str(data.get("pending_action", "")),
        "pending_action_message": str(data.get("pending_action_message", "")),
        "total_chars": total_chars,
        "total_words": total_words,
        "top_major_word_stats": top_majors,
        "paper_outputs": paper_outputs,
        "architect_outline": outline if isinstance(outline, list) else [],
        "planner_outputs": planner_outputs,
        "overall_review_summary": str(data.get("review_summary", "")),
        "overall_review_plans": data.get("major_review_plans", []) or [],
        "major_review_items": reviewed_sections,
        "related_works_path": str(data.get("related_works_path", "inputs/related_works.md")),
        "research_gap_output_path": str(data.get("research_gap_output_path", "outputs/research_gaps.md")),
        "workflow_metrics": metrics,
        **runtime,
    }


HTML = """<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>ThesisLoom State Dashboard</title>
  <style>
    :root {
      --bg: #f4efe6;
      --panel: #fffaf3;
      --ink: #1f2937;
      --muted: #5b6470;
      --ok: #0f766e;
      --warn: #b45309;
      --bad: #b91c1c;
      --line: #e5d7c7;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: \"IBM Plex Sans\", \"Segoe UI\", sans-serif;
      color: var(--ink);
      background: radial-gradient(circle at 20% 20%, #fff7ed 0%, var(--bg) 48%, #efe5d6 100%);
      min-height: 100vh;
    }
    .wrap { max-width: 1080px; margin: 24px auto; padding: 0 16px 24px; }
    .hero {
      border: 1px solid var(--line);
      border-radius: 16px;
      background: var(--panel);
      padding: 18px 18px 12px;
      box-shadow: 0 8px 24px rgba(31, 41, 55, 0.08);
    }
    .title { margin: 0 0 8px; font-size: 24px; letter-spacing: .2px; }
    .sub { margin: 0; color: var(--muted); }
    .topic-line {
      margin-top: 10px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #fff;
      font-weight: 700;
      font-size: 16px;
      line-height: 1.35;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .grid {
      margin-top: 14px;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
    }
    .card {
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #fff;
      padding: 12px;
      animation: in .28s ease both;
    }
    .k { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .06em; }
    .v { margin-top: 6px; font-size: 20px; font-weight: 700; }
    .line {
      margin-top: 14px;
      border: 1px dashed var(--line);
      border-radius: 12px;
      background: #fff;
      padding: 12px;
      color: var(--muted);
      font-size: 14px;
      word-break: break-all;
      white-space: pre-wrap;
    }
    .loading-wrap {
      margin-top: 12px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .loader {
      width: 30px;
      height: 30px;
      border-radius: 50%;
      border: 3px solid #d6c3ad;
      border-top-color: #c2410c;
      box-shadow: 0 0 0 rgba(249, 115, 22, .35);
      animation: spin .85s linear infinite, halo 1.1s ease-in-out infinite;
      opacity: 0;
      transition: opacity .15s ease;
    }
    .loader.show { opacity: 1; }
    .loadbar {
      flex: 1;
      height: 10px;
      border-radius: 999px;
      background: #f1e6d8;
      overflow: hidden;
      position: relative;
    }
    .loadbar::after {
      content: \"\";
      position: absolute;
      left: -45%;
      top: 0;
      width: 45%;
      height: 100%;
      background: linear-gradient(90deg, transparent 0%, #f97316 50%, transparent 100%);
      animation: sweep 0.95s ease-in-out infinite;
    }
    .loadbar.pause::after { animation-play-state: paused; opacity: 0; }
    .pill {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 12px;
      border: 1px solid var(--line);
      background: #fff;
      margin-right: 8px;
    }
    .runtime {
      margin-top: 10px;
      padding: 8px 10px;
      border-radius: 10px;
      border: 1px solid #f59e0b;
      background: #fff7ed;
      color: #9a3412;
      font-weight: 600;
    }
    .btn { cursor: pointer; border: 1px solid var(--line); background: #fff; padding: 8px 10px; border-radius: 10px; margin-right: 6px; margin-top: 6px; }
    .input { width: 100%; padding: 8px; border-radius: 10px; border: 1px solid var(--line); margin-top: 8px; }
    .textarea {
      width: 100%;
      min-height: 170px;
      resize: vertical;
      border-radius: 10px;
      border: 1px solid var(--line);
      padding: 10px;
      font-family: Consolas, \"Courier New\", monospace;
      font-size: 12px;
      background: #fff;
    }
    .logs {
      margin-top: 14px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #fff;
      padding: 10px;
      max-height: 260px;
      overflow: auto;
      font-family: Consolas, \"Courier New\", monospace;
      font-size: 12px;
      line-height: 1.35;
      white-space: pre-wrap;
    }
    .refresh-dots::after {
      content: \"...\";
      display: inline-block;
      width: 1.2em;
      overflow: hidden;
      vertical-align: bottom;
      animation: dots 1.1s steps(4, end) infinite;
    }
    .ok { color: var(--ok); }
    .warn { color: var(--warn); }
    .bad { color: var(--bad); }
    @keyframes in {
      from { opacity: 0; transform: translateY(6px); }
      to { opacity: 1; transform: translateY(0); }
    }
    @keyframes spin {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
    @keyframes sweep {
      0% { left: -45%; }
      100% { left: 100%; }
    }
    @keyframes halo {
      0% { box-shadow: 0 0 0 0 rgba(249, 115, 22, .35); }
      100% { box-shadow: 0 0 0 10px rgba(249, 115, 22, 0); }
    }
    @keyframes dots {
      0% { width: 0em; }
      100% { width: 1.2em; }
    }
  </style>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"hero\">
      <h1 class=\"title\">ThesisLoom State Dashboard</h1>
      <p class=\"sub\">每 2 秒自动刷新一次，可在页面驱动关键流程动作。</p>
      <div id=\"topic-line\" class=\"topic-line\">Topic: -</div>
      <div style=\"margin-top:10px\">
        <span id=\"phase-pill\" class=\"pill\">phase: unknown</span>
        <span id=\"pass-pill\" class=\"pill\">passed: false</span>
        <span id=\"time-pill\" class=\"pill\">server: -</span>
      </div>
      <div class=\"loading-wrap\">
        <div id=\"loader\" class=\"loader\"></div>
        <div id=\"loadbar\" class=\"loadbar\"></div>
      </div>
      <div id=\"runtime\" class=\"runtime\">workflow runtime: unknown</div>

      <div class=\"grid\">
        <div class="card"><div class="k">Model</div><div id="model" class="v">-</div></div>
        <div class="card"><div class="k">Language</div><div id="language" class="v">-</div></div>
        <div class=\"card\"><div class=\"k\">Current Node</div><div id=\"node\" class=\"v\">-</div></div>
        <div class=\"card\"><div class=\"k\">Pending Action</div><div id=\"pending-action\" class=\"v\">-</div></div>
        <div class=\"card\"><div class=\"k\">Review Round</div><div id=\"round\" class=\"v\">-</div></div>
        <div class=\"card\"><div class=\"k\">Completed Sections</div><div id=\"sections\" class=\"v\">-</div></div>
        <div class=\"card\"><div class=\"k\">Pending Rewrites</div><div id=\"pending\" class=\"v\">-</div></div>
        <div class=\"card\"><div class=\"k\">Total Words</div><div id=\"words\" class=\"v\">-</div></div>
      </div>

      <div id=\"action-message\" class=\"line\">待处理动作: -</div>
      <div id=\"action-panel\" class=\"line\">加载中...</div>
      <div class=\"line\">
        <div><b>inputs.json 在线编辑</b> <span id=\"inputs-path\">-</span></div>
        <textarea id=\"inputs-editor\" class=\"textarea\" placeholder=\"加载 inputs.json 中...\"></textarea>
        <button class=\"btn\" id=\"btn-inputs-save\">保存 inputs</button>
        <button class=\"btn\" id=\"btn-inputs-start\">保存并开始工作流</button>
      </div>
      <div class=\"line\">
        <div><b>Workflow 日志</b></div>
        <button class=\"btn\" id=\"btn-log-key\">关键日志</button>
        <button class=\"btn\" id=\"btn-log-detail\">详细日志</button>
        <div id=\"logs\" class=\"logs\">日志加载中...</div>
      </div>
      <div id=\"ckpt\" class=\"line\">checkpoint: -</div>
      <div id=\"paths\" class=\"line\">paths: -</div>
      <div id=\"file-preview\" class=\"line\">文件预览: -</div>
      <div id=\"msg\" class=\"line\">状态读取中...</div>
    </div>
  </div>
  <script>
    let logMode = 'key';
    let inputsSaveTimer = null;

    function setText(id, value) {
      const el = document.getElementById(id);
      if (el) el.textContent = value;
    }

    function setLoading(active) {
      const loader = document.getElementById('loader');
      const loadbar = document.getElementById('loadbar');
      if (!loader || !loadbar) return;
      loader.className = active ? 'loader show' : 'loader';
      loadbar.className = active ? 'loadbar' : 'loadbar pause';
      const msg = document.getElementById('msg');
      if (active && msg) {
        msg.className = 'line warn refresh-dots';
        msg.textContent = '状态刷新中';
      }
    }

    async function postAction(payload) {
      const resp = await fetch('/api/action', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      const data = await resp.json();
      if (!data.ok) {
        setText('msg', '动作提交失败: ' + (data.message || 'unknown'));
        document.getElementById('msg').className = 'line bad';
      } else {
        setText('msg', '动作已提交: ' + payload.action);
        document.getElementById('msg').className = 'line ok';
      }
      return data;
    }

    async function loadFile(path) {
      const resp = await fetch('/api/file?path=' + encodeURIComponent(path));
      const data = await resp.json();
      if (!data.ok) {
        setText('file-preview', '文件预览失败: ' + (data.message || 'unknown'));
        return;
      }
      setText('file-preview', '文件预览(' + path + '):\\n' + data.content.slice(0, 4000));
    }

    async function loadInputs() {
      const resp = await fetch('/api/inputs?_=' + Date.now());
      const data = await resp.json();
      if (!data.ok) {
        setText('msg', '读取 inputs 失败: ' + (data.message || 'unknown'));
        document.getElementById('msg').className = 'line bad';
        return;
      }
      setText('inputs-path', data.path || '-');
      const editor = document.getElementById('inputs-editor');
      if (editor && !editor.dataset.dirty) {
        editor.value = data.raw || '{}';
      }
    }

    async function saveInputs() {
      const editor = document.getElementById('inputs-editor');
      const content = (editor && typeof editor.value === 'string') ? editor.value : '{}';
      const resp = await fetch('/api/inputs', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({content})
      });
      const data = await resp.json();
      if (!data.ok) {
        setText('msg', '保存 inputs 失败: ' + (data.message || 'unknown'));
        document.getElementById('msg').className = 'line bad';
        return false;
      }
      if (editor) editor.dataset.dirty = '';
      setText('msg', 'inputs 已保存');
      document.getElementById('msg').className = 'line ok';
      return true;
    }

    async function saveInputsAndStart() {
      const ok = await saveInputs();
      if (!ok) return;
      await postAction({action: 'confirm_inputs_ready'});
    }

    async function loadLogs() {
      const resp = await fetch('/api/logs?mode=' + encodeURIComponent(logMode) + '&limit=120&_=' + Date.now());
      const data = await resp.json();
      const box = document.getElementById('logs');
      if (!box) return;
      if (!data.ok) {
        box.textContent = '日志读取失败';
        return;
      }
      const rows = (data.items || []).map((x) => {
        const t = x.time || '-';
        const lvl = x.level || 'detail';
        const msg = x.message || '';
        return '[' + t + '][' + lvl + '] ' + msg;
      });
      box.textContent = rows.length ? rows.join('\\n') : '暂无日志';
      box.scrollTop = box.scrollHeight;
    }

    function renderActionPanel(state) {
      const panel = document.getElementById('action-panel');
      const action = state.pending_action || '';

      if (!action) {
        panel.innerHTML = '<b>当前无待处理动作。</b><br>你可以点击下方按钮预览文献或改稿指令文件。' +
          '<br><button class="btn" id="btn-preview-related">预览 related_works</button>' +
          '<button class="btn" id="btn-preview-manual">预览 revision_requests</button>';
        document.getElementById('btn-preview-related').onclick = function() {
          loadFile(state.related_works_path || 'inputs/related_works.md');
        };
        document.getElementById('btn-preview-manual').onclick = function() {
          loadFile(state.manual_revision_path || 'inputs/revision_requests.md');
        };
        return;
      }

      if (action === 'confirm_inputs_ready') {
        panel.innerHTML = '<b>请先编辑并保存 inputs.json，然后点击“保存并开始工作流”。</b>';
        return;
      }

      if (action === 'set_enable_search') {
        panel.innerHTML = '<b>请选择是否执行文献检索</b><br>' +
          '<button class="btn" id="btn-search-yes">是，执行检索</button>' +
          '<button class="btn" id="btn-search-no">否，跳过检索</button>';
        document.getElementById('btn-search-yes').onclick = function() {
          postAction({action: 'set_enable_search', value: true});
        };
        document.getElementById('btn-search-no').onclick = function() {
          postAction({action: 'set_enable_search', value: false});
        };
        return;
      }

      if (action === 'confirm_related_works') {
        panel.innerHTML = '<b>请先补充文献综述文件后继续</b><br>' +
          '<button class="btn" id="btn-preview-related">预览 related_works</button>' +
          '<button class="btn" id="btn-related-done">已补充，继续生成 research_gaps</button>';
        document.getElementById('btn-preview-related').onclick = function() {
          loadFile(state.related_works_path || 'inputs/related_works.md');
        };
        document.getElementById('btn-related-done').onclick = function() {
          postAction({action: 'confirm_related_works'});
        };
        return;
      }

      if (action === 'enter_reviewing') {
        panel.innerHTML = '<b>进入审稿阶段前确认</b><br>' +
          '<label><input type="checkbox" id="load-req" checked> 加载自定义要求文件</label><br>' +
          '<input class="input" id="req-path" value="inputs/user_requirements.md" placeholder="user_requirements 路径">' +
          '<input class="input" id="manual-path" value="' + (state.manual_revision_path || 'inputs/revision_requests.md') + '" placeholder="人工改稿指令文件路径">' +
          '<button class="btn" id="btn-preview-manual">预览 revision_requests</button>' +
          '<button class="btn" id="btn-enter-review">确认进入审稿</button>';
        document.getElementById('btn-preview-manual').onclick = function() {
          const mp = document.getElementById('manual-path').value || 'inputs/revision_requests.md';
          loadFile(mp);
        };
        document.getElementById('btn-enter-review').onclick = function() {
          postAction({
            action: 'enter_reviewing',
            load_requirements: document.getElementById('load-req').checked,
            requirements_path: document.getElementById('req-path').value || 'inputs/user_requirements.md',
            manual_revision_path: document.getElementById('manual-path').value || 'inputs/revision_requests.md'
          });
        };
        return;
      }

      panel.innerHTML = '<b>未知动作:</b> ' + action;
    }

    async function refresh() {
      setLoading(true);
      try {
        const resp = await fetch('/api/state?_=' + Date.now());
        const data = await resp.json();

        setText('time-pill', 'server: ' + (data.server_time || '-'));
        setText('runtime', 'workflow runtime: ' + (data.runtime_status || 'unknown') + ' | mode: ' + (data.runtime_interaction_mode || '-') + ' | ' + (data.runtime_message || '-') + ' | ' + (data.runtime_time || '-'));

        const topicLine = (data.pending_action === 'confirm_inputs_ready')
          ? (data.inputs_topic || data.topic || '(empty topic)')
          : (data.topic || data.inputs_topic || '(empty topic)');
        setText('topic-line', 'Topic: ' + topicLine);

        setText('inputs-path', data.inputs_path || '-');

        if (!data.ok) {
          setText('msg', data.message || '读取失败');
          document.getElementById('msg').className = 'line bad';
          setText('action-panel', '状态接口返回失败，请稍后重试。');
          return;
        }

        if (!data.has_checkpoint) {
          setText('phase-pill', 'phase: ' + (data.workflow_phase || 'idle'));
          setText('model', (data.inputs_model || data.model || '-'));
          setText('language', (data.inputs_language || data.language || '-'));
          setText('node', '-');
          setText('pending-action', '-');
          setText('round', '-');
          setText('sections', '0');
          setText('pending', '0');
          setText('words', '0');
          setText('action-message', '待处理动作说明: -');
          setText('ckpt', 'checkpoint: -');
          setText('paths', 'related_works: - | research_gaps: - | revision: -');
          setText('msg', data.message || '暂无 checkpoint');
          document.getElementById('msg').className = 'line warn';
          setText('action-panel', '尚未生成 checkpoint，等待工作流初始化。');
          return;
        }

        setText('phase-pill', 'phase: ' + data.workflow_phase);
        const passText = data.passed ? 'passed: true' : 'passed: false';
        setText('pass-pill', passText);
        document.getElementById('pass-pill').className = 'pill ' + (data.passed ? 'ok' : 'warn');

        setText('model', (data.model || '-'));
        setText('language', (data.language || '-'));
        setText('node', data.current_node || '-');
        setText('pending-action', data.pending_action || '-');
        setText('round', String(data.review_round) + ' / ' + String(data.max_review_rounds));
        setText('sections', String(data.completed_section_count));
        setText('pending', String(data.pending_rewrite_count));
        setText('words', String(data.total_words || 0));

        setText('action-message', '待处理动作说明: ' + (data.pending_action_message || '-'));
        setText('ckpt', 'checkpoint: ' + data.checkpoint_path + ' | updated: ' + data.checkpoint_mtime + ' | mark: ' + (data.last_checkpoint_reason || '-'));
        setText('paths', 'related_works: ' + data.related_works_path + ' | research_gaps: ' + data.research_gap_output_path + ' | revision: ' + (data.manual_revision_path || '-'));

        renderActionPanel(data);
        setText('msg', '状态读取成功，自动刷新中。');
        document.getElementById('msg').className = 'line ok';
      } catch (e) {
        setText('msg', '请求失败: ' + e);
        document.getElementById('msg').className = 'line bad';
        setText('phase-pill', 'phase: -');
        setText('pass-pill', 'passed: -');
        setText('model', '-');
        setText('language', '-');
        setText('node', '-');
        setText('pending-action', '-');
        setText('round', '-');
        setText('sections', '-');
        setText('pending', '-');
        setText('words', '-');
        setText('action-message', '待处理动作说明: -');
        setText('action-panel', '无法连接 /api/state。请确认已运行 main.py，并访问 http://127.0.0.1:8765');
      } finally {
        setLoading(false);
      }
    }

    document.getElementById('btn-inputs-save').onclick = saveInputs;
    document.getElementById('btn-inputs-start').onclick = saveInputsAndStart;
    document.getElementById('btn-log-key').onclick = function() { logMode = 'key'; loadLogs(); };
    document.getElementById('btn-log-detail').onclick = function() { logMode = 'detail'; loadLogs(); };
    document.getElementById('inputs-editor').addEventListener('input', function() {
      this.dataset.dirty = '1';
      if (inputsSaveTimer) {
        clearTimeout(inputsSaveTimer);
      }
      inputsSaveTimer = setTimeout(function() {
        saveInputs();
      }, 900);
    });

    loadInputs();
    refresh();
    loadLogs();
    setInterval(refresh, 2000);
    setInterval(loadLogs, 2000);
  </script>
</body>
</html>
"""


def _load_dashboard_html() -> str:
  candidates = [
    "docs/dashboard_app.html",
    "dashboard_app.html",
  ]
  for p in candidates:
    if os.path.exists(p):
      try:
        with open(p, "r", encoding="utf-8") as f:
          return f.read()
      except Exception:
        continue
  return HTML


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/state"):
            payload = _read_state_snapshot()
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path.startswith("/api/inputs"):
            payload = _read_inputs_payload()
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path.startswith("/api/logs"):
            q = parse_qs(parsed.query)
            mode = str((q.get("mode") or ["key"])[0]).strip().lower()
            if mode not in {"key", "detail"}:
                mode = "key"
            limit = _safe_int((q.get("limit") or ["80"])[0], 80)
            limit = max(10, min(limit, 300))
            payload = {"ok": True, "mode": mode, "items": _read_workflow_logs(mode, limit)}
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path.startswith("/api/file"):
            q = parse_qs(parsed.query)
            path = str((q.get("path") or [""])[0])
            if not _is_safe_rel_path(path):
                payload = {"ok": False, "message": "非法路径"}
            elif not os.path.exists(path):
                payload = {"ok": False, "message": "文件不存在"}
            else:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    payload = {"ok": True, "content": content}
                except Exception as e:
                    payload = {"ok": False, "message": str(e)}

            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path.startswith("/api/editable-files"):
            payload = {"ok": True, "items": EDITABLE_INPUT_FILES}
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path.startswith("/api/input-file"):
            q = parse_qs(parsed.query)
            path = str((q.get("path") or [""])[0])
            if (not _is_safe_rel_path(path)) or (not _is_allowed_editable_input_file(path)):
                payload = {"ok": False, "message": "非法或不允许编辑的路径"}
            elif not os.path.exists(path):
                payload = {"ok": True, "path": path, "content": ""}
            else:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        payload = {"ok": True, "path": path, "content": f.read()}
                except Exception as e:
                    payload = {"ok": False, "message": str(e)}

            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/" or parsed.path.startswith("/?"):
            body = _load_dashboard_html().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/inputs":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length > 0 else b"{}"
                payload = json.loads(raw.decode("utf-8"))
                content = str(payload.get("content", ""))
            except Exception as e:
                body = json.dumps({"ok": False, "message": f"请求体解析失败: {e}"}, ensure_ascii=False).encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            result = _write_inputs_payload(content)
            code = 200 if result.get("ok") else 400
            body = json.dumps(result, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/input-file":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length > 0 else b"{}"
                payload = json.loads(raw.decode("utf-8"))
                path = str(payload.get("path", "")).strip()
                content = str(payload.get("content", ""))
            except Exception as e:
                body = json.dumps({"ok": False, "message": f"请求体解析失败: {e}"}, ensure_ascii=False).encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if (not _is_safe_rel_path(path)) or (not _is_allowed_editable_input_file(path)):
                body = json.dumps({"ok": False, "message": "非法或不允许编辑的路径"}, ensure_ascii=False).encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            try:
                folder = os.path.dirname(path)
                if folder:
                    os.makedirs(folder, exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                body = json.dumps({"ok": True, "path": path}, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            except Exception as e:
                body = json.dumps({"ok": False, "message": str(e)}, ensure_ascii=False).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

        if parsed.path != "/api/action":
            self.send_response(404)
            self.end_headers()
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8"))
        except Exception as e:
            body = json.dumps({"ok": False, "message": f"请求体解析失败: {e}"}, ensure_ascii=False).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        action = str(payload.get("action", "")).strip()
        allowed = {"confirm_inputs_ready", "set_enable_search", "confirm_related_works", "enter_reviewing"}
        if action not in allowed:
            body = json.dumps({"ok": False, "message": f"不支持的动作: {action}"}, ensure_ascii=False).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if action == "enter_reviewing":
            req_path = str(payload.get("requirements_path", "inputs/user_requirements.md")).strip()
            manual_path = str(payload.get("manual_revision_path", "inputs/revision_requests.md")).strip()
            if not _is_safe_rel_path(req_path) or not _is_safe_rel_path(manual_path):
                body = json.dumps({"ok": False, "message": "路径必须是相对路径且不能包含 .."}, ensure_ascii=False).encode("utf-8")
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

        _write_action(payload)
        body = json.dumps({"ok": True, "message": "动作已写入"}, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


def _run_rich_terminal_dashboard() -> None:
    console = Console()

    def _render():
        data = _read_state_snapshot()
        table = Table(title="ThesisLoom Live State", expand=True)
        table.add_column("Key", style="cyan", no_wrap=True)
        table.add_column("Value", style="white")

        if not data.get("ok"):
            table.add_row("Status", f"[red]{data.get('message', 'error')}[/red]")
        elif not data.get("has_checkpoint"):
            table.add_row("Status", f"[yellow]{data.get('message', 'no checkpoint')}[/yellow]")
        else:
            table.add_row("Phase", str(data.get("workflow_phase", "-")))
            table.add_row("Node", str(data.get("current_node", "-")))
            table.add_row("PendingAction", str(data.get("pending_action", "-")))
            table.add_row("Topic", str(data.get("topic", "-")))
            table.add_row("Model", f"{data.get('model', '-')} / {data.get('language', '-')}")
            table.add_row("Review", f"{data.get('review_round', 0)} / {data.get('max_review_rounds', 0)}")
            table.add_row("Passed", str(data.get("passed", False)))
            table.add_row("Words", str(data.get("total_words", 0)))
            table.add_row("Mark", str(data.get("last_checkpoint_reason", "-")))
            table.add_row("Updated", str(data.get("checkpoint_mtime", "-")))
            table.add_row("Runtime", str(data.get("runtime_status", "-")))

        return Panel(table, title="ThesisLoom Terminal Dashboard", border_style="green")

    console.print("| Rich terminal dashboard started. Press Ctrl+C to stop.")
    try:
        with Live(_render(), refresh_per_second=1.5, console=console) as live:
            while True:
                live.update(_render())
                time.sleep(0.8)
    except KeyboardInterrupt:
        console.print("\n| Dashboard stopped")


def start_web_server(host: str = HOST, port: int = PORT) -> ThreadingHTTPServer:
    os.chdir(Path(__file__).resolve().parent)
    return ThreadingHTTPServer((host, port), Handler)


def main() -> None:
    if "--terminal" in sys.argv:
        if not all([Console, Live, Table, Panel]):
            print("| [WARN] rich 未安装，无法使用终端仪表盘。请先安装: pip install rich")
            return
        _run_rich_terminal_dashboard()
        return

    server = start_web_server(HOST, PORT)
    print(f"| State dashboard running at http://{HOST}:{PORT}")
    print("| Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n| Dashboard stopped")


if __name__ == "__main__":
    main()
