"""Drive the assembly GUI Bridge program over its stdin/stdout protocol."""
import subprocess
import sys
from pathlib import Path

folder = Path(sys.argv[1])
p = subprocess.Popen([str(folder / "_radapp.exe")], cwd=folder, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     text=True, bufsize=1)
answers = {"GET txtNumber Text": "41", "INPUT What is your name?": "Ali", "MSGBOX Hello from x64 assembly!": "1"}


def event(line):
    print(">>", line)
    p.stdin.write(line + "\n")
    p.stdin.flush()
    got = []
    while True:
        out = p.stdout.readline().rstrip("\r\n")
        if not out:
            if p.poll() is not None:
                break
            continue
        print("<<", out)
        got.append(out)
        if out == "DONE":
            break
        if out in answers:
            p.stdin.write(answers[out] + "\n")
            p.stdin.flush()
    return got


ok = True
g = event("EVENT Form1 Load")
ok &= any(x.startswith("SET lblMessage Text Hello from assembly!") for x in g)
g = event("EVENT btnAdd Click")
ok &= "SET txtNumber Text 42" in g and "SET lblClicks Text 1" in g
g = event("EVENT btnAdd Click")
ok &= "SET lblClicks Text 2" in g
g = event("EVENT btnHello Click")
ok &= "SET lblMessage Text Ali" in g
g = event("EVENT lblMessage Click")          # no handler: only DONE
ok &= g == ["DONE"]
p.stdin.write("QUIT\n")
p.stdin.flush()
p.wait(timeout=5)
print("exit", p.returncode, "RESULT", "OK" if ok else "FAIL")
