"""Running service functions: the shared base (preconditions, session, security, events) and the routine
runner (RoutineControl 0x31 start / poll results / stop, with progress, timeout and result interpretation).

Every function is blocking and meant to run in a worker thread; it reports through ``emit(Event)`` and stops
when ``client.cancelled`` is set (a running routine is then stopped with 31 02 first).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import definitions as D
from .text import BiText, bi, bi_of, pick
from .transport import Cancelled, NegativeResponse, NoResponse, ServiceClient, ServiceError


@dataclass
class Event:
    kind: str                       # log | progress | status | instruction | precondition | result | warning
    text: BiText = field(default_factory=lambda: BiText(""))
    progress: int | None = None
    data: dict = field(default_factory=dict)


@dataclass
class Precondition:
    index: int
    text: BiText
    automatic: bool = False
    ok: bool | None = None          # None = not checked / manual
    value: str = ""                 # what was read for an automatic check
    error: str = ""


@dataclass
class Result:
    ok: bool
    status: BiText
    progress: int | None = None
    values: list = field(default_factory=list)       # [(BiText name, str value)]
    error: ServiceError | None = None
    raw: bytes = b""
    data: dict = field(default_factory=dict)


_OPS = {"<": lambda a, b: a < b, "<=": lambda a, b: a <= b, ">": lambda a, b: a > b, ">=": lambda a, b: a >= b,
        "==": lambda a, b: a == b, "!=": lambda a, b: a != b, "in": lambda a, b: a in b}


class ServiceBase:
    def __init__(self, client: ServiceClient, pack: dict, *, plugin=None, emit=None):
        self.client = client
        self.pack = pack
        self.plugin = plugin
        self._emit = emit

    # ------------------------------------------------------------------ helpers
    def emit(self, kind: str, text: BiText | str = "", progress: int | None = None, **data) -> None:
        if self._emit is None:
            return
        if not isinstance(text, BiText):
            text = BiText(str(text), str(text))
        try:
            self._emit(Event(kind, text, progress, data))
        except Exception:  # noqa: BLE001 - the UI must not break the function
            pass

    def ecu(self, entry: dict):
        return D.ecu_of(self.pack, entry["ecu"])

    def prepare(self, entry: dict) -> None:
        """Enter the session the function needs and unlock security access (plug-in) when it asks for it."""
        ecu = self.ecu(entry)
        self.client.check_cancel()
        if entry.get("session"):
            self.emit("log", bi(f"Diagnostic session: {entry['session']}", f"جلسة التشخيص: {entry['session']}"))
            self.client.session(ecu, entry["session"])
        level = entry.get("security_level") or 0
        if level:
            self.emit("log", bi(f"Security access level {level} (plug-in)", f"وصول أمني مستوى {level} (إضافة)"))
            self.client.security_access(ecu, int(level), self.plugin)

    def read_did(self, ecu, did) -> tuple[bytes, object, dict | None]:
        did_i = D.ident(did)
        resp = self.client.request(ecu, bytes([0x22, did_i >> 8, did_i & 0xFF]), note="read DID")
        info = D.did_info(self.pack, did_i)
        raw = resp[3:]
        if info is not None and info.get("bytes"):
            raw = raw[:int(info["bytes"])]
        value = D.decode_value(info or {"type": "hex"}, raw)
        return raw, value, info

    def preconditions(self, entry: dict, check: bool = True) -> list[Precondition]:
        """The checklist of *entry*; automatic checks are read from the control unit when *check* is set."""
        out = []
        for i, pc in enumerate(entry.get("preconditions") or []):
            if isinstance(pc, str):
                pc = {"text": pc}
            item = Precondition(i, bi_of(pc, "text"), automatic=bool(pc.get("check")))
            if item.automatic and check:
                chk = pc["check"]
                try:
                    ecu = D.ecu_of(self.pack, chk.get("ecu") or entry["ecu"])
                    raw, value, info = self.read_did(ecu, chk["did"])
                    item.value = D.format_value(info or {}, value)
                    want = chk.get("value")
                    if isinstance(want, (int, float)) or (isinstance(want, list) and all(
                            isinstance(w, (int, float)) for w in want)):
                        value = D.numeric_value(info or {}, raw)
                    item.ok = bool(_OPS[chk["op"]](value, want))
                except ServiceError as e:
                    item.ok, item.error = False, str(e)
                except (KeyError, TypeError, ValueError) as e:
                    item.ok, item.error = False, str(e)
            out.append(item)
        return out

    def require(self, entry: dict, confirmed, *, enforce_checks: bool = True) -> list[Precondition]:
        """Stop with a readable error unless every manual item is confirmed and every automatic check passes."""
        items = self.preconditions(entry, check=True)
        confirmed = set(confirmed or [])
        missing = [it for it in items if not it.automatic and it.index not in confirmed]
        for it in items:
            if it.automatic:
                state = bi("(ok)", "(متحقق)") if it.ok else (bi("(not checked)", "(لم يُفحص)") if it.ok is None
                                                            else bi("(NOT MET)", "(غير متحقق)"))
            else:
                state = bi("(confirmed)", "(تم التأكيد)") if it.index in confirmed else bi("(not confirmed)", "(لم يُؤكَّد)")
            self.emit("precondition", it.text + (f"  [{it.value}]" if it.value else "") + "  " + state,
                      index=it.index, ok=it.ok, value=it.value)
        if missing:
            raise ServiceError(bi("Confirm every precondition first:\n- " + "\n- ".join(m.text.en for m in missing),
                                  "أكّد كل الشروط المسبقة أولًا:\n- " + "\n- ".join(m.text.get("ar") for m in missing)),
                               code="preconditions")
        failed = [it for it in items if it.automatic and it.ok is False]
        if failed and enforce_checks:
            raise ServiceError(bi(
                "Preconditions not met (read from the vehicle):\n- " + "\n- ".join(
                    f"{f.text.en} [{f.value or f.error}]" for f in failed),
                "الشروط المسبقة غير متحققة (قراءة من السيارة):\n- " + "\n- ".join(
                    f"{f.text.get('ar')} [{f.value or f.error}]" for f in failed)), code="preconditions")
        return items


class RoutineRunner(ServiceBase):
    """RoutineControl: start, poll results with progress until done / failed / timeout, stop on cancel."""

    def _ids(self, r: dict) -> tuple[bool, bytes]:
        kwp = self.ecu(r).protocol == "kwp"
        rid = D.hexbytes(r["rid"])
        return kwp, rid

    def _start_req(self, r, params: bytes) -> bytes:
        kwp, rid = self._ids(r)
        return (bytes([0x31]) + rid if kwp else bytes([0x31, 0x01]) + rid) + params

    def _results_req(self, r) -> bytes:
        kwp, rid = self._ids(r)
        return bytes([0x33]) + rid if kwp else bytes([0x31, 0x03]) + rid

    def _stop_req(self, r) -> bytes:
        kwp, rid = self._ids(r)
        params = D.hexbytes((r.get("stop") or {}).get("params", ""))
        return (bytes([0x32]) + rid if kwp else bytes([0x31, 0x02]) + rid) + params

    def _record(self, r, resp: bytes) -> bytes:
        kwp, rid = self._ids(r)
        return resp[1 + len(rid):] if kwp else resp[2 + len(rid):]

    def interpret(self, r: dict, record: bytes) -> list:
        out = []
        for f in r.get("results") or []:
            pos, n = int(f.get("byte", 0)), int(f.get("bytes", 1))
            chunk = record[pos:pos + n]
            if len(chunk) < n:
                continue
            value = D.decode_value(f, chunk)
            out.append((bi_of(f, "name"), D.format_value(f, value)))
        return out

    def _status_text(self, poll: dict, status: int) -> BiText:
        st = (poll.get("statuses") or {}).get(f"{status:02X}")
        if isinstance(st, dict):
            return BiText(st.get("en", ""), st.get("ar", ""))
        if isinstance(st, str):
            return BiText(st, st)
        return bi(f"status 0x{status:02X}", f"الحالة 0x{status:02X}")

    def stop(self, r: dict) -> None:
        try:
            self.client.request(self.ecu(r), self._stop_req(r), note="stop routine")
            self.emit("log", bi("Routine stopped (31 02).", "أُوقف الروتين (31 02)."))
        except ServiceError as e:
            self.emit("warning", bi("Stop routine failed: ", "فشل إيقاف الروتين: ") + e.text)

    def run(self, r: dict, confirmed=(), *, params: bytes | None = None, enforce_checks: bool = True) -> Result:
        ecu = self.ecu(r)
        self.client.context = {"action": "routine", "id": r["id"]}
        started = False
        try:
            self.require(r, confirmed, enforce_checks=enforce_checks)
            self.prepare(r)
            p = D.hexbytes(r.get("start_params", "")) if params is None else params
            self.emit("status", bi(f"Starting {r.get('name')}...", f"بدء {pick(r, 'name', 'ar')}..."), progress=0)
            resp = self.client.request(ecu, self._start_req(r, p), timeout=5.0, note="start routine")
            started = True
            record = self._record(r, resp)
            poll = r.get("poll")
            shown: set = set()
            self._instructions(r, 0, shown)
            if not poll:
                values = self.interpret(r, record)
                for name, v in values:
                    self.emit("result", name + f": {v}")
                done = bi("Completed.", "اكتمل.")
                self.emit("status", done, progress=100)
                return Result(True, done, 100, values, raw=resp)
            return self._poll(r, poll, record, shown)
        except Cancelled as e:
            if started:
                self.stop(r)
            self.emit("status", e.text)
            return Result(False, e.text, error=e)
        except ServiceError as e:
            if started and not isinstance(e, NegativeResponse):
                self.stop(r)
            self.emit("status", e.text)
            return Result(False, e.text, error=e)
        finally:
            self.client.back_to_default(ecu)
            self.client.context = {}

    def _instructions(self, r, progress: int, shown: set) -> None:
        for i, ins in enumerate(r.get("instructions") or []):
            if i not in shown and progress >= int(ins.get("at", 0)):
                shown.add(i)
                self.emit("instruction", bi_of(ins, "text"), progress=progress)

    def _poll(self, r: dict, poll: dict, record: bytes, shown: set) -> Result:
        ecu = self.ecu(r)
        clock, sleep = self.client.clock, self.client.sleep
        t0 = clock()
        timeout = float(poll.get("timeout_s", 120))
        interval = max(0.05, float(poll.get("interval_s", 1.0)))
        sb = int(poll.get("status_byte", 0))
        pb = poll.get("progress_byte")
        done = {int(x, 16) for x in poll.get("done") or []}
        failed = {int(x, 16) for x in poll.get("failed") or []}
        misses = 0
        last_progress = 0
        while True:
            self.client.check_cancel()
            if clock() - t0 > timeout:
                self.stop(r)
                err = ServiceError(bi(
                    f"The routine did not finish within {timeout:g} s (timeout). It was stopped; check the "
                    "conditions and try again.",
                    f"لم ينتهِ الروتين خلال {timeout:g} ثانية (انتهت المهلة). تم إيقافه؛ راجع الشروط وأعد المحاولة."),
                    code="timeout")
                self.emit("status", err.text, progress=last_progress)
                return Result(False, err.text, last_progress, self.interpret(r, record), error=err)
            sleep(interval)
            try:
                resp = self.client.request(ecu, self._results_req(r), note="routine results")
                misses = 0
            except NegativeResponse as e:
                if e.nrc in (0x21, 0x23, 0x24, 0x78):          # busy / not complete yet
                    continue
                raise
            except NoResponse:
                misses += 1
                self.emit("warning", bi(f"No answer to the results request ({misses}).",
                                        f"لا يوجد رد على طلب النتائج ({misses})."))
                continue
            record = self._record(r, resp)
            if len(record) <= sb:
                continue
            status = record[sb]
            if pb is not None and len(record) > int(pb):
                prog = record[int(pb)] * float(poll.get("progress_scale", 1))
                last_progress = max(0, min(100, int(prog)))
            elif status in done:
                last_progress = 100
            text = self._status_text(poll, status)
            self.emit("progress", text, progress=last_progress, status=status)
            self._instructions(r, last_progress, shown)
            if status in done:
                values = self.interpret(r, record)
                for name, v in values:
                    self.emit("result", name + f": {v}")
                self._instructions(r, 100, shown)
                same = str(getattr(text, "en", text)).strip().rstrip(".").lower() in ("completed", "complete", "done")
                fin = bi("Completed.", "اكتمل.") if same else bi("Completed: ", "اكتمل: ") + text
                self.emit("status", fin, progress=100)
                return Result(True, fin, 100, values, raw=resp)
            if status in failed:
                values = self.interpret(r, record)
                err = ServiceError(bi("The routine failed: ", "فشل الروتين: ") + text, code="routine_failed")
                self.emit("status", err.text, progress=last_progress)
                return Result(False, err.text, last_progress, values, error=err, raw=resp)
