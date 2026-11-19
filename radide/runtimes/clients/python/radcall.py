"""radcall - call functions written in other languages of a RAD IDE project.

    from radcall import radcall
    total = radcall("MathVB.AddNumbers", 2, 3)     # Function AddNumbers in MathVB.bas
    text = radcall("TextRing.shout", "hello")      # func shout in TextRing.ring
    radcall("Form2.Show")                          # open a form written in any language

Values travel as JSON: numbers, strings, booleans, None, lists and dicts.
Errors in the called function raise RadCallError.

The IDE runs a RAD Hub for every Run/Debug and sets RAD_HUB / RAD_PROJECT. Outside the
IDE, radcall starts a private hub itself when the RAD IDE package can be imported.
This file has no dependencies (standard library only); it is also used by the
Python and VB6 workers (run_worker()).
"""
from __future__ import annotations

import itertools
import json
import os
import socket
import sys
import threading

__all__ = ["radcall", "RadCallError", "run_worker"]

_TIMEOUT_MARGIN = 5.0


class RadCallError(Exception):
    """The called function failed, could not be found, or timed out."""


def _timeout() -> float:
    try:
        return float(os.environ.get("RAD_TIMEOUT", "") or 60.0) + _TIMEOUT_MARGIN
    except ValueError:
        return 65.0


def _dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=_jsonable)


def _jsonable(v):
    if isinstance(v, (set, frozenset, tuple)):
        return list(v)
    if hasattr(v, "items") and callable(v.items):
        return dict(v.items())
    if hasattr(v, "__iter__") and not isinstance(v, (str, bytes)):
        return list(v)
    return str(v)


# ============================================================================ TCP client
class _TcpChannel:
    """One socket per thread (calls from several threads run in parallel)."""

    def __init__(self, address: str):
        host, _, port = address.rpartition(":")
        self.addr = (host or "127.0.0.1", int(port))
        self.local = threading.local()
        self.ids = itertools.count(1)

    def _conn(self):
        c = getattr(self.local, "conn", None)
        if c is None:
            try:
                sock = socket.create_connection(self.addr, timeout=10)
            except OSError as e:
                raise RadCallError(f"cannot reach the RAD Hub at {self.addr[0]}:{self.addr[1]}: {e}") from None
            sock.settimeout(_timeout())
            c = self.local.conn = (sock, sock.makefile("rb"))
        return c

    def call(self, name: str, args: list):
        sock, f = self._conn()
        rid = next(self.ids)
        try:
            sock.sendall((_dumps({"id": rid, "call": name, "args": args}) + "\n").encode("utf-8"))
            while True:
                raw = f.readline()
                if not raw:
                    raise RadCallError("the RAD Hub closed the connection")
                msg = json.loads(raw.decode("utf-8"))
                if msg.get("id") == rid:
                    return msg
        except (OSError, ValueError) as e:
            self.local.conn = None
            try:
                sock.close()
            except OSError:
                pass
            if isinstance(e, socket.timeout):
                raise RadCallError(f"timeout: {name} did not answer") from None
            raise RadCallError(f"RAD Hub connection failed: {e}") from None


# ============================================================================ worker channel
class _WorkerChannel:
    """stdin/stdout of a worker process: serves "func" requests and makes nested calls."""

    def __init__(self, dispatch, out, inp):
        self.dispatch, self.out, self.inp = dispatch, out, inp
        self.ids = itertools.count(1)
        self.lock = threading.Lock()

    def send(self, msg: dict) -> None:
        data = (_dumps(msg) + "\n").encode("utf-8")
        with self.lock:
            self.out.write(data)
            self.out.flush()

    def _read(self):
        while True:
            raw = self.inp.readline()
            if not raw:
                return None
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                sys.stderr.write(f"radcall worker: bad request line: {line[:200]}\n")
                continue
            if isinstance(msg, dict):
                return msg

    def serve_one(self, msg: dict) -> None:
        rid = msg.get("id")
        try:
            result = self.dispatch(str(msg.get("func", "")), msg.get("args") or [])
            reply = {"id": rid, "result": result}
            try:
                _dumps(reply)
            except (TypeError, ValueError):
                reply = {"id": rid, "result": str(result)}
        except Exception as e:  # noqa: BLE001 - report every error to the caller
            reply = {"id": rid, "error": f"{type(e).__name__}: {e}" if not isinstance(e, RadCallError) else str(e)}
        self.send(reply)

    def serve_forever(self) -> None:
        while True:
            msg = self._read()
            if msg is None:
                return
            if "func" in msg:
                self.serve_one(msg)

    def call(self, name: str, args: list):
        rid = next(self.ids)
        self.send({"id": rid, "call": name, "args": args})
        while True:
            msg = self._read()
            if msg is None:
                raise RadCallError("the RAD Hub closed the worker")
            if "func" in msg:              # someone calls us while we wait (re-entrant call)
                self.serve_one(msg)
            elif msg.get("id") == rid:
                return msg


_channel = None
_private_hub = None
_chan_lock = threading.Lock()


def _get_channel():
    global _channel, _private_hub
    with _chan_lock:
        if _channel is not None:
            return _channel
        address = os.environ.get("RAD_HUB", "")
        if not address:
            folder = os.environ.get("RAD_PROJECT") or os.path.dirname(os.path.abspath(sys.argv[0] or "."))
            try:
                from radide.runtimes.radhub import RadHub   # outside the IDE: own hub
            except ImportError:
                raise RadCallError("RAD_HUB is not set - run the program from RAD IDE "
                                   "(or with: python -m radide.runtimes.radhub <project> -- <program>)") from None
            _private_hub = RadHub(folder)
            address = _private_hub.start()
            os.environ.update(_private_hub.env())
            import atexit
            atexit.register(_private_hub.stop)
        _channel = _TcpChannel(address)
        return _channel


def radcall(name: str, *args):
    """Call ``"<Module>.<function>"`` of any language in the project and return its result."""
    if not isinstance(name, str) or "." not in name:
        raise RadCallError(f"radcall: expected \"Module.function\", got {name!r}")
    msg = _get_channel().call(name, list(args))
    if "error" in msg:
        raise RadCallError(str(msg["error"]))
    return msg.get("result")


def run_worker(dispatch) -> None:
    """Serve requests on stdin/stdout until stdin closes. *dispatch(func, args)* returns the
    result or raises. ``print`` output is moved to stderr so it cannot break the protocol;
    radcall() inside the worker goes through the same channel (no deadlock on call-backs)."""
    global _channel
    out = sys.stdout.buffer
    inp = sys.stdin.buffer
    sys.stdout = sys.stderr
    ch = _WorkerChannel(dispatch, out, inp)
    with _chan_lock:
        _channel = ch
    ch.serve_forever()
