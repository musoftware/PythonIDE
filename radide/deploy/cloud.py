"""Cloud / Git / SSH deploy targets for the Publish dialog (no Qt in this module).

Targets: Vercel (vercel CLI), Netlify (netlify-cli), GitHub Pages (git push to a gh-pages branch), Azure App
Service (az CLI), AWS (Elastic Beanstalk with eb / aws CLI, or an S3 static site), Render and Railway (git push,
Render deploy hook, `railway up` when the CLI exists), and a generic SSH server (rsync or SFTP upload + remote
commands such as a service restart).

Rules:
* the IDE NEVER signs in to the user's accounts. Before a deploy it runs a read-only status command
  (`vercel whoami`, `netlify status`, `az account show`, `aws sts get-caller-identity`, `git ls-remote` ...)
  and, when that fails, stops with a clear "Sign in first: run `<cli> login` in the Terminal" message;
* every target has a dry run (Preview): the commands it would run + the files it would upload, nothing changes;
* commands never wait for input (stdin closed, GIT_TERMINAL_PROMPT=0, CI=1) so a missing login fails fast;
* secrets (passwords, tokens, deploy hooks) are never stored in project.radproj - the Qt layer keeps them in the
  user's settings like Publish passwords (radide/web_site/publish.py).

Profiles live in project.radproj under "deploy" (a list of dicts).
`plan(profile, folder, dry_run)` -> list[Step]; `execute(steps, log, cancel)` runs them.
"""
from __future__ import annotations

import os
import posixpath
import re
import shlex
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.request
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from . import docker as dk

NO_WINDOW = dk.NO_WINDOW
NPM_CLI_VERSIONS = {"vercel": "vercel", "netlify": "netlify-cli"}     # package names (latest when installed)
BUILD_DIRS = ("dist", "build", "out", "_site", "public_html", "www", "site")
NONINTERACTIVE_ENV = {"GIT_TERMINAL_PROMPT": "0", "CI": "1", "NO_UPDATE_NOTIFIER": "1", "AWS_PAGER": "",
                      "NETLIFY_NO_UPDATE_NOTIFIER": "1", "VERCEL_TELEMETRY_DISABLED": "1",
                      "GCM_INTERACTIVE": "never"}


class DeployError(Exception):
    pass


class SignInRequired(DeployError):
    pass


# ====================================================================== profile
@dataclass
class DeployProfile:
    name: str = "Cloud"
    target: str = "vercel"            # see TARGETS
    folder: str = ""                  # folder to deploy, relative to the project ("" = auto: build output / site)
    build_cmd: str = ""               # optional local build before deploying (npm run build ...)
    production: bool = True
    site_url: str = ""
    options: dict = field(default_factory=dict)   # target specific (see Target.fields)

    def opt(self, key: str, default=""):
        v = self.options.get(key)
        return default if v in (None, "") else v

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "DeployProfile":
        p = DeployProfile()
        for k, v in (d or {}).items():
            if hasattr(p, k) and k not in ("password", "token"):
                setattr(p, k, v)
        if not isinstance(p.options, dict):
            p.options = {}
        for secret in ("password", "token", "hook_url"):
            p.options.pop(secret, None)          # never accept secrets from the project file
        if p.target not in TARGETS:
            p.target = "ssh"
        return p


def load_profiles(project) -> list[DeployProfile]:
    raw = (getattr(project, "extra", None) or {}).get("deploy") or []
    return [DeployProfile.from_dict(d) for d in raw if isinstance(d, dict)]


def save_profiles(project, profiles: list[DeployProfile]) -> None:
    data = []
    for p in profiles:
        d = p.to_dict()
        d["options"] = {k: v for k, v in (d.get("options") or {}).items() if k not in SECRET_KEYS}
        data.append(d)
    project.extra["deploy"] = data
    project.save()


SECRET_KEYS = {"password", "token", "hook_url"}


# ====================================================================== steps
@dataclass
class Step:
    title: str
    argv: list[str] | None = None                  # a command ...
    func: Callable | None = None                   # ... or a Python callable(log, cancel) -> str|None
    cwd: str = ""
    env: dict = field(default_factory=dict)
    secrets: list[str] = field(default_factory=list)   # strings masked in logs / previews
    check: bool = True                             # a failing command stops the deploy
    signin: str = ""                               # non-empty: this step is a sign-in check; message if it fails
    timeout: float = 1800
    always: bool = False                           # clean-up step: also runs after a failure
    fail_pattern: str = ""                         # regex: output matching it counts as a failure (exit 0 CLIs)

    def describe(self) -> str:
        if self.argv:
            text = " ".join(_q(a) for a in self.argv)
            for s in self.secrets:
                if s:
                    text = text.replace(s, "****")
            return ("(in " + self.cwd + ") " if self.cwd else "") + text
        return f"[{self.title}]"


def _q(a: str) -> str:
    a = str(a)
    return a if re.fullmatch(r"[\w@%+=:,./\\-]+", a) else '"' + a.replace('"', '\\"') + '"'


_CMD_UNSAFE = re.compile(r'[&|<>^%!"\r\n]')


def _check_cmd_args(argv: list[str]) -> None:
    """.cmd / .bat shims are run through cmd.exe: refuse arguments cmd.exe would interpret."""
    if os.name == "nt" and argv and argv[0].lower().endswith((".cmd", ".bat")):
        bad = [a for a in argv[1:] if _CMD_UNSAFE.search(str(a))]
        if bad:
            raise DeployError(f"Unsafe characters for a .cmd tool in: {bad[0]!r}")


