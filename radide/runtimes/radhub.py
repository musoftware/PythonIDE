"""RAD Hub - lets the languages of one project call each other (docs/CONTRACTS.md, section 2).

The IDE starts a hub for every Run/Debug and gives the program (and every worker)
``RAD_HUB=127.0.0.1:<port>`` and ``RAD_PROJECT=<folder>``.

Client -> hub (TCP, UTF-8 JSON, one object per line)::

    {"id": 1, "call": "Helpers.add", "args": [2, 3]}  ->  {"id": 1, "result": 5}
                                                          {"id": 1, "error": "message"}

Hub -> worker (the worker's stdin/stdout, JSON lines)::

    {"id": 7, "func": "add", "args": [2, 3]}  ->  {"id": 7, "result": 5} / {"id": 7, "error": "..."}

A worker may itself call other modules *through its stdout* (no socket needed, and a
call back into the same worker cannot deadlock)::

    worker -> hub   {"id": 3, "call": "Other.f", "args": [...]}
    hub -> worker   {"id": 3, "result": ...}          (no "func" key = an answer)

While it waits for such an answer the worker keeps serving "func" requests it reads.
Workers log to stderr; any stdout line that is not a protocol object is shown as output.

``<Module>`` is a file stem in the project folder (a module or a form's code file), else in
the folders of the referenced projects (solutions, docs/CONTRACTS.md section 7: consumer
first, then its references in order, transitively; env ``RAD_PROJECT_PATH`` lists them).
The language comes from the file extension; the worker runs in the module's own folder
(``plugin.worker_command(module_folder, file)``) with ``RAD_PROJECT`` = that folder.
Reference proxy files (AUTO-GENERATED ... reference to X) are never served as modules.
``<Form>.Show`` for a project form starts that form as its own program (any language).

Command line (outside the IDE)::

    python -m radide.runtimes.radhub <project-folder> -- <program> [args...]
    python -m radide.runtimes.radhub <project-folder> --serve      (prints the address)
"""
from __future__ import annotations

import itertools
import json
import os
import socket
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path

CLIENTS = Path(__file__).resolve().parent / "clients"
try:     # what a REAL Python puts on PYTHONPATH: never _internal of a release build (python312.dll extension
    from ..paths import python_root      # modules there break another Python version: paths.python_root)
    IDE_ROOT = python_root()
    PY_CLIENTS = IDE_ROOT / "radide" / "runtimes" / "clients"
except Exception:  # noqa: BLE001 - loaded outside the package
    IDE_ROOT = Path(__file__).resolve().parent.parent.parent
    PY_CLIENTS = CLIENTS
DEFAULT_TIMEOUT = 60.0
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class HubError(Exception):
    pass


def _dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str)


def _parse_line(line: str):
    """Return (prefix_text, message_dict | None) for one line written by a worker."""
    s = line.rstrip("\r\n")
    i = s.find('{"id"')
    if i < 0:
        return s, None
    try:
        msg = json.loads(s[i:])
    except ValueError:
        return s, None
    if not isinstance(msg, dict) or "id" not in msg:
        return s, None
    return s[:i], msg


class _Pending:
    __slots__ = ("event", "msg")

    def __init__(self):
        self.event = threading.Event()
        self.msg: dict | None = None


