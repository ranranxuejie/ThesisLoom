import glob
import json
import os
import re
import sys
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

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


def _count_mixed_words(text: str) -> int:
    txt = str(text or "")
    en_tokens = re.findall(r"[A-Za-z0-9_]+", txt)
    zh_chars = re.findall(r"[\u4e00-\u9fff]", txt)
    return len(en_tokens) + len(zh_chars)


def _read_state_snapshot() -> dict:
    checkpoint = _latest_checkpoint_path()
    if not checkpoint:
        return {
            "ok": True,
            "has_checkpoint": False,
            "message": "尚未检测到 checkpoint 文件。",
            "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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

    return {
        "ok": True,
        "has_checkpoint": True,
        "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "checkpoint_path": checkpoint,
        "checkpoint_mtime": datetime.fromtimestamp(os.path.getmtime(checkpoint)).strftime("%Y-%m-%d %H:%M:%S"),
        "topic": str(data.get("topic", "")),
        "model": str(data.get("model", "")),
        "language": str(data.get("language", "")),
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
        "total_chars": total_chars,
        "total_words": total_words,
        "top_major_word_stats": top_majors,
        "related_works_path": str(data.get("related_works_path", "inputs/related_works.md")),
        "research_gap_output_path": str(data.get("research_gap_output_path", "outputs/research_gaps.md")),
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
    .wrap { max-width: 980px; margin: 24px auto; padding: 0 16px 24px; }
    .hero {
      border: 1px solid var(--line);
      border-radius: 16px;
      background: var(--panel);
      padding: 18px 18px 12px;
      box-shadow: 0 8px 24px rgba(31, 41, 55, 0.08);
    }
    .title { margin: 0 0 8px; font-size: 24px; letter-spacing: .2px; }
    .sub { margin: 0; color: var(--muted); }
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
    }
    .pill {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 12px;
      border: 1px solid var(--line);
      background: #fff;
      margin-right: 8px;
    }
    .ok { color: var(--ok); }
    .warn { color: var(--warn); }
    .bad { color: var(--bad); }
    @keyframes in {
      from { opacity: 0; transform: translateY(6px); }
      to { opacity: 1; transform: translateY(0); }
    }
  </style>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"hero\">
      <h1 class=\"title\">ThesisLoom State Dashboard</h1>
      <p class=\"sub\">每 2 秒自动刷新一次，实时读取最新 checkpoint。</p>
      <div style=\"margin-top:10px\">
        <span id=\"phase-pill\" class=\"pill\">phase: unknown</span>
        <span id=\"pass-pill\" class=\"pill\">passed: false</span>
        <span id=\"time-pill\" class=\"pill\">server: -</span>
      </div>
      <div style=\"margin-top:10px\">
        <button id=\"toggle-refresh\" class=\"pill\" style=\"cursor:pointer\">暂停刷新</button>
        <button id=\"manual-refresh\" class=\"pill\" style=\"cursor:pointer\">手动刷新</button>
      </div>
      <div class=\"grid\">
        <div class=\"card\"><div class=\"k\">Topic</div><div id=\"topic\" class=\"v\">-</div></div>
        <div class=\"card\"><div class=\"k\">Model / Language</div><div id=\"model\" class=\"v\">-</div></div>
        <div class=\"card\"><div class=\"k\">Current Node</div><div id=\"node\" class=\"v\">-</div></div>
        <div class=\"card\"><div class=\"k\">Review Round</div><div id=\"round\" class=\"v\">-</div></div>
        <div class=\"card\"><div class=\"k\">Major Chapters</div><div id=\"majors\" class=\"v\">-</div></div>
        <div class=\"card\"><div class=\"k\">Completed Sections</div><div id=\"sections\" class=\"v\">-</div></div>
        <div class=\"card\"><div class=\"k\">Pending Rewrites</div><div id=\"pending\" class=\"v\">-</div></div>
        <div class=\"card\"><div class=\"k\">Search Queries</div><div id=\"queries\" class=\"v\">-</div></div>
        <div class=\"card\"><div class=\"k\">Paper Search Limit</div><div id=\"limit\" class=\"v\">-</div></div>
        <div class=\"card\"><div class=\"k\">✍️ 总词数</div><div id=\"words\" class=\"v\">-</div></div>
        <div class=\"card\"><div class=\"k\">🔣 总字符数</div><div id=\"chars\" class=\"v\">-</div></div>
        <div class=\"card\"><div class=\"k\">🧩 自定义要求长度</div><div id=\"reqsize\" class=\"v\">-</div></div>
      </div>
      <div id=\"ckpt\" class=\"line\">checkpoint: -</div>
      <div id=\"paths\" class=\"line\">paths: -</div>
      <div id=\"query-preview\" class=\"line\">queries: -</div>
      <div id=\"word-preview\" class=\"line\">word stats: -</div>
      <div id=\"msg\" class=\"line\">状态读取中...</div>
    </div>
  </div>
  <script>
    let autoRefresh = true;

    function setText(id, value) {
      const el = document.getElementById(id);
      if (el) el.textContent = value;
    }

    async function refresh() {
      try {
        const resp = await fetch('/api/state?_=' + Date.now());
        const data = await resp.json();

        setText('time-pill', 'server: ' + (data.server_time || '-'));
        if (!data.ok) {
          setText('msg', data.message || '读取失败');
          document.getElementById('msg').className = 'line bad';
          return;
        }

        if (!data.has_checkpoint) {
          setText('msg', data.message || '暂无 checkpoint');
          document.getElementById('msg').className = 'line warn';
          return;
        }

        setText('phase-pill', 'phase: ' + data.workflow_phase);
        const passText = data.passed ? 'passed: true' : 'passed: false';
        setText('pass-pill', passText);
        document.getElementById('pass-pill').className = 'pill ' + (data.passed ? 'ok' : 'warn');

        setText('topic', data.topic || '(empty topic)');
        setText('model', (data.model || '-') + ' / ' + (data.language || '-'));
        setText('node', data.current_node || '-');
        setText('round', String(data.review_round) + ' / ' + String(data.max_review_rounds));
        setText('majors', String(data.major_chapter_count));
        setText('sections', String(data.completed_section_count));
        setText('pending', String(data.pending_rewrite_count));
        setText('queries', String(data.search_query_count));
        setText('limit', String(data.paper_search_limit));
        setText('words', String(data.total_words || 0));
        setText('chars', String(data.total_chars || 0));
        setText('reqsize', String(data.user_requirements_size || 0));

        setText('ckpt', 'checkpoint: ' + data.checkpoint_path + ' | updated: ' + data.checkpoint_mtime + ' | mark: ' + (data.last_checkpoint_reason || '-'));
        setText('paths', 'related_works: ' + data.related_works_path + ' | research_gaps: ' + data.research_gap_output_path);
        setText('query-preview', 'queries: ' + (data.search_queries || []).slice(0, 5).join(' || '));
        const topWords = (data.top_major_word_stats || []).map(x => ('Chapter ' + x[0] + ': ' + x[1])).join(' | ');
        setText('word-preview', 'word stats: ' + (topWords || 'N/A'));
        setText('msg', '状态读取成功，自动刷新中。');
        document.getElementById('msg').className = 'line ok';
      } catch (e) {
        setText('msg', '请求失败: ' + e);
        document.getElementById('msg').className = 'line bad';
      }
    }

    document.getElementById('toggle-refresh').onclick = function() {
      autoRefresh = !autoRefresh;
      this.textContent = autoRefresh ? '暂停刷新' : '恢复刷新';
    };
    document.getElementById('manual-refresh').onclick = function() {
      refresh();
    };

    refresh();
    setInterval(function() {
      if (autoRefresh) refresh();
    }, 2000);
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/state"):
            payload = _read_state_snapshot()
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.path == "/" or self.path.startswith("/?"):
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(404)
        self.end_headers()

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
            table.add_row("🚦 Phase", str(data.get("workflow_phase", "-")))
            table.add_row("🧠 Node", str(data.get("current_node", "-")))
            table.add_row(
                "📍 Location",
                f"major={data.get('current_major_chapter_id', '-')}, sub={data.get('current_sub_chapter_id', '-')}",
            )
            table.add_row("📝 Topic", str(data.get("topic", "-")))
            table.add_row("🤖 Model", f"{data.get('model', '-')} / {data.get('language', '-')}")
            table.add_row("🔁 Review", f"{data.get('review_round', 0)} / {data.get('max_review_rounds', 0)}")
            table.add_row("✅ Passed", str(data.get("passed", False)))
            table.add_row("✍️ Words", str(data.get("total_words", 0)))
            table.add_row("🔣 Chars", str(data.get("total_chars", 0)))
            table.add_row("🧩 UserReq", str(data.get("user_requirements_size", 0)))
            table.add_row("🔎 QueryCount", str(data.get("search_query_count", 0)))
            table.add_row("📦 Mark", str(data.get("last_checkpoint_reason", "-")))
            table.add_row("🕒 Updated", str(data.get("checkpoint_mtime", "-")))

        return Panel(table, title="ThesisLoom Terminal Dashboard", border_style="green")

    console.print("| Rich terminal dashboard started. Press Ctrl+C to stop.")
    try:
        with Live(_render(), refresh_per_second=1.5, console=console) as live:
            while True:
                live.update(_render())
                time.sleep(0.8)
    except KeyboardInterrupt:
        console.print("\n| Dashboard stopped")


def main() -> None:
    os.chdir(Path(__file__).resolve().parent)

    if "--terminal" in sys.argv:
        if not all([Console, Live, Table, Panel]):
            print("| [WARN] rich 未安装，无法使用终端仪表盘。请先安装: pip install rich")
            return
        _run_rich_terminal_dashboard()
        return

    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"| State dashboard running at http://{HOST}:{PORT}")
    print("| Terminal mode: python state_dashboard.py --terminal")
    print("| Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n| Dashboard stopped")


if __name__ == "__main__":
    main()
