"""Common interface of remote file systems (SSH/SFTP, WSL, Dev Containers).

Every backend speaks POSIX paths ("/home/me/app/main.py") and offers the same operations, so the Remote
Explorer, the editor tabs, the remote terminal, Run/Build and Search work the same way on all of them.
Backends whose files are reachable as Windows paths (WSL through \\\\wsl$, Dev Containers through the bind
mount) return them from local_path(); SSH files are edited through a local cache (remote/cache.py).
"""
from __future__ import annotations

import fnmatch
import posixpath
import re
import shlex
import stat as _stat
from dataclasses import dataclass
from typing import Callable

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".hg", ".svn", ".mypy_cache", ".tox"}
MAX_SEARCH_FILE = 2_000_000          # bytes; larger files are skipped by the Python search


@dataclass
class Entry:
    name: str
    path: str                 # POSIX path
    is_dir: bool
    size: int = 0
    mtime: float = 0.0
    is_link: bool = False


@dataclass
class SearchHit:
    path: str
    line: int                 # 1-based
    text: str


class RemoteError(Exception):
    """A failed remote operation (message is shown to the user)."""


def q(s: str) -> str:
    """Quote for a POSIX shell."""
    return shlex.quote(str(s))


def norm(path: str) -> str:
    p = posixpath.normpath(str(path).replace("\\", "/") or "/")
    return "/" + p.lstrip("/") if not p.startswith("//") else p


def with_cwd(cmd: str, cwd: str | None) -> str:
    return f"cd {q(cwd)} && {cmd}" if cwd else cmd


def mode_is_dir(mode: int | None) -> bool:
    return bool(mode is not None and _stat.S_ISDIR(mode))


class ShellBackend:
    """An interactive shell: write(text) sends input; poll() returns new output (bytes) or None when
    the shell has ended.  Implemented over a paramiko channel or a local process (wsl.exe / docker exec)."""

    def write(self, data: bytes) -> None:
        raise NotImplementedError

    def poll(self) -> bytes | None:
        raise NotImplementedError

    def interrupt(self) -> None:
        self.write(b"\x03")

    def close(self) -> None:
        pass


class RemoteFS:
    kind = "remote"           # "ssh" | "wsl" | "devcontainer"

    def __init__(self, root: str = "/"):
        self.root = norm(root)

    # ------------------------------------------------------------- description
    @property
    def label(self) -> str:
        return self.kind

    @property
    def key(self) -> str:
        """Stable id (settings, cache folder)."""
        return re.sub(r"[^A-Za-z0-9_.@-]+", "_", self.label)

    def local_path(self, path: str):
        """A Windows path that reaches the same file directly, or None (then use the cache)."""
        return None

    # ------------------------------------------------------------- files (override)
    def listdir(self, path: str) -> list[Entry]:
        raise NotImplementedError

    def stat(self, path: str) -> Entry | None:
        raise NotImplementedError

    def read(self, path: str) -> bytes:
        raise NotImplementedError

    def write(self, path: str, data: bytes) -> None:
        raise NotImplementedError

    def mkdir(self, path: str) -> None:
        raise NotImplementedError

    def remove(self, path: str) -> None:
        """Delete a file or a whole folder."""
        raise NotImplementedError

    def rename(self, old: str, new: str) -> None:
        raise NotImplementedError

    # ------------------------------------------------------------- commands (override)
    def exec_stream(self, cmd: str, cwd: str | None, on_output: Callable[[str], None],
                    should_stop: Callable[[], bool] = lambda: False, timeout: float | None = None) -> int:
        """Run *cmd* with a POSIX shell in *cwd*; on_output gets text as it arrives. Returns the exit code."""
        raise NotImplementedError

    def exec(self, cmd: str, cwd: str | None = None, timeout: float | None = 60) -> tuple[int, str]:
        out: list[str] = []
        code = self.exec_stream(cmd, cwd, out.append, timeout=timeout)
        return code, "".join(out)

    def open_shell(self, cwd: str | None = None) -> ShellBackend:
        raise NotImplementedError

    def close(self) -> None:
        pass

    # ------------------------------------------------------------- helpers
    def is_dir(self, path: str) -> bool:
        e = self.stat(path)
        return bool(e and e.is_dir)

    def exists(self, path: str) -> bool:
        return self.stat(path) is not None

    def join(self, *parts: str) -> str:
        return norm(posixpath.join(*parts))

    def walk_files(self, folder: str, glob: str = "", limit: int = 20000):
        """Yield Entry for every file under *folder* (skips .git, node_modules, ...)."""
        stack = [norm(folder)]
        count = 0
        pats = [g.strip() for g in glob.replace(";", ",").split(",") if g.strip()]
        while stack:
            d = stack.pop()
            try:
                items = self.listdir(d)
            except Exception:  # noqa: BLE001 - unreadable folder
                continue
            for e in sorted(items, key=lambda x: x.name.lower(), reverse=True):
                if e.is_dir:
                    if e.name not in SKIP_DIRS and not e.is_link:
                        stack.append(e.path)
                    continue
                if pats and not any(fnmatch.fnmatch(e.name, p) for p in pats):
                    continue
                count += 1
                if count > limit:
                    return
                yield e

    def search(self, text: str, folder: str, glob: str = "", regex: bool = False, case: bool = False,
               max_results: int = 2000, should_stop: Callable[[], bool] = lambda: False) -> list[SearchHit]:
        """Find *text* in the files under *folder* (Python implementation; backends with a shell
        override it with grep)."""
        rx = compile_query(text, regex, case)
        hits: list[SearchHit] = []
        for e in self.walk_files(folder, glob):
            if should_stop() or len(hits) >= max_results:
                break
            if e.size > MAX_SEARCH_FILE:
                continue
            try:
                data = self.read(e.path)
            except Exception:  # noqa: BLE001
                continue
            if b"\x00" in data[:4096]:
                continue
            for i, line in enumerate(data.decode("utf-8", errors="replace").splitlines(), 1):
                if rx.search(line):
                    hits.append(SearchHit(e.path, i, line.strip()[:400]))
                    if len(hits) >= max_results:
                        break
        return hits

    def grep_search(self, text: str, folder: str, glob: str, regex: bool, case: bool, max_results: int,
                    should_stop: Callable[[], bool] = lambda: False) -> list[SearchHit] | None:
        """Search with grep on the remote side; None when grep is not usable there."""
        opts = ["-rnI"] + [f"--exclude-dir={d}" for d in sorted(SKIP_DIRS)]
        if not case:
            opts.append("-i")
        opts.append("-E" if regex else "-F")
        for g in [g.strip() for g in glob.replace(";", ",").split(",") if g.strip()]:
            opts.append(f"--include={q(g)}")
        cmd = (f"command -v grep >/dev/null 2>&1 || exit 127; "
               f"out=$(grep {' '.join(opts)} -e {q(text)} -- {q(norm(folder))} 2>/dev/null); rc=$?; "
               f"printf '%s\\n' \"$out\" | head -n {int(max_results)}; exit $rc")
        try:
            code, out = self.exec(cmd, None, timeout=120)
        except Exception:  # noqa: BLE001
            return None
        if code not in (0, 1):
            return None
        hits = []
        for line in out.splitlines():
            m = re.match(r"^(/.*?):(\d+):(.*)$", line)
            if m:
                hits.append(SearchHit(m.group(1), int(m.group(2)), m.group(3).strip()[:400]))
        return hits


