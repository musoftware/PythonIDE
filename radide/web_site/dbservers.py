"""On-demand local database servers (MariaDB / MySQL and PostgreSQL) for the Databases workspace.

No Windows services: the IDE starts a server when the user asks ("Start local MariaDB / MySQL",
"Start local PostgreSQL" in the Databases dock) and stops it when asked or when the IDE exits.

* Binaries: portable zips extracted into ``%LOCALAPPDATA%\\RADIDE\\toolchains\\mariadb`` (MariaDB "winx64" zip
  from mariadb.org) and ``%LOCALAPPDATA%\\RADIDE\\toolchains\\pgsql`` (EDB "binaries" zip, the ``pgsql`` folder),
  else an installed server on PATH / under Program Files.
* Data: ``%LOCALAPPDATA%\\RADIDE\\db\\<engine>\\data`` - created on the first start (``mariadb-install-db`` /
  ``initdb``), the server listens on 127.0.0.1 only.
* Login: user ``radide`` (superuser / all privileges), database ``radide``, a random password generated on the
  first start. The password belongs to the data folder, so it is kept next to it in
  ``%LOCALAPPDATA%\\RADIDE\\db\\<engine>\\radide-server.json`` encrypted with Windows DPAPI (the same helper as
  the Databases ``PasswordStore``; base64 elsewhere) - never in a project file.

No Qt here (UI: radide/features/databases.py).
"""
from __future__ import annotations

import base64
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .databases import ConnectionInfo, DatabaseError, _dpapi

USER = "radide"
DATABASE = "radide"
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_EXE = ".exe" if sys.platform == "win32" else ""


def radide_local() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
    return Path(base) / "RADIDE"


def toolchains_dir() -> Path:
    return radide_local() / "toolchains"


def db_root() -> Path:
    return radide_local() / "db"


def _bin_candidates(folder: Path):
    """``folder/bin`` and ``folder/<one level>/bin`` (zip extracted with its top folder)."""
    yield folder / "bin"
    if folder.is_dir():
        for sub in sorted(folder.iterdir(), reverse=True):
            if sub.is_dir():
                yield sub / "bin"


def _find_bin(exe: str, toolchain: str, globs: list[str]) -> Path | None:
    for b in _bin_candidates(toolchains_dir() / toolchain):
        if (b / (exe + _EXE)).exists():
            return b
    w = shutil.which(exe)
    if w:
        return Path(w).parent
    for g in globs:
        root, _, pattern = g.partition("|")
        r = Path(root)
        if r.is_dir():
            for d in sorted(r.glob(pattern), reverse=True):
                if (d / (exe + _EXE)).exists():
                    return d
    return None


def port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.4):
            return True
    except OSError:
        return False


def _pick_port(preferred: int) -> int:
    for p in [preferred] + list(range(preferred + 1, preferred + 50)):
        if not port_in_use(p):
            s = socket.socket()
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
            finally:
                s.close()
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _protect(pw: str) -> str:
    data = pw.encode("utf-8")
    if sys.platform == "win32":
        return "dpapi:" + base64.b64encode(_dpapi(data, encrypt=True)).decode("ascii")
    return "b64:" + base64.b64encode(data).decode("ascii")


def _unprotect(raw: str) -> str:
    kind, _, payload = (raw or "").partition(":")
    blob = base64.b64decode(payload)
    if kind == "dpapi":
        return _dpapi(blob, encrypt=False).decode("utf-8")
    return blob.decode("utf-8")


