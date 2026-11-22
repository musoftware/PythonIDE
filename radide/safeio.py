"""Safe file writing for the IDE's own saves (forms, code files, project.radproj, .radsln, recovery).

    atomic_write_text(path, text)    the new content goes to a temporary file in the same folder, is flushed
                                     to the disk (fsync) and then replaces the old file in one step
                                     (os.replace = MoveFileEx REPLACE_EXISTING). A crash, a killed process,
                                     a full disk or a locked file therefore leaves either the old or the new
                                     file - never a truncated one - and no temporary file behind.
    atomic_write_bytes(path, data)   the same for bytes.
    SaveError                        an OSError whose message says what happened in words a user understands
                                     (disk full, read-only, locked by another program, path too long) and
                                     what to do; the original errno / winerror are kept.
    describe(exc, path)              that message for any OSError.
    check_open_size(path)            a file too large to open in an editor (default 256 MB) raises SaveError
                                     instead of reading a gigabyte into memory.
    backup_previous(path)            the last saved version of a file is copied (small files only) to
                                     %LOCALAPPDATA%\\RADIDE\\recovery\\backups\\<folder hash>\\ before it is
                                     replaced - nothing is written into the project folder.

No Qt import: usable from runtimes, tests and the IDE."""
from __future__ import annotations

import errno
import hashlib
import os
import time
from pathlib import Path

TMP_SUFFIX = ".radtmp"
MAX_OPEN_BYTES = 256 * 1024 * 1024
BACKUP_MAX_BYTES = 4 * 1024 * 1024

# Windows error codes
_SHARING = {32, 33}                 # ERROR_SHARING_VIOLATION, ERROR_LOCK_VIOLATION
_ACCESS = {5}                       # ERROR_ACCESS_DENIED (read-only file/folder, file opened without delete share)
_DISK_FULL = {112, 39}              # ERROR_DISK_FULL, ERROR_HANDLE_DISK_FULL
_TOO_LONG = {206, 3}                # ERROR_FILENAME_EXCED_RANGE, ERROR_PATH_NOT_FOUND (long path, no support)


class SaveError(OSError):
    """A failed save / open with a readable message (str(e)); .path is the file."""

    def __init__(self, message: str, path=None, cause: BaseException | None = None):
        code = getattr(cause, "errno", None) or errno.EIO
        super().__init__(code, message)
        self.message = message
        self.path = str(path) if path is not None else ""
        self.cause = cause
        self.winerror = getattr(cause, "winerror", None)

    def __str__(self) -> str:
        return self.message


class SavePermissionError(SaveError, PermissionError):
    """Access denied / read-only / locked (also an ordinary PermissionError)."""


def _error(exc: BaseException, path) -> SaveError:
    cls = SavePermissionError if isinstance(exc, PermissionError) or _kind(exc) in ("access", "locked",
                                                                                     "readonly") else SaveError
    return cls(describe(exc, path), path, exc)


def _kind(exc: BaseException) -> str:
    win = getattr(exc, "winerror", None)
    en = getattr(exc, "errno", None)
    if win in _DISK_FULL or en in (errno.ENOSPC, getattr(errno, "EDQUOT", -1)):
        return "full"
    if win in _SHARING:
        return "locked"
    if en == errno.EROFS:
        return "readonly"
    if win in _ACCESS or en in (errno.EACCES, errno.EPERM):
        return "access"
    if win == 206 or en == errno.ENAMETOOLONG:
        return "long"
    return "other"


def _held_by_other(path: str) -> bool:
    """Another process has *path* open without sharing write access (CreateFileW -> ERROR_SHARING_VIOLATION;
    Python's open() reports that only as EACCES)."""
    if os.name != "nt":
        return False
    try:
        import ctypes
        from ctypes import wintypes as wt
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        k.CreateFileW.restype = wt.HANDLE
        k.CreateFileW.argtypes = [wt.LPCWSTR, wt.DWORD, wt.DWORD, ctypes.c_void_p, wt.DWORD, wt.DWORD, wt.HANDLE]
        h = k.CreateFileW(str(path), 0x40000000, 0x7, None, 3, 0x80, None)   # GENERIC_WRITE, share all, existing
        if h == wt.HANDLE(-1).value:
            return ctypes.get_last_error() in _SHARING
        k.CloseHandle(h)
    except Exception:  # noqa: BLE001
        pass
    return False


def describe(exc: BaseException, path=None) -> str:
    """A message for a failed save of *path* that a user can act on."""
    p = str(path or getattr(exc, "filename", "") or "")
    kind = _kind(exc)
    if kind == "access" and p and os.path.isfile(p) and os.access(p, os.W_OK):
        # a replace refused although the file is writable: another program has it open without sharing
        # (Excel opens with FILE_SHARE_READ only) - opening it for writing tells
        if _held_by_other(p):
            kind = "locked"
    if kind == "full":
        return (f"Could not save {p}: the disk is full.\nFree some space (or save to another drive) and save "
                f"again. The file on disk was not changed.")
    if kind == "locked":
        return (f"Could not save {p}: the file is locked by another program (for example Excel, an editor or "
                f"a running build).\nClose that program and save again. The file on disk was not changed.")
    if kind in ("access", "readonly"):
        ro = ""
        try:
            if p and os.path.exists(p) and not os.access(p, os.W_OK):
                ro = " (the file is read-only)"
            elif p and not os.access(os.path.dirname(p) or ".", os.W_OK):
                ro = " (the folder is read-only)"
        except OSError:
            pass
        return (f"Could not save {p}: access denied{ro}.\nThe file may be read-only, open in another program, "
                f"or in a folder you cannot write to (for example under Program Files). Use File > Save As "
                f"to save a copy somewhere else. The file on disk was not changed.")
    if kind == "long":
        return (f"Could not save {p}: the path is too long for Windows.\nMove the project to a shorter folder "
                f"(for example C:\\Projects). The file on disk was not changed.")
    return f"Could not save {p}: {getattr(exc, 'strerror', None) or exc}. The file on disk was not changed."


