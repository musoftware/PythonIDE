"""Publish a web site (WebMatrix "Publish"): profiles, FTP / FTPS / SFTP / local folder targets,
incremental upload with a state cache, dry run, exclusions and progress.

The engine has no Qt dependency: `Publisher(profile, local_root, cache_file).run(...)` reports through
plain callbacks so it can run in a worker thread. The Qt dialog (`PublishDialog`) is in
radide/features/web_tools.py.

Profiles are stored in project.radproj under "publish" (a list of dicts) *without* passwords.
Passwords are kept in the user's QSettings (obfuscated, not encrypted) or asked for each time.
"""
from __future__ import annotations

import base64
import fnmatch
import ftplib
import hashlib
import json
import os
import posixpath
import shutil
import socket
import ssl
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

KINDS = ("ftp", "ftps", "sftp", "folder")
KIND_LABELS = {"ftp": "FTP", "ftps": "FTPS (explicit TLS)", "sftp": "SFTP (SSH)", "folder": "Local folder / network share"}
DEFAULT_PORTS = {"ftp": 21, "ftps": 21, "sftp": 22, "folder": 0}
DEFAULT_EXCLUDES = [".git", ".svn", ".hg", ".radide", ".radide_backup*", "project.radproj", "*.radsln",
                    "__pycache__", "*.pyc", ".vscode", ".idea", "Thumbs.db", ".DS_Store", "*.bak", "*.tmp",
                    "~$*",
                    # a Python web site's virtual environment (python_web.py keeps it in <project>/.venv): it is
                    # machine-specific (absolute paths, this Windows' Python) - the host installs requirements.txt
                    ".venv", ".pytest_cache", ".mypy_cache",
                    # runtime data of the site: never overwrite the live database / sessions on the host
                    "data/*.sqlite", "data/*.sqlite-*", "data/*.db", "data/sessions",
                    # ... also where the frameworks keep them: Laravel (database/database.sqlite, sessions),
                    # Rails (storage/*.sqlite3), CodeIgniter (writable/*.db, writable/session)
                    "database/*.sqlite", "database/*.sqlite-*", "storage/*.sqlite3", "storage/*.sqlite3-*",
                    "storage/framework/sessions", "writable/*.db", "writable/session"]
CACHE_DIR = ".radide/publish"


def paramiko_available() -> bool:
    import importlib.util
    return importlib.util.find_spec("paramiko") is not None


# ====================================================================== profiles
@dataclass
class PublishProfile:
    name: str = "Default"
    kind: str = "ftp"                     # ftp | ftps | sftp | folder
    host: str = ""
    port: int = 0                         # 0 = default for the kind
    user: str = ""
    remote_dir: str = "/"                 # remote folder (or the destination folder for "folder")
    site_url: str = ""                    # the published site's address (opened after publishing)
    local_dir: str = ""                   # folder to publish, relative to the project ("" = web root)
    passive: bool = True                  # FTP passive mode
    verify_tls: bool = True               # FTPS: verify the server certificate
    host_key: str = ""                    # SFTP: trusted host key "<type> <base64>" (set on first connect)
    key_file: str = ""                    # SFTP: private key file (optional, instead of a password)
    excludes: list[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDES))
    delete_removed: bool = False          # delete remote files that were published before and are gone now
    save_password: bool = True            # False = ask for the password every time
    timeout: int = 30

    def effective_port(self) -> int:
        return int(self.port) or DEFAULT_PORTS.get(self.kind, 0)

    def target_id(self) -> str:
        """Identifies the destination; the incremental cache is reset when it changes."""
        if self.kind == "folder":
            return "folder:" + os.path.normcase(os.path.abspath(self.remote_dir or ""))
        return f"{self.kind}://{self.user}@{self.host}:{self.effective_port()}{self.remote_dir or '/'}"

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "PublishProfile":
        p = PublishProfile()
        for k, v in (d or {}).items():
            if hasattr(p, k) and k != "password":       # never accept a password from a file
                setattr(p, k, v)
        if p.kind not in KINDS:
            p.kind = "ftp"
        try:
            p.port = int(p.port or 0)
        except (TypeError, ValueError):
            p.port = 0
        if not isinstance(p.excludes, list):
            p.excludes = [s.strip() for s in str(p.excludes).splitlines() if s.strip()]
        return p


def load_profiles(project) -> list[PublishProfile]:
    raw = (getattr(project, "extra", None) or {}).get("publish") or []
    return [PublishProfile.from_dict(d) for d in raw if isinstance(d, dict)]


