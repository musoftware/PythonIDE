"""SSH / SFTP backend (paramiko): files over SFTP, commands over exec channels, an interactive shell over a
PTY channel.  Host keys are checked: known keys come from ~/.ssh/known_hosts and the IDE's own
%LOCALAPPDATA%\\RADIDE\\remote\\known_hosts; an unknown key raises UnknownHostKey so the UI can show the
fingerprint and ask, then connect(trust=key) again."""
from __future__ import annotations

import codecs
import os
import posixpath
import stat as _stat
import threading
import time
from pathlib import Path
from typing import Callable

from .base import Entry, RemoteError, RemoteFS, ShellBackend, norm, with_cwd


def data_dir() -> Path:
    """%LOCALAPPDATA%\\RADIDE\\remote (known_hosts, file cache); tests (organisation RADIDE-TEST...) use
    ...\\RADIDE-TEST\\remote, and RADIDE_REMOTE_DATA overrides both."""
    override = os.environ.get("RADIDE_REMOTE_DATA")
    if override:
        base = Path(override)
        base.mkdir(parents=True, exist_ok=True)
        return base
    app = "RADIDE"
    try:
        from PyQt6.QtCore import QCoreApplication
        org = QCoreApplication.organizationName()
        if org.upper().startswith("RADIDE-TEST"):
            app = "RADIDE-TEST"
    except Exception:  # noqa: BLE001
        pass
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / app / "remote"
    base.mkdir(parents=True, exist_ok=True)
    return base


def known_hosts_file() -> Path:
    return data_dir() / "known_hosts"


def fingerprint(key) -> str:
    import base64
    import hashlib
    digest = hashlib.sha256(key.asbytes()).digest()
    return "SHA256:" + base64.b64encode(digest).decode().rstrip("=")


class UnknownHostKey(RemoteError):
    def __init__(self, hostname: str, key):
        self.hostname, self.key = hostname, key
        super().__init__(f"The host key of {hostname} is not known yet.\n{key.get_name()} {fingerprint(key)}")


class ChangedHostKey(RemoteError):
    pass


def ssh_config_hosts() -> dict[str, dict]:
    """Hosts of ~/.ssh/config: alias -> {hostname, user, port, identityfile}."""
    cfg_file = Path.home() / ".ssh" / "config"
    if not cfg_file.is_file():
        return {}
    try:
        import paramiko
        cfg = paramiko.SSHConfig.from_path(str(cfg_file))
    except Exception:  # noqa: BLE001
        return {}
    out = {}
    for alias in sorted(cfg.get_hostnames()):
        if any(c in alias for c in "*?!"):
            continue
        c = cfg.lookup(alias)
        out[alias] = {"hostname": c.get("hostname", alias), "user": c.get("user", ""),
                      "port": int(c.get("port", 22) or 22), "identityfile": (c.get("identityfile") or [""])[0]}
    return out


class _ChannelShell(ShellBackend):
    def __init__(self, chan):
        self.chan = chan

    def write(self, data: bytes) -> None:
        try:
            self.chan.sendall(data)
        except Exception as e:  # noqa: BLE001
            raise RemoteError(f"The remote shell is closed: {e}") from e

    def poll(self) -> bytes | None:
        out = b""
        try:
            while self.chan.recv_ready():
                out += self.chan.recv(65536)
            while self.chan.recv_stderr_ready():
                out += self.chan.recv_stderr(65536)
        except Exception:  # noqa: BLE001
            return out or None
        if not out and (self.chan.closed or self.chan.exit_status_ready() or self.chan.eof_received):
            return None
        return out

    def close(self) -> None:
        try:
            self.chan.close()
        except Exception:  # noqa: BLE001
            pass


