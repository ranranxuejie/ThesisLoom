import argparse
import os
import subprocess
import sys
import threading

from workflow import _run_workflow_safely


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8865


def main() -> None:
    parser = argparse.ArgumentParser(description="ThesisLoom runner")
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
    args = parser.parse_args()

    os.environ["THESISLOOM_SHOW_LLM_OUTPUT"] = "1" if args.show_llm_output == "yes" else "0"

    stop_event = threading.Event()
    workflow_thread = threading.Thread(
        target=_run_workflow_safely,
        kwargs={"stop_event": stop_event, "interaction_mode": args.interaction},
        name="workflow-runner",
        daemon=True,
    )
    workflow_thread.start()

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "streamlit_app.py",
        "--server.headless",
        "true",
        "--server.address",
        str(args.host),
        "--server.port",
        str(args.port),
    ]

    try:
        streamlit_proc = subprocess.Popen(cmd)
    except Exception as e:
        stop_event.set()
        workflow_thread.join(timeout=2)
        print(f"| Streamlit 启动失败: {e}")
        return

    print(f"| Streamlit 控制台已启动: http://{args.host}:{args.port}")
    print(f"| 工作流已在后台启动，交互模式: {args.interaction}")
    print(f"| 终端完整输出 LLM 结果: {args.show_llm_output}")
    if args.interaction == "cli":
        print("| CLI 模式下，工作流会在终端等待输入；Streamlit 页面用于观察与编辑。")
    else:
        print("| Web 模式下，请在 Streamlit 页面右侧动作面板中驱动流程继续。")
    print("| 按 Ctrl+C 退出")
    try:
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