def save_profiles(project, profiles: list[PublishProfile]) -> None:
    project.extra["publish"] = [p.to_dict() for p in profiles]
    project.save()


def site_root(project) -> Path:
    """The web root of a website project (project.radproj "web": {"root": ...}) or the project folder."""
    try:
        from .project import site_root as _site_root
        return _site_root(project)
    except Exception:  # noqa: BLE001 - older layouts without radide.web_site.project
        pass
    folder = Path(project.folder)
    web = (getattr(project, "extra", None) or {}).get("web") or {}
    root = web.get("root") if isinstance(web, dict) else None
    return (folder / root).resolve() if root else folder


def local_root(project, profile: PublishProfile) -> Path:
    """Folder to publish. Default: the web root - but when the web root is a sub-folder of the project
    (public/ of the PHP Data App, Laravel ...) the pages need the files beside it (../app, ../vendor), so the
    whole project folder is published and the host's document root is pointed at that sub-folder."""
    if profile.local_dir:
        return (Path(project.folder) / profile.local_dir).resolve()
    root, folder = site_root(project), Path(project.folder).resolve()
    if root != folder and folder in root.parents:
        return folder
    return root


# ---------------------------------------------------------------- passwords (never in the project)
def _pw_key(project_folder, profile_name: str) -> str:
    h = hashlib.sha1(f"{os.path.normcase(str(project_folder))}|{profile_name}".encode()).hexdigest()[:16]
    return f"publish/passwords/{h}"


def get_password(settings, project_folder, profile_name: str) -> str | None:
    v = settings.value(_pw_key(project_folder, profile_name))
    if not v:
        return None
    try:
        return base64.b64decode(str(v).encode()).decode("utf-8")
    except Exception:  # noqa: BLE001
        return None


def set_password(settings, project_folder, profile_name: str, password: str | None) -> None:
    key = _pw_key(project_folder, profile_name)
    if password:
        settings.setValue(key, base64.b64encode(password.encode("utf-8")).decode())
    else:
        settings.remove(key)
    settings.sync()


# ====================================================================== local scan + plan
def is_excluded(rel: str, patterns: list[str]) -> bool:
    """rel is a posix relative path; a pattern matches the whole path or any of its parts."""
    parts = rel.split("/")
    for pat in patterns:
        pat = pat.strip().replace("\\", "/").strip("/")
        if not pat or pat.startswith("#"):
            continue
        if "/" in pat:
            if fnmatch.fnmatch(rel, pat) or rel.startswith(pat + "/"):
                return True
        elif any(fnmatch.fnmatch(part, pat) for part in parts):
            return True
    return False


