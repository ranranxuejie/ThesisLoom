import argparse
import os
import subprocess
import sys
import threading
import time
import importlib
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

from workflow import _run_workflow_safely


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8865


def _runtime_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", "")
        if meipass:
            return Path(meipass).resolve()
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _workspace_root_for_runtime() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _streamlit_script_path() -> Path:
    runtime_base = _runtime_base_dir()
    source_base = Path(__file__).resolve().parent
    candidates = [
        runtime_base / "streamlit_app.py",
        source_base / "streamlit_app.py",
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def _start_streamlit_subprocess(app_path: Path, host: str, port: int, frozen_mode: bool) -> subprocess.Popen:
    if frozen_mode:
        cmd = [
            sys.executable,
            "--internal-streamlit",
            "--host",
            str(host),
            "--port",
            str(port),
        ]
    else:
        cmd = [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(app_path),
            "--server.headless",
            "true",
            "--server.address",
            str(host),
            "--server.port",
            str(port),
        ]
    return subprocess.Popen(cmd)


def _run_streamlit_inprocess(app_path: Path, host: str, port: int) -> None:
    from streamlit.web import cli as stcli

    old_argv = list(sys.argv)
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.headless",
        "true",
        "--server.address",
        str(host),
        "--server.port",
        str(port),
        "--browser.gatherUsageStats",
        "false",
        "--global.developmentMode",
        "false",
        "--server.fileWatcherType",
        "none",
    ]
    try:
        stcli.main()
    finally:
        sys.argv = old_argv


def _console_url(host: str, port: int) -> str:
    return f"http://{host}:{port}"


def _wait_until_streamlit_ready(host: str, port: int, timeout_seconds: float = 45.0) -> bool:
    health_url = f"{_console_url(host, port)}/_stcore/health"
    deadline = time.time() + max(2.0, float(timeout_seconds))
    while time.time() < deadline:
        try:
            request = urllib.request.Request(health_url, method="GET")
            with urllib.request.urlopen(request, timeout=1.5) as resp:
                if int(getattr(resp, "status", 0)) == 200:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        except Exception:
            pass
        time.sleep(0.25)
    return False


def _open_browser_async(url: str) -> None:
    def _worker() -> None:
        try:
            webbrowser.open(url, new=1, autoraise=True)
        except Exception:
            pass

    threading.Thread(target=_worker, name="browser-opener", daemon=True).start()


def _open_desktop_window(url: str) -> bool:
    try:
        webview = importlib.import_module("webview")
    except Exception as e:
        print(f"| 桌面窗口模式不可用，自动回退到浏览器: {e}")
        return False

    try:
        webview.create_window(
            "ThesisLoom",
            url=url,
            width=1520,
            height=920,
            min_size=(980, 640),
        )
        webview.start(debug=False)
        return True
    except Exception as e:
        print(f"| 桌面窗口启动失败，自动回退到浏览器: {e}")
        return False


def main() -> None:
    frozen_mode = bool(getattr(sys, "frozen", False))
    default_ui_mode = "window" if frozen_mode else "browser"

    parser = argparse.ArgumentParser(description="ThesisLoom runner")
    parser.add_argument(
        "--internal-streamlit",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--interaction",
        choices=["web", "cli"],
        default="web",
        help="workflow 等待动作时采用 web 还是 cli 交互",
    )
    parser.add_argument(
        "--show-llm-output",
        choices=["yes", "no"],
        default="no",
        help="是否在命令行打印每次 LLM 的完整最终输出",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="Web 控制台监听地址")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Web 控制台监听端口")
    parser.add_argument(
        "--ui-mode",
        choices=["window", "browser"],
        default=default_ui_mode,
        help="控制台显示方式：window=桌面窗口，browser=系统浏览器",
    )
    args = parser.parse_args()

    if bool(args.internal_streamlit):
        app_path = _streamlit_script_path()
        if not app_path.exists():
            print(f"| 未找到 streamlit_app.py: {app_path}")
            return
        try:
            _run_streamlit_inprocess(app_path=app_path, host=args.host, port=args.port)
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"| Streamlit 启动失败: {e}")
        return

    os.environ["THESISLOOM_SHOW_LLM_OUTPUT"] = "1" if args.show_llm_output == "yes" else "0"
    workspace_root = _workspace_root_for_runtime()
    os.chdir(workspace_root)

    stop_event = threading.Event()
    workflow_thread = threading.Thread(
        target=_run_workflow_safely,
        kwargs={"stop_event": stop_event, "interaction_mode": args.interaction},
        name="workflow-runner",
        daemon=True,
    )
    workflow_thread.start()

    app_path = _streamlit_script_path()
    if not app_path.exists():
        stop_event.set()
        workflow_thread.join(timeout=2)
        print(f"| 未找到 streamlit_app.py: {app_path}")
        return

    try:
        streamlit_proc = _start_streamlit_subprocess(
            app_path=app_path,
            host=args.host,
            port=args.port,
            frozen_mode=frozen_mode,
        )
    except Exception as e:
        stop_event.set()
        workflow_thread.join(timeout=2)
        print(f"| Streamlit 启动失败: {e}")
        return

    console_url = _console_url(args.host, args.port)

    print(f"| Streamlit 控制台已启动: {console_url}")
    print(f"| 工作流已在后台启动，交互模式: {args.interaction}")
    print(f"| 终端完整输出 LLM 结果: {args.show_llm_output}")
    print(f"| 控制台显示模式: {args.ui_mode}")
    if args.interaction == "cli":
        print("| CLI 模式下，工作流会在终端等待输入；Streamlit 页面用于观察与编辑。")
    else:
        print("| Web 模式下，请在 Streamlit 页面右侧动作面板中驱动流程继续。")
    if args.ui_mode == "window":
        print("| 关闭桌面窗口即可退出。")
    else:
        print("| 按 Ctrl+C 退出")

    try:
        ready = _wait_until_streamlit_ready(args.host, args.port)
        if not ready:
            print("| 警告: Streamlit 启动超时，页面可能暂时不可访问。")

        if args.ui_mode == "window":
            opened = _open_desktop_window(console_url) if ready else False
            if not opened:
                _open_browser_async(console_url)
                streamlit_proc.wait()
        else:
            _open_browser_async(console_url)
            streamlit_proc.wait()
    except KeyboardInterrupt:
        print("\n| 正在停止服务...")
    finally:
        stop_event.set()
        if streamlit_proc.poll() is None:
            streamlit_proc.terminate()
            try:
                streamlit_proc.wait(timeout=5)
            except Exception:
                streamlit_proc.kill()
        workflow_thread.join(timeout=5)
        if workflow_thread.is_alive():
            print("| 工作流尚未完全退出，进程结束后将自动停止。")
        else:
            print("| 工作流已停止。")


if __name__ == "__main__":
    main()

# 