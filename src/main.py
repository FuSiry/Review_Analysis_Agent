from __future__ import annotations

import os
import sys


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv()
    except Exception:
        return


def _parse_host_port(argv: list[str]) -> tuple[str, int]:
    host = os.getenv("HOST", "127.0.0.1")
    port_str = os.getenv("PORT", "8000")
    try:
        port = int(port_str)
    except Exception:
        port = 8000

    if "--host" in argv:
        i = argv.index("--host")
        if i + 1 < len(argv):
            host = argv[i + 1]

    if "--port" in argv:
        i = argv.index("--port")
        if i + 1 < len(argv):
            try:
                port = int(argv[i + 1])
            except Exception:
                port = port

    if len(argv) == 1 and argv[0].isdigit():
        port = int(argv[0])
    elif len(argv) == 2 and argv[1].isdigit():
        host = argv[0]
        port = int(argv[1])

    return host, port


def main() -> None:
    """Main entry point for Review Analysis Agent."""

    _load_dotenv()
    host, port = _parse_host_port(sys.argv[1:])

    import uvicorn

    uvicorn.run("src.cli.server:app", host=host, port=port)


if __name__ == "__main__":
    main()

