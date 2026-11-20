"""RAD IDE - one RAD Hub call for clients without TCP sockets (Lua without LuaSocket).

    python radcall_helper.py <request file>

The file holds one JSON request ({"id": 1, "call": "Module.func", "args": [...]});
the hub's answer line is printed to stdout. Errors are printed as {"id": ..., "error": ...}.
"""
import json
import os
import socket
import sys


def main() -> int:
    rid = None
    try:
        with open(sys.argv[1], "rb") as f:
            raw = f.read().decode("utf-8").strip()
        rid = json.loads(raw).get("id")
        addr = os.environ.get("RAD_HUB", "")
        if not addr:
            raise RuntimeError("RAD Hub is not running (RAD_HUB is not set)")
        host, _, port = addr.rpartition(":")
        with socket.create_connection((host, int(port)), timeout=300) as s:
            s.sendall(raw.encode("utf-8") + b"\n")
            f = s.makefile("rb")
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                if isinstance(msg, dict) and msg.get("id") == rid:
                    sys.stdout.buffer.write(line + b"\n")
                    sys.stdout.flush()
                    return 0
        raise RuntimeError("RAD Hub closed the connection")
    except Exception as e:  # noqa: BLE001 - reported to the Lua caller
        sys.stdout.write(json.dumps({"id": rid, "error": str(e)}) + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