def run_stream(argv: list[str], cwd: str = "", env: dict | None = None, log: Callable[[str], None] = print,
               cancel: threading.Event | None = None, timeout: float = 1800, secrets=()) -> tuple[int, str]:
    """Runs a command, streams its output to log line by line. Returns (exit code, full output)."""
    _check_cmd_args(argv)
    e = dict(os.environ)
    e.update(NONINTERACTIVE_ENV)
    e.update(env or {})
    try:
        p = subprocess.Popen(argv, cwd=cwd or None, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace", env=e,
                             creationflags=NO_WINDOW)
    except FileNotFoundError:
        return 127, f"{argv[0]}: not found"
    except OSError as ex:
        return 126, str(ex)
    out: list[str] = []
    t0 = time.monotonic()

    def reader():
        for line in p.stdout:
            line = line.rstrip("\r\n")
            for s in secrets:
                if s:
                    line = line.replace(s, "****")
            out.append(line)
            log(line)
    th = threading.Thread(target=reader, daemon=True)
    th.start()
    while p.poll() is None:
        if (cancel is not None and cancel.is_set()) or time.monotonic() - t0 > timeout:
            _kill_tree(p)
            th.join(2)
            return (130 if cancel is not None and cancel.is_set() else 124), "\n".join(out)
        time.sleep(0.05)
    th.join(5)
    return p.returncode, "\n".join(out)


def _kill_tree(p: subprocess.Popen) -> None:
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True,
                           creationflags=NO_WINDOW, timeout=15)
        else:
            p.kill()
    except (OSError, subprocess.SubprocessError):
        pass


@dataclass
class DeployResult:
    ok: bool
    message: str
    dry_run: bool = False
    url: str = ""
    signin_needed: bool = False
    hostkey: tuple = ()             # (key text, fingerprint) of an SSH server seen for the first time


def execute(steps: list[Step], log: Callable[[str], None] = print, cancel: threading.Event | None = None
            ) -> DeployResult:
    done: set[int] = set()
    res = _execute(steps, log, cancel, done)
    if not res.ok:
        for i, st in enumerate(steps):
            if st.always and i not in done and st.func:
                try:
                    st.func(log, None)
                except Exception:  # noqa: BLE001 - clean-up must not hide the real error
                    pass
    return res


def _execute(steps: list[Step], log, cancel, done: set[int]) -> DeployResult:
    url = ""
    for i, st in enumerate(steps, 1):
        done.add(i - 1)
        if cancel is not None and cancel.is_set():
            return DeployResult(False, "Cancelled.")
        log(f"--- [{i}/{len(steps)}] {st.title}")
        if st.argv:
            log("> " + st.describe())
            code, out = run_stream(st.argv, st.cwd, st.env, log, cancel, st.timeout, st.secrets)
            m = re.findall(r"https://[\w.-]+\.(?:vercel\.app|netlify\.app|azurewebsites\.net|onrender\.com|"
                           r"up\.railway\.app|github\.io|elasticbeanstalk\.com|amazonaws\.com)[^\s\"'<>]*", out)
            if m:
                url = m[-1]
            if code == 0 and st.fail_pattern and re.search(st.fail_pattern, out, re.I):
                code = 1
            if code == 127:
                return DeployResult(False, f"{st.argv[0]} was not found. {st.signin or ''}".strip())
            if code != 0:
                if st.signin:
                    return DeployResult(False, st.signin, signin_needed=True)
                if st.check:
                    return DeployResult(False, f"'{st.title}' failed (exit code {code}).")
                log(f"(exit code {code}, continuing)")
        elif st.func:
            try:
                res = st.func(log, cancel)
                if isinstance(res, str) and res.startswith("http"):
                    url = res
            except SignInRequired as ex:
                return DeployResult(False, str(ex), signin_needed=True)
            except DeployError as ex:
                return DeployResult(False, str(ex))
            except Exception as ex:  # noqa: BLE001 - report any failure of a step
                if hasattr(ex, "fingerprint") and hasattr(ex, "key"):      # publish.HostKeyUnknown
                    return DeployResult(False, f"The SSH server's host key is not trusted yet ({ex.fingerprint}).",
                                        hostkey=(ex.key, ex.fingerprint))
                return DeployResult(False, f"'{st.title}' failed: {ex}")
    return DeployResult(True, "Deployed." + (f" {url}" if url else ""), url=url)


# ====================================================================== tool discovery
def npm_cli_dir(name: str) -> Path:
    return dk.tools_root() / "npm-cli" / name


def find_npm_cli(name: str) -> list[str]:
    """Command prefix for an npm CLI: PATH, then RAD IDE's private install, else []."""
    p = shutil.which(name)
    if p:
        return [p]
    base = npm_cli_dir(name) / "node_modules" / ".bin"
    for cand in ((base / f"{name}.cmd"), (base / name)) if os.name == "nt" else ((base / name),):
        if cand.is_file():
            return [str(cand)]
    return []


def npx_cli(name: str) -> list[str]:
    npx = shutil.which("npx")
    return [npx, "--yes", NPM_CLI_VERSIONS.get(name, name)] if npx else []


def install_npm_cli(name: str, log: Callable[[str], None] = print, cancel=None) -> list[str]:
    """npm install --prefix %LOCALAPPDATA%\\RADIDE\\tools\\npm-cli\\<name> <package> (no global changes)."""
    npm = shutil.which("npm")
    if not npm:
        raise DeployError("npm was not found - install Node.js (https://nodejs.org) first.")
    d = npm_cli_dir(name)
    d.mkdir(parents=True, exist_ok=True)
    pkg = NPM_CLI_VERSIONS.get(name, name)
    code, out = run_stream([npm, "install", "--prefix", str(d), "--no-fund", "--no-audit", pkg], log=log,
                           cancel=cancel, timeout=1800)
    if code != 0:
        raise DeployError(f"npm install {pkg} failed (exit {code}).")
    found = find_npm_cli(name)
    if found:
        c, v = _quick(found + ["--version"])
        (d / "SOURCE.txt").write_text(f"npm package {pkg}\nversion {v.strip().splitlines()[-1] if v else '?'}\n",
                                      encoding="utf-8")
    return found


def _quick(argv: list[str], cwd: str = "", timeout: float = 60) -> tuple[int, str]:
    code, out, err = dk.run(argv, cwd=cwd or None, timeout=timeout, env=NONINTERACTIVE_ENV)
    return code, (out + ("\n" + err if err else "")).strip()


def git_exe() -> str:
    return shutil.which("git") or ""