# ============================================================================ worker
class Worker:
    """One long-running process that serves the functions of one module file."""

    def __init__(self, hub: "RadHub", module: str, path: Path, plugin, argv: list[str],
                 folder: Path | None = None):
        self.hub, self.module, self.path, self.plugin, self.argv = hub, module, path, plugin, argv
        self.folder = Path(folder) if folder is not None else hub.folder
        self.pending: dict[int, _Pending] = {}
        self.lock = threading.Lock()
        self.write_lock = threading.Lock()
        self.ids = itertools.count(1)
        self.stderr_tail: deque[str] = deque(maxlen=15)
        self.dead = False
        env = hub.child_env(worker=True)
        env["RAD_PROJECT"] = str(self.folder)          # the module's own project
        try:
            self.proc = subprocess.Popen(argv, cwd=str(self.folder), env=env, stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                         creationflags=NO_WINDOW)
        except OSError as e:
            raise HubError(f"cannot start the {plugin.display_name} worker for {path.name}: {e}") from None
        threading.Thread(target=self._read_out, daemon=True, name=f"radhub-out-{module}").start()
        threading.Thread(target=self._read_err, daemon=True, name=f"radhub-err-{module}").start()

    def alive(self) -> bool:
        return not self.dead and self.proc.poll() is None

    # ------------------------------------------------------------ io
    def _write(self, msg: dict) -> None:
        data = (_dumps(msg) + "\n").encode("utf-8")
        with self.write_lock:
            self.proc.stdin.write(data)
            self.proc.stdin.flush()

    def request(self, func: str, args: list, timeout: float):
        rid = next(self.ids)
        p = _Pending()
        with self.lock:
            if self.dead:
                raise HubError(self._death_message())
            self.pending[rid] = p
        try:
            self._write({"id": rid, "func": func, "args": args})
        except (OSError, ValueError):
            with self.lock:
                self.pending.pop(rid, None)
            raise HubError(self._death_message()) from None
        if not p.event.wait(timeout):
            with self.lock:
                self.pending.pop(rid, None)
            raise HubError(f"timeout: {self.module}.{func} did not answer within {timeout:g} s")
        msg = p.msg or {}
        if "error" in msg:
            raise HubError(str(msg["error"]))
        if msg.get("dead"):
            raise HubError(self._death_message())
        return msg.get("result")

    def _death_message(self) -> str:
        code = self.proc.poll()
        tail = "\n".join(self.stderr_tail).strip()
        msg = f"the {self.plugin.display_name} worker for {self.path.name} stopped"
        if code is not None:
            msg += f" (exit code {code})"
        return msg + (":\n" + tail if tail else "")

    def _read_out(self) -> None:
        for raw in iter(self.proc.stdout.readline, b""):
            line = raw.decode("utf-8", errors="replace")
            text, msg = _parse_line(line)
            if text.strip():
                self.hub.log(f"[{self.module}] {text}\n")
            if msg is None:
                continue
            if "call" in msg:                       # nested call made by the worker
                threading.Thread(target=self._serve_nested, args=(msg,), daemon=True).start()
                continue
            with self.lock:
                p = self.pending.pop(msg.get("id"), None)
            if p is not None:
                p.msg = msg
                p.event.set()
        self._on_exit()

    def _serve_nested(self, msg: dict) -> None:
        try:
            reply = {"id": msg.get("id"), "result": self.hub.call(str(msg.get("call", "")), msg.get("args") or [])}
        except HubError as e:
            reply = {"id": msg.get("id"), "error": str(e)}
        except Exception as e:  # noqa: BLE001 - never kill the reader
            reply = {"id": msg.get("id"), "error": f"{type(e).__name__}: {e}"}
        try:
            self._write(reply)
        except (OSError, ValueError):
            pass

    def _read_err(self) -> None:
        for raw in iter(self.proc.stderr.readline, b""):
            line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
            self.stderr_tail.append(line)
            if line.strip():
                self.hub.log(f"[{self.module}] {line}\n")

    def _on_exit(self) -> None:
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        time.sleep(0.05)                    # let the stderr reader catch up
        with self.lock:
            self.dead = True
            pending, self.pending = self.pending, {}
        for p in pending.values():
            p.msg = {"dead": True}
            p.event.set()

    def stop(self) -> None:
        try:
            self.proc.stdin.close()
        except OSError:
            pass
        try:
            self.proc.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                pass


