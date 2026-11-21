"""ELM327 / STN11xx / OBDLink adapters: AT initialisation, protocol detection, header / filter management and
parsing of the adapter's text answers into complete service messages (``parse_response``).

The link always runs with headers on (``ATH1``), spaces on (``ATS1``) and CAN auto-formatting on: every line
then carries the sender's id and the ISO-TP PCI byte, so answers from several control units and multi-frame
answers (first frame + consecutive frames) are reassembled correctly. Answers with headers off (``014`` /
``0: 49 02 ...`` style) are understood too.
"""
from __future__ import annotations

import re
import time

from . import isotp, protocols
from .base import DiagLink, LinkError, Response
from .transport import Transport

# adapter messages -> (English, Arabic, error code)
ELM_ERRORS: dict[str, tuple[str, str, str]] = {
    "UNABLE TO CONNECT": ("The adapter found no protocol the car answers on. Is the ignition on and the adapter "
                          "fully plugged in?",
                          "لم يجد المحوّل بروتوكولًا ترد عليه السيارة. هل الإشعال يعمل والمحوّل مركّب جيدًا؟",
                          "unable_to_connect"),
    "BUS INIT": ("K-line initialisation failed (ISO 9141 / KWP2000). Check the ignition and try the other K-line "
                 "protocols.", "فشلت تهيئة خط K (ISO 9141 / KWP2000). تأكد من الإشعال وجرّب بروتوكولات خط K الأخرى.",
                 "bus_init"),
    "CAN ERROR": ("CAN bus error: wrong CAN speed, or the adapter is not connected to a CAN bus.",
                  "خطأ في ناقل CAN: سرعة CAN خاطئة، أو المحوّل غير متصل بناقل CAN.", "can_error"),
    "BUS ERROR": ("Bus error: a short circuit or noise on the diagnostic lines.",
                  "خطأ في الناقل: قصر أو تشويش على خطوط التشخيص.", "bus_error"),
    "BUS BUSY": ("The bus is too busy to send the request.", "الناقل مشغول جدًا لإرسال الطلب.", "bus_busy"),
    "FB ERROR": ("Feedback error: what the adapter sent did not come back from the bus (wiring problem).",
                 "خطأ ارتداد: ما أرسله المحوّل لم يرجع من الناقل (مشكلة في التوصيل).", "fb_error"),
    "DATA ERROR": ("The answer had a checksum / format error.", "الرد به خطأ في المجموع الاختباري أو الصيغة.",
                   "data_error"),
    "<DATA ERROR": ("The answer had a checksum error.", "الرد به خطأ في المجموع الاختباري.", "data_error"),
    "<RX ERROR": ("The adapter received a damaged message.", "استقبل المحوّل رسالة تالفة.", "rx_error"),
    "BUFFER FULL": ("The adapter's buffer overflowed (the computer read too slowly).",
                    "امتلأت ذاكرة المحوّل المؤقتة (قرأ الكمبيوتر ببطء).", "buffer_full"),
    "STOPPED": ("The adapter stopped (a character arrived while it was working).",
                "توقف المحوّل (وصل حرف أثناء عمله).", "stopped"),
    "LV RESET": ("The adapter reset because the voltage dropped (cranking?).",
                 "أُعيد تشغيل المحوّل بسبب انخفاض الجهد (أثناء تشغيل المحرك؟).", "lv_reset"),
    "ACT ALERT": ("The adapter is about to go to sleep (no activity).", "المحوّل على وشك الدخول في وضع السكون.",
                  "act_alert"),
    "ERR": ("Adapter internal error.", "خطأ داخلي في المحوّل.", "internal"),
    "?": ("The adapter did not understand the command.", "لم يفهم المحوّل الأمر.", "unknown_command"),
}
NO_DATA = "NO DATA"
_HEX = re.compile(r"^[0-9A-F]+$")


class ElmError(LinkError):
    pass


def _error_for(line: str) -> tuple[str, str, str] | None:
    u = line.upper()
    if u.startswith("BUS INIT"):
        return ELM_ERRORS["BUS INIT"] if "ERROR" in u else None
    for key, val in ELM_ERRORS.items():
        if key == "ERR":
            if re.match(r"^ERR\d+", u):
                return val
            continue
        if u == key or (key != "?" and u.startswith(key)):
            return val
    return None


def _tokens(line: str, fam: str, bits29: bool) -> list[str]:
    """Hex byte tokens of one line; the CAN id stays one token (``7E8`` / ``18DAF110``)."""
    s = line.strip().upper()
    if " " in s:
        parts = s.split()
        if fam == "can" and bits29 and len(parts) >= 4 and all(len(p) == 2 for p in parts[:4]):
            parts = ["".join(parts[:4])] + parts[4:]
        return parts
    if fam == "can":
        n = 8 if bits29 else 3
        return [s[:n]] + [s[i:i + 2] for i in range(n, len(s), 2)]
    return [s[i:i + 2] for i in range(0, len(s), 2)]