def git_origin(folder) -> str:
    g = git_exe()
    if not g:
        return ""
    code, out = _quick([g, "-C", str(folder), "remote", "get-url", "origin"], timeout=15)
    return out.strip().splitlines()[0] if code == 0 and out.strip() else ""


def git_branch(folder) -> str:
    g = git_exe()
    if not g:
        return ""
    code, out = _quick([g, "-C", str(folder), "rev-parse", "--abbrev-ref", "HEAD"], timeout=15)
    return out.strip() if code == 0 else ""


def output_dir(folder, profile: DeployProfile | None = None) -> Path:
    """The folder to upload: the profile's folder, a build output folder (dist, build, out ...), the web root
    of a website project, else the project folder."""
    folder = Path(folder)
    if profile and profile.folder:
        return (folder / profile.folder).resolve()
    for n in BUILD_DIRS:
        if (folder / n).is_dir() and any((folder / n).iterdir()):
            return folder / n
    try:
        import json
        web = json.loads((folder / "project.radproj").read_text(encoding="utf-8")).get("web") or {}
        root = web.get("root") if isinstance(web, dict) else ""
        if root and root not in (".", ""):
            return (folder / root).resolve()
    except (OSError, ValueError):
        pass
    return folder


SKIP_UPLOAD = {".git", ".radide", ".radide_backup", "node_modules", "__pycache__", ".venv", "venv", ".vercel",
               ".netlify", ".idea", ".vscode", "project.radproj",
               # container files are for Docker, not for a static host
               "Dockerfile", ".dockerignore", "compose.yaml", "compose.yml", "docker-compose.yml",
               "docker-compose.yaml", ".devcontainer"}


def list_files(root: Path, excludes: list[str] | None = None, limit: int = 20000) -> list[str]:
    from ..web_site.publish import is_excluded
    ex = list(excludes or [])
    out = []
    for dp, dns, fns in os.walk(root):
        rel_dir = os.path.relpath(dp, root).replace("\\", "/")
        rel_dir = "" if rel_dir == "." else rel_dir
        dns[:] = sorted(d for d in dns if d not in SKIP_UPLOAD and not d.startswith(".radide")
                        and not is_excluded(posixpath.join(rel_dir, d), ex))
        for f in sorted(fns):
            rel = posixpath.join(rel_dir, f) if rel_dir else f
            if f in SKIP_UPLOAD or f.endswith((".radsln",)) or is_excluded(rel, ex):
                continue
            out.append(rel)
            if len(out) >= limit:
                return out
    return out


# ====================================================================== targets
@dataclass
class Field:
    key: str
    label: str
    kind: str = "text"          # text | bool | choice | password | multiline | int
    default: object = ""
    placeholder: str = ""
    tip: str = ""
    choices: tuple = ()


class Target:
    id = ""
    label = ""
    cli_name = ""                       # for messages
    signin_cmd = ""                     # what the user runs in the Terminal to sign in
    docs = ""
    fields: list[Field] = []
    npm = False                         # installable into a private npm prefix

    def tool(self) -> list[str]:
        return []

    def available(self) -> tuple[bool, str]:
        t = self.tool()
        if t:
            return True, f"{self.cli_name}: {t[0] if len(t) == 1 else ' '.join(t)}"
        return False, self.missing_hint()

    def missing_hint(self) -> str:
        return f"{self.cli_name} was not found."

    def signin_command(self) -> str:
        """The command the user runs to sign in (the private npm install when there is one)."""
        if self.npm and self.tool():
            return f'"{self.tool()[0]}" login'
        return self.signin_cmd.split("   ")[0]

    def signin_message(self) -> str:
        return (f"Sign in first: open View > Terminal and run `{self.signin_command()}` (RAD IDE never signs in to your "
                f"accounts), then deploy again.")

    def signin_check(self, profile: DeployProfile, folder: Path) -> Step | None:
        return None

    def config_files(self, profile: DeployProfile, folder: Path) -> dict[str, str]:
        return {}

    def steps(self, profile: DeployProfile, folder: Path, dry_run: bool, secrets: dict) -> list[Step]:
        raise NotImplementedError

    def preview_files(self, profile: DeployProfile, folder: Path) -> tuple[Path, list[str]]:
        root = output_dir(folder, profile)
        return root, list_files(root, profile.opt("excludes_list", []) or [])


def _build_step(profile: DeployProfile, folder: Path) -> list[Step]:
    if not profile.build_cmd.strip():
        return []
    argv = _split_cmd(profile.build_cmd)
    return [Step("Build", argv, cwd=str(folder))]


def _split_cmd(cmd: str) -> list[str]:
    argv = shlex.split(cmd, posix=os.name != "nt")
    if argv and os.name == "nt":
        argv = [a.strip('"') for a in argv]
        found = shutil.which(argv[0])
        if found:
            argv[0] = found
    return argv


class VercelTarget(Target):
    id, label, cli_name, signin_cmd = "vercel", "Vercel", "vercel", "npx vercel login"
    docs = "https://vercel.com/docs/cli/deploy"
    npm = True
    fields = [Field("project", "Project name", placeholder="(folder name)",
                    tip="Vercel project name (--name is deprecated; the first deploy links the folder)"),
              Field("scope", "Team / scope", placeholder="(personal account)"),
              Field("prebuilt", "Build locally (vercel build + --prebuilt)", "bool", False)]

    def tool(self):
        return find_npm_cli("vercel")

    def missing_hint(self):
        return ("vercel CLI not installed. Press 'Install CLI' (npm into RAD IDE's private folder) or it will be run "
                "with npx." if shutil.which("npx") else "vercel CLI needs Node.js (https://nodejs.org).")

    def _cmd(self):
        return self.tool() or npx_cli("vercel")

    def signin_check(self, profile, folder):
        return Step("Check Vercel sign-in", self._cmd() + ["whoami"], cwd=str(folder), signin=self.signin_message(),
                    timeout=180)

    def steps(self, profile, folder, dry_run, secrets):
        base = self._cmd()
        if not base:
            raise DeployError(self.missing_hint())
        cwd = str(output_dir(folder, profile) if profile.folder else folder)
        args = base + ["deploy", "--yes"]
        if profile.production:
            args.append("--prod")
        if profile.opt("scope"):
            args += ["--scope", profile.opt("scope")]
        st: list[Step] = []
        if profile.opt("prebuilt"):
            st.append(Step("vercel build", base + ["build"] + (["--prod"] if profile.production else []), cwd=cwd))
            args.append("--prebuilt")
        st.append(Step("vercel deploy", args, cwd=cwd))
        return _build_step(profile, folder) + st

    def config_files(self, profile, folder):
        return {"vercel.json": '{\n  "$schema": "https://openapi.vercel.sh/vercel.json",\n  "cleanUrls": true\n}\n'}


