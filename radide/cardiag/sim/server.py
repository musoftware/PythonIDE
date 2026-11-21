"""The Demo car as a Wi-Fi ELM327 adapter: a TCP server (default 127.0.0.1:35000) where every connection gets
its own ELM327 interpreter in front of the same virtual car. Other OBD apps that support Wi-Fi adapters can
connect to it; RAD IDE's own Wi-Fi option and pyserial's ``socket://127.0.0.1:35000`` work too."""
from __future__ import annotations

import socket
import threading

from .elm import ElmInterpreter

DEFAULT_PORT = 35000


class DemoCarServer:
    def __init__(self, car, host: str = "127.0.0.1", port: int = DEFAULT_PORT, stn: str | None = None, log=None):
        self.car, self.host, self.port, self.stn = car, host, port, stn
        self.log = log
        self.sock: socket.socket | None = None
        self.thread: threading.Thread | None = None
        self.clients: list[socket.socket] = []
        self._stop = threading.Event()

    @property
    def running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def start(self) -> int:
        """Start listening; returns the port (pass port=0 for a free one)."""
        if self.running:
            return self.port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.host, self.port))
        s.listen(4)
        s.settimeout(0.2)
        self.sock = s
        self.port = s.getsockname()[1]
        self._stop.clear()
        self.thread = threading.Thread(target=self._serve, name="radide-demo-car-server", daemon=True)
        self.thread.start()
        if self.log is not None:
            self.log.info("sim", f"Demo car server listening on {self.host}:{self.port}")
        return self.port

    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                conn, addr = self.sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            self.clients.append(conn)
            if self.log is not None:
                self.log.info("sim", f"client connected: {addr[0]}:{addr[1]}")
            threading.Thread(target=self._client, args=(conn,), daemon=True).start()

    def _client(self, conn: socket.socket) -> None:
        interp = ElmInterpreter(self.car, stn=self.stn)
        conn.settimeout(0.02)
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        try:
            while not self._stop.is_set():
                try:
                    data = conn.recv(4096)
                    if data == b"":
                        break
                    interp.feed(data)
                except socket.timeout:
                    pass
                out = interp.read(0)
                if out:
                    conn.sendall(out)
        except OSError:
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass
            if conn in self.clients:
                self.clients.remove(conn)

    def stop(self) -> None:
        self._stop.set()
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
        for c in list(self.clients):
            try:
                c.close()
            except OSError:
                pass
        if self.thread is not None:
            self.thread.join(timeout=2)
        self.thread = None
        if self.log is not None:
            self.log.info("sim", "Demo car server stopped")
