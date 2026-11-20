"""Dev Containers: open a folder that has .devcontainer/devcontainer.json; RAD IDE starts (or builds) the
container with the docker CLI, bind-mounts the folder at /workspaces/<name>, and runs every command,
terminal and build inside it with `docker exec`.  Files stay on the Windows side (the bind mount), so the
editor reads and writes them directly.

Supported devcontainer.json keys: image, build.dockerfile / dockerFile, build.context, build.args, name,
workspaceFolder, containerEnv, remoteEnv, remoteUser / containerUser, forwardPorts, appPort, runArgs,
mounts (string form), overrideCommand, postCreateCommand, postStartCommand, postAttachCommand.
Not supported (explained to the user): dockerComposeFile, features, initializeCommand (runs on the host).
Docker is never installed by the IDE; without docker the UI explains what is needed."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path, PurePosixPath
from typing import Callable

from .base import LocalMappedFS, RemoteError, ShellBackend, norm, q
from .process import ProcessShell, run, run_stream

LABEL = "radide.devcontainer"


def docker_exe() -> str:
    exe = shutil.which("docker")
    if exe:
        return exe
    for c in (r"C:\Program Files\Docker\Docker\resources\bin\docker.exe",):
        if Path(c).is_file():
            return c
    return ""


def docker_status() -> tuple[bool, str]:
    exe = docker_exe()
    if not exe:
        return False, ("The docker CLI was not found. Install Docker Desktop (or another Docker engine) to use "
                       "Dev Containers - it needs administrator rights, RAD IDE does not install it.")
    code, out = run([exe, "version", "--format", "{{.Server.Version}}"], timeout=20)
    text = out.decode("utf-8", "replace").strip()
    if code != 0 or not re.match(r"^\d", text):
        return False, f"docker is installed but its engine is not running (start Docker Desktop).\n{text[:300]}"
    return True, f"Docker engine {text.splitlines()[0]}"


def strip_jsonc(text: str) -> str:
    """Remove // and /* */ comments (outside strings) and trailing commas."""
    out, i, n = [], 0, len(text)
    in_str = False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
        elif text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
        else:
            out.append(c)
            i += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out))


def find_config(folder) -> Path | None:
    f = Path(folder)
    for c in (f / ".devcontainer" / "devcontainer.json", f / ".devcontainer.json"):
        if c.is_file():
            return c
    sub = sorted((f / ".devcontainer").glob("*/devcontainer.json")) if (f / ".devcontainer").is_dir() else []
    return sub[0] if sub else None


def load_config(path) -> dict:
    try:
        return json.loads(strip_jsonc(Path(path).read_text(encoding="utf-8")))
    except (OSError, ValueError) as e:
        raise RemoteError(f"Cannot read {path}: {e}") from e


def _commands(value) -> list[str]:
    """A lifecycle command: string, argv list, or {name: string|list}."""
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [" ".join(q(x) for x in value)]
    if isinstance(value, dict):
        out = []
        for v in value.values():
            out += _commands(v)
        return out
    return []