class NetlifyTarget(Target):
    id, label, cli_name, signin_cmd = "netlify", "Netlify", "netlify", "npx netlify-cli login"
    docs = "https://docs.netlify.com/cli/get-started/"
    npm = True
    fields = [Field("site", "Site ID / name", placeholder="(asked by `netlify link` the first time)",
                    tip="--site: the Netlify site to deploy to"),
              Field("message", "Deploy message", placeholder="Deployed from RAD IDE")]

    def tool(self):
        return find_npm_cli("netlify")

    def missing_hint(self):
        return ("netlify CLI not installed. Press 'Install CLI' (npm into RAD IDE's private folder) or it will be run "
                "with npx." if shutil.which("npx") else "netlify CLI needs Node.js (https://nodejs.org).")

    def _cmd(self):
        return self.tool() or npx_cli("netlify")

    def signin_check(self, profile, folder):
        return Step("Check Netlify sign-in", self._cmd() + ["status"], cwd=str(folder), signin=self.signin_message(),
                    timeout=180, fail_pattern=r"not logged in")

    def steps(self, profile, folder, dry_run, secrets):
        base = self._cmd()
        if not base:
            raise DeployError(self.missing_hint())
        out = output_dir(folder, profile)
        args = base + ["deploy", "--dir", str(out), "--message", profile.opt("message", "Deployed from RAD IDE")]
        if profile.production:
            args.append("--prod")
        if profile.opt("site"):
            args += ["--site", profile.opt("site")]
        args.append("--json")
        return _build_step(profile, folder) + [Step("netlify deploy", args, cwd=str(folder))]

    def config_files(self, profile, folder):
        out = output_dir(folder, profile)
        rel = os.path.relpath(out, folder).replace("\\", "/")
        build = profile.build_cmd.strip()
        text = "[build]\n" + (f'  command = "{build}"\n' if build else "") + f'  publish = "{rel}"\n'
        return {"netlify.toml": "# generated by RAD IDE\n" + text}


class GitHubPagesTarget(Target):
    id, label, cli_name, signin_cmd = "ghpages", "GitHub Pages", "git", "gh auth login"
    docs = "https://docs.github.com/pages"
    fields = [Field("remote", "Repository URL", placeholder="(the project's 'origin' remote)",
                    tip="git URL to push to, e.g. https://github.com/you/site.git (or a local path)"),
              Field("branch", "Branch", default="gh-pages"),
              Field("cname", "Custom domain (CNAME)", placeholder="www.example.com"),
              Field("message", "Commit message", default="Deploy from RAD IDE")]

    def tool(self):
        g = git_exe()
        return [g] if g else []

    def missing_hint(self):
        return "git was not found (https://git-scm.com)."

    def remote(self, profile, folder) -> str:
        return profile.opt("remote") or git_origin(folder)

    def signin_check(self, profile, folder):
        remote = self.remote(profile, folder)
        if not remote or not self.tool():
            return None
        return Step("Check access to the repository", self.tool() + ["ls-remote", "--heads", remote],
                    signin=("Cannot read the repository. Sign in first: run `gh auth login` (or set up your git "
                            "credentials) in the Terminal, and check the repository URL."), timeout=120)

    def steps(self, profile, folder, dry_run, secrets):
        g = git_exe()
        if not g:
            raise DeployError(self.missing_hint())
        remote = self.remote(profile, folder)
        if not remote:
            raise DeployError("No repository: set 'Repository URL' or add an 'origin' remote to the project.")
        src = output_dir(folder, profile)
        branch = profile.opt("branch", "gh-pages")

        def push(log, cancel):
            return ghpages_push(src, remote, branch, profile.opt("message", "Deploy from RAD IDE"),
                                profile.opt("cname"), log, cancel, dry_run=dry_run)
        return _build_step(profile, folder) + [Step(f"Push {src.name}/ to {branch}", func=push)]


def ghpages_push(src: Path, remote: str, branch: str = "gh-pages", message: str = "Deploy from RAD IDE",
                 cname: str = "", log=print, cancel=None, dry_run: bool = False) -> str:
    """Copies `src` into a fresh temporary repository and force-pushes it as `branch` of `remote`
    (the usual gh-pages workflow: the branch only holds the built site)."""
    g = git_exe()
    files = list_files(Path(src))
    if not files:
        raise DeployError(f"Nothing to publish in {src}.")
    log(f"{len(files)} file(s) from {src}")
    if dry_run:
        for f in files[:200]:
            log("  + " + f)
        log(f"(dry run) would push them to {remote} branch {branch}")
        return ""
    tmp = Path(tempfile.mkdtemp(prefix="radide-ghpages-"))
    try:
        for rel in files:
            dst = tmp / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(Path(src) / rel, dst)
        (tmp / ".nojekyll").write_text("", encoding="utf-8")
        if cname:
            (tmp / "CNAME").write_text(cname.strip() + "\n", encoding="utf-8")
        ident = []
        c, name = _quick([g, "config", "user.name"])
        if c != 0 or not name.strip():
            ident += ["-c", "user.name=RAD IDE"]
        c, mail = _quick([g, "config", "user.email"])
        if c != 0 or not mail.strip():
            ident += ["-c", "user.email=radide@localhost"]
        for argv in ([g, "init", "-q"], [g, "checkout", "-q", "-b", branch], [g, "add", "-A"],
                     [g, *ident, "commit", "-q", "-m", message]):
            code, out = run_stream(argv, str(tmp), log=log, cancel=cancel, timeout=300)
            if code != 0:
                raise DeployError(f"{' '.join(argv[1:3])} failed: {out[-300:]}")
        code, out = run_stream([g, "push", "--force", remote, f"{branch}:{branch}"], str(tmp), log=log,
                               cancel=cancel, timeout=900)
        if code != 0:
            if re.search(r"auth|denied|403|401|credential|could not read Username", out, re.I):
                raise SignInRequired("git push was refused. Sign in first: run `gh auth login` (or set up your "
                                     "git credentials) in the Terminal, then deploy again.")
            raise DeployError(f"git push failed (exit {code}).")
        m = re.match(r"(?:https://github\.com/|git@github\.com:)([^/]+)/([^/.]+)", remote)
        return f"https://{m.group(1)}.github.io/{m.group(2)}/" if m else ""
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


