"""WSL backend: files through \\\\wsl$\\<distro>\\..., commands through `wsl.exe -d <distro> --cd <dir> -e sh -lc`.
Nothing is installed: when wsl.exe or a distro is missing the UI explains how to get one."""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path, PureWindowsPath
from typing import Callable

from .base import LocalMappedFS, RemoteError, ShellBackend, norm
from .process import ProcessShell, run, run_stream

UNC_PREFIXES = ("\\\\wsl$\\", "\\\\wsl.localhost\\")


def wsl_exe() -> str:
    if sys.platform != "win32":
        return ""
    return shutil.which("wsl.exe") or ""


def _decode(b: bytes) -> str:
    if b.count(b"\x00") > len(b) // 4:            # wsl.exe prints UTF-16LE
        return b.decode("utf-16-le", errors="replace").replace("\ufeff", "")
    return b.decode("utf-8", errors="replace")


def distros() -> list[dict]:
    """[{name, default, state, version}] of the installed WSL distributions (empty without WSL)."""
    exe = wsl_exe()
    if not exe:
        return []
    code, out = run([exe, "-l", "-v"], timeout=20)
    text = _decode(out)
    if code != 0:
        return []
    res = []
    for line in text.splitlines()[1:]:
        line = line.replace("\x00", "").rstrip()
        if not line.strip():
            continue
        default = line.lstrip().startswith("*")
        parts = line.replace("*", " ").split()
        if not parts:
            continue
        name = parts[0]
        state = parts[1] if len(parts) > 1 else ""
        ver = parts[2] if len(parts) > 2 else ""
        res.append({"name": name, "default": default, "state": state, "version": ver})
    return res


def status_text() -> str:
    if not wsl_exe():
        return "WSL is not available on this computer (Windows only)."
    ds = distros()
    if not ds:
        return ("WSL is present but no Linux distribution is installed. Install one from an elevated "
                "terminal with  wsl --install -d Ubuntu  (needs administrator rights; RAD IDE does not do it).")
    return "WSL distributions: " + ", ".join(d["name"] + (" (default)" if d["default"] else "") for d in ds)


def unc_path(distro: str, path: str) -> Path:
    return Path("\\\\wsl$\\" + distro + "\\" + norm(path).lstrip("/").replace("/", "\\"))


def parse_unc(path: str) -> tuple[str, str] | None:
    """\\\\wsl$\\Ubuntu\\home\\me -> ("Ubuntu", "/home/me")."""
    s = str(path).replace("/", "\\")
    for pre in UNC_PREFIXES:
        if s.lower().startswith(pre):
            rest = s[len(pre):]
            distro, _, tail = rest.partition("\\")
            return distro, "/" + tail.replace("\\", "/").strip("/")
    return None


def windows_to_wsl(path: str) -> str:
    """C:\\Users\\me -> /mnt/c/Users/me (default automount)."""
    p = PureWindowsPath(path)
    if p.drive and re.match(r"^[A-Za-z]:$", p.drive):
        return "/mnt/" + p.drive[0].lower() + "/" + "/".join(p.parts[1:])
    return str(path).replace("\\", "/")


class WSLFS(LocalMappedFS):
    kind = "wsl"

    def __init__(self, distro: str, root: str = ""):
        super().__init__(root or "/")
        self.distro = distro
        self._exe = wsl_exe()
        if not self._exe:
            raise RemoteError("wsl.exe was not found")
        if not root:
            code, out = run(self._argv("echo $HOME", None), timeout=30)
            home = _decode(out).strip().splitlines()[-1:] if code == 0 else []
            self.root = norm(home[0]) if home and home[0].startswith("/") else "/"

    @property
    def label(self) -> str:
        return f"WSL: {self.distro}"

    def _local(self, path: str) -> Path:
        return unc_path(self.distro, path)

    def _argv(self, cmd: str, cwd: str | None) -> list[str]:
        argv = [self._exe, "-d", self.distro]
        if cwd:
            argv += ["--cd", norm(cwd)]
        return argv + ["-e", "sh", "-lc", cmd]

    def exec_stream(self, cmd: str, cwd: str | None, on_output: Callable[[str], None],
                    should_stop: Callable[[], bool] = lambda: False, timeout: float | None = None) -> int:
        return run_stream(self._argv(cmd, cwd), on_output, should_stop, timeout)

    def open_shell(self, cwd: str | None = None) -> ShellBackend:
        argv = [self._exe, "-d", self.distro] + (["--cd", norm(cwd)] if cwd else []) + [
            "-e", "sh", "-c", "if command -v bash >/dev/null 2>&1; then exec bash; else exec sh; fi"]
        return ProcessShell(argv)

    def search(self, text, folder, glob="", regex=False, case=False, max_results=2000,
               should_stop=lambda: False):
        hits = self.grep_search(text, folder, glob, regex, case, max_results, should_stop)
        if hits is not None:
            return hits
        return super().search(text, folder, glob, regex, case, max_results, should_stop)


__all__ = ["WSLFS", "distros", "status_text", "unc_path", "parse_unc", "windows_to_wsl", "wsl_exe"]