class DevContainer:
    def __init__(self, folder, config_path=None):
        self.folder = Path(folder).resolve()
        self.config_path = Path(config_path) if config_path else find_config(self.folder)
        if self.config_path is None:
            raise RemoteError(f"{self.folder} has no .devcontainer/devcontainer.json")
        self.config = load_config(self.config_path)
        self.docker = docker_exe()
        h = hashlib.sha1(str(self.folder).lower().encode()).hexdigest()[:10]
        slug = re.sub(r"[^a-z0-9_.-]+", "-", self.folder.name.lower()).strip("-.") or "workspace"
        self.hash = h
        self.container_name = f"radide-dc-{slug}-{h}"
        self.image_tag = f"radide-dc-{slug}-{h}:latest"
        self.workspace = norm(self.config.get("workspaceFolder") or f"/workspaces/{self.folder.name}")
        self.user = self.config.get("remoteUser") or ""
        self.env = {**(self.config.get("containerEnv") or {}), **(self.config.get("remoteEnv") or {})}

    @property
    def name(self) -> str:
        return str(self.config.get("name") or self.folder.name)

    def unsupported(self) -> list[str]:
        c = self.config
        out = []
        if c.get("dockerComposeFile"):
            out.append("dockerComposeFile (Docker Compose dev containers) - start the services with "
                       "`docker compose up -d` and use Run Command; not automated yet")
        if c.get("features"):
            out.append("features (Dev Container Features) are ignored - add what you need to the Dockerfile")
        if c.get("initializeCommand"):
            out.append("initializeCommand (runs on the host) is not run")
        return out

    def _need_docker(self):
        if not self.docker:
            raise RemoteError(docker_status()[1])

    # ------------------------------------------------------------- container state
    def container_state(self) -> str:
        """'running', 'exited', 'created' ... or '' when there is no container yet."""
        self._need_docker()
        code, out = run([self.docker, "ps", "-a", "--filter", f"name=^/{self.container_name}$",
                         "--format", "{{.State}}"], timeout=30)
        return out.decode("utf-8", "replace").strip().splitlines()[0] if code == 0 and out.strip() else ""

    def _build_argv(self) -> list[str] | None:
        c = self.config
        build = c.get("build") or {}
        dockerfile = build.get("dockerfile") or build.get("dockerFile") or c.get("dockerFile")
        if not dockerfile:
            return None
        base = self.config_path.parent
        df = (base / dockerfile).resolve()
        ctx = (base / (build.get("context") or ".")).resolve()
        argv = [self.docker, "build", "-t", self.image_tag, "-f", str(df)]
        for k, v in (build.get("args") or {}).items():
            argv += ["--build-arg", f"{k}={v}"]
        if build.get("target"):
            argv += ["--target", str(build["target"])]
        return argv + [str(ctx)]

    def run_argv(self, image: str) -> list[str]:
        c = self.config
        argv = [self.docker, "run", "-d", "--name", self.container_name, "--label", f"{LABEL}={self.folder}",
                "-v", f"{self.folder}:{self.workspace}", "-w", self.workspace]
        for k, v in (c.get("containerEnv") or {}).items():
            argv += ["-e", f"{k}={v}"]
        ports = list(c.get("forwardPorts") or [])
        app = c.get("appPort")
        ports += app if isinstance(app, list) else ([app] if app else [])
        for p in ports:
            p = str(p)
            if re.match(r"^\d+$", p):
                argv += ["-p", f"127.0.0.1:{p}:{p}"]
            elif re.match(r"^[\d.:]+$", p):
                argv += ["-p", p]
        for m in c.get("mounts") or []:
            if isinstance(m, str):
                argv += ["--mount", m]
        if c.get("containerUser"):
            argv += ["-u", str(c["containerUser"])]
        argv += [str(a) for a in (c.get("runArgs") or [])]
        if c.get("overrideCommand", True):
            argv += ["--entrypoint", "/bin/sh", image, "-c", "trap 'exit 0' TERM; while sleep 1000; do :; done"]
        else:
            argv += [image]
        return argv

    def plan(self) -> list[str]:
        """The docker commands up() will run (shown before running them)."""
        steps = []
        b = self._build_argv() if self.docker else None
        image = self.image_tag if b else str(self.config.get("image") or "")
        if b:
            steps.append(" ".join(b))
        if self.docker:
            steps.append(" ".join(self.run_argv(image or "<no image>")))
        steps += [f"(once) {x}" for x in _commands(self.config.get("postCreateCommand"))]
        steps += [f"(each start) {x}" for x in _commands(self.config.get("postStartCommand"))]
        return steps

    def up(self, on_output: Callable[[str], None] = lambda s: None,
           should_stop: Callable[[], bool] = lambda: False) -> str:
        """Start the container (create / build it the first time). Returns the container name."""
        self._need_docker()
        ok, msg = docker_status()
        if not ok:
            raise RemoteError(msg)
        if self.config.get("dockerComposeFile"):
            raise RemoteError("This dev container uses Docker Compose (dockerComposeFile), which RAD IDE does not "
                              "automate yet. Start it with `docker compose up -d` in the Terminal.")
        for u in self.unsupported():
            on_output(f"note: {u}\n")
        state = self.container_state()
        if state == "running":
            on_output(f"Container {self.container_name} is running.\n")
            return self.container_name
        if state:
            on_output(f"Starting container {self.container_name} ...\n")
            code, out = run([self.docker, "start", self.container_name], timeout=120)
            if code != 0:
                raise RemoteError(out.decode("utf-8", "replace"))
            self._lifecycle("postStartCommand", on_output, should_stop)
            return self.container_name
        b = self._build_argv()
        image = self.config.get("image")
        if b:
            on_output("$ " + " ".join(b) + "\n")
            if run_stream(b, on_output, should_stop) != 0:
                raise RemoteError("docker build failed (see Output)")
            image = self.image_tag
        if not image:
            raise RemoteError("devcontainer.json has neither \"image\" nor \"build.dockerfile\"")
        argv = self.run_argv(str(image))
        on_output("$ " + " ".join(argv) + "\n")
        if run_stream(argv, on_output, should_stop) != 0:
            raise RemoteError("docker run failed (see Output; a missing image is pulled automatically by docker)")
        self._lifecycle("postCreateCommand", on_output, should_stop)
        self._lifecycle("postStartCommand", on_output, should_stop)
        return self.container_name

    def _lifecycle(self, key: str, on_output, should_stop) -> None:
        for cmd in _commands(self.config.get(key)):
            on_output(f"[{key}] $ {cmd}\n")
            code = run_stream(self.exec_argv(cmd, self.workspace), on_output, should_stop)
            if code != 0:
                on_output(f"[{key}] exit code {code}\n")

    def stop(self, remove: bool = False) -> str:
        self._need_docker()
        code, out = run([self.docker, "rm", "-f", self.container_name] if remove else
                        [self.docker, "stop", "-t", "2", self.container_name], timeout=60)
        return out.decode("utf-8", "replace")

    # ------------------------------------------------------------- exec
    def exec_argv(self, cmd: str, cwd: str | None, interactive: bool = False) -> list[str]:
        argv = [self.docker, "exec", "-i", "-w", norm(cwd or self.workspace)]
        if self.user:
            argv += ["-u", self.user]
        for k, v in (self.config.get("remoteEnv") or {}).items():
            argv += ["-e", f"{k}={v}"]
        return argv + [self.container_name, "sh", "-lc" if not interactive else "-c", cmd]


class DevContainerFS(LocalMappedFS):
    kind = "devcontainer"

    def __init__(self, dc: DevContainer):
        super().__init__(dc.workspace)
        self.dc = dc

    @property
    def label(self) -> str:
        return f"Dev Container: {self.dc.name}"

    def _local(self, path: str) -> Path:
        p = PurePosixPath(norm(path))
        ws = PurePosixPath(self.dc.workspace)
        if p != ws and ws not in p.parents:
            raise RemoteError(f"{path} is outside the workspace folder {ws} (only the workspace is editable)")
        rel = p.relative_to(ws)
        return self.dc.folder.joinpath(*rel.parts)

    def exec_stream(self, cmd, cwd, on_output, should_stop=lambda: False, timeout=None) -> int:
        return run_stream(self.dc.exec_argv(cmd, cwd), on_output, should_stop, timeout)

    def open_shell(self, cwd: str | None = None) -> ShellBackend:
        return ProcessShell(self.dc.exec_argv(
            "if command -v bash >/dev/null 2>&1; then exec bash; else exec sh; fi", cwd, interactive=True))


__all__ = ["DevContainer", "DevContainerFS", "docker_exe", "docker_status", "find_config", "load_config",
           "strip_jsonc"]
