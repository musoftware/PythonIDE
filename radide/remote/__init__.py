"""Remote development: SSH/SFTP hosts, WSL distributions and Dev Containers behind one RemoteFS interface
(radide/remote/base.py).  The IDE side (File > Open Remote, Remote Explorer, remote editor tabs, remote
terminal, Run/Build, Search, polling watcher) is radide/features/remote.py.

    from radide.remote import SSHFS, WSLFS, DevContainer, DevContainerFS
    fs = SSHFS("example.com", "me", password="...").connect()   # UnknownHostKey -> ask, connect(trust=e.key)
    fs.listdir(fs.root); fs.read(path); fs.write(path, data); fs.exec("make", cwd=fs.root)
"""
from __future__ import annotations

from .base import Entry, RemoteError, RemoteFS, SearchHit, ShellBackend
from .devcontainer import DevContainer, DevContainerFS, docker_status, find_config
from .ssh import SSHFS, ChangedHostKey, UnknownHostKey, fingerprint
from .watcher import PollingWatcher
from .wsl import WSLFS, distros, parse_unc, unc_path

__all__ = ["Entry", "RemoteError", "RemoteFS", "SearchHit", "ShellBackend", "DevContainer", "DevContainerFS",
           "docker_status", "find_config", "SSHFS", "ChangedHostKey", "UnknownHostKey", "fingerprint",
           "PollingWatcher", "WSLFS", "distros", "parse_unc", "unc_path"]