AZURE_RUNTIMES = ("PYTHON:3.12", "PYTHON:3.11", "NODE:22-lts", "NODE:20-lts", "PHP:8.3", "PHP:8.2",
                  "DOTNETCORE:9.0", "DOTNETCORE:8.0", "JAVA:21-java21", "JAVA:17-java17")


class AzureTarget(Target):
    id, label, cli_name, signin_cmd = "azure", "Azure App Service", "az", "az login"
    docs = "https://learn.microsoft.com/cli/azure/webapp#az-webapp-up"
    fields = [Field("app", "App name", placeholder="my-site (becomes my-site.azurewebsites.net)"),
              Field("group", "Resource group", placeholder="(created / chosen by az webapp up)"),
              Field("runtime", "Runtime", "choice", "", choices=("",) + AZURE_RUNTIMES,
                    tip="empty = detected by az webapp up"),
              Field("sku", "Plan (SKU)", "choice", "F1", choices=("F1", "B1", "B2", "S1", "P1V3")),
              Field("location", "Region", placeholder="westeurope")]

    def tool(self):
        p = shutil.which("az")
        if not p and os.name == "nt":
            for base in (os.environ.get("ProgramFiles", ""), os.environ.get("ProgramFiles(x86)", "")):
                c = Path(base) / "Microsoft SDKs" / "Azure" / "CLI2" / "wbin" / "az.cmd"
                if base and c.is_file():
                    p = str(c)
        return [p] if p else []

    def missing_hint(self):
        return ("Azure CLI (az) not found. Install it from https://aka.ms/installazurecliwindows "
                "(or `pip install azure-cli` into your own Python), then run `az login` in the Terminal.")

    def signin_check(self, profile, folder):
        if not self.tool():
            return None
        return Step("Check Azure sign-in", self.tool() + ["account", "show", "--output", "none"],
                    signin=self.signin_message(), timeout=120)

    def steps(self, profile, folder, dry_run, secrets):
        az = self.tool()
        if not az:
            raise DeployError(self.missing_hint())
        if not profile.opt("app"):
            raise DeployError("Set the App name.")
        args = az + ["webapp", "up", "--name", profile.opt("app"), "--sku", profile.opt("sku", "F1")]
        for k, flag in (("group", "--resource-group"), ("runtime", "--runtime"), ("location", "--location")):
            if profile.opt(k):
                args += [flag, profile.opt(k)]
        if dry_run:
            args.append("--dryrun")
        return _build_step(profile, folder) + [Step("az webapp up" + (" --dryrun" if dry_run else ""), args,
                                                    cwd=str(output_dir(folder, profile) if profile.folder else folder))]


class AwsTarget(Target):
    id, label, cli_name, signin_cmd = "aws", "AWS (Elastic Beanstalk / S3)", "aws", "aws configure sso   (or aws configure)"
    docs = "https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/eb-cli3.html"
    fields = [Field("mode", "Service", "choice", "eb", choices=("eb", "s3"),
                    tip="eb = Elastic Beanstalk app; s3 = static site in an S3 bucket"),
              Field("application", "EB application", placeholder="my-app"),
              Field("environment", "EB environment", placeholder="my-app-env"),
              Field("bucket", "S3 bucket", placeholder="EB: bucket for the source bundle; S3: the site bucket"),
              Field("region", "Region", placeholder="eu-west-1"),
              Field("aws_profile", "AWS profile", placeholder="(default)")]

    def tool(self):
        p = shutil.which("aws")
        if not p and os.name == "nt":
            c = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Amazon" / "AWSCLIV2" / "aws.exe"
            if c.is_file():
                p = str(c)
        return [p] if p else []

    def eb(self):
        p = shutil.which("eb")
        return [p] if p else []

    def available(self):
        if self.tool() or self.eb():
            return True, "aws: " + " / ".join(x[0] for x in (self.tool(), self.eb()) if x)
        return False, self.missing_hint()

    def missing_hint(self):
        return ("AWS CLI not found. Install it from https://aws.amazon.com/cli/ (or the EB CLI: `pip install "
                "awsebcli`), then run `aws configure sso` in the Terminal.")

    def _common(self, profile):
        a = []
        if profile.opt("region"):
            a += ["--region", profile.opt("region")]
        if profile.opt("aws_profile"):
            a += ["--profile", profile.opt("aws_profile")]
        return a

    def signin_check(self, profile, folder):
        if not self.tool():
            return None
        return Step("Check AWS sign-in", self.tool() + ["sts", "get-caller-identity"] + self._common(profile),
                    signin=self.signin_message(), timeout=120)

    def steps(self, profile, folder, dry_run, secrets):
        mode = profile.opt("mode", "eb")
        aws, eb = self.tool(), self.eb()
        build = _build_step(profile, folder)
        if mode == "s3":
            if not aws:
                raise DeployError(self.missing_hint())
            if not profile.opt("bucket"):
                raise DeployError("Set the S3 bucket.")
            args = aws + ["s3", "sync", str(output_dir(folder, profile)), f"s3://{profile.opt('bucket')}", "--delete",
                          "--exclude", ".git/*", "--exclude", "project.radproj"] + self._common(profile)
            if dry_run:
                args.append("--dryrun")
            return build + [Step("aws s3 sync", args)]
        env = profile.opt("environment")
        if not env:
            raise DeployError("Set the Elastic Beanstalk environment.")
        if eb and (Path(folder) / ".elasticbeanstalk").is_dir():
            if dry_run:
                return build + [Step("eb status (dry run)", eb + ["status", env], cwd=str(folder))]
            return build + [Step("eb deploy", eb + ["deploy", env, "--label", f"radide-{int(time.time())}"],
                                 cwd=str(folder))]
        if not aws:
            raise DeployError(self.missing_hint())
        app, bucket = profile.opt("application"), profile.opt("bucket")
        if not app or not bucket:
            raise DeployError("Set the EB application and an S3 bucket for the source bundle (or run `eb init` once "
                              "in the project folder to use the EB CLI).")
        label = f"radide-{time.strftime('%Y%m%d-%H%M%S')}"
        zip_path = Path(tempfile.gettempdir()) / f"{label}.zip"
        src = output_dir(folder, profile) if profile.folder else Path(folder)

        def make_zip(log, cancel):
            n = zip_folder(src, zip_path)
            log(f"source bundle {zip_path} ({n} files)")
        steps = [Step("Make the source bundle", func=make_zip),
                 Step("Upload the bundle", aws + ["s3", "cp", str(zip_path), f"s3://{bucket}/{label}.zip"]
                      + self._common(profile) + (["--dryrun"] if dry_run else [])),
                 ]
        if not dry_run:
            steps += [Step("Create the application version", aws + [
                          "elasticbeanstalk", "create-application-version", "--application-name", app,
                          "--version-label", label, "--source-bundle", f"S3Bucket={bucket},S3Key={label}.zip"]
                          + self._common(profile)),
                      Step("Update the environment", aws + [
                          "elasticbeanstalk", "update-environment", "--environment-name", env,
                          "--version-label", label] + self._common(profile))]
        return build + steps


