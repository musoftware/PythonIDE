"""A tiny stdio language server that answers like asm-lsp (initialize, didOpen/didChange, hover, completion).

Used by test_asm_lsp.py to exercise RAD IDE's LSP client path for assembly (radide/lsp.py LspClient with the
rad-asm-* editors) on machines where the real asm-lsp is not installed. It knows a few x86 instructions only.
"""
import json
import sys

DOCS = {"mov": "MOV - Move: copies the second operand to the first.",
        "add": "ADD - Add: adds the second operand to the first.",
        "push": "PUSH - Push a value onto the stack."}


def send(msg):
    body = json.dumps(msg).encode("utf-8")
    sys.stdout.buffer.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)
    sys.stdout.buffer.flush()


def read():
    headers = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        line = line.strip()
        if not line:
            break
        k, _, v = line.decode("ascii").partition(":")
        headers[k.strip().lower()] = v.strip()
    n = int(headers.get("content-length", "0"))
    return json.loads(sys.stdin.buffer.read(n).decode("utf-8"))


docs = {}
while True:
    msg = read()
    if msg is None:
        break
    method, mid, params = msg.get("method"), msg.get("id"), msg.get("params") or {}
    if method == "initialize":
        send({"jsonrpc": "2.0", "id": mid, "result": {
            "capabilities": {"hoverProvider": True, "completionProvider": {"triggerCharacters": []},
                             "textDocumentSync": 1},
            "serverInfo": {"name": "asm-lsp (stand-in)", "version": "test"}}})
    elif method in ("textDocument/didOpen", "textDocument/didChange"):
        td = params["textDocument"]
        text = td.get("text") if method.endswith("didOpen") else params["contentChanges"][-1]["text"]
        docs[td["uri"]] = text
    elif method == "textDocument/hover":
        lines = docs.get(params["textDocument"]["uri"], "").splitlines()
        ln, col = params["position"]["line"], params["position"]["character"]
        word = ""
        if ln < len(lines):
            s = lines[ln]
            a = col
            while a > 0 and (s[a - 1].isalnum() or s[a - 1] == "_"):
                a -= 1
            b = col
            while b < len(s) and (s[b].isalnum() or s[b] == "_"):
                b += 1
            word = s[a:b].lower()
        doc = DOCS.get(word)
        send({"jsonrpc": "2.0", "id": mid,
              "result": {"contents": {"kind": "markdown", "value": f"**{word}** (asm-lsp)\n\n{doc}"}} if doc else None})
    elif method == "textDocument/completion":
        send({"jsonrpc": "2.0", "id": mid, "result": {"isIncomplete": False, "items": [
            {"label": k, "kind": 14, "detail": "asm-lsp", "documentation": v} for k, v in DOCS.items()]}})
    elif method == "shutdown":
        send({"jsonrpc": "2.0", "id": mid, "result": None})
    elif method == "exit":
        break
    elif mid is not None:
        send({"jsonrpc": "2.0", "id": mid, "result": None})
