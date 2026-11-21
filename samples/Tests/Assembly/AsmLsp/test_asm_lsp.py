"""asm-lsp: install from the official GitHub release on request, use it through RAD IDE's LSP client, and keep
the built-in assembly IntelliSense as the fallback (radide/asm_intel/lsp.py).

1. Install plan: the pinned release (RELEASE) and its prebuilt archives for Linux x86-64 / macOS; on Windows
   (no Windows binary in the release) the release tag is built with cargo from the official repository.
2. Online (skipped offline): the GitHub API's asset list of the release equals the pinned names + SHA-256
   digests and has no Windows asset; the Linux archive is really downloaded from the release, verified and
   unpacked (``_download_release`` into a temporary tools folder - the binary is not run).
3. The LSP client: the asm-lsp found by the IDE (``server_command``) - or, when it is not installed, a stand-in
   server (standin_asm_lsp.py) - is started by ``radide.lsp.LspClient`` for a ``rad-asm-nasm`` editor:
   initialize, didOpen, hover on ``mov``, completion; ``radide.lsp.server_command("rad-asm-nasm")`` resolves
   to ``tools\\asm-lsp\\bin\\asm-lsp.exe`` once it exists.
4. Fallback: QSettings ``asm/useAsmLsp = false`` -> no server; the built-in provider still completes and hovers.

    python samples/Tests/Assembly/AsmLsp/test_asm_lsp.py
"""
import json
import shutil
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))

from PyQt6.QtCore import QCoreApplication, QSettings            # noqa: E402

QCoreApplication.setOrganizationName("RADIDE-TEST")
QCoreApplication.setApplicationName("RADIDE-TEST")
app = QCoreApplication.instance() or QCoreApplication(sys.argv[:1])

from radide import lsp as lspmod                                  # noqa: E402
from radide.asm_intel import lsp as asm_lsp                       # noqa: E402

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""), flush=True)


def wait(cond, timeout=20.0):
    end = time.time() + timeout
    while time.time() < end:
        app.processEvents()
        if cond():
            return True
        time.sleep(0.02)
    return False


QSettings("RADIDE-TEST", "RADIDE-TEST").clear()

# ---------------------------------------------------------------- 1. install plan
import platform  # noqa: E402

orig_platform, orig_machine = sys.platform, platform.machine
try:
    sys.platform, platform.machine = "linux", (lambda: "x86_64")
    linux = asm_lsp.release_asset()
    sys.platform, platform.machine = "darwin", (lambda: "arm64")
    mac = asm_lsp.release_asset()
    sys.platform, platform.machine = "win32", (lambda: "AMD64")
    win = asm_lsp.release_asset()
finally:
    sys.platform, platform.machine = orig_platform, orig_machine
check("release archive for Linux x86-64", linux and linux[0] == "asm-lsp-x86_64-unknown-linux-gnu.tar.gz", str(linux))
check("release archive for macOS arm64", mac and mac[0] == "asm-lsp-aarch64-apple-darwin.tar.gz", str(mac))
check("no release archive for Windows -> cargo build of the release tag", win is None)
cmd = asm_lsp.install_command()
check("Windows install command builds the official repository at the release tag",
      cmd[1:3] == ["install", "--git"] and cmd[3] == "https://github.com/bergercookie/asm-lsp" and
      cmd[cmd.index("--tag") + 1] == f"v{asm_lsp.RELEASE}" and "--locked" in cmd, " ".join(cmd))
check("asset URL is the GitHub release download",
      asm_lsp.asset_url("x.tar.gz") == f"https://github.com/bergercookie/asm-lsp/releases/download/v{asm_lsp.RELEASE}/x.tar.gz")

