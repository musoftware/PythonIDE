r"""Start a local SSH + SFTP test server (paramiko) so File > Open Remote can be tried without a real Linux host.
Serves the folder ./site; commands run with Git Bash. Stop with Ctrl+C.

    .venv\Scripts\python.exe samples\Tests\Remote\SSH_TestServer\run_server.py
"""
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from sshserver import BASH, TestSSHServer, to_msys  # noqa: E402

if not Path(BASH).is_file():
    sys.exit(f"Git Bash was not found at {BASH} - the test server runs remote commands with it.")
srv = TestSSHServer(HERE / "site", user="dev", password="s3cret")
print(f"SSH test server on 127.0.0.1 port {srv.port}")
print("File > Open Remote > Connect to SSH Host...: host 127.0.0.1, port above, user dev, password s3cret,")
print(f"folder {to_msys(HERE / 'site')}  (or ~). Accept the host key once. Ctrl+C stops the server.")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    pass
finally:
    srv.stop()