def _guess_family(line: str) -> tuple[str, bool]:
    parts = line.split()
    if parts and len(parts[0]) == 3:
        return "can", False
    if parts and len(parts[0]) == 8:
        return "can", True
    if len(parts) >= 5 and parts[0] in ("18", "19", "1C") and parts[1] in ("DA", "DB"):
        return "can", True
    return "kline", False


def parse_response(text: str, protocol: protocols.Protocol | None = None, command: str = "",
                   headers: bool = True) -> tuple[list[Response], list[LinkError]]:
    """Adapter text (everything up to the ``>`` prompt) -> (complete answers, adapter errors).

    "NO DATA" gives no answers and no error; "SEARCHING..." and "BUS INIT: ...OK" are skipped."""
    responses: list[Response] = []
    errors: list[LinkError] = []
    cmd = command.replace(" ", "").upper()
    can_frames: list[tuple[int, bytes, str]] = []
    nohdr_multi: dict[int, bytes] = {}
    nohdr_len = 0
    for raw in re.split(r"[\r\n]+", text):
        line = raw.strip().strip(">").strip()
        if not line:
            continue
        u = line.upper()
        if cmd and u.replace(" ", "") == cmd:
            continue                                  # echo
        if u.startswith("SEARCHING"):
            line = line[len("SEARCHING..."):].strip()
            u = line.upper()
            if not line:
                continue
        if u.startswith("BUS INIT"):
            if "ERROR" in u:
                en, ar, code = ELM_ERRORS["BUS INIT"]
                errors.append(ElmError(en, ar, code))
                continue
            line = re.sub(r"^BUS INIT:\s*\.*\s*(OK)?", "", line, flags=re.I).strip()
            u = line.upper()
            if not line:
                continue
        if u in ("OK", NO_DATA) or u.startswith(NO_DATA):
            continue
        err = _error_for(u)
        if err is not None:
            errors.append(ElmError(*err))
            continue
        compact = u.replace(" ", "")
        m = re.match(r"^([0-9A-F]):\s*(.*)$", u)
        if m and not headers:                         # headers off multi-frame: "0: 49 02 01 ..."
            nohdr_multi[int(m.group(1), 16)] = bytes.fromhex(m.group(2).replace(" ", ""))
            continue
        if not _HEX.match(compact):
            continue                                  # adapter chatter we do not know
        if not headers:
            if len(compact) == 3 and not nohdr_multi:       # byte count line before "0: ..."
                nohdr_len = int(compact, 16)
                continue
            responses.append(Response(0, bytes.fromhex(compact if len(compact) % 2 == 0 else compact[:-1]), [line]))
            continue
        fam, b29 = (protocol.family, protocol.bits29) if protocol else _guess_family(u)
        toks = _tokens(u, fam, b29)
        try:
            if fam == "can":
                cid = int(toks[0], 16)
                body = toks[1:]
                if body and len(body[0]) == 1:        # ATD1: DLC digit after the id
                    body = body[1:]
                can_frames.append((cid, bytes(int(b, 16) for b in body), line))
            else:
                bs = bytes(int(b, 16) for b in toks)
                if len(bs) < 4:
                    continue
                if bs[0] & 0x80 and bs[0] & 0x3F:     # KWP2000 format byte with length
                    n = bs[0] & 0x3F
                    src, data = bs[2], bs[3:3 + n]
                elif bs[0] in (0x80, 0xC0) and len(bs) > 4:      # format byte + separate length byte
                    n = bs[3]
                    src, data = bs[2], bs[4:4 + n]
                else:                                 # ISO 9141-2 / J1850: 3 header bytes + data + check byte
                    src, data = bs[2], bs[3:-1]
                responses.append(Response(src, bytes(data), [line]))
        except ValueError:
            continue
    if nohdr_multi:
        data = b"".join(nohdr_multi[k] for k in sorted(nohdr_multi))
        responses.append(Response(0, data[:nohdr_len] if nohdr_len else data, []))
    # ISO-TP reassembly per CAN id
    asm: dict[int, isotp.Reassembler] = {}
    lines: dict[int, list] = {}
    for cid, data, line in can_frames:
        r = asm.setdefault(cid, isotp.Reassembler())
        lines.setdefault(cid, []).append(line)
        try:
            state, payload = r.feed(data)
        except isotp.IsoTpError as e:
            errors.append(ElmError(f"Damaged multi-frame answer from {protocols.fmt_id(cid)}: {e}",
                                   f"رد متعدد الإطارات تالف من {protocols.fmt_id(cid)}: {e}", "isotp"))
            continue
        if state == "done":
            responses.append(Response(cid, payload, lines.pop(cid, [])))
    for cid, r in asm.items():
        if r.busy:
            errors.append(ElmError(f"Incomplete multi-frame answer from {protocols.fmt_id(cid)}.",
                                   f"رد متعدد الإطارات غير مكتمل من {protocols.fmt_id(cid)}.", "isotp"))
    return responses, errors


