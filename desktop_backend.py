import argparse
import threading

from state_dashboard import start_web_server
from workflow import _run_workflow_safely


def main() -> None:
    parser = argparse.ArgumentParser(description="ThesisLoom desktop backend runner")
    parser.add_argument("--host", default="127.0.0.1", help="dashboard host")
    parser.add_argument("--port", type=int, default=8765, help="dashboard port")
    parser.add_argument(
        "--interaction",
        choices=["web", "cli"],
        default="web",
        help="workflow interaction mode",
    )
    args = parser.parse_args()

    stop_event = threading.Event()
    workflow_thread = threading.Thread(
        target=_run_workflow_safely,
        kwargs={"stop_event": stop_event, "interaction_mode": args.interaction},
        name="workflow-runner",
        daemon=True,
    )
    workflow_thread.start()

    server = start_web_server(host=args.host, port=args.port)
    print(f"| Backend running at http://{args.host}:{args.port}")
    print("| Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        try:
            server.shutdown()
        except Exception:
            pass
        try:
            server.server_close()
        except Exception:
            pass

        workflow_thread.join(timeout=5)


if __name__ == "__main__":
    main()

