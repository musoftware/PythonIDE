"""In-process SSH test server (paramiko): password + public-key auth, exec (Git Bash), shell (bash -s), SFTP.
Remote paths are Git Bash (msys) paths of real folders under ROOT, e.g. /c/Users/.../srv/proj."""
from __future__ import annotations

import os
import socket
import subprocess
import threading
from pathlib import Path

import paramiko
from paramiko import SFTPAttributes, SFTPHandle, SFTPServer, SFTPServerInterface, ServerInterface
from paramiko.sftp import SFTP_FAILURE, SFTP_OK, SFTP_PERMISSION_DENIED

BASH = r"C:\Program Files\Git\bin\bash.exe"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def to_msys(p: Path) -> str:
    s = str(p.resolve()).replace("\\", "/")
    return "/" + s[0].lower() + s[2:]


def from_msys(s: str) -> Path:
    s = s.replace("\\", "/")
    if len(s) >= 2 and s[0] == "/" and s[1].isalpha() and (len(s) == 2 or s[2] == "/"):
        return Path(s[1].upper() + ":/" + s[3:])
    return Path(s)


class Stats:
    execs: list[str] = []
    shells = 0
    sftp_sessions = 0


class Server(ServerInterface):
    def __init__(self, cfg):
        self.cfg = cfg

    def get_allowed_auths(self, username):
        return "password,publickey"

    def check_auth_password(self, username, password):
        ok = username == self.cfg["user"] and password == self.cfg["password"]
        return paramiko.AUTH_SUCCESSFUL if ok else paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        ok = username == self.cfg["user"] and self.cfg.get("pubkey") is not None and \
            key.asbytes() == self.cfg["pubkey"].asbytes()
        return paramiko.AUTH_SUCCESSFUL if ok else paramiko.AUTH_FAILED

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_SUCCEEDED if kind == "session" else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_pty_request(self, *a):
        return True

    def check_channel_exec_request(self, channel, command):
        cmd = command.decode("utf-8", "replace")
        Stats.execs.append(cmd)
        threading.Thread(target=self._exec, args=(channel, cmd), daemon=True).start()
        return True

    def check_channel_shell_request(self, channel):
        Stats.shells += 1
        threading.Thread(target=self._shell, args=(channel,), daemon=True).start()
        return True

    def _exec(self, chan, cmd):
        env = {**os.environ, "HOME": self.cfg["home_msys"], "LANG": "C.UTF-8"}
        p = subprocess.Popen([BASH, "-c", cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             stdin=subprocess.DEVNULL, cwd=str(self.cfg["root"]), env=env, creationflags=NO_WINDOW)

        def pump(stream, send):
            for b in iter(lambda: stream.read1(65536), b""):
                try:
                    send(b)
                except Exception:  # noqa: BLE001
                    break
        t1 = threading.Thread(target=pump, args=(p.stdout, chan.sendall), daemon=True)
        t2 = threading.Thread(target=pump, args=(p.stderr, chan.sendall_stderr), daemon=True)
        t1.start()
        t2.start()
        while p.poll() is None:
            if chan.closed:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True,
                               creationflags=NO_WINDOW)
                break
            try:
                p.wait(0.1)
            except subprocess.TimeoutExpired:
                pass
        t1.join(5)
        t2.join(5)
        try:
            chan.send_exit_status(p.wait())
            chan.close()
        except Exception:  # noqa: BLE001
            pass

    def _shell(self, chan):
        env = {**os.environ, "HOME": self.cfg["home_msys"], "LANG": "C.UTF-8"}
        p = subprocess.Popen([BASH, "-s"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
                             cwd=str(self.cfg["root"]), env=env, creationflags=NO_WINDOW)
        self.cfg.setdefault("procs", []).append(p)

        def out():
            for b in iter(lambda: p.stdout.read1(65536), b""):
                try:
                    chan.sendall(b)
                except Exception:  # noqa: BLE001
                    break
            try:
                chan.send_exit_status(p.wait())
                chan.close()
            except Exception:  # noqa: BLE001
                pass
        threading.Thread(target=out, daemon=True).start()
        while True:
            try:
                b = chan.recv(4096)
            except Exception:  # noqa: BLE001
                break
            if not b:
                break
            b = b.replace(b"\x03", b"").replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            try:
                p.stdin.write(b)
                p.stdin.flush()
            except OSError:
                break
        if p.poll() is None:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True, creationflags=NO_WINDOW)