def compile_query(text: str, regex: bool, case: bool) -> re.Pattern:
    flags = 0 if case else re.IGNORECASE
    return re.compile(text if regex else re.escape(text), flags)


class LocalMappedFS(RemoteFS):
    """Backends whose POSIX paths map to Windows paths (WSL via \\\\wsl$, Dev Container bind mounts)."""

    def _local(self, path: str):
        raise NotImplementedError

    def local_path(self, path: str):
        return self._local(path)

    def _entry(self, path: str, lp) -> Entry:
        st = lp.lstat()
        is_link = _stat.S_ISLNK(st.st_mode)
        is_dir = lp.is_dir()
        return Entry(posixpath.basename(path.rstrip("/")) or "/", norm(path), is_dir,
                     0 if is_dir else st.st_size, st.st_mtime, is_link)

    def listdir(self, path: str) -> list[Entry]:
        lp = self._local(path)
        try:
            out = []
            for c in lp.iterdir():
                try:
                    out.append(self._entry(self.join(path, c.name), c))
                except OSError:
                    out.append(Entry(c.name, self.join(path, c.name), False))
            return out
        except OSError as e:
            raise RemoteError(f"Cannot list {path}: {e}") from e

    def stat(self, path: str) -> Entry | None:
        lp = self._local(path)
        try:
            return self._entry(path, lp)
        except OSError:
            return None

    def read(self, path: str) -> bytes:
        try:
            return self._local(path).read_bytes()
        except OSError as e:
            raise RemoteError(f"Cannot read {path}: {e}") from e

    def write(self, path: str, data: bytes) -> None:
        try:
            self._local(path).write_bytes(data)
        except OSError as e:
            raise RemoteError(f"Cannot write {path}: {e}") from e

    def mkdir(self, path: str) -> None:
        try:
            self._local(path).mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise RemoteError(f"Cannot create {path}: {e}") from e

    def remove(self, path: str) -> None:
        import shutil
        lp = self._local(path)
        try:
            if lp.is_dir() and not lp.is_symlink():
                shutil.rmtree(lp)
            else:
                lp.unlink()
        except OSError as e:
            raise RemoteError(f"Cannot delete {path}: {e}") from e

    def rename(self, old: str, new: str) -> None:
        try:
            self._local(old).rename(self._local(new))
        except OSError as e:
            raise RemoteError(f"Cannot rename {old}: {e}") from e


__all__ = ["Entry", "SearchHit", "RemoteError", "RemoteFS", "LocalMappedFS", "ShellBackend", "q", "norm",
           "with_cwd", "compile_query", "SKIP_DIRS"]