# ---------------------------------------------------------------- 2. online: release metadata + a real download
try:
    req = urllib.request.Request(f"https://api.github.com/repos/bergercookie/asm-lsp/releases/tags/v{asm_lsp.RELEASE}",
                                 headers={"User-Agent": "RAD-IDE-test", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        rel = json.loads(r.read().decode("utf-8"))
except OSError as e:
    rel = None
    print(f"SKIP online checks: {e}")
if rel is not None:
    assets = {a["name"]: (a.get("digest") or "").replace("sha256:", "") for a in rel.get("assets", [])}
    pinned = {n: h for n, h in asm_lsp.ASSETS.values()}
    check("pinned archives + SHA-256 = the release's assets on GitHub", all(assets.get(n) == h for n, h in pinned.items()),
          ", ".join(f"{n}: {'ok' if assets.get(n) == h else assets.get(n)}" for n, h in pinned.items()))
    check("the release has no Windows binary (why Windows builds it)",
          not any("windows" in n.lower() or n.lower().endswith(".exe") for n in assets), ", ".join(assets))
    tmp = Path(tempfile.mkdtemp(prefix="asm-lsp-dl-"))
    saved = asm_lsp.ASM_LSP_DIR
    asm_lsp.ASM_LSP_DIR = tmp
    try:
        logs = []
        name, sha = asm_lsp.ASSETS[("linux", "x86_64")]
        ok = asm_lsp._download_release(name, sha, logs.append)
        binary = tmp / "bin" / "asm-lsp"
        check("download + SHA-256 check + unpack of the Linux release archive",
              ok and binary.is_file() and binary.read_bytes()[:4] == b"\x7fELF", "; ".join(logs)[-200:])
        bad = asm_lsp._download_release(name, "0" * 64, logs.append)
        check("a file with another SHA-256 is refused and deleted", not bad and "mismatch" in logs[-1] and
              not (tmp / "_download" / name).exists(), logs[-1][:120])
    finally:
        asm_lsp.ASM_LSP_DIR = saved
        shutil.rmtree(tmp, ignore_errors=True)

# ---------------------------------------------------------------- 3. the LSP client
real = asm_lsp.find_asm_lsp()
argv = [real] if real else [sys.executable, "-u", str(HERE / "standin_asm_lsp.py")]
print(f"server: {'asm-lsp ' + real if real else 'stand-in (asm-lsp is not installed here)'}")
work = Path(tempfile.mkdtemp(prefix="asm-lsp-ws-"))
src = work / "main.asm"
text = "global main\nsection .text\nmain:\n    mov rax, 1\n    add rax, 2\n    ret\n"
src.write_text(text, encoding="utf-8")
client = lspmod.LspClient("rad-asm-nasm", work, argv)
ready = []
client.ready.connect(lambda: ready.append(1))
check("LspClient starts the server", client.start())
check("initialize answered", wait(lambda: ready, 30), str(client.capabilities)[:120])
client.did_open(src, text, lspmod.LANGUAGE_IDS.get("rad-asm-nasm", "asm") if hasattr(lspmod, "LANGUAGE_IDS") else "asm")
hov, comp = [], []
client.hover(src, 3, 5, hov.append)
wait(lambda: hov, 20)
check("hover on 'mov' comes from the server", bool(hov) and "mov" in hov[0].lower(), (hov[0] if hov else "")[:100])
client.completion(src, text, 4, 6, comp.append)
wait(lambda: comp, 20)
check("completion items come from the server", bool(comp) and any(i["label"].lower().startswith("add") for i in comp[0]),
      f"{len(comp[0]) if comp else 0} items")
client.stop()
wait(lambda: not client.running(), 5)

# server_command finds tools\asm-lsp\bin\asm-lsp.exe (a placeholder file: it is not started)
tmp_tools = Path(tempfile.mkdtemp(prefix="asm-lsp-tools-"))
saved = asm_lsp.ASM_LSP_DIR
asm_lsp.ASM_LSP_DIR = tmp_tools
try:
    if not real:
        (tmp_tools / "bin").mkdir(parents=True)
        (tmp_tools / "bin" / ("asm-lsp" + asm_lsp.EXE)).write_bytes(b"")
        found = lspmod.server_command("rad-asm-nasm")
        check("radide.lsp.server_command('rad-asm-nasm') -> tools\\asm-lsp\\bin\\asm-lsp",
              bool(found) and Path(found[0]).parent == tmp_tools / "bin", str(found))
    check("one server for all four assembly editors (SERVER_GROUP)",
          {lspmod.server_key(f"rad-asm-{d}") for d in ("nasm", "masm", "fasm", "gas")} == {"rad-asm"})
    # ---------------------------------------------------------------- 4. fallback
    s = QSettings("RADIDE-TEST", "RADIDE-TEST")
    s.setValue("asm/useAsmLsp", False)
    s.sync()
    check("asm/useAsmLsp = false -> no server", asm_lsp.server_command() is None and
          lspmod.server_command("rad-asm-nasm") is None)
finally:
    asm_lsp.ASM_LSP_DIR = saved
    shutil.rmtree(tmp_tools, ignore_errors=True)
    QSettings("RADIDE-TEST", "RADIDE-TEST").clear()

from radide.languages import get_plugin  # noqa: E402
plugin = get_plugin("asm-nasm")
items = plugin.completions(text, 3, 6, str(src), None)
check("built-in provider still completes (fallback)", any(c.name.lower() == "mov" for c in items), f"{len(items)} items")
h = plugin.hover(text, 3, 5, str(src), None) if hasattr(plugin, "hover") else ""
check("built-in provider still hovers (fallback)", bool(h) and "mov" in str(h).lower(), str(h)[:80])
shutil.rmtree(work, ignore_errors=True)

passed = sum(1 for _n, ok in results if ok)
print(f"\n{passed} / {len(results)} checks passed")
print("RESULT", "OK" if passed == len(results) else "FAIL")
sys.exit(0 if passed == len(results) else 1)