def _tmp_for(path: Path) -> Path:
    # hidden-looking name in the same folder (same volume: os.replace is atomic); the publish data scan
    # and the project tree skip names starting with "."
    return path.with_name(f".{path.name}.{os.getpid()}.{time.monotonic_ns() % 1_000_000:06d}{TMP_SUFFIX}")


def _replace(src: Path, dst: Path) -> None:
    """os.replace with a short retry: an indexer / antivirus / cloud sync client holds a file for a moment."""
    delays = (0.05, 0.1, 0.2, 0.4)
    for i in range(len(delays) + 1):
        try:
            os.replace(src, dst)
            return
        except PermissionError as e:
            if i == len(delays) or getattr(e, "winerror", None) not in (5, 32, 33):
                raise
            time.sleep(delays[i])


def atomic_write_bytes(path, data: bytes, *, backup: bool = False) -> None:
    path = Path(path)
    if path.exists() and not os.access(path, os.W_OK):
        e = PermissionError(errno.EACCES, f"{path.name} is read-only", str(path))
        raise _error(e, path) from None
    tmp = _tmp_for(path)
    try:
        f = open(tmp, "wb")  # noqa: SIM115
    except PermissionError as e:
        # a folder whose ACL lets the user change files but not create new ones: the only way left is
        # writing the file in place (not atomic, but the size is checked afterwards)
        if path.is_file() and getattr(e, "winerror", None) in (None, 5):
            _write_in_place(path, data, backup)
            return
        raise _error(e, path) from e
    except OSError as e:
        raise _error(e, path) from e
    try:
        with f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
    except OSError as e:
        _remove(tmp)
        raise _error(e, path) from e
    except BaseException:
        _remove(tmp)
        raise
    if backup:
        backup_previous(path)
    try:
        _replace(tmp, path)
    except OSError as e:
        _remove(tmp)
        raise _error(e, path) from e


def _write_in_place(path: Path, data: bytes, backup: bool) -> None:
    saved = backup_previous(path)               # always: this write is not atomic
    try:
        with open(path, "r+b") as f:
            f.write(data)
            f.truncate()
            f.flush()
            os.fsync(f.fileno())
    except OSError as e:
        if saved is not None:                   # put the old content back
            try:
                with open(path, "wb") as f:
                    f.write(saved.read_bytes())
            except OSError:
                pass
        raise _error(e, path) from e


def atomic_write_text(path, text: str, encoding: str = "utf-8", errors: str = "strict", newline: str | None = None,
                      *, backup: bool = False) -> None:
    """Like Path.write_text (same newline translation: '\\n' -> os.linesep unless *newline* is given)."""
    nl = os.linesep if newline is None else newline     # exactly what a text-mode file does on write
    if nl not in ("", "\n"):
        text = text.replace("\n", nl)
    data = text.encode(encoding, errors)
    atomic_write_bytes(path, data, backup=backup)


def _remove(p: Path) -> None:
    try:
        os.remove(p)
    except OSError:
        pass


def clean_stale_temps(folder) -> int:
    """Temporary files left by a process that was killed during a save (older than a minute)."""
    n = 0
    try:
        for p in Path(folder).glob(f".*{TMP_SUFFIX}"):
            try:
                if time.time() - p.stat().st_mtime > 60:
                    p.unlink()
                    n += 1
            except OSError:
                pass
    except OSError:
        pass
    return n


def recovery_root() -> Path:
    from .paths import user_data_dir
    return user_data_dir() / "recovery"


def folder_key(folder) -> str:
    """A short stable key for a project folder (recovery and backup sub-folders)."""
    norm = os.path.normcase(os.path.abspath(str(folder)))
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:12]


def backup_previous(path) -> Path | None:
    """Copy the current (last saved) content of *path* to the backup folder; None when skipped."""
    path = Path(path)
    try:
        if not path.is_file() or path.stat().st_size > BACKUP_MAX_BYTES:
            return None
        dst = recovery_root() / "backups" / folder_key(path.parent) / path.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        data = path.read_bytes()
        tmp = _tmp_for(dst)
        tmp.write_bytes(data)
        os.replace(tmp, dst)
        return dst
    except OSError:
        return None                       # a backup must never make a save fail


def check_open_size(path, limit: int = MAX_OPEN_BYTES) -> None:
    """Raise SaveError for a file too large to load into an editor."""
    try:
        size = os.path.getsize(path)
    except OSError:
        return
    if size > limit:
        raise SaveError(f"{path} is too large to open in the editor ({size / 1048576:,.0f} MB; the limit is "
                        f"{limit / 1048576:,.0f} MB).\nOpen it with a tool made for large files.", path)


def read_text_guarded(path, encoding: str = "utf-8", errors: str = "strict", limit: int = MAX_OPEN_BYTES) -> str:
    check_open_size(path, limit)
    return Path(path).read_text(encoding=encoding, errors=errors)


__all__ = ["MAX_OPEN_BYTES", "SaveError", "SavePermissionError", "atomic_write_bytes", "atomic_write_text", "backup_previous",
           "check_open_size", "clean_stale_temps", "describe", "folder_key", "read_text_guarded",
           "recovery_root"]