# ============================================================================ hub
class RadHub:
    def __init__(self, folder: Path, log=None, timeout: float | None = None, interpreter_for=None,
                 search_folders=None):
        self.folder = Path(folder).resolve()
        # folders of referenced projects (in search order). None = from the solution that
        # contains *folder*, else from env RAD_PROJECT_PATH (a hub started outside the IDE)
        if search_folders is None:
            search_folders = self._discover_search_folders()
        self.search_folders: list[Path] = []
        for f in search_folders or []:
            try:
                rf = Path(f).resolve()
            except OSError:
                continue
            if rf != self.folder and rf not in self.search_folders:
                self.search_folders.append(rf)
        self._log = log
        if timeout is None:
            try:
                timeout = float(os.environ.get("RAD_TIMEOUT", "") or DEFAULT_TIMEOUT)
            except ValueError:
                timeout = DEFAULT_TIMEOUT
        self.timeout = timeout
        self.interpreter_for = interpreter_for     # callable(plugin) -> interpreter path ("" = default)
        self.workers: dict[str, Worker] = {}
        self.forms: dict[str, subprocess.Popen] = {}
        self._wlock = threading.Lock()
        self._server: socket.socket | None = None
        self._conns: set[socket.socket] = set()
        self._stopping = False
        self.port = 0

    # ------------------------------------------------------------ lifecycle
    @property
    def address(self) -> str:
        return f"127.0.0.1:{self.port}"

    def start(self) -> str:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(("127.0.0.1", 0))
        srv.listen(16)
        self._server, self.port = srv, srv.getsockname()[1]
        threading.Thread(target=self._accept, daemon=True, name="radhub-accept").start()
        return self.address

    @property
    def folders(self) -> list[Path]:
        """Where modules are looked up: the project folder, then the referenced projects."""
        return [self.folder, *self.search_folders]

    def _discover_search_folders(self) -> list[Path]:
        try:
            from ..solution import Solution
            sol = Solution.find_for_project(self.folder)
            if sol is not None:
                proj = sol.project_for_folder(self.folder)
                if proj is not None:
                    return sol.search_folders(proj)[1:]
        except Exception:  # noqa: BLE001 - a broken solution file must not stop the program
            pass
        env = os.environ.get("RAD_PROJECT_PATH", "")
        return [Path(p) for p in env.split(os.pathsep) if p.strip()]

    def env(self) -> dict[str, str]:
        """Variables to add to the program's environment."""
        return {"RAD_HUB": self.address, "RAD_PROJECT": str(self.folder),
                "RAD_PROJECT_PATH": os.pathsep.join(str(f) for f in self.folders)}

    def child_env(self, worker: bool = False, base: dict | None = None) -> dict[str, str]:
        env = dict(base if base is not None else os.environ)
        env.update(self.env())
        paths = [str(IDE_ROOT), str(PY_CLIENTS / "python")]
        if env.get("PYTHONPATH"):
            paths += [p for p in env["PYTHONPATH"].split(os.pathsep) if p and p not in paths]
        env["PYTHONPATH"] = os.pathsep.join(paths)
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        if worker:
            env["RAD_WORKER"] = "1"
        else:
            env.pop("RAD_WORKER", None)
        return env

    def stop(self) -> None:
        self._stopping = True
        if self._server is not None:
            try:
                self._server.close()
            except OSError:
                pass
        for c in list(self._conns):
            try:
                c.close()
            except OSError:
                pass
        with self._wlock:
            workers, self.workers = list(self.workers.values()), {}
            forms, self.forms = list(self.forms.values()), {}
        for w in workers:
            w.stop()
        for p in forms:
            if p.poll() is None:
                p.kill()
                try:
                    p.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    pass

    def log(self, text: str) -> None:
        if self._log is not None:
            try:
                self._log(text)
                return
            except Exception:  # noqa: BLE001 - logging must never break a call
                pass
        sys.stderr.write(text)
        sys.stderr.flush()

    # ------------------------------------------------------------ tcp clients
    def _accept(self) -> None:
        while not self._stopping:
            try:
                conn, _ = self._server.accept()
            except OSError:
                return
            self._conns.add(conn)
            threading.Thread(target=self._client, args=(conn,), daemon=True, name="radhub-client").start()

    def _client(self, conn: socket.socket) -> None:
        send_lock = threading.Lock()

        def answer(rid, req):
            try:
                reply = {"id": rid, "result": self.call(str(req.get("call", "")), req.get("args") or [])}
            except HubError as e:
                reply = {"id": rid, "error": str(e)}
            except Exception as e:  # noqa: BLE001
                reply = {"id": rid, "error": f"{type(e).__name__}: {e}"}
            data = (_dumps(reply) + "\n").encode("utf-8")
            with send_lock:
                try:
                    conn.sendall(data)
                except OSError:
                    pass

        try:
            f = conn.makefile("rb")
            for raw in f:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    req = json.loads(line)
                    if not isinstance(req, dict):
                        raise ValueError("not an object")
                except ValueError:
                    with send_lock:
                        conn.sendall((_dumps({"id": None, "error": "bad request (expected one JSON object "
                                                                  "per line)"}) + "\n").encode("utf-8"))
                    continue
                # one thread per request: a client may send several calls at once (threads)
                threading.Thread(target=answer, args=(req.get("id"), req), daemon=True).start()
        except OSError:
            pass
        finally:
            self._conns.discard(conn)
            try:
                conn.close()
            except OSError:
                pass

    # ------------------------------------------------------------ calls
    def call(self, target: str, args):
        """Run ``Module.function(*args)`` and return its result (raises HubError)."""
        if not isinstance(args, list):
            args = [args]
        module, dot, func = target.strip().partition(".")
        if not dot or not module or not func:
            raise HubError(f"bad call name '{target}' (expected \"Module.function\")")
        if func.lower() == "show":
            for folder in self.folders:
                project = self._project(folder)
                form = self._find_form(project, module) if project is not None else None
                if form is not None:
                    return self.show_form(project, form)
        path, plugin = self._find_module(None, module)
        w = self._worker(module, path, plugin)
        try:
            return w.request(func, args, self.timeout)
        except HubError as e:
            raise HubError(f"{module}.{func}: {e}") from None

    def _project(self, folder: Path | None = None):
        from ..model import Project
        try:
            return Project.load(folder or self.folder)
        except (OSError, ValueError, KeyError):
            return None

    @staticmethod
    def _is_proxy(path: Path) -> bool:
        try:
            with open(path, "rb") as f:
                return b"AUTO-GENERATED by RAD IDE (reference to" in f.read(2048)
        except OSError:
            return False

    @staticmethod
    def _find_form(project, name: str) -> str | None:
        return next((f for f in project.forms if f.lower() == name.lower()), None)

    def _find_module(self, project, name: str):
        """(path, plugin) of module *name*: the project folder first, then the referenced
        projects' folders. *project* = the Project of self.folder (None = load it)."""
        for i, folder in enumerate(self.folders):
            proj = project if (i == 0 and project is not None) else self._project(folder)
            found = self._find_in_folder(folder, proj, name)
            if found is not None:
                return found
        where = "the project" if not self.search_folders else "the project or its references"
        raise HubError(f"module '{name}' was not found in {where}")

    def _find_in_folder(self, folder: Path, project, name: str):
        from ..languages import plugin_for_file, plugin_for_form
        default = project.language if project is not None else ""
        proxies = set()
        if project is not None:
            proxies = {f.lower() for files in getattr(project, "reference_files", {}).values() for f in files}
            for mod in project.modules:
                if Path(mod).stem.lower() == name.lower() and mod.lower() not in proxies:
                    if self._is_proxy(folder / mod):
                        continue
                    plugin = plugin_for_file(mod, default)
                    if plugin is None:
                        raise HubError(f"no language plugin for {mod}")
                    return folder / mod, plugin
            form = self._find_form(project, name)
            if form is not None:
                plugin = plugin_for_form(project, form)
                return folder / plugin.code_file(form), plugin
        # any code file of the folder (projects created outside the IDE)
        try:
            files = sorted(folder.iterdir())
        except OSError:
            return None
        for f in files:
            if f.is_file() and f.stem.lower() == name.lower() and not f.name.startswith("_") \
                    and f.name.lower() not in proxies and not self._is_proxy(f):
                plugin = plugin_for_file(f.name, default)
                if plugin is not None:
                    return f, plugin
        return None

    def _worker(self, module: str, path: Path, plugin) -> Worker:
        key = os.path.normcase(str(Path(path).resolve()))
        with self._wlock:
            if self._stopping:
                raise HubError("the program is stopping")
            w = self.workers.get(key)
            if w is not None and w.alive():
                return w
            if not path.exists():
                raise HubError(f"{path.name} does not exist")
            try:
                argv = plugin.worker_command(path.parent, path.name)
            except Exception as e:  # noqa: BLE001 - report plugin failures as call errors
                raise HubError(f"{plugin.display_name} cannot start a worker for {path.name}: {e}") from None
            if not argv:
                raise HubError(f"{plugin.display_name} modules cannot be called from other languages yet "
                               f"(no worker for {path.name})")
            self.log(f"[RAD Hub] starting {plugin.display_name} worker for {path.name}\n")
            w = Worker(self, Path(path).stem, path, plugin, [str(a) for a in argv], folder=path.parent)
            self.workers[key] = w
            return w

    # ------------------------------------------------------------ forms of other languages
    def show_form(self, project, form: str) -> bool:
        from ..languages import plugin_for_form
        with self._wlock:
            p = self.forms.get(form.lower())
            if p is not None and p.poll() is None:
                return True
            plugin = plugin_for_form(project, form)
            interp = ""
            if self.interpreter_for is not None:
                try:
                    interp = self.interpreter_for(plugin) or ""
                except Exception:  # noqa: BLE001
                    interp = ""
            interp = interp or plugin.find_interpreter("")
            if not interp:
                raise HubError(f"{form}.Show: no {plugin.display_name} interpreter found")
            spec = plugin.run_spec(Path(project.folder), form, interp)
            env = self.child_env(base=spec.env)
            env["RAD_START_FORM"] = form
            self.log(f"[RAD Hub] showing {form} ({plugin.display_name})\n")
            try:
                p = subprocess.Popen([spec.program, *spec.args], cwd=str(spec.cwd), env=env,
                                     stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     creationflags=NO_WINDOW)
            except OSError as e:
                raise HubError(f"{form}.Show: cannot start {spec.program}: {e}") from None
            self.forms[form.lower()] = p
        threading.Thread(target=self._pump_form, args=(form, p), daemon=True).start()
        return True

    def _pump_form(self, form: str, p: subprocess.Popen) -> None:
        for raw in iter(p.stdout.readline, b""):
            self.log(f"[{form}] {raw.decode('utf-8', errors='replace')}")
        p.wait()


# ============================================================================ command line
def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    folder = Path(argv.pop(0)).resolve()
    hub = RadHub(folder)
    hub.start()
    try:
        if argv[:1] == ["--serve"]:
            print(hub.address, flush=True)
            sys.stdin.read()                  # serve until stdin closes
            return 0
        if argv[:1] == ["--"]:
            argv = argv[1:]
        if not argv:
            print("missing program", file=sys.stderr)
            return 2
        return subprocess.call(argv, cwd=str(folder), env=hub.child_env())
    finally:
        hub.stop()


if __name__ == "__main__":
    sys.exit(main())