def zip_folder(src: Path, dest: Path) -> int:
    files = list_files(Path(src))
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in files:
            z.write(Path(src) / rel, rel)
    return len(files)


class GitPushTarget(Target):
    """Render / Railway: the service builds from the git repository connected in its dashboard."""
    id, label, cli_name = "render", "Render (git push)", "git"
    signin_cmd = "gh auth login"
    service = "Render"
    fields = [Field("remote", "Git remote", default="origin", tip="remote name or URL connected to the service"),
              Field("branch", "Branch", placeholder="(current branch)"),
              Field("hook_url", "Deploy hook URL (secret)", "password",
                    tip="Render: Settings > Deploy Hook. Optional - triggers a deploy without a push. Kept in your "
                        "user settings, never in the project.")]

    def tool(self):
        g = git_exe()
        return [g] if g else []

    def signin_check(self, profile, folder):
        g = self.tool()
        if not g:
            return None
        return Step("Check access to the git remote", g + ["-C", str(folder), "ls-remote", "--heads",
                                                          profile.opt("remote", "origin")],
                    signin=("Cannot reach the git remote. Sign in first: run `gh auth login` (or set up your git "
                            f"credentials) in the Terminal, and connect the repository in the {self.service} "
                            "dashboard."), timeout=120)

    def steps(self, profile, folder, dry_run, secrets):
        g = self.tool()
        if not g:
            raise DeployError("git was not found.")
        if not (Path(folder) / ".git").exists():
            raise DeployError("The project is not a git repository: Git > Initialize, commit, add the remote that "
                              f"{self.service} watches, then deploy.")
        branch = profile.opt("branch") or git_branch(folder) or "main"
        args = g + ["-C", str(folder), "push", profile.opt("remote", "origin"), f"HEAD:{branch}"]
        if dry_run:
            args.insert(4, "--dry-run")
        steps = [Step(f"git push to {self.service}", args)]
        hook = secrets.get("hook_url", "")
        if hook:
            def trigger(log, cancel):
                if dry_run:
                    log("(dry run) would POST the deploy hook")
                    return ""
                req = urllib.request.Request(hook, data=b"", method="POST", headers={"User-Agent": "RAD-IDE"})
                with urllib.request.urlopen(req, timeout=60) as r:
                    log(f"deploy hook: HTTP {r.status}")
                return ""
            steps.append(Step("Trigger the deploy hook", func=trigger))
        return steps

    def config_files(self, profile, folder):
        st = dk.detect_stack(folder)
        env = {"python": "python", "node": "node", "php": "docker", "static": "static", "dotnet": "docker",
               "java": "docker", "rails": "ruby", "go": "go"}.get(dk.FAMILY.get(st.kind, ""), "docker")
        name = re.sub(r"[^a-z0-9-]", "-", Path(folder).name.lower())
        lines = ["# generated by RAD IDE - Render Blueprint (https://render.com/docs/blueprint-spec)", "services:"]
        if env == "static":
            lines += ["  - type: web", f"    name: {name}", "    runtime: static",
                      f"    staticPublishPath: {os.path.relpath(output_dir(folder, profile), folder).replace(chr(92), '/')}"]
            if profile.build_cmd:
                lines.append(f"    buildCommand: {profile.build_cmd}")
        else:
            lines += ["  - type: web", f"    name: {name}", f"    runtime: {env}", "    plan: free"]
            if env == "python":
                start = {"django": f"gunicorn {st.details.get('wsgi')}",
                         "fastapi": f"uvicorn {st.details.get('module')}:{st.details.get('app')} --host 0.0.0.0 "
                                    "--port $PORT"}.get(st.kind, f"gunicorn {st.details.get('module', 'app')}:"
                                                                 f"{st.details.get('app', 'app')}")
                lines += ["    buildCommand: pip install -r requirements.txt", f"    startCommand: {start}"]
            elif env == "node":
                lines += ["    buildCommand: npm install" + (" && npm run build" if st.details.get("has_build") else ""),
                          "    startCommand: npm start"]
        return {"render.yaml": "\n".join(lines) + "\n"}