class SSHFS(RemoteFS):
    kind = "ssh"

    def __init__(self, host: str, user: str, port: int = 22, password: str = "", key_file: str = "",
                 passphrase: str = "", root: str = "", use_agent: bool = True, timeout: float = 15):
        super().__init__(root or "/")
        self.host, self.user, self.port = host, user, int(port or 22)
        self.password, self.key_file, self.passphrase = password, key_file, passphrase
        self.use_agent, self.timeout = use_agent, timeout
        self._root_arg = root
        self.client = None
        self.sftp = None
        self._lock = threading.RLock()

    @property
    def label(self) -> str:
        return f"{self.user}@{self.host}" + (f":{self.port}" if self.port != 22 else "")

    # ------------------------------------------------------------------ connection
    def connect(self, trust=None) -> "SSHFS":
        """Connect and open SFTP.  *trust*: a host key the user accepted (saved to known_hosts)."""
        try:
            import paramiko
        except ImportError as e:
            raise RemoteError("paramiko is not installed (pip install paramiko)") from e
        kh = known_hosts_file()
        client = paramiko.SSHClient()
        try:
            client.load_system_host_keys()
        except Exception:  # noqa: BLE001 - unreadable ~/.ssh/known_hosts
            pass
        if kh.is_file():
            try:
                client.load_host_keys(str(kh))
            except Exception:  # noqa: BLE001
                pass
        hostname = self.host if self.port == 22 else f"[{self.host}]:{self.port}"
        if trust is not None:
            client.get_host_keys().add(hostname, trust.get_name(), trust)
            try:
                client.save_host_keys(str(kh))
            except Exception:  # noqa: BLE001
                pass

        class Policy(paramiko.MissingHostKeyPolicy):
            def missing_host_key(self, _client, name, key):
                raise UnknownHostKey(name, key)
        client.set_missing_host_key_policy(Policy())
        pkey = None
        if self.key_file:
            pkey = self._load_key(paramiko, self.key_file, self.passphrase)
        try:
            client.connect(self.host, port=self.port, username=self.user, password=self.password or None,
                           pkey=pkey, timeout=self.timeout, banner_timeout=self.timeout, auth_timeout=self.timeout,
                           allow_agent=self.use_agent and not (self.password or pkey),
                           look_for_keys=not (self.password or pkey))
        except UnknownHostKey:
            client.close()
            raise
        except paramiko.BadHostKeyException as e:
            client.close()
            raise ChangedHostKey(f"WARNING: the host key of {self.host} CHANGED (possible attack or a "
                                 f"reinstalled server).\nExpected {fingerprint(e.expected_key)}, got "
                                 f"{fingerprint(e.key)}.\nRemove the old line from {kh} if the change is "
                                 "expected.") from e
        except paramiko.AuthenticationException as e:
            client.close()
            raise RemoteError(f"Authentication failed for {self.label}: {e}") from e
        except Exception as e:  # noqa: BLE001 - socket errors, timeouts ...
            client.close()
            raise RemoteError(f"Cannot connect to {self.label}: {e}") from e
        tr = client.get_transport()
        if tr is not None:
            tr.set_keepalive(30)
        self.client = client
        try:
            self.sftp = client.open_sftp()
        except Exception as e:  # noqa: BLE001
            client.close()
            self.client = None
            raise RemoteError(f"The server does not offer SFTP: {e}") from e
        root = self._root_arg or "."
        if root.startswith("~"):
            root = "." + root[1:]
        try:
            self.root = norm(self.sftp.normalize(root))
        except Exception:  # noqa: BLE001
            self.root = norm(self.sftp.normalize("."))
        return self

    @staticmethod
    def _load_key(paramiko, path: str, passphrase: str):
        errors = []
        for cls in (paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.RSAKey):
            try:
                return cls.from_private_key_file(os.path.expanduser(path), password=passphrase or None)
            except paramiko.PasswordRequiredException as e:
                raise RemoteError(f"The key {path} needs its passphrase") from e
            except Exception as e:  # noqa: BLE001
                errors.append(str(e))
        raise RemoteError(f"Cannot read the private key {path}: {errors[-1] if errors else ''}")

    @property
    def connected(self) -> bool:
        tr = self.client.get_transport() if self.client is not None else None
        return bool(tr is not None and tr.is_active())

    def _need(self):
        if not self.connected or self.sftp is None:
            raise RemoteError(f"Not connected to {self.label}")
        return self.sftp

    def close(self) -> None:
        with self._lock:
            for x in (self.sftp, self.client):
                try:
                    if x is not None:
                        x.close()
                except Exception:  # noqa: BLE001
                    pass
            self.sftp = self.client = None

    # ------------------------------------------------------------------ files
    def _to_entry(self, path: str, a) -> Entry:
        is_link = bool(a.st_mode is not None and _stat.S_ISLNK(a.st_mode))
        is_dir = bool(a.st_mode is not None and _stat.S_ISDIR(a.st_mode))
        if is_link:
            try:
                is_dir = _stat.S_ISDIR(self.sftp.stat(path).st_mode or 0)
            except Exception:  # noqa: BLE001 - dangling link
                pass
        return Entry(posixpath.basename(path.rstrip("/")) or "/", norm(path), is_dir,
                     0 if is_dir else int(a.st_size or 0), float(a.st_mtime or 0), is_link)

    def listdir(self, path: str) -> list[Entry]:
        with self._lock:
            sftp = self._need()
            try:
                return [self._to_entry(self.join(path, a.filename), a) for a in sftp.listdir_attr(norm(path))
                        if a.filename not in (".", "..")]
            except OSError as e:
                raise RemoteError(f"Cannot list {path}: {e}") from e

    def stat(self, path: str) -> Entry | None:
        with self._lock:
            sftp = self._need()
            try:
                return self._to_entry(norm(path), sftp.lstat(norm(path)))
            except (OSError, IOError):
                return None

    def read(self, path: str) -> bytes:
        with self._lock:
            sftp = self._need()
            try:
                with sftp.open(norm(path), "rb") as f:
                    f.prefetch()
                    return f.read()
            except OSError as e:
                raise RemoteError(f"Cannot read {path}: {e}") from e

    def write(self, path: str, data: bytes) -> None:
        """Write via a temporary file + rename (keeps the old file if the upload breaks)."""
        p = norm(path)
        with self._lock:
            sftp = self._need()
            mode = None
            try:
                mode = sftp.stat(p).st_mode
            except OSError:
                pass
            tmp = p + ".radide-tmp"
            try:
                with sftp.open(tmp, "wb") as f:
                    f.set_pipelined(True)
                    f.write(data)
                if mode is not None:
                    try:
                        sftp.chmod(tmp, _stat.S_IMODE(mode))
                    except OSError:
                        pass
                try:
                    sftp.posix_rename(tmp, p)
                except (OSError, IOError):
                    try:
                        sftp.remove(p)
                    except OSError:
                        pass
                    sftp.rename(tmp, p)
            except (OSError, IOError):
                try:
                    sftp.remove(tmp)
                except (OSError, IOError):
                    pass
                try:                                   # no write permission in the folder: write in place
                    with sftp.open(p, "wb") as f:
                        f.write(data)
                except (OSError, IOError) as e:
                    raise RemoteError(f"Cannot write {path}: {e}") from e

    def mkdir(self, path: str) -> None:
        with self._lock:
            sftp = self._need()
            p = norm(path)
            try:
                sftp.stat(p)
                return
            except (OSError, IOError):
                pass
            parent = posixpath.dirname(p)
            if parent and parent != p:
                self.mkdir(parent)                    # only climbs as far as folders are missing
            try:
                sftp.mkdir(p)
            except (OSError, IOError) as e:
                raise RemoteError(f"Cannot create {p}: {e}") from e

    def remove(self, path: str) -> None:
        with self._lock:
            sftp = self._need()
            p = norm(path)
            try:
                a = sftp.lstat(p)
                if _stat.S_ISDIR(a.st_mode or 0):
                    for c in sftp.listdir_attr(p):
                        self.remove(self.join(p, c.filename))
                    sftp.rmdir(p)
                else:
                    sftp.remove(p)
            except (OSError, IOError) as e:
                raise RemoteError(f"Cannot delete {path}: {e}") from e

    def rename(self, old: str, new: str) -> None:
        with self._lock:
            sftp = self._need()
            try:
                sftp.rename(norm(old), norm(new))
            except (OSError, IOError) as e:
                raise RemoteError(f"Cannot rename {old}: {e}") from e

    # ------------------------------------------------------------------ commands
    def exec_stream(self, cmd: str, cwd: str | None, on_output: Callable[[str], None],
                    should_stop: Callable[[], bool] = lambda: False, timeout: float | None = None) -> int:
        if not self.connected:
            raise RemoteError(f"Not connected to {self.label}")
        chan = self.client.get_transport().open_session()
        chan.set_combine_stderr(True)
        chan.exec_command(with_cwd(cmd, cwd))
        dec = codecs.getincrementaldecoder("utf-8")(errors="replace")
        start = time.monotonic()
        try:
            while True:
                got = False
                while chan.recv_ready():
                    data = chan.recv(65536)
                    if data:
                        on_output(dec.decode(data))
                        got = True
                if chan.exit_status_ready() and not chan.recv_ready():
                    break
                if should_stop() or (timeout and time.monotonic() - start > timeout):
                    chan.close()
                    on_output(dec.decode(b"", final=True))
                    return -1
                if not got:
                    time.sleep(0.02)
            tail = dec.decode(b"", final=True)
            if tail:
                on_output(tail)
            return chan.recv_exit_status()
        finally:
            chan.close()

    def open_shell(self, cwd: str | None = None) -> ShellBackend:
        if not self.connected:
            raise RemoteError(f"Not connected to {self.label}")
        chan = self.client.get_transport().open_session()
        try:
            chan.get_pty(term="dumb", width=220, height=50)
        except Exception:  # noqa: BLE001 - a server without PTYs still gives a plain shell
            pass
        chan.invoke_shell()
        sh = _ChannelShell(chan)
        if cwd:
            from .base import q
            sh.write(f"cd {q(cwd)}\n".encode())
        return sh

    def search(self, text, folder, glob="", regex=False, case=False, max_results=2000,
               should_stop=lambda: False):
        hits = self.grep_search(text, folder, glob, regex, case, max_results, should_stop)
        if hits is not None:
            return hits
        return super().search(text, folder, glob, regex, case, max_results, should_stop)


__all__ = ["SSHFS", "UnknownHostKey", "ChangedHostKey", "fingerprint", "known_hosts_file", "ssh_config_hosts",
           "data_dir"]
