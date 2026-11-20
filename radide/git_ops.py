"""Git operations behind the full Git client (radide/features/git_full.py) - no Qt in here, so
everything can be tested on temporary repositories:

  branches / remotes / tags / stashes (list + actions), repository state (merge, rebase, cherry-pick,
  revert in progress), conflicts and the 3-way merge segments, commit graph lanes, blame, compare with a
  commit, friendly explanations of network / authentication errors, .gitignore templates and the GitHub
  CLI (gh) - finding it and downloading the official portable zip into %LOCALAPPDATA%\\RADIDE\\tools\\gh.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from .features.git_panel import Git, find_git

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
US = "\x1f"


# ===================================================================== running git
class GitX(Git):
    """Git with the extra commands of a full client. Every command runs non-interactively: no
    credential prompt (GIT_TERMINAL_PROMPT=0) and no editor (GIT_EDITOR=true), so a merge / rebase
    --continue never hangs the IDE."""

    def run(self, *args: str, stdin: str | None = None, timeout: int = 60) -> tuple[int, str]:
        if not self.exe:
            return -1, "git was not found"
        env = dict(os.environ, GIT_TERMINAL_PROMPT="0", LC_ALL="C.UTF-8", GIT_EDITOR="true",
                   GIT_SEQUENCE_EDITOR="true", GIT_MERGE_AUTOEDIT="no", GCM_INTERACTIVE="never")
        try:
            r = subprocess.run([self.exe, "-c", "core.quotepath=false", "-c", "color.ui=never", *args],
                               cwd=str(self.folder), input=stdin.encode("utf-8") if stdin is not None else None,
                               capture_output=True, timeout=timeout, env=env, creationflags=NO_WINDOW)
        except (OSError, subprocess.TimeoutExpired) as e:
            return -1, str(e)
        out = (r.stdout + (b"\n" + r.stderr if r.stderr else b"")).decode("utf-8", errors="replace")
        return r.returncode, out.replace("\r\n", "\n")

    def raw(self, *args: str) -> tuple[int, bytes]:
        """stdout as bytes (file contents at a revision)."""
        if not self.exe:
            return -1, b""
        try:
            r = subprocess.run([self.exe, *args], cwd=str(self.folder), capture_output=True, timeout=60,
                               creationflags=NO_WINDOW, env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
        except (OSError, subprocess.TimeoutExpired):
            return -1, b""
        return r.returncode, r.stdout

    def stdout(self, *args: str) -> str:
        """Only stdout (stderr warnings must not end up in parsed output)."""
        if not self.exe:
            return ""
        try:
            r = subprocess.run([self.exe, "-c", "core.quotepath=false", "-c", "color.ui=never", *args],
                               cwd=str(self.folder), capture_output=True, timeout=60, creationflags=NO_WINDOW,
                               env=dict(os.environ, GIT_TERMINAL_PROMPT="0", LC_ALL="C.UTF-8"))
        except (OSError, subprocess.TimeoutExpired):
            return ""
        return r.stdout.decode("utf-8", errors="replace").replace("\r\n", "\n") if r.returncode == 0 else ""

    # ------------------------------------------------------------ repository state
    def git_dir(self) -> Path | None:
        d = self.out("rev-parse", "--absolute-git-dir")
        return Path(d.splitlines()[0]) if d else None

    def has_commits(self) -> bool:
        return bool(self.out("rev-parse", "--verify", "-q", "HEAD"))

    def state(self) -> str:
        """'' | 'merge' | 'rebase' | 'cherry-pick' | 'revert'"""
        d = self.git_dir()
        if d is None:
            return ""
        if (d / "rebase-merge").is_dir() or (d / "rebase-apply").is_dir():
            return "rebase"
        if (d / "MERGE_HEAD").exists():
            return "merge"
        if (d / "CHERRY_PICK_HEAD").exists():
            return "cherry-pick"
        if (d / "REVERT_HEAD").exists():
            return "revert"
        return ""

    def merge_message(self) -> str:
        d = self.git_dir()
        try:
            text = (d / "MERGE_MSG").read_text(encoding="utf-8", errors="replace") if d else ""
        except OSError:
            return ""
        return "\n".join(l for l in text.splitlines() if not l.startswith("#")).strip()

    def conflicts(self) -> list[str]:
        return [l for l in self.stdout("diff", "--name-only", "--diff-filter=U").splitlines() if l.strip()]

    def abort(self) -> tuple[int, str]:
        st = self.state()
        if not st:
            return 0, "nothing to abort"
        return self.run(st, "--abort")

    def continue_(self) -> tuple[int, str]:
        st = self.state()
        if not st:
            return 0, "nothing to continue"
        if self.conflicts():
            return 1, "There are still unresolved conflicts. Resolve them (and mark them resolved) first."
        if st == "merge":
            return self.run("commit", "--no-edit")
        return self.run(st, "--continue")

    # ------------------------------------------------------------ branches
    def branches(self) -> list["Branch"]:
        fmt = US.join(["%(refname)", "%(refname:short)", "%(upstream:short)", "%(upstream:track)",
                       "%(objectname:short)", "%(committerdate:relative)", "%(subject)", "%(HEAD)"])
        fmt = fmt.replace(US, "%1f")
        out = []
        for line in self.stdout("for-each-ref", f"--format={fmt}", "refs/heads", "refs/remotes").splitlines():
            parts = line.split(US)
            if len(parts) != 8 or parts[0].endswith("/HEAD"):
                continue
            ref, short, up, track, sha, date, subj, head = parts
            out.append(Branch(short, ref.startswith("refs/remotes/"), up, track.strip("[]"), sha, date, subj,
                              head == "*"))
        return out

    def create_branch(self, name: str, start: str = "", checkout: bool = True, track: bool = False):
        if checkout:
            args = ["checkout", "-b", name] + (["--track"] if track else []) + ([start] if start else [])
        else:
            args = ["branch"] + (["--track"] if track else []) + [name] + ([start] if start else [])
        return self.run(*args)

    def switch(self, name: str, remote: bool = False):
        if remote:                          # origin/feature -> local feature tracking it
            local = name.split("/", 1)[1] if "/" in name else name
            if any(b.name == local and not b.remote for b in self.branches()):
                return self.run("checkout", local)
            return self.run("checkout", "-b", local, "--track", name)
        return self.run("checkout", name)

    def rename_branch(self, old: str, new: str):
        return self.run("branch", "-m", old, new)

    def delete_branch(self, name: str, force: bool = False):
        return self.run("branch", "-D" if force else "-d", name)

    def set_upstream(self, branch: str, upstream: str):
        return self.run("branch", f"--set-upstream-to={upstream}", branch)

    def unset_upstream(self, branch: str):
        return self.run("branch", "--unset-upstream", branch)

    def merge(self, ref: str, no_ff: bool = False, squash: bool = False):
        args = ["merge"] + (["--no-ff"] if no_ff else []) + (["--squash"] if squash else []) + [ref]
        return self.run(*args)

    def rebase(self, onto: str):
        return self.run("rebase", onto)

    def remote_urls(self) -> dict[str, str]:
        out = {}
        for line in self.stdout("remote", "-v").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] not in out:
                out[parts[0]] = parts[1]
        return out

    def add_remote(self, name: str, url: str):
        return self.run("remote", "add", name, url)

    def remove_remote(self, name: str):
        return self.run("remote", "remove", name)

    # ------------------------------------------------------------ tags
    def tags(self) -> list[tuple[str, str, str, str]]:
        """(name, commit, date, message)"""
        fmt = "%(refname:short)%1f%(objectname:short)%1f%(*objectname:short)%1f%(creatordate:short)%1f%(contents:subject)"
        out = []
        for line in self.stdout("for-each-ref", "--sort=-creatordate", f"--format={fmt}", "refs/tags").splitlines():
            p = line.split(US)
            if len(p) == 5:
                out.append((p[0], p[2] or p[1], p[3], p[4]))
        return out

    def create_tag(self, name: str, commit: str = "", message: str = ""):
        args = ["tag"] + (["-a", "-m", message] if message else []) + [name] + ([commit] if commit else [])
        return self.run(*args)

    def delete_tag(self, name: str):
        return self.run("tag", "-d", name)

    # ------------------------------------------------------------ stashes
    def stashes(self) -> list[tuple[str, str, str]]:
        """(stash@{n}, when, message)"""
        out = []
        for line in self.stdout("stash", "list", "--format=%gd%x1f%cr%x1f%gs").splitlines():
            p = line.split(US)
            if len(p) == 3:
                out.append((p[0], p[1], p[2]))
        return out

    def stash_save(self, message: str = "", untracked: bool = True, keep_index: bool = False):
        args = ["stash", "push"] + (["-u"] if untracked else []) + (["--keep-index"] if keep_index else [])
        if message:
            args += ["-m", message]
        return self.run(*args)

    def stash_apply(self, ref: str, pop: bool = False):
        return self.run("stash", "pop" if pop else "apply", ref)

    def stash_drop(self, ref: str):
        return self.run("stash", "drop", ref)

    def stash_show(self, ref: str) -> str:
        return self.run("stash", "show", "-p", "--stat", ref)[1]

    # ------------------------------------------------------------ commits
    def commit_amend(self, message: str = ""):
        if message.strip():
            return self.run("commit", "--amend", "-F", "-", stdin=message)
        return self.run("commit", "--amend", "--no-edit")

    def last_message(self) -> str:
        return self.stdout("log", "-1", "--pretty=%B").strip()

    def head_is_pushed(self) -> bool:
        """True when HEAD is already contained in its upstream (amending it rewrites published history)."""
        if not self.upstream():
            return False
        return self.run("merge-base", "--is-ancestor", "HEAD", "@{u}")[0] == 0

    def cherry_pick(self, commit: str):
        return self.run("cherry-pick", commit)

    def revert(self, commit: str):
        return self.run("revert", "--no-edit", commit)

    def reset(self, commit: str, mode: str = "mixed"):
        return self.run("reset", f"--{mode}", commit)

    def undo_last_commit(self):
        return self.run("reset", "--soft", "HEAD~1")

    def discard(self, paths: list[str], untracked: bool = False):
        top = self.toplevel() or self.folder
        if untracked:
            errs = []
            for p in paths:
                try:
                    (top / p).unlink()
                except OSError as e:
                    errs.append(str(e))
            return (1 if errs else 0), "\n".join(errs)
        return self.run("checkout", "--", *[str(top / p) for p in paths])

    # ------------------------------------------------------------ graph
    def graph(self, n: int = 500, all_refs: bool = True, skip: int = 0) -> list["GraphRow"]:
        args = ["log", "--topo-order", f"-n{n}", f"--skip={skip}", "--date=format:%Y-%m-%d %H:%M",
                "--pretty=format:%H%x1f%P%x1f%h%x1f%D%x1f%an%x1f%ad%x1f%s"]
        if all_refs:
            args.insert(1, "--all")
        commits = []
        for line in self.stdout(*args).splitlines():
            p = line.split(US)
            if len(p) == 7:
                commits.append(Commit(p[0], p[1].split(), p[2], p[3], p[4], p[5], p[6]))
        return compute_lanes(commits)

    def file_log(self, path: str, n: int = 200) -> list[tuple[str, str, str, str]]:
        out = []
        for line in self.stdout("log", "--follow", f"-n{n}", "--date=format:%Y-%m-%d %H:%M",
                                "--pretty=format:%h%x1f%ad%x1f%an%x1f%s", "--", path).splitlines():
            p = line.split(US)
            if len(p) == 4:
                out.append(tuple(p))
        return out

    def refs_for_compare(self) -> list[str]:
        refs = ["HEAD", "HEAD~1", "HEAD~2"]
        refs += [b.name for b in self.branches()]
        refs += [t[0] for t in self.tags()]
        return list(dict.fromkeys(refs))

    def compare_with(self, path: str, ref: str) -> str:
        """Unified diff of the file between *ref* and the working copy."""
        return self.run("diff", ref, "--", path)[1]

    def show_file(self, ref: str, path: str) -> str | None:
        code, data = self.raw("show", f"{ref}:{path}")
        return data.decode("utf-8", errors="replace") if code == 0 else None

    # ------------------------------------------------------------ blame
    def blame(self, path: str, contents: str | None = None) -> list["BlameLine"]:
        args = ["blame", "--porcelain"]
        if contents is not None:
            args += ["--contents", "-"]
        args += ["--", path]
        if not self.exe:
            return []
        try:
            r = subprocess.run([self.exe, *args], cwd=str(self.folder), capture_output=True, timeout=60,
                               input=contents.encode("utf-8") if contents is not None else None,
                               creationflags=NO_WINDOW, env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
        except (OSError, subprocess.TimeoutExpired):
            return []
        if r.returncode != 0:
            return []
        return parse_blame(r.stdout.decode("utf-8", errors="replace"))


@dataclass
class Branch:
    name: str
    remote: bool
    upstream: str = ""
    track: str = ""          # "ahead 1, behind 2" | "gone" | ""
    sha: str = ""
    date: str = ""
    subject: str = ""
    head: bool = False


# ===================================================================== commit graph
@dataclass
class Commit:
    sha: str
    parents: list[str]
    short: str
    refs: str
    author: str
    date: str
    subject: str


@dataclass
class GraphRow:
    commit: Commit
    col: int                              # lane of the commit's dot
    before: list                          # lane -> sha expected above this row (None = free)
    after: list                           # lanes below this row
    incoming: list[int] = field(default_factory=list)     # lanes that end in this commit
    parent_cols: list[int] = field(default_factory=list)  # lanes the commit continues into

    @property
    def width(self) -> int:
        return max(len(self.before), len(self.after), self.col + 1)


def compute_lanes(commits: list[Commit]) -> list[GraphRow]:
    """Classic lane assignment for a topo-ordered log: every lane waits for one commit hash."""
    lanes: list = []
    rows = []
    for c in commits:
        before = lanes[:]
        if c.sha in lanes:
            col = lanes.index(c.sha)
        else:
            col = lanes.index(None) if None in lanes else len(lanes)
            if col == len(lanes):
                lanes.append(None)
        incoming = [i for i, h in enumerate(before) if h == c.sha]
        for i in incoming:
            lanes[i] = None
        parent_cols = []
        for k, p in enumerate(c.parents):
            if k == 0:
                if p in lanes:                       # another child already waits for this parent
                    parent_cols.append(lanes.index(p))
                else:
                    lanes[col] = p
                    parent_cols.append(col)
                continue
            if p in lanes:
                parent_cols.append(lanes.index(p))
            else:
                free = next((i for i, h in enumerate(lanes) if h is None and i != col), None)
                if free is None:
                    lanes.append(p)
                    free = len(lanes) - 1
                else:
                    lanes[free] = p
                parent_cols.append(free)
        while lanes and lanes[-1] is None:
            lanes.pop()
        rows.append(GraphRow(c, col, before, lanes[:], incoming, parent_cols))
    return rows


# ===================================================================== blame
@dataclass
class BlameLine:
    sha: str
    author: str
    time: int
    summary: str
    text: str

    @property
    def uncommitted(self) -> bool:
        return set(self.sha) == {"0"}

    @property
    def date(self) -> str:
        import time as _t
        return _t.strftime("%Y-%m-%d", _t.localtime(self.time)) if self.time else ""


def parse_blame(text: str) -> list[BlameLine]:
    info: dict[str, dict] = {}
    out: list[BlameLine] = []
    cur = None
    for line in text.split("\n"):
        if not line:
            continue
        if line.startswith("\t"):
            if cur is not None:
                d = info[cur]
                out.append(BlameLine(cur, d.get("author", ""), int(d.get("author-time", "0") or 0),
                                     d.get("summary", ""), line[1:]))
            continue
        parts = line.split(" ")
        if len(parts[0]) == 40 and re.fullmatch(r"[0-9a-f]{40}", parts[0]) and len(parts) >= 3:
            cur = parts[0]
            info.setdefault(cur, {})
        elif cur is not None:
            key, _, val = line.partition(" ")
            info[cur].setdefault(key, val)
    return out


# ===================================================================== 3-way merge
@dataclass
class Conflict:
    ours: list[str]
    base: list[str]
    theirs: list[str]


def merge_segments(git: GitX, path: str) -> tuple[list, str]:
    """Segments of a conflicted file: str lines (merged cleanly) and Conflict objects.
    Built from the index stages :1: (base) :2: (ours/current) :3: (theirs/incoming)."""
    stages = {k: git.raw("show", f":{k}:{path}") for k in (1, 2, 3)}
    texts = {k: (v[1] if v[0] == 0 else b"") for k, v in stages.items()}
    eol = "\r\n" if b"\r\n" in (texts[2] or texts[3]) else "\n"
    with tempfile.TemporaryDirectory() as td:
        files = []
        for k, name in ((2, "ours"), (1, "base"), (3, "theirs")):
            f = Path(td) / name
            f.write_bytes(texts[k].replace(b"\r\n", b"\n"))
            files.append(str(f))
        try:
            r = subprocess.run([git.exe, "merge-file", "-p", "--diff3", "-L", "Current", "-L", "Base",
                                "-L", "Incoming", *files], capture_output=True, timeout=60,
                               creationflags=NO_WINDOW)
            merged = r.stdout.decode("utf-8", errors="replace")
        except (OSError, subprocess.TimeoutExpired):
            merged = ""
    return parse_conflict_markers(merged), eol


def parse_conflict_markers(text: str) -> list:
    segs: list = []
    lines = text.split("\n")
    trailing_nl = text.endswith("\n")
    if trailing_nl:
        lines = lines[:-1]
    i = 0
    while i < len(lines):
        l = lines[i]
        if l.startswith("<<<<<<< "):
            ours, base, theirs = [], [], []
            target = ours
            i += 1
            while i < len(lines) and not lines[i].startswith(">>>>>>> "):
                s = lines[i]
                if s.startswith("||||||| "):
                    target = base
                elif s == "=======":
                    target = theirs
                else:
                    target.append(s)
                i += 1
            segs.append(Conflict(ours, base, theirs))
        else:
            segs.append(l)
        i += 1
    return segs


def side_text(segs: list, side: str) -> tuple[list[str], list[tuple[int, int]]]:
    """Full text of one side ('ours' | 'base' | 'theirs') and the line range of every conflict in it."""
    out: list[str] = []
    ranges = []
    for s in segs:
        if isinstance(s, Conflict):
            part = getattr(s, side)
            ranges.append((len(out), len(out) + len(part)))
            out.extend(part)
        else:
            out.append(s)
    return out, ranges


def marker_block(k: int, c: Conflict) -> list[str]:
    return [f"<<<<<<< Current #{k}", *c.ours, "=======", *c.theirs, f">>>>>>> Incoming #{k}"]


def initial_result(segs: list) -> list[str]:
    out, k = [], 0
    for s in segs:
        if isinstance(s, Conflict):
            k += 1
            out.extend(marker_block(k, s))
        else:
            out.append(s)
    return out


def find_block(lines: list[str], k: int) -> tuple[int, int] | None:
    """(start, end-exclusive) of the marker block of conflict *k* in the result lines."""
    try:
        a = lines.index(f"<<<<<<< Current #{k}")
        b = lines.index(f">>>>>>> Incoming #{k}", a)
    except ValueError:
        return None
    return a, b + 1


def remaining_conflicts(text: str) -> int:
    return sum(1 for l in text.split("\n") if l.startswith("<<<<<<< "))


# ===================================================================== network errors
_ERRORS = [
    (r"could not read Username|terminal prompts disabled|Authentication failed|invalid username or password"
     r"|HTTP Basic: Access denied|403 Forbidden|returned error: 403",
     "The server needs you to sign in (or your saved password / token is wrong).\n"
     "* GitHub: install the GitHub CLI and run 'gh auth login' (Git > GitHub > Sign in), or use Git Credential "
     "Manager (it ships with Git for Windows) by running one pull/push from a terminal once.\n"
     "* GitHub and GitLab no longer accept your account password over HTTPS - use a personal access token."),
    (r"Permission denied \(publickey\)|Host key verification failed",
     "The SSH key was refused. Add your public key (~/.ssh/id_ed25519.pub) to your account on the server, or "
     "switch the remote to an https:// URL (Branches > Remotes)."),
    (r"Could not resolve host|Failed to connect|Connection timed out|Couldn't connect to server|unable to access",
     "The server could not be reached. Check your internet connection, proxy and the remote URL."),
    (r"Repository not found|does not appear to be a git repository|not found",
     "The remote repository does not exist or you have no access to it. Check the remote URL "
     "(Branches > Remotes) and that you are signed in with the right account."),
    (r"\[rejected\].*\(fetch first\)|\(non-fast-forward\)|Updates were rejected",
     "The remote has commits you do not have yet. Pull (or Fetch + Merge/Rebase) first, then push again."),
    (r"has no upstream branch|no tracking information",
     "This branch is not connected to a remote branch yet. Use Push (it publishes the branch) or Branches > "
     "Set Upstream."),
    (r"would be overwritten by merge|Your local changes to the following files would be overwritten",
     "You have uncommitted changes that the pull would overwrite. Commit or Stash them first."),
    (r"CONFLICT|Automatic merge failed",
     "The pull produced merge conflicts. Use Git > Resolve Conflicts, then commit to finish the merge."),
]


def explain_error(text: str) -> str:
    """A plain-language explanation of a failed git network command ('' when unknown)."""
    for pattern, explanation in _ERRORS:
        if re.search(pattern, text, re.IGNORECASE):
            return explanation
    return ""


PROGRESS_RE = re.compile(r"([A-Za-z][A-Za-z ]+?):\s+(\d{1,3})%")


def parse_progress(chunk: str) -> tuple[str, int] | None:
    """Last 'Receiving objects:  45% (..)' in a chunk of git --progress output."""
    found = PROGRESS_RE.findall(chunk)
    if not found:
        return None
    phase, pct = found[-1]
    return phase.strip(), min(100, int(pct))


# ===================================================================== .gitignore
GITIGNORE_TEMPLATES = {
    "RAD IDE": "__pycache__/\n*.pyc\n.radide_backup/\n_deleted/\nbuild/\ndist/\n",
    "Python": "__pycache__/\n*.py[cod]\n*.egg-info/\n.venv/\nvenv/\n.pytest_cache/\n.mypy_cache/\nbuild/\ndist/\n",
    "Node / JavaScript": "node_modules/\nnpm-debug.log*\nyarn-error.log*\n.npm/\ndist/\n.env\n",
    "Java / Kotlin / Android": "*.class\n*.jar\ntarget/\nbuild/\n.gradle/\nlocal.properties\n*.apk\n.idea/\n",
    "C# / Visual Studio": "bin/\nobj/\n.vs/\n*.user\n*.suo\npackages/\nTestResults/\n",
    "C / C++ / Qt": "*.o\n*.obj\n*.exe\n*.dll\n*.so\n*.a\n*.lib\nbuild/\nCMakeFiles/\nCMakeCache.txt\n*.pro.user\n",
    "Go": "*.exe\n*.test\n*.out\nvendor/\n",
    "Rust": "target/\n**/*.rs.bk\n",
    "PHP / Web": "vendor/\n.env\n*.log\n",
    "Godot / Games": ".godot/\n.import/\nexport_presets.cfg\n",
    "OS files (Windows / macOS)": "Thumbs.db\ndesktop.ini\n.DS_Store\n",
    "Editors": ".vscode/\n.idea/\n*.swp\n*~\n",
    "Secrets": ".env\n*.pem\n*.key\nsecrets.*\n",
}


def add_to_gitignore(top: Path, patterns: list[str], header: str = "") -> list[str]:
    """Append the patterns that are not in <top>/.gitignore yet; returns the ones added."""
    gi = Path(top) / ".gitignore"
    try:
        text = gi.read_text(encoding="utf-8")
    except OSError:
        text = ""
    have = {l.strip() for l in text.splitlines()}
    new = [p for p in patterns if p.strip() and p.strip() not in have]
    if not new:
        return []
    if text and not text.endswith("\n"):
        text += "\n"
    if header:
        text += ("\n" if text else "") + f"# {header}\n"
    text += "\n".join(new) + "\n"
    gi.write_text(text, encoding="utf-8")
    return new


# ===================================================================== GitHub CLI
def tools_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "RADIDE" / "tools"


def find_gh() -> str:
    local = tools_dir() / "gh" / "bin" / "gh.exe"
    if local.exists():
        return str(local)
    found = shutil.which("gh")
    if found:
        return found
    for hint in (r"C:\Program Files\GitHub CLI\gh.exe", r"C:\Program Files (x86)\GitHub CLI\gh.exe"):
        if Path(hint).exists():
            return hint
    return ""


GH_RELEASE_API = "https://api.github.com/repos/cli/cli/releases/latest"


def gh_latest_zip() -> tuple[str, str]:
    """(version, download url) of the official Windows amd64 zip of the latest gh release."""
    req = urllib.request.Request(GH_RELEASE_API, headers={"User-Agent": "RAD-IDE",
                                                         "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    for a in data.get("assets", []):
        name = a.get("name", "")
        if name.endswith("_windows_amd64.zip"):
            return data.get("tag_name", ""), a["browser_download_url"]
    raise RuntimeError("no Windows zip in the latest gh release")


def download_gh(target: Path | None = None, progress=None) -> Path:
    """Download + unpack the official gh zip into <tools>/gh (portable; no admin, no PATH change).
    progress(done_bytes, total_bytes) is called while downloading. Returns the gh.exe path."""
    target = Path(target) if target else tools_dir() / "gh"
    version, url = gh_latest_zip()
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=str(target.parent)) as td:
        zpath = Path(td) / "gh.zip"
        req = urllib.request.Request(url, headers={"User-Agent": "RAD-IDE"})
        with urllib.request.urlopen(req, timeout=60) as r, open(zpath, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = r.read(256 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)
        unpack = Path(td) / "unpacked"
        with zipfile.ZipFile(zpath) as z:
            for m in z.namelist():                         # no path traversal out of the folder
                if m.startswith(("/", "\\")) or ".." in Path(m).parts:
                    raise RuntimeError(f"unsafe path in zip: {m}")
            z.extractall(unpack)
        exe = next(unpack.rglob("gh.exe"), None)
        if exe is None:
            raise RuntimeError("gh.exe not found in the zip")
        root = exe.parent.parent                          # <root>/bin/gh.exe
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(root, target)
    (target / "RADIDE_SOURCE.txt").write_text(f"GitHub CLI {version}\n{url}\n", encoding="utf-8")
    return target / "bin" / "gh.exe"


class GitHub:
    """The gh CLI in one repository folder."""

    def __init__(self, folder: Path, exe: str | None = None):
        self.folder = Path(folder)
        self.exe = exe if exe is not None else find_gh()

    def run(self, *args: str, timeout: int = 60) -> tuple[int, str]:
        if not self.exe:
            return -1, "The GitHub CLI (gh) is not installed."
        env = dict(os.environ, GH_PROMPT_DISABLED="1", NO_COLOR="1", GH_NO_UPDATE_NOTIFIER="1",
                   GIT_TERMINAL_PROMPT="0")
        try:
            r = subprocess.run([self.exe, *args], cwd=str(self.folder), capture_output=True, timeout=timeout,
                               env=env, creationflags=NO_WINDOW)
        except (OSError, subprocess.TimeoutExpired) as e:
            return -1, str(e)
        out = r.stdout.decode("utf-8", errors="replace")
        if r.returncode != 0:
            out += r.stderr.decode("utf-8", errors="replace")
        return r.returncode, out.replace("\r\n", "\n")

    def version(self) -> str:
        code, text = self.run("--version")
        return text.splitlines()[0] if code == 0 and text else ""

    def auth_status(self) -> tuple[bool, str]:
        code, text = self.run("auth", "status")
        return code == 0, text.strip()

    def _json(self, *args: str) -> tuple[list, str]:
        code, text = self.run(*args)
        if code != 0:
            return [], text.strip()
        try:
            return json.loads(text or "[]"), ""
        except ValueError:
            return [], text.strip()

    def prs(self, state: str = "open"):
        return self._json("pr", "list", "--state", state, "--limit", "50",
                          "--json", "number,title,headRefName,baseRefName,author,state,url,isDraft")

    def issues(self, state: str = "open"):
        return self._json("issue", "list", "--state", state, "--limit", "50",
                          "--json", "number,title,author,state,url,labels")

    def checkout_pr(self, number: int):
        return self.run("pr", "checkout", str(number))

    def create_pr(self, title: str, body: str, base: str = "", head: str = "", draft: bool = False):
        args = ["pr", "create", "--title", title, "--body", body]
        if base:
            args += ["--base", base]
        if head:
            args += ["--head", head]
        if draft:
            args.append("--draft")
        return self.run(*args, timeout=120)


def explain_gh_error(text: str) -> str:
    if re.search(r"gh auth login|not logged in|authentication", text, re.I):
        return "Sign in to GitHub first: Git > GitHub > Sign in (runs 'gh auth login' in a console window)."
    if re.search(r"none of the git remotes|no git remotes|not a github|could not determine", text, re.I):
        return "This repository has no GitHub remote. Add one in Branches > Remotes (https://github.com/<you>/<repo>.git)."
    if re.search(r"must first push|aren't any commits|no commits between", text, re.I):
        return "Push the branch first (and make sure it has commits that the base branch does not have)."
    return ""


__all__ = ["GitX", "Branch", "Commit", "GraphRow", "BlameLine", "Conflict", "GitHub", "compute_lanes",
           "parse_blame", "merge_segments", "parse_conflict_markers", "side_text", "initial_result",
           "find_block", "marker_block", "remaining_conflicts", "explain_error", "explain_gh_error",
           "parse_progress", "GITIGNORE_TEMPLATES", "add_to_gitignore", "find_gh", "download_gh", "gh_latest_zip",
           "tools_dir", "find_git"]