class RailwayTarget(GitPushTarget):
    id, label, service = "railway", "Railway", "Railway"
    signin_cmd = "railway login   (or gh auth login for git push)"
    fields = [Field("use_cli", "Use the Railway CLI (railway up) when installed", "bool", True),
              Field("service_name", "Service", placeholder="(linked service)"),
              Field("remote", "Git remote", default="origin"),
              Field("branch", "Branch", placeholder="(current branch)")]

    def railway(self):
        p = shutil.which("railway")
        return [p] if p else []

    def available(self):
        if self.railway():
            return True, f"railway CLI: {self.railway()[0]}"
        return (bool(self.tool()), "railway CLI not found (npm i -g @railway/cli); deploying by git push to the "
                                   "repository Railway watches." if self.tool() else "git was not found.")

    def signin_check(self, profile, folder):
        if profile.opt("use_cli", True) and self.railway():
            return Step("Check Railway sign-in", self.railway() + ["whoami"], cwd=str(folder),
                        signin="Sign in first: run `railway login` in the Terminal (RAD IDE never signs in for you).",
                        timeout=60)
        return super().signin_check(profile, folder)

    def steps(self, profile, folder, dry_run, secrets):
        if profile.opt("use_cli", True) and self.railway():
            args = self.railway() + ["up", "--detach"]
            if profile.opt("service_name"):
                args += ["--service", profile.opt("service_name")]
            if dry_run:
                return [Step("railway status (dry run)", self.railway() + ["status"], cwd=str(folder), check=False),
                        Step("would run", func=lambda log, c: log("(dry run) " + " ".join(args)))]
            return _build_step(profile, folder) + [Step("railway up", args, cwd=str(folder))]
        return super().steps(profile, folder, dry_run, secrets)

    def config_files(self, profile, folder):
        return {"railway.json": '{\n  "$schema": "https://railway.com/railway.schema.json",\n'
                                '  "build": { "builder": "NIXPACKS" },\n  "deploy": { "restartPolicyType": '
                                '"ON_FAILURE" }\n}\n'}


class SshTarget(Target):
    id, label, cli_name, signin_cmd = "ssh", "SSH server (rsync / SFTP + restart)", "ssh", "ssh-copy-id / a key file"
    fields = [Field("host", "Server", placeholder="example.com"),
              Field("port", "Port", "int", 22),
              Field("user", "User name", placeholder="deploy"),
              Field("password", "Password (secret)", "password", tip="or leave empty and use a key file / agent"),
              Field("key_file", "Key file", placeholder="(optional) C:\\Users\\you\\.ssh\\id_ed25519"),
              Field("remote_dir", "Remote folder", default="/var/www/app"),
              Field("method", "Upload with", "choice", "auto", choices=("auto", "sftp", "rsync"),
                    tip="auto = rsync when rsync and ssh are installed, else SFTP (incremental)"),
              Field("delete_removed", "Delete remote files removed locally", "bool", False),
              Field("before_cmds", "Commands before upload", "multiline", placeholder="(optional)"),
              Field("restart_cmds", "Commands after upload", "multiline",
                    placeholder="cd /var/www/app && pip install -r requirements.txt\nsudo systemctl restart app",
                    tip="one per line, run on the server over SSH; a failing command stops the deploy"),
              Field("host_key", "Trusted host key", placeholder="(trusted on first connection)")]

    def tool(self):
        from ..web_site.publish import paramiko_available
        return ["paramiko"] if paramiko_available() else []

    def available(self):
        if self.tool():
            r = " + rsync" if self.rsync() else ""
            return True, f"SFTP (paramiko){r}"
        return False, "SSH deploy needs the 'paramiko' package (pip install paramiko)."

    def rsync(self) -> list[str]:
        r, s = shutil.which("rsync"), shutil.which("ssh")
        return [r, s] if r and s else []

    def publish_profile(self, profile: DeployProfile, folder: Path):
        from ..web_site import publish as pub
        p = pub.PublishProfile(name="deploy:" + profile.name, kind="sftp", host=profile.opt("host"),
                               port=int(profile.opt("port", 22) or 22), user=profile.opt("user"),
                               remote_dir=profile.opt("remote_dir", "/var/www/app"),
                               key_file=profile.opt("key_file"), host_key=profile.opt("host_key"),
                               delete_removed=bool(profile.opt("delete_removed", False)))
        root = output_dir(folder, profile)
        p.local_dir = os.path.relpath(root, folder) if root != Path(folder) else ""
        p.excludes = list(pub.DEFAULT_EXCLUDES) + ["node_modules", ".venv", "venv", ".env"]
        return p

    def connect(self, profile: DeployProfile, password: str | None):
        """A connected paramiko SSHClient (same host-key rules as Publish > SFTP)."""
        from ..web_site import publish as pub
        t = pub.SftpTarget(self.publish_profile(profile, Path(".")), password)
        t.connect()
        return t

    def steps(self, profile, folder, dry_run, secrets):
        if not profile.opt("host"):
            raise DeployError("Set the server.")
        if not self.tool():
            raise DeployError(self.available()[1])
        from ..web_site import publish as pub
        password = secrets.get("password") or None
        pp = self.publish_profile(profile, folder)
        root = output_dir(folder, profile)
        before = [c.strip() for c in str(profile.opt("before_cmds", "")).splitlines() if c.strip()]
        after = [c.strip() for c in str(profile.opt("restart_cmds", "")).splitlines() if c.strip()]
        steps = _build_step(profile, folder)
        holder: dict = {}

        def connect(log, cancel):
            holder["t"] = self.connect(profile, password)
            log(f"connected to {holder['t'].describe()}")

        def remote(cmds, title):
            def fn(log, cancel):
                if dry_run:
                    for c in cmds:
                        log(f"(dry run) ssh $ {c}")
                    return ""
                if "t" not in holder:
                    connect(log, cancel)
                for c in cmds:
                    code = ssh_exec(holder["t"].client, c, log, cancel)
                    if code != 0:
                        raise DeployError(f"Remote command failed (exit {code}): {c}")
                return ""
            return Step(title, func=fn)

        if not dry_run:
            steps.append(Step("Connect", func=connect))
        if before:
            steps.append(remote(before, "Commands before upload"))
        method = profile.opt("method", "auto")
        use_rsync = method == "rsync" or (method == "auto" and self.rsync() and not password)
        if use_rsync and self.rsync():
            rs, ssh = self.rsync()
            port = int(profile.opt("port", 22) or 22)
            e = f"{ssh} -p {port}" + (f" -i {profile.opt('key_file')}" if profile.opt("key_file") else "")
            args = [rs, "-az", "--itemize-changes", "-e", e] + (["--delete"] if profile.opt("delete_removed") else []) \
                + (["--dry-run"] if dry_run else [])
            for ex in pp.excludes:
                args += ["--exclude", ex]
            dest = f"{profile.opt('user') + '@' if profile.opt('user') else ''}{profile.opt('host')}:" \
                   f"{profile.opt('remote_dir', '/var/www/app').rstrip('/')}/"
            steps.append(Step("rsync", args + [str(root).replace("\\", "/") + "/", dest]))
        else:
            if method == "rsync":
                raise DeployError("rsync / ssh were not found - choose SFTP or 'auto'.")

            def upload(log, cancel):
                pub_ = pub.Publisher(pp, root, pub.cache_file_for(folder, pp.name), password)
                if "t" in holder:
                    pub_.target_factory = lambda _p, _pw=None: _Reuse(holder["t"])
                finished = threading.Event()

                def watch_cancel():
                    while not finished.wait(0.3):
                        if cancel is not None and cancel.is_set():
                            pub_.cancel()
                            return
                if cancel is not None:
                    threading.Thread(target=watch_cancel, daemon=True).start()
                try:
                    res = pub_.run(dry_run=dry_run, log=log)
                finally:
                    finished.set()
                if not res.ok or res.error:
                    raise DeployError(res.error or "upload failed: " + "; ".join(f"{a}: {b}" for a, b in res.failed[:3]))
                return ""
            steps.append(Step("Upload (SFTP, changed files only)", func=upload))
        if after:
            steps.append(remote(after, "Commands after upload"))

        def close(log, cancel):
            t = holder.pop("t", None)
            if t is not None:
                t.close()
            return profile.site_url or ""
        steps.append(Step("Disconnect", func=close, always=True))
        return steps

    def preview_files(self, profile, folder):
        return output_dir(folder, profile), []


