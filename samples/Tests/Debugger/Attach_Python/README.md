# Attach_Python

**Debug > Attach to Process (Python, debugpy)** - `worker.py` prints a tick every half second forever.

**Try it:**
1. Start it outside the IDE: `python -u worker.py` (any Python 3.8+; debugpy is injected by the IDE).
2. Open this project, open `worker.py`, F9 on line 6 (`doubled = count * 2`).
3. Debug > Attach to Process... (Ctrl+Alt+P), filter `python`, pick the worker (Automatic = debugpy), Attach.
   It stops on line 6: Locals shows `count`; F5 continues to the next tick.
4. Stop (Shift+F5) detaches: the worker keeps running. Close its console window to end it.

A venv `python.exe` is only a launcher: the IDE attaches to its child (the real interpreter) automatically.