# =============================================================================== base
class LocalServer:
    engine = ""            # folder name under db/ and toolchains/
    kind = ""              # ConnectionInfo.kind
    title = ""
    default_port = 0
    install_hint = ""

    def __init__(self, bin_dir: Path | str | None = None, root: Path | str | None = None, log=None):
        self._bin = Path(bin_dir) if bin_dir else None
        self.root = Path(root) if root else db_root() / self.engine
        self.log = log or (lambda text: None)
        self.proc: subprocess.Popen | None = None    # set when this IDE started the server process
        self.started_here = False
        self._logf = None

    # ------------------------------------------------------------------ paths / state
    @property
    def bin_dir(self) -> Path | None:
        if self._bin is None:
            self._bin = self.find_bin()
        return self._bin

    def find_bin(self) -> Path | None:
        raise NotImplementedError

    def exe(self, name: str) -> str:
        b = self.bin_dir
        if b is None:
            raise DatabaseError(f"{self.title} was not found. {self.install_hint}")
        return str(b / (name + _EXE))

    @property
    def available(self) -> bool:
        return self.bin_dir is not None

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def state_path(self) -> Path:
        return self.root / "radide-server.json"

    @property
    def log_path(self) -> Path:
        return self.root / "server.log"

    def state(self) -> dict:
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _save_state(self, **kw) -> None:
        st = self.state()
        st.update(kw)
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(st, indent=2), encoding="utf-8")

    @property
    def initialized(self) -> bool:
        return self.data_dir.is_dir() and bool(self.state().get("initialized"))

    @property
    def port(self) -> int:
        return int(self.state().get("port") or self.default_port)

    def password(self) -> str:
        raw = self.state().get("password", "")
        if not raw:
            return ""
        try:
            return _unprotect(raw)
        except Exception as e:  # noqa: BLE001 - other Windows user / corrupt
            raise DatabaseError(f"Cannot read the password of the local {self.title} server ({e})") from e

    def connection_info(self, name: str = "") -> ConnectionInfo:
        return ConnectionInfo(name or f"Local {self.title}", self.kind, host="127.0.0.1", port=self.port,
                              user=USER, database=DATABASE, remember_password=True)

    # ------------------------------------------------------------------ status
    def is_running(self) -> bool:
        raise NotImplementedError

    def status(self) -> str:
        if not self.available:
            return f"{self.title}: not installed - {self.install_hint}"
        if not self.initialized:
            return f"{self.title}: installed ({self.bin_dir}), not initialized yet (first Start creates the data folder)"
        if self.is_running():
            who = "started by this IDE" if self.started_here else "running"
            return f"{self.title}: {who} on 127.0.0.1:{self.port} (user {USER}, database {DATABASE})"
        return f"{self.title}: stopped (data: {self.data_dir})"

    # ------------------------------------------------------------------ helpers
    def _run(self, args: list[str], timeout: float = 180, env: dict | None = None) -> str:
        self.log(f"[db-server] {Path(args[0]).name} {' '.join(a for a in args[1:] if 'pass' not in a.lower())}")
        try:
            r = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=env,
                               stdin=subprocess.DEVNULL, creationflags=_NO_WINDOW, errors="replace")
        except (OSError, subprocess.SubprocessError) as e:
            raise DatabaseError(f"{Path(args[0]).name} failed: {e}") from e
        out = (r.stdout or "") + (r.stderr or "")
        if r.returncode != 0:
            raise DatabaseError(f"{Path(args[0]).name} failed (exit {r.returncode}):\n{out[-3000:]}")
        return out

    def read_log(self) -> str:
        try:
            return self.log_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def _wait_port(self, timeout: float) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.proc is not None and self.proc.poll() is not None:
                return False
            if port_in_use(self.port):
                return True
            time.sleep(0.2)
        return False

    def _close_log(self):
        if self._logf is not None:
            try:
                self._logf.close()
            except OSError:
                pass
            self._logf = None

    def _ensure_port(self) -> None:
        """Keep the saved port; choose another one when something else listens there now."""
        if not self.state().get("port") or (port_in_use(self.port) and not self.is_running()):
            self._save_state(port=_pick_port(self.default_port))

    # ------------------------------------------------------------------ public API
    def start(self, timeout: float = 90) -> ConnectionInfo:
        """Initialize the data folder when needed, start the server and return its connection."""
        if not self.available:
            raise DatabaseError(f"{self.title} was not found. {self.install_hint}")
        if self.is_running():
            return self.connection_info()
        self._ensure_port()
        first = not self.initialized
        if first:
            self._init_data()
        self._start(timeout)
        if first or not self.state().get("ready"):
            self._first_setup()
            self._save_state(ready=True)
        self.log(f"[db-server] {self.status()}")
        return self.connection_info()

    def stop(self, timeout: float = 30) -> bool:
        """Stop the server (gracefully, then by killing the process this IDE started). True if it stopped."""
        if not self.is_running():
            self._reap()
            return True
        try:
            self._stop(timeout)
        except Exception as e:  # noqa: BLE001
            self.log(f"[db-server] graceful stop of {self.title} failed: {e}")
        deadline = time.time() + timeout
        while time.time() < deadline and self.is_running():
            time.sleep(0.2)
        if self.is_running() and self.proc is not None and self.proc.poll() is None:
            self.proc.kill()
        self._reap()
        stopped = not self.is_running()
        self.log(f"[db-server] {self.title} {'stopped' if stopped else 'is still running'}")
        return stopped

    def stop_if_started_here(self) -> None:
        """For IDE exit: stop only a server this IDE started."""
        if self.started_here:
            try:
                self.stop()
            except Exception:  # noqa: BLE001
                pass

    def _reap(self):
        if self.proc is not None:
            try:
                self.proc.wait(5)
            except subprocess.TimeoutExpired:
                pass
            self.proc = None
        self.started_here = False
        self._close_log()

    # engine specific
    def _init_data(self) -> None:
        raise NotImplementedError

    def _start(self, timeout: float) -> None:
        raise NotImplementedError

    def _first_setup(self) -> None:
        raise NotImplementedError

    def _stop(self, timeout: float) -> None:
        raise NotImplementedError