class _Reuse:
    """Wraps an already connected SftpTarget so Publisher does not open a second connection."""
    def __init__(self, t):
        self.t = t

    def __getattr__(self, n):
        return getattr(self.t, n)

    def connect(self):
        pass

    def close(self):
        pass


def ssh_exec(client, command: str, log=print, cancel=None, timeout: float = 1800) -> int:
    """Runs a command over SSH, streams its output, returns the exit status."""
    log(f"ssh $ {command}")
    transport = client.get_transport()
    chan = transport.open_session()
    chan.set_combine_stderr(True)
    chan.exec_command(command)
    buf = b""
    t0 = time.monotonic()
    while True:
        if chan.recv_ready():
            buf += chan.recv(65536)
            *lines, buf = buf.split(b"\n")
            for ln in lines:
                log(ln.decode("utf-8", "replace").rstrip("\r"))
        elif chan.exit_status_ready() and not chan.recv_ready():
            break
        else:
            if (cancel is not None and cancel.is_set()) or time.monotonic() - t0 > timeout:
                chan.close()
                return 130
            time.sleep(0.03)
    if buf:
        log(buf.decode("utf-8", "replace").rstrip("\r"))
    code = chan.recv_exit_status()
    chan.close()
    return code


TARGETS: dict[str, Target] = {t.id: t for t in (VercelTarget(), NetlifyTarget(), GitHubPagesTarget(), AzureTarget(),
                                                AwsTarget(), GitPushTarget(), RailwayTarget(), SshTarget())}


def target(tid: str) -> Target:
    return TARGETS[tid]


def plan(profile: DeployProfile, folder, dry_run: bool = False, secrets: dict | None = None,
         check_signin: bool = True) -> list[Step]:
    """The steps of a deploy: a sign-in check (read-only) + the deploy itself."""
    t = target(profile.target)
    folder = Path(folder)
    steps: list[Step] = []
    if check_signin:
        s = t.signin_check(profile, folder)
        if s is not None:
            steps.append(s)
    return steps + t.steps(profile, folder, dry_run, dict(secrets or {}))


def preview_text(profile: DeployProfile, folder, secrets: dict | None = None) -> str:
    """Human readable dry run without running anything: commands + files."""
    t = target(profile.target)
    folder = Path(folder)
    ok, status = t.available()
    lines = [f"Target: {t.label}", f"Tool: {status}", ""]
    try:
        steps = plan(profile, folder, dry_run=False, secrets=secrets)
    except DeployError as ex:
        return "\n".join(lines + [f"Cannot deploy yet: {ex}"])
    lines.append("Steps:")
    for i, s in enumerate(steps, 1):
        lines.append(f"  {i}. {s.title}: {s.describe()}")
    root, files = t.preview_files(profile, folder)
    if files:
        lines += ["", f"Files from {root} ({len(files)}):"] + [f"  {f}" for f in files[:300]]
        if len(files) > 300:
            lines.append(f"  ... and {len(files) - 300} more")
    if t.signin_cmd:
        lines += ["", f"Sign-in: RAD IDE only checks it. If needed run `{t.signin_cmd}` in the Terminal."]
    return "\n".join(lines)


def deploy(profile: DeployProfile, folder, dry_run: bool = False, secrets: dict | None = None,
           log: Callable[[str], None] = print, cancel: threading.Event | None = None,
           check_signin: bool = True) -> DeployResult:
    try:
        steps = plan(profile, folder, dry_run, secrets, check_signin=check_signin)
    except DeployError as ex:
        return DeployResult(False, str(ex), dry_run)
    r = execute(steps, log, cancel)
    r.dry_run = dry_run
    if r.ok and dry_run:
        r.message = "Dry run finished - nothing was changed."
    if r.ok and not r.url and profile.site_url:
        r.url = profile.site_url
    return r
