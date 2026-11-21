"""DOS toolchains: download each free compiler from its official source (skipped with a reason when offline),
check the SHA-256 record, find DOSBox-X, re-assemble the helper programs and compare with the embedded bytes."""
from __future__ import annotations

import json
import sys

from _common import WORK, check, online, skip, summary

from radide.retro.dos import helpers, toolchain as T


def main() -> int:
    net = online()
    for key, rel in T.RELEASES.items():
        name = f"toolchain {key} {rel.version}"
        exe = T.find(key)
        if not exe:
            if not net:
                skip(name, "offline and not installed")
                continue
            ok = T.install(key, log=lambda t: print("   ", t))
            exe = T.find(key)
            check(name + " downloaded", ok and exe, exe)
        else:
            check(name + " installed", exe, exe)
        src = T.tool_dir(key) / "RADIDE-SOURCE.json"
        if src.is_file():
            data = json.loads(src.read_text(encoding="utf-8"))
            check(name + " SHA-256 recorded", data.get("sha256") == rel.sha256 and data.get("url") == rel.url, data)
        elif key == "innoextract":
            skip(name + " SHA-256 recorded", "shared copy installed by the Lazarus support")
    check("Free Pascal 8086 small-model units", T.fpc_units("small"), T.fpc_units("small"))
    check("Open Watcom 16-bit DOS libraries", (T.tool_dir("openwatcom") / "lib286" / "dos").is_dir())
    check("FreeBASIC DOS runtime library", (T.tool_dir("freebasic") / "lib" / "dos" / "libfb.a").is_file())
    exe = T.dosbox_exe(download=net)
    if exe:
        check("DOSBox-X found through radide.retro.emu", exe.lower().endswith("dosbox-x.exe"), exe)
    else:
        skip("DOSBox-X found through radide.retro.emu", "offline and not installed")
    jw = T.jwasm_exe()
    if jw:
        built = helpers.assemble_sources(jw, WORK / "helpers")
        for n in ("RADKEYS.COM", "RADSCR.COM", "RADCAP.COM", "RADMOUSE.COM"):
            check(f"helper {n} = JWasm build of helpers_src", built.get(n) == helpers.com_bytes(n),
                  (len(built.get(n, b"")), len(helpers.com_bytes(n))))
    else:
        skip("helpers re-assembled", "JWasm not installed")
    # user tools: proprietary compilers are configured, never downloaded
    cfg = WORK / "dos-config.json"
    import os
    os.environ["RADIDE_DOS_CONFIG"] = str(cfg)
    fake = WORK / "fakeqb"
    fake.mkdir(exist_ok=True)
    (fake / "QBASIC.EXE").write_bytes(b"MZ")
    T.set_user_path("qbasic", str(fake))
    check("own QBASIC.EXE folder is found", T.user_tool("qbasic").upper().endswith("QBASIC.EXE"), T.user_tool("qbasic"))
    from radide.retro.dos.run import qbasic_command
    mount, cmd = qbasic_command({"main": "MAIN.BAS"})
    check("Run in My QBasic: QBASIC.EXE /RUN MAIN.BAS from drive D:", mount == str(fake) and
          cmd == "D:\\QBASIC.EXE /RUN MAIN.BAS", (mount, cmd))
    T.set_user_path("qbasic", "")
    from radide.retro.dos import dosbox
    conf = dosbox.write_conf(dosbox.DosRun(mounts=[("C", WORK)], commands=["GAME.EXE"], cycles="286",
                                           debugger=True, keep_window=True), WORK / "dbg.conf").read_text()
    check("DOSBox-X debugger run: DEBUGBOX + cycles preset + keep window",
          "debugbox GAME.EXE" in conf and "cycles=fixed 2000" in conf and "type EXIT" in conf, conf)
    check("proprietary tools have no download entry", not ({"qbasic", "quickbasic", "turbopascal", "turboc"} &
                                                          set(T.RELEASES)))
    del os.environ["RADIDE_DOS_CONFIG"]
    return summary()


if __name__ == "__main__":
    sys.exit(main())