# =============================================================================== MariaDB / MySQL
class MariaDBServer(LocalServer):
    engine = "mariadb"
    kind = "mysql"
    title = "MariaDB"
    default_port = 3306
    install_hint = ("Download the MariaDB \"Windows x86_64 ZIP\" from https://mariadb.org/download/ and extract it "
                    "to %LOCALAPPDATA%\\RADIDE\\toolchains\\mariadb (bin\\mariadbd.exe).")

    def find_bin(self) -> Path | None:
        for exe in ("mariadbd", "mysqld"):
            b = _find_bin(exe, "mariadb", [r"C:\Program Files|MariaDB*\bin", r"C:\Program Files\MySQL|MySQL Server*\bin"])
            if b is not None:
                return b
        return None

    def _server_exe(self) -> str:
        b = self.bin_dir
        if b is None:
            raise DatabaseError(f"{self.title} was not found. {self.install_hint}")
        return str(b / ("mariadbd" + _EXE)) if (b / ("mariadbd" + _EXE)).exists() else str(b / ("mysqld" + _EXE))

    def _connect(self, user: str = USER, password: str | None = None, database: str | None = None, timeout=3):
        import pymysql
        return pymysql.connect(host="127.0.0.1", port=self.port, user=user,
                               password=self.password() if password is None else password,
                               database=database, connect_timeout=timeout, autocommit=True)

    def is_running(self) -> bool:
        if self.proc is not None and self.proc.poll() is None:
            return True
        if not self.initialized or not port_in_use(self.port):
            return False
        pid = self.data_dir / f"{socket.gethostname()}.pid"
        if pid.exists():
            return True
        try:                                  # something listens: is it our server (our password works)?
            self._connect(timeout=2).close()
            return True
        except Exception:  # noqa: BLE001
            return False

    def _init_data(self) -> None:
        if self.data_dir.exists() and any(self.data_dir.iterdir()):
            raise DatabaseError(f"The data folder exists but was not set up by RAD IDE: {self.data_dir}")
        self.root.mkdir(parents=True, exist_ok=True)
        tool = Path(self._server_exe()).parent / ("mariadb-install-db" + _EXE)
        if not tool.exists():
            tool = tool.parent / ("mysql_install_db" + _EXE)
        if tool.exists():
            # root gets no password here (nothing on the command line); _first_setup sets it right away
            self._run([str(tool), f"--datadir={self.data_dir}", f"--port={self.port}", "--silent"])
        else:                                 # MySQL: mysqld --initialize-insecure
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self._run([self._server_exe(), "--initialize-insecure", f"--datadir={self.data_dir}", "--console"])
        self._save_state(initialized=True, password=_protect(secrets.token_urlsafe(18)), ready=False,
                         engine=self.engine, created=time.strftime("%Y-%m-%d %H:%M:%S"))

    def _start(self, timeout: float) -> None:
        ini = self.data_dir / "my.ini"
        args = [self._server_exe()]
        if ini.exists():
            args.append(f"--defaults-file={ini}")
        args += [f"--datadir={self.data_dir}", f"--port={self.port}", "--bind-address=127.0.0.1",
                 "--console", "--character-set-server=utf8mb4", "--collation-server=utf8mb4_unicode_ci"]
        self.log(f"[db-server] starting {self.title} on 127.0.0.1:{self.port}")
        self._logf = open(self.log_path, "a", encoding="utf-8", errors="replace")
        self.proc = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=self._logf, stderr=subprocess.STDOUT,
                                     cwd=str(self.root), creationflags=_NO_WINDOW)
        self.started_here = True
        if not self._wait_port(timeout):
            log = self.read_log()
            self.stop(10)
            raise DatabaseError(f"{self.title} did not start:\n{log[-3000:]}")

    def _first_setup(self) -> None:
        import pymysql
        pw = self.password()
        conn = None
        deadline = time.time() + 30
        while conn is None:
            for user, p in (("root", ""), ("root", pw), (USER, pw)):
                try:
                    conn = self._connect(user, p, timeout=3)
                    break
                except pymysql.MySQLError:
                    continue
            if conn is None:
                if time.time() > deadline:
                    raise DatabaseError(f"Cannot log in to the new {self.title} server")
                time.sleep(0.5)
        try:
            with conn.cursor() as cur:
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DATABASE}` CHARACTER SET utf8mb4 "
                            "COLLATE utf8mb4_unicode_ci")
                for host in ("localhost", "127.0.0.1", "::1"):
                    cur.execute(f"CREATE USER IF NOT EXISTS '{USER}'@'{host}' IDENTIFIED BY %s", (pw,))
                    cur.execute(f"ALTER USER '{USER}'@'{host}' IDENTIFIED BY %s", (pw,))
                    cur.execute(f"GRANT ALL PRIVILEGES ON *.* TO '{USER}'@'{host}' WITH GRANT OPTION")
                cur.execute("SELECT Host FROM mysql.user WHERE User='root'")
                for (host,) in cur.fetchall():
                    cur.execute(f"ALTER USER 'root'@'{host}' IDENTIFIED BY %s", (pw,))
                cur.execute("FLUSH PRIVILEGES")
        finally:
            conn.close()

    def _stop(self, timeout: float) -> None:
        conn = self._connect(timeout=5)
        try:
            with conn.cursor() as cur:
                cur.execute("SHUTDOWN")
        finally:
            try:
                conn.close()
            except Exception:  # noqa: BLE001
                pass


# =============================================================================== PostgreSQL
class PostgresServer(LocalServer):
    engine = "pgsql"
    kind = "postgresql"
    title = "PostgreSQL"
    default_port = 5432
    install_hint = ("Download the PostgreSQL \"zip archive\" binaries for Windows x86-64 from "
                    "https://www.enterprisedb.com/download-postgresql-binaries and extract its pgsql folder to "
                    "%LOCALAPPDATA%\\RADIDE\\toolchains\\pgsql (bin\\pg_ctl.exe).")

    def find_bin(self) -> Path | None:
        return _find_bin("pg_ctl", "pgsql", [r"C:\Program Files\PostgreSQL|*\bin"])

    def _env(self) -> dict:
        env = dict(os.environ)
        env.pop("PGPASSWORD", None)
        env["PGPORT"] = str(self.port)
        env["LC_MESSAGES"] = "C"
        return env

    def _pg_ctl(self, *args, timeout: float = 120) -> subprocess.CompletedProcess:
        return subprocess.run([self.exe("pg_ctl"), "-D", str(self.data_dir), *args], capture_output=True, text=True,
                              timeout=timeout, env=self._env(), stdin=subprocess.DEVNULL, creationflags=_NO_WINDOW,
                              errors="replace")

    def is_running(self) -> bool:
        if not self.initialized or not self.available:
            return False
        try:
            return self._pg_ctl("status", timeout=20).returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    def _init_data(self) -> None:
        if self.data_dir.exists() and any(self.data_dir.iterdir()):
            raise DatabaseError(f"The data folder exists but was not set up by RAD IDE: {self.data_dir}")
        self.root.mkdir(parents=True, exist_ok=True)
        pw = secrets.token_urlsafe(18)
        fd, pwfile = tempfile.mkstemp(prefix="radide-pg-", suffix=".txt")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(pw + "\n")
            self._run([self.exe("initdb"), "-D", str(self.data_dir), "-U", USER, "-A", "scram-sha-256",
                       f"--pwfile={pwfile}", "-E", "UTF8", "--no-locale"], env=self._env())
        finally:
            try:
                os.remove(pwfile)
            except OSError:
                pass
        with open(self.data_dir / "postgresql.conf", "a", encoding="utf-8") as f:
            f.write("\n# RAD IDE local server\nlisten_addresses = '127.0.0.1'\n")
        self._save_state(initialized=True, password=_protect(pw), ready=False, engine=self.engine,
                         created=time.strftime("%Y-%m-%d %H:%M:%S"))

    def _start(self, timeout: float) -> None:
        self.log(f"[db-server] starting {self.title} on 127.0.0.1:{self.port}")
        # pg_ctl starts postgres with a restricted token (works for administrators too) and returns when ready.
        # Output goes to the log file: an inherited pipe would keep this call waiting for the server's lifetime.
        with open(os.devnull, "w") as nul:
            r = subprocess.run([self.exe("pg_ctl"), "-D", str(self.data_dir), "-l", str(self.log_path),
                                "-o", f"-p {self.port} -c listen_addresses=127.0.0.1", "-w", "-t", str(int(timeout)),
                                "start"], stdin=subprocess.DEVNULL, stdout=nul, stderr=nul, env=self._env(),
                               creationflags=_NO_WINDOW, timeout=timeout + 30)
        self.started_here = True
        if r.returncode != 0 or not port_in_use(self.port):
            log = self.read_log()
            self.stop(10)
            raise DatabaseError(f"{self.title} did not start:\n{log[-3000:]}")

    def _connect(self, database: str = DATABASE, timeout: int = 5):
        import psycopg
        return psycopg.connect(host="127.0.0.1", port=self.port, user=USER, password=self.password(),
                               dbname=database, connect_timeout=timeout, autocommit=True)

    def _first_setup(self) -> None:
        conn = self._connect("postgres")
        try:
            if conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DATABASE,)).fetchone() is None:
                conn.execute(f'CREATE DATABASE "{DATABASE}"')
        finally:
            conn.close()

    def _stop(self, timeout: float) -> None:
        r = self._pg_ctl("stop", "-m", "fast", "-w", "-t", str(int(timeout)), timeout=timeout + 15)
        if r.returncode != 0:
            raise DatabaseError((r.stdout + r.stderr).strip())


SERVERS = {"mysql": MariaDBServer, "postgresql": PostgresServer}


def servers(log=None) -> dict[str, LocalServer]:
    """One manager per engine: {"mysql": MariaDBServer, "postgresql": PostgresServer}."""
    return {k: cls(log=log) for k, cls in SERVERS.items()}
