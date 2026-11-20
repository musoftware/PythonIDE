# SSH test server (Remote - SSH)

A tiny in-process SSH server (paramiko: password + public-key auth, exec, shell, SFTP) that serves `site/`, so the
remote features can be tried on Windows without a Linux machine. The IDE's automated test used the same server.

What it shows: File > Open Remote > Connect to SSH Host, the host-key prompt, the Remote Explorer (browse, new
file/folder, rename, delete, upload, download), editing over SFTP with the local cache and the conflict check,
Run / Build on the remote side with output in Output, remote Search (grep on the server), the remote terminal
(a tab of the Terminal dock) and the polling watcher (edit `site/main.py` in Notepad: the open tab reloads).

How to try it:
1. `.venv\Scripts\python.exe samples\Tests\Remote\SSH_TestServer\run_server.py` (needs Git Bash; it prints the port).
2. In RAD IDE: File > Open Remote > Connect to SSH Host... - host `127.0.0.1`, that port, user `dev`,
   password `s3cret`, folder `~`. Accept the host key.
3. Double-click `main.py`, edit, Ctrl+S (uploads). Remote Explorer > Build asks for a command (`make` is guessed;
   use `make || echo build-ok` if make is missing). Terminal button: type `ls`, `pwd`.

Paths on this test server are Git Bash paths (`/c/Users/...`), which is how the server maps the remote file
system onto the Windows folder. A real Linux server shows normal paths (`/home/you/...`).