class Handle(SFTPHandle):
    def stat(self):
        try:
            return SFTPAttributes.from_stat(os.fstat(self.readfile.fileno()))
        except OSError as e:
            return SFTPServer.convert_errno(e.errno)

    def chattr(self, attr):
        return SFTP_OK


def make_sftp(cfg):
    root = Path(cfg["root"]).resolve()

    class Stub(SFTPServerInterface):
        def session_started(self):
            Stats.sftp_sessions += 1

        def _real(self, path):
            p = from_msys(path).resolve()
            if p != root and root not in p.parents:
                raise PermissionError(path)
            return p

        def canonicalize(self, path):
            if path in (".", "", "./"):
                return cfg["home_msys"]
            if path.startswith("./"):
                path = cfg["home_msys"] + path[1:]
            return to_msys(from_msys(path)) if path.startswith("/") else cfg["home_msys"] + "/" + path

        def list_folder(self, path):
            try:
                rp = self._real(path)
                out = []
                for n in os.listdir(rp):
                    a = SFTPAttributes.from_stat(os.lstat(rp / n))
                    a.filename = n
                    out.append(a)
                return out
            except PermissionError:
                return SFTP_PERMISSION_DENIED
            except OSError as e:
                return SFTPServer.convert_errno(e.errno)

        def stat(self, path):
            try:
                return SFTPAttributes.from_stat(os.stat(self._real(path)))
            except PermissionError:
                return SFTP_PERMISSION_DENIED
            except OSError as e:
                return SFTPServer.convert_errno(e.errno)

        lstat = stat

        def open(self, path, flags, attr):
            try:
                rp = self._real(path)
                fd = os.open(rp, flags | getattr(os, "O_BINARY", 0), 0o666)
            except PermissionError:
                return SFTP_PERMISSION_DENIED
            except OSError as e:
                return SFTPServer.convert_errno(e.errno)
            if flags & (os.O_WRONLY | os.O_RDWR):
                mode = "ab" if flags & os.O_APPEND else ("r+b" if flags & os.O_RDWR else "wb")
            else:
                mode = "rb"
            f = os.fdopen(fd, mode)
            h = Handle(flags)
            h.filename = str(rp)
            h.readfile = f
            h.writefile = f
            return h

        def remove(self, path):
            try:
                os.remove(self._real(path))
            except OSError as e:
                return SFTPServer.convert_errno(e.errno)
            return SFTP_OK

        def rename(self, old, new):
            try:
                if self._real(new).exists():
                    return SFTP_FAILURE
                os.rename(self._real(old), self._real(new))
            except OSError as e:
                return SFTPServer.convert_errno(e.errno)
            return SFTP_OK

        def posix_rename(self, old, new):
            try:
                os.replace(self._real(old), self._real(new))
            except OSError as e:
                return SFTPServer.convert_errno(e.errno)
            return SFTP_OK

        def mkdir(self, path, attr):
            try:
                os.mkdir(self._real(path))
            except OSError as e:
                return SFTPServer.convert_errno(e.errno)
            return SFTP_OK

        def rmdir(self, path):
            try:
                os.rmdir(self._real(path))
            except OSError as e:
                return SFTPServer.convert_errno(e.errno)
            return SFTP_OK

        def chattr(self, path, attr):
            return SFTP_OK
    return Stub


class TestSSHServer:
    def __init__(self, root: Path, user="dev", password="s3cret", pubkey=None):
        self.cfg = {"root": root, "user": user, "password": password, "pubkey": pubkey,
                    "home_msys": to_msys(root)}
        self.host_key = paramiko.RSAKey.generate(2048)
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(10)
        self.port = self.sock.getsockname()[1]
        self.transports = []
        self._stop = False
        threading.Thread(target=self._accept, daemon=True).start()

    def _accept(self):
        while not self._stop:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            t = paramiko.Transport(conn)
            t.add_server_key(self.host_key)
            t.set_subsystem_handler("sftp", SFTPServer, make_sftp(self.cfg))
            self.transports.append(t)
            try:
                t.start_server(server=Server(self.cfg))
            except Exception:  # noqa: BLE001
                pass

    def stop(self):
        self._stop = True
        try:
            self.sock.close()
        except OSError:
            pass
        for t in self.transports:
            try:
                t.close()
            except Exception:  # noqa: BLE001
                pass
        for p in self.cfg.get("procs", []):
            if p.poll() is None:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True,
                               creationflags=NO_WINDOW)
