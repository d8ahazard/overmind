import argparse
import os

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the OverMind API server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    parser.add_argument(
        "--self",
        dest="allow_self_project",
        action="store_true",
        help="Enable the Self project option.",
    )
    args = parser.parse_args()

    if args.allow_self_project:
        os.environ["AI_DEVTEAM_ALLOW_SELF_PROJECT"] = "true"
        os.environ["AI_DEVTEAM_SELF_ACTIVE"] = "true"

    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
