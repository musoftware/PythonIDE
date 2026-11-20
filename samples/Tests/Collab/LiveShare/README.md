# Live Share tests (real-time collaboration)

Tests for **Share > Start Collaboration Session** (`radide/collab/*`, `radide/features/live_share.py`).
`project/` is the small folder that gets shared. Each test copies it to a temp folder first, so the sample
itself is never edited.

| Test | What it checks |
|---|---|
| `test_crdt_ot.py` | OT transform property TP1 (3000 random cases), the Jupiter Python<->Monaco link (400 random runs with crossing messages), and pycrdt (Yjs) convergence of 3 replicas with **out-of-order** delivery plus the Yjs sync step. All runs use Arabic and emoji. |
| `test_session.py` | Host and 2 guests over real WebSockets on localhost, no UI. Covers a wrong password and a wrong code being refused, the file tree, 268 random concurrent edits from 3 replicas converging, cursor broadcast, Arabic chat, the shared terminal, read-only **enforced by the host** (a bypassing edit is refused and the guest is reset), a `../` path being refused, leave and end. |
| `test_plain_editor.py` | The binding for the built-in (non-Monaco) editor: random concurrent edits converge. |
| `test_live_share.py` | **Two RAD IDE main windows** (host and guest) in one process, using real Monaco editors. Covers a wrong password, join, the shared tree, a `[Live]` tab, 180 concurrent random Monaco edits on both sides (inserts and deletes, Arabic and emoji) converging in both CRDTs, both Monaco models and both Python mirrors. Also covers remote cursor and selection decorations, chat, the shared Output/Terminal, follow mode, read-only (editor locked, host refuses, guest reverted), the Arabic UI, leave, rejoin and end. It saves `widget.grab()` screenshots of both IDE windows. |

Run from the repository root:

```
.venv\Scripts\python.exe samples\Tests\Collab\LiveShare\test_crdt_ot.py
.venv\Scripts\python.exe samples\Tests\Collab\LiveShare\test_session.py
.venv\Scripts\python.exe samples\Tests\Collab\LiveShare\test_plain_editor.py
.venv\Scripts\python.exe samples\Tests\Collab\LiveShare\test_live_share.py <out_dir> [--onscreen]
```

`test_live_share.py` runs on the offscreen platform by default. The offscreen platform has no fonts and paints
web views blank, so pass `--onscreen` to get meaningful screenshots. The two windows are closed at the end.

Requirements: `pip install pycrdt` (the Yjs CRDT). `PyQt6.QtWebSockets` ships with PyQt6.

## Using it in the IDE

1. Host: **Share > Start Collaboration Session...** Choose your name and the shared folder (the project folder
   by default), and optionally a password and "Guests join read-only". The invite link
   `radide-collab://<lan-ip>:47820/<CODE>` is copied to the clipboard.
2. Guest (another RAD IDE on the LAN): **Share > Join Collaboration Session...** Paste the link and enter the
   password.
3. Double-click a file in the Live Share window's *Shared files* to open it in a `[Live]` tab and edit together.
   Each participant's cursor and selection shows in their colour.
4. Double-click a participant, or use **Share > Follow Participant**, to follow them.
5. The host's Terminal and Output appear read-only in the guest's *Shared Terminal* tab.
6. Host: use the *Read-only* column or **Share > Guests Read-only**. Guest: **Save Shared File on Host**
   (also in the editor's context menu).
7. **End Collaboration Session** (host) or **Leave Collaboration Session** (guest).