def file_hash(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_local(root: Path, excludes: list[str]) -> dict[str, dict]:
    """rel posix path -> {"size", "mtime"} for every published file under root."""
    out: dict[str, dict] = {}
    root = Path(root)
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        rel_dir = "" if rel_dir == "." else rel_dir
        dirnames[:] = sorted(d for d in dirnames
                             if not is_excluded(f"{rel_dir}/{d}" if rel_dir else d, excludes))
        for fn in sorted(filenames):
            rel = f"{rel_dir}/{fn}" if rel_dir else fn
            if is_excluded(rel, excludes):
                continue
            st = (Path(dirpath) / fn).stat()
            out[rel] = {"size": st.st_size, "mtime": round(st.st_mtime, 3)}
    return out


@dataclass
class Plan:
    uploads: list[str] = field(default_factory=list)      # new or changed files
    new: set[str] = field(default_factory=set)            # subset of uploads never published before
    deletes: list[str] = field(default_factory=list)      # remote files to delete (delete_removed)
    unchanged: list[str] = field(default_factory=list)
    local: dict[str, dict] = field(default_factory=dict)  # scan result (+ "hash" when computed)
    bytes: int = 0

    def summary(self) -> str:
        return (f"{len(self.uploads)} to upload ({len(self.new)} new, {fmt_size(self.bytes)}), "
                f"{len(self.deletes)} to delete, {len(self.unchanged)} unchanged")


def fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return str(n)


def load_cache(cache_file: Path | None, profile: PublishProfile) -> dict[str, dict]:
    if not cache_file or not Path(cache_file).is_file():
        return {}
    try:
        data = json.loads(Path(cache_file).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    if data.get("target") != profile.target_id():
        return {}
    files = data.get("files")
    return files if isinstance(files, dict) else {}


def save_cache(cache_file: Path | None, profile: PublishProfile, files: dict[str, dict]) -> None:
    if not cache_file:
        return
    cache_file = Path(cache_file)
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache_file.with_suffix(".tmp")
    tmp.write_text(json.dumps({"target": profile.target_id(), "time": time.time(), "files": files},
                              indent=1, sort_keys=True), encoding="utf-8")
    os.replace(tmp, cache_file)


def cache_file_for(project_folder, profile_name: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in profile_name) or "profile"
    return Path(project_folder) / CACHE_DIR / f"{safe}.json"


def make_plan(root: Path, profile: PublishProfile, cache: dict[str, dict], force: bool = False) -> Plan:
    """Compare the local files with what the cache says was published. A file whose size and mtime
    are unchanged is skipped; when only the mtime changed, the content hash decides."""
    plan = Plan(local=scan_local(root, profile.excludes))
    for rel, info in plan.local.items():
        old = cache.get(rel)
        if force or not old:
            plan.uploads.append(rel)
            if not old:
                plan.new.add(rel)
            continue
        if old.get("size") == info["size"] and abs(float(old.get("mtime", 0)) - info["mtime"]) < 0.002:
            info["hash"] = old.get("hash", "")
            plan.unchanged.append(rel)
            continue
        if old.get("size") == info["size"] and old.get("hash"):
            info["hash"] = file_hash(Path(root) / rel)
            if info["hash"] == old["hash"]:
                plan.unchanged.append(rel)
                continue
        plan.uploads.append(rel)
    if profile.delete_removed:
        plan.deletes = sorted(rel for rel in cache if rel not in plan.local)
    plan.bytes = sum(plan.local[r]["size"] for r in plan.uploads)
    return plan


# ====================================================================== targets
class PublishError(Exception):
    pass


class HostKeyUnknown(PublishError):
    """SFTP: the server's host key is not trusted yet. `.key` = "<type> <base64>", `.fingerprint`."""

    def __init__(self, key: str, fingerprint: str):
        super().__init__(f"Unknown SSH host key {fingerprint}")
        self.key = key
        self.fingerprint = fingerprint


class Target:
    def connect(self) -> None: ...
    def ensure_dir(self, rel_dir: str) -> None: ...
    def upload(self, local: Path, rel: str, progress: Callable[[int], None] | None = None) -> None: ...
    def delete(self, rel: str) -> None: ...
    def list_dir(self, rel_dir: str = "") -> list[str]: return []
    def close(self) -> None: ...

    def describe(self) -> str:
        return type(self).__name__


class FolderTarget(Target):
    def __init__(self, profile: PublishProfile):
        if not profile.remote_dir:
            raise PublishError("No destination folder set.")
        self.dest = Path(profile.remote_dir)

    def describe(self) -> str:
        return str(self.dest)

    def connect(self) -> None:
        self.dest.mkdir(parents=True, exist_ok=True)

    def ensure_dir(self, rel_dir: str) -> None:
        (self.dest / rel_dir).mkdir(parents=True, exist_ok=True)

    def upload(self, local: Path, rel: str, progress=None) -> None:
        dst = self.dest / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_name(dst.name + ".radide-part")
        shutil.copy2(local, tmp)
        os.replace(tmp, dst)
        if progress:
            progress(local.stat().st_size)

    def exists(self, rel: str) -> bool:
        return (self.dest / rel).is_file()

    def delete(self, rel: str) -> None:
        p = self.dest / rel
        if p.is_file():
            p.unlink()

    def list_dir(self, rel_dir: str = "") -> list[str]:
        p = self.dest / rel_dir
        return sorted(x.name for x in p.iterdir()) if p.is_dir() else []


def _rpath(base: str, rel: str) -> str:
    base = (base or "/").replace("\\", "/")
    return posixpath.join(base, rel) if rel else base


class _FTP_TLS(ftplib.FTP_TLS):
    """FTPS whose data connections reuse the control connection's TLS session
    (required by vsftpd "require_ssl_reuse" and FileZilla Server)."""

    def ntransfercmd(self, cmd, rest=None):
        conn, size = ftplib.FTP.ntransfercmd(self, cmd, rest)
        if self._prot_p:
            conn = self.context.wrap_socket(conn, server_hostname=self.host, session=self.sock.session)
        return conn, size


class FtpTarget(Target):
    def __init__(self, profile: PublishProfile, password: str | None):
        if not profile.host:
            raise PublishError("No FTP server set.")
        self.p = profile
        self.password = password or ""
        self.ftp: ftplib.FTP | None = None
        self._dirs: set[str] = set()

    def describe(self) -> str:
        return f"{self.p.kind}://{self.p.host}:{self.p.effective_port()}{self.p.remote_dir or '/'}"

    def connect(self) -> None:
        p = self.p
        try:
            if p.kind == "ftps":
                ctx = ssl.create_default_context()
                if not p.verify_tls:
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                ftp = _FTP_TLS(context=ctx, timeout=p.timeout)
            else:
                ftp = ftplib.FTP(timeout=p.timeout)
            ftp.connect(p.host, p.effective_port())
            ftp.login(p.user or "anonymous", self.password)
            if isinstance(ftp, ftplib.FTP_TLS):
                ftp.prot_p()
            ftp.set_pasv(bool(p.passive))
            ftp.voidcmd("TYPE I")
        except ftplib.error_perm as e:
            raise PublishError(f"FTP login failed: {e}") from e
        except (OSError, ftplib.Error, EOFError) as e:
            raise PublishError(f"Cannot connect to {p.host}:{p.effective_port()}: {e}") from e
        self.ftp = ftp
        self.ensure_dir("")

    def ensure_dir(self, rel_dir: str) -> None:
        self._ensure_abs(_rpath(self.p.remote_dir, rel_dir).rstrip("/") or "/")

    def _ensure_abs(self, path: str) -> None:
        if path in self._dirs or path in ("", "/"):
            return
        parent = posixpath.dirname(path)
        if parent not in ("", "/") and parent not in self._dirs:
            self._ensure_abs(parent)
        try:
            self.ftp.mkd(path)
        except ftplib.error_perm:
            try:                           # already exists? (servers answer 550 for both cases)
                cur = self.ftp.pwd()
                self.ftp.cwd(path)
                self.ftp.cwd(cur)
            except ftplib.error_perm as e:
                raise PublishError(f"Cannot create remote folder {path}: {e}") from e
        self._dirs.add(path)

    def upload(self, local: Path, rel: str, progress=None) -> None:
        self.ensure_dir(posixpath.dirname(rel))
        cb = (lambda block: progress(len(block))) if progress else None
        with open(local, "rb") as f:
            self.ftp.storbinary(f"STOR {_rpath(self.p.remote_dir, rel)}", f, 32768, cb)

    def delete(self, rel: str) -> None:
        try:
            self.ftp.delete(_rpath(self.p.remote_dir, rel))
        except ftplib.error_perm:
            pass                            # already gone

    def list_dir(self, rel_dir: str = "") -> list[str]:
        try:
            return sorted(posixpath.basename(n) for n in self.ftp.nlst(_rpath(self.p.remote_dir, rel_dir)))
        except ftplib.error_perm:
            return []

    def close(self) -> None:
        if self.ftp is not None:
            try:
                self.ftp.quit()
            except Exception:  # noqa: BLE001
                try:
                    self.ftp.close()
                except Exception:  # noqa: BLE001
                    pass
            self.ftp = None


class SftpTarget(Target):
    def __init__(self, profile: PublishProfile, password: str | None):
        if not paramiko_available():
            raise PublishError("SFTP needs the 'paramiko' package (pip install paramiko).")
        if not profile.host:
            raise PublishError("No SFTP server set.")
        self.p = profile
        self.password = password or None
        self.client = None
        self.sftp = None
        self._dirs: set[str] = set()

    def describe(self) -> str:
        return f"sftp://{self.p.host}:{self.p.effective_port()}{self.p.remote_dir or '/'}"

    def connect(self) -> None:
        import paramiko
        p = self.p
        trusted = p.host_key.strip()

        class Policy(paramiko.MissingHostKeyPolicy):
            def missing_host_key(self, client, hostname, key):
                text = f"{key.get_name()} {key.get_base64()}"
                if trusted and text == trusted:
                    return
                fp = "SHA256:" + base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip("=")
                if trusted:
                    raise PublishError(f"The SSH host key of {hostname} CHANGED ({fp}). "
                                       "If this is expected, clear the trusted key in the profile.")
                raise HostKeyUnknown(text, fp)

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(Policy())
        try:
            client.connect(p.host, p.effective_port(), username=p.user or None, password=self.password,
                           key_filename=p.key_file or None, timeout=p.timeout, allow_agent=not self.password,
                           look_for_keys=not self.password and not p.key_file)
        except PublishError:
            client.close()
            raise
        except paramiko.AuthenticationException as e:
            client.close()
            raise PublishError(f"SFTP login failed: {e}") from e
        except (OSError, paramiko.SSHException, socket.error) as e:
            client.close()
            raise PublishError(f"Cannot connect to {p.host}:{p.effective_port()}: {e}") from e
        self.client = client
        self.sftp = client.open_sftp()
        self.ensure_dir("")

    def ensure_dir(self, rel_dir: str) -> None:
        path = _rpath(self.p.remote_dir, rel_dir).rstrip("/") or "/"
        self._ensure_abs(path)

    def _ensure_abs(self, path: str) -> None:
        if path in self._dirs or path in ("", "/", "."):
            return
        parent = posixpath.dirname(path)
        if parent and parent != path:
            self._ensure_abs(parent)
        try:
            self.sftp.stat(path)
        except IOError:
            try:
                self.sftp.mkdir(path)
            except IOError as e:
                raise PublishError(f"Cannot create remote folder {path}: {e}") from e
        self._dirs.add(path)

    def upload(self, local: Path, rel: str, progress=None) -> None:
        self.ensure_dir(posixpath.dirname(rel))
        last = [0]

        def cb(done, _total):
            if progress:
                progress(done - last[0])
            last[0] = done
        self.sftp.put(str(local), _rpath(self.p.remote_dir, rel), callback=cb)

    def delete(self, rel: str) -> None:
        try:
            self.sftp.remove(_rpath(self.p.remote_dir, rel))
        except IOError:
            pass

    def list_dir(self, rel_dir: str = "") -> list[str]:
        try:
            return sorted(self.sftp.listdir(_rpath(self.p.remote_dir, rel_dir)))
        except IOError:
            return []

    def close(self) -> None:
        for x in (self.sftp, self.client):
            try:
                if x is not None:
                    x.close()
            except Exception:  # noqa: BLE001
                pass
        self.sftp = self.client = None


def make_target(profile: PublishProfile, password: str | None = None) -> Target:
    if profile.kind == "folder":
        return FolderTarget(profile)
    if profile.kind in ("ftp", "ftps"):
        return FtpTarget(profile, password)
    if profile.kind == "sftp":
        return SftpTarget(profile, password)
    raise PublishError(f"Unknown publish method {profile.kind!r}")


def test_connection(profile: PublishProfile, password: str | None = None) -> str:
    """Connects, lists the remote folder and disconnects. Returns a short message; raises PublishError."""
    t = make_target(profile, password)
    t.connect()
    try:
        names = t.list_dir("")
    finally:
        t.close()
    return f"Connected to {t.describe()} ({len(names)} item(s) in the remote folder)."


# ====================================================================== publisher
@dataclass
class PublishResult:
    ok: bool = True
    dry_run: bool = False
    uploaded: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    skipped: int = 0
    bytes: int = 0
    seconds: float = 0.0
    error: str = ""
    cancelled: bool = False

    def summary(self) -> str:
        if self.error:
            return f"Publish failed: {self.error}"
        verb = "Would upload" if self.dry_run else "Uploaded"
        s = (f"{verb} {len(self.uploaded)} file(s) ({fmt_size(self.bytes)}), "
             f"{'would delete' if self.dry_run else 'deleted'} {len(self.deleted)}, "
             f"{self.skipped} unchanged")
        if self.failed:
            s += f", {len(self.failed)} FAILED"
        if self.cancelled:
            s += " - cancelled"
        return s + f" in {self.seconds:.1f} s."


class Publisher:
    def __init__(self, profile: PublishProfile, root: Path, cache_file: Path | None = None,
                 password: str | None = None):
        self.profile = profile
        self.root = Path(root)
        self.cache_file = Path(cache_file) if cache_file else None
        self.password = password
        self.cancelled = False
        self.target_factory = make_target          # tests may replace it

    def cancel(self) -> None:
        self.cancelled = True

    def plan(self, force: bool = False) -> Plan:
        cache = load_cache(self.cache_file, self.profile)
        plan = make_plan(self.root, self.profile, cache, force)
        if self.profile.kind == "folder" and not force:
            # a local destination is cheap to check: re-copy files deleted there by hand
            dest = Path(self.profile.remote_dir)
            for rel in list(plan.unchanged):
                if not (dest / rel).is_file():
                    plan.unchanged.remove(rel)
                    plan.uploads.append(rel)
                    plan.bytes += plan.local[rel]["size"]
            plan.uploads.sort()
        return plan

    def run(self, dry_run: bool = False, force: bool = False, only: set[str] | None = None,
            log: Callable[[str], None] = print,
            progress: Callable[[int, int, str], None] | None = None) -> PublishResult:
        """progress(done_bytes, total_bytes, current_file)."""
        t0 = time.time()
        res = PublishResult(dry_run=dry_run)
        if not self.root.is_dir():
            res.ok, res.error = False, f"Local folder not found: {self.root}"
            return res
        cache = load_cache(self.cache_file, self.profile)
        plan = self.plan(force)
        uploads = [r for r in plan.uploads if only is None or r in only]
        deletes = [r for r in plan.deletes if only is None or r in only]
        res.skipped = len(plan.unchanged) + (len(plan.uploads) - len(uploads))
        total = sum(plan.local[r]["size"] for r in uploads)
        log(f"Publishing {self.root} -> {self.profile.target_id()}  ({plan.summary()})")
        if dry_run:
            for r in uploads:
                log(f"  {'+' if r in plan.new else '~'} {r}  ({fmt_size(plan.local[r]['size'])})")
            for r in deletes:
                log(f"  - {r}")
            res.uploaded, res.deleted, res.bytes = uploads, deletes, total
            res.seconds = time.time() - t0
            log(res.summary())
            return res
        if not uploads and not deletes:
            res.seconds = time.time() - t0
            log("Everything is up to date.")
            # keep new hashes computed while planning
            save_cache(self.cache_file, self.profile, self._merge(cache, plan, []))
            return res
        try:
            target = self.target_factory(self.profile, self.password)
            log(f"Connecting to {target.describe()} ...")
            target.connect()
        except HostKeyUnknown:
            raise                           # the UI asks whether to trust the server, then retries
        except PublishError as e:
            res.ok, res.error = False, str(e)
            log(res.summary())
            return res
        done = [0]

        def bump(n: int, rel: str):
            done[0] += n
            if progress:
                progress(done[0], total, rel)
        uploaded_ok: list[str] = []
        try:
            for rel in uploads:
                if self.cancelled:
                    res.cancelled = True
                    break
                local = self.root / rel
                before = done[0]
                try:
                    target.upload(local, rel, lambda n, r=rel: bump(n, r))
                    done[0] = before + plan.local[rel]["size"]   # exact even if callbacks are coarse
                    if progress:
                        progress(done[0], total, rel)
                    uploaded_ok.append(rel)
                    res.bytes += plan.local[rel]["size"]
                    log(f"  uploaded {rel}")
                except Exception as e:  # noqa: BLE001 - keep going with the other files
                    res.failed.append((rel, str(e)))
                    log(f"  FAILED {rel}: {e}")
                    if isinstance(e, (OSError, EOFError, ftplib.Error)) and not isinstance(e, ftplib.error_perm):
                        # the connection may be broken: try to reconnect once
                        try:
                            target.close()
                            target.connect()
                        except Exception as e2:  # noqa: BLE001
                            res.error = f"connection lost: {e2}"
                            break
            deleted: list[str] = []
            if not res.cancelled and not res.error:
                for rel in deletes:
                    try:
                        target.delete(rel)
                        deleted.append(rel)
                        log(f"  deleted {rel}")
                    except Exception as e:  # noqa: BLE001
                        res.failed.append((rel, str(e)))
            res.deleted = deleted
        finally:
            target.close()
            res.uploaded = uploaded_ok
            files = self._merge(cache, plan, uploaded_ok)
            for rel in res.deleted:
                files.pop(rel, None)
            save_cache(self.cache_file, self.profile, files)
        res.ok = not res.failed and not res.error and not res.cancelled
        res.seconds = time.time() - t0
        log(res.summary())
        return res

    def _merge(self, cache: dict, plan: Plan, uploaded: list[str]) -> dict:
        files = {k: v for k, v in cache.items() if k in plan.local or k in plan.deletes}
        for rel in plan.unchanged:
            info = dict(plan.local[rel])
            if not info.get("hash"):
                info["hash"] = cache.get(rel, {}).get("hash") or file_hash(self.root / rel)
            files[rel] = info
        for rel in uploaded:
            info = dict(plan.local[rel])
            info["hash"] = info.get("hash") or file_hash(self.root / rel)
            files[rel] = info
        return files

    def forget(self) -> None:
        """Clear the incremental cache (next publish uploads everything)."""
        if self.cache_file and self.cache_file.is_file():
            self.cache_file.unlink()