def parse_voltage(text: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s*V", text.upper())
    return float(m.group(1)) if m else None


class ElmLink(DiagLink):
    """An ELM327-compatible adapter on any transport (transport.py)."""
    kind = "elm"
    channel = "elm"

    def __init__(self, transport: Transport, protocol: str = protocols.AUTO, log=None, search_timeout: float = 15.0):
        super().__init__(log)
        self.t = transport
        self.wanted = (protocol or protocols.AUTO).upper()
        self.search_timeout = search_timeout
        self.elm_version = ""
        self.stn = ""                 # STN chip id when the adapter is an STN11xx / OBDLink
        self.device = ""              # AT@1 / STDI description
        self._hdr: str | None = None
        self._cra: str | None = None
        self._cp: str | None = None
        self._st: int | None = None

    # ------------------------------------------------------------------ low level
    def raw(self, command: str, timeout: float = 1.5) -> str:
        """Send one command line, return the adapter's text up to the prompt (logged to the bus console)."""
        self.log.tx(self.channel, command)
        self.t.write(command.encode("ascii") + b"\r")
        data = self.t.read_until(b">", timeout)
        text = data.decode("ascii", "replace")
        shown = " | ".join(s.strip() for s in re.split(r"[\r\n]+", text.replace(">", "")) if s.strip())
        self.log.rx(self.channel, shown if shown else "(no answer)")
        if not data.endswith(b">") and b">" not in data:
            raise ElmError(f"The adapter did not answer '{command}' in time.",
                           f"لم يرد المحوّل على '{command}' في الوقت المحدد.", "timeout")
        return text

    def cmd(self, command: str, timeout: float = 1.5) -> list[str]:
        text = self.raw(command, timeout)
        c = command.replace(" ", "").upper()
        return [s.strip() for s in re.split(r"[\r\n]+", text.replace(">", ""))
                if s.strip() and s.strip().replace(" ", "").upper() != c]

    def at(self, command: str, timeout: float = 1.5) -> str:
        lines = self.cmd(command, timeout)
        return lines[-1] if lines else ""

    # ------------------------------------------------------------------ open / close
    def open(self) -> None:
        t = self.t
        self.log.info(self.channel, f"connecting via {t.describe()}")
        t.write(b"\r")                                # leave any half-typed command
        t.read_until(b">", 0.5)
        t.flush_input()
        ident = ""
        for _ in range(2):
            try:
                ident = next((s for s in self.cmd("ATZ", 3.0) if "ELM" in s.upper() or "STN" in s.upper()), "")
            except ElmError:
                ident = ""
            if ident:
                break
            t.flush_input()
        if not ident:
            try:
                ident = self.at("ATI", 2.0)
            except ElmError as e:
                raise ElmError("No ELM327-compatible adapter answered. Check the port / speed and the adapter's "
                               "power (it is powered by the car's OBD socket).",
                               "لم يرد أي محوّل متوافق مع ELM327. تأكد من المنفذ والسرعة ومن تغذية المحوّل "
                               "(يتغذى من مقبس OBD في السيارة).", "no_adapter") from e
        self.elm_version = ident
        for c in ("ATE0", "ATL0", "ATS1", "ATH1", "ATCAF1", "ATAT1"):
            self.at(c)
        try:
            sti = self.at("STI")
            if sti and sti != "?" and "?" not in sti:
                self.stn = sti
                self.device = self.at("STDI")
        except ElmError:
            pass
        if not self.device:
            try:
                self.device = self.at("AT@1")
            except ElmError:
                self.device = ""
        self.adapter_info = self.stn or self.elm_version
        self._hdr = self._cra = self._cp = None
        self._st = None
        self.is_open = True
        try:
            self.detect_protocol(self.wanted)
        except LinkError:
            self.is_open = False
            raise

    def detect_protocol(self, wanted: str = protocols.AUTO) -> protocols.Protocol:
        """Select *wanted* (``"0"`` = let the adapter search) and wake the bus with ``0100``."""
        self.at(f"ATSP{wanted}")
        self.protocol = None
        text = self.raw("0100", self.search_timeout)
        resp, errors = parse_response(text, None, "0100")
        if not resp:
            if errors:
                raise errors[0]
            raise ElmError("The car did not answer the OBD-II request (0100). Is the ignition on?",
                           "لم ترد السيارة على طلب OBD-II (0100). هل الإشعال يعمل؟", "unable_to_connect")
        dpn = self.at("ATDPN").strip().upper()
        p = protocols.get(dpn)
        if p is None:
            raise ElmError(f"Unknown protocol number from the adapter: {dpn}", f"رقم بروتوكول غير معروف: {dpn}")
        self.protocol = p
        self.log.info(self.channel, f"protocol: {p.name}")
        return p

    def close(self) -> None:
        if self.is_open:
            try:
                self.at("ATPC", 1.0)
            except LinkError:
                pass
        self.t.close()
        self.is_open = False

    # ------------------------------------------------------------------ addressing
    def _set(self, attr: str, command: str, value: str) -> None:
        if getattr(self, attr) != value:
            self.at(f"{command}{value}" if value else command)
            setattr(self, attr, value)

    def _address(self, tx_id: int | None, rx_id: int | None) -> None:
        p = self.protocol
        if p is None:
            return
        if p.is_can:
            if p.bits29:
                tx = tx_id if tx_id is not None else protocols.FUNC_29
                self._set("_cp", "ATCP", f"{(tx >> 24) & 0x1F:02X}")
                self._set("_hdr", "ATSH", f"{tx & 0xFFFFFF:06X}")
                self._set("_cra", "ATCRA" if rx_id is not None else "ATAR",
                          f"{rx_id:08X}" if rx_id is not None else "")
            else:
                tx = tx_id if tx_id is not None else protocols.FUNC_11
                self._set("_hdr", "ATSH", f"{tx:03X}")
                self._set("_cra", "ATCRA" if rx_id is not None else "ATAR",
                          f"{rx_id:03X}" if rx_id is not None else "")
            return
        if p.code in ("4", "5"):                       # KWP2000: format byte (length added by the adapter)
            hdr = "C133F1" if tx_id is None else f"80{tx_id & 0xFF:02X}F1"
        elif p.code == "1":
            hdr = "616AF1" if tx_id is None else f"E4{tx_id & 0xFF:02X}F1"
        else:                                          # ISO 9141-2, J1850 VPW
            hdr = "686AF1" if tx_id is None else f"6C{tx_id & 0xFF:02X}F1"
        self._set("_hdr", "ATSH", hdr)          # answers to the tester (F1) are received in both cases

    def _timeout(self, timeout: float) -> None:
        st = max(0x10, min(0xFF, int(timeout / 0.004)))
        if st != self._st:
            self.at(f"ATST{st:02X}")
            self._st = st

    # ------------------------------------------------------------------ requests
    def _request(self, payload, tx_id, rx_id, timeout, expect):
        if self.protocol is None:
            raise ElmError("No vehicle protocol yet.", "لم يُحدَّد بروتوكول السيارة بعد.", "no_protocol")
        self._address(tx_id, rx_id)
        self._timeout(timeout)
        hexs = payload.hex().upper()
        text = self.raw(hexs, timeout + 3.0)
        resp, errors = parse_response(text, self.protocol, hexs)
        if rx_id is not None:
            resp = [r for r in resp if r.source == rx_id] or resp
        if errors and not resp:
            raise errors[0]
        for e in errors:
            self.log.error(self.channel, e.en)
        return resp

    def listen(self, rx_id=None, timeout=2.0):
        """Wait for answers without sending (``ATMA`` with the receive filter set, stopped by a key press)."""
        if self.protocol is None:
            return []
        self.log.tx(self.channel, "ATMA")
        self.t.write(b"ATMA\r")
        buf = bytearray()
        end = time.monotonic() + timeout
        resp: list[Response] = []
        while time.monotonic() < end:
            chunk = self.t.read_available(0.05)
            if not chunk:
                continue
            buf += chunk
            resp, _ = parse_response(buf.decode("ascii", "replace").rsplit("\r", 1)[0] if b"\r" in buf else "",
                                     self.protocol, "ATMA")
            if rx_id is not None:
                resp = [r for r in resp if r.source == rx_id]
            if any(not r.is_pending for r in resp):
                break
        self.t.write(b"\r")
        rest = self.t.read_until(b">", 1.5)
        text = (bytes(buf) + rest).decode("ascii", "replace")
        self.log.rx(self.channel, " | ".join(s.strip() for s in re.split(r"[\r\n]+", text.replace(">", ""))
                                             if s.strip()) or "(nothing)")
        resp, _ = parse_response(text, self.protocol, "ATMA")
        if rx_id is not None:
            resp = [r for r in resp if r.source == rx_id]
        return resp

    def voltage(self) -> float | None:
        try:
            return parse_voltage(self.at("ATRV"))
        except LinkError:
            return None
