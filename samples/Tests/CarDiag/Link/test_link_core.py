"""Car diagnostics link layer tests (no Qt, no hardware): radide/cardiag/link + radide/cardiag/sim.

Run:  python samples\\Tests\\CarDiag\\Link\\test_link_core.py

* ISO-TP: segmentation / reassembly (single, first + consecutive, padding, CAN FD escapes, > 4095 bytes,
  extended addressing), sequence errors, block size, STmin, flow control; IsoTpChannel and RawCanLink against
  the Demo car's virtual CAN bus (multi-frame both ways, ECU block size, functional multi-unit answers);
* ELM327 text parsing: CAN 11 / 29-bit with and without spaces, multi-frame with headers on and off, two units
  interleaved, ATD1, echo, NO DATA, SEARCHING..., BUS INIT: ...OK / ERROR, UNABLE TO CONNECT, CAN ERROR, ?,
  K-line ISO 9141 / KWP2000 headers, response pending;
* ElmLink against the Demo car on every protocol (auto detect 3-9), wrong protocol, ignition off, STN id,
  TCP server (Wi-Fi path) and pyserial socket:// (serial path);
* UDS client: sessions, tester present / keep-alive / S3 time-out, DTCs by mask, snapshots, extended data,
  permanent, clear one / all (airbag only clears all and the fault stays), routines with preconditions and
  progress (cooling system bleed), response pending (service reset) via ATMA, IO control, security access only
  via a plug-in (wrong key, missing plug-in), NRC explanations in Arabic;
* OBD-II service layer: PIDs, readiness, freeze frame, modes 03 / 07 / 0A / 04 / 06 / 08 / 09, K-line VIN;
* KWP2000 client on the K-line variant; ECU discovery on CAN 11-bit, 29-bit and K-line;
* the service layer's transport shape (exchange / receive) incl. radide/cardiag/service ServiceClient;
* J2534 registry enumeration (+ loading a DLL when one is installed and matches the bitness), BLE availability,
  COM port listing; bus log.
"""
from __future__ import annotations

import os
import sys
import tempfile
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".."))
sys.path.insert(0, ROOT)

from radide.cardiag.link import isotp, protocols  # noqa: E402
from radide.cardiag.link.base import LinkError  # noqa: E402
from radide.cardiag.link.discovery import discover  # noqa: E402
from radide.cardiag.link.elm import ElmLink, parse_response  # noqa: E402
from radide.cardiag.link.kwp import KwpClient  # noqa: E402
from radide.cardiag.link.log import BUS_LOG, BusLog  # noqa: E402
from radide.cardiag.link.manager import LinkConfig, demo_can_link, demo_link, open_link  # noqa: E402
from radide.cardiag.link.obd import Obd, decode_dtcs, decode_pid  # noqa: E402
from radide.cardiag.link.transport import LoopbackTransport, SerialTransport, TcpTransport  # noqa: E402
from radide.cardiag.link.uds import (NegativeResponse, UdsClient, UdsError, dtc_from_str, dtc_str,  # noqa: E402
                                     status_text)
from radide.cardiag.sim import VirtualCar  # noqa: E402
from radide.cardiag.sim.canbus import VirtualCanBus  # noqa: E402
from radide.cardiag.sim.elm import ElmInterpreter  # noqa: E402
from radide.cardiag.sim.server import DemoCarServer  # noqa: E402

RESULTS = []
HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.join(ROOT, "radide", "cardiag", "sim", "demo_seedkey.py")


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  [{str(detail)[:600]}]"), flush=True)
    return bool(cond)


def raises(fn, exc=Exception):
    try:
        fn()
    except exc as e:
        return e
    return None


def elm_link(car, protocol="0", stn=None) -> ElmLink:
    link = ElmLink(LoopbackTransport(ElmInterpreter(car, stn=stn)), protocol, BusLog())
    link.open()
    return link


# ===================================================================== ISO-TP
def test_isotp():
    f = isotp.segment(b"\x22\xF1\x90")
    check("isotp: single frame padded", f == [bytes.fromhex("0322F190AAAAAAAA")], f)
    check("isotp: no padding", isotp.segment(b"\x3E\x00", padding=None) == [b"\x02\x3E\x00"])
    vin = b"\x62\xF1\x90" + b"XRDDEM0CAR0123456"
    fr = isotp.segment(vin)
    check("isotp: first frame + consecutive frames", fr[0][:2] == b"\x10\x14" and [x[0] for x in fr[1:]] == [0x21, 0x22]
          and len(fr) == 3, [x.hex() for x in fr])
    ok = True
    for n in (1, 6, 7, 8, 13, 62, 63, 64, 300, 4095, 5000):
        data = bytes((i * 7 + n) & 0xFF for i in range(n))
        r = isotp.Reassembler()
        got = None
        for fr_ in isotp.segment(data):
            st, val = r.feed(fr_)
            if st == "done":
                got = val
        ok = ok and got == data
    check("isotp: round trip 1..5000 bytes (incl. 32-bit length escape)", ok)
    big = isotp.segment(bytes(5000))
    check("isotp: > 4095 bytes uses the escape first frame", big[0][:2] == b"\x10\x00" and
          int.from_bytes(big[0][2:6], "big") == 5000)
    fd = isotp.segment(bytes(range(20)), dl=64)
    check("isotp: CAN FD single frame escape", fd[0][:2] == b"\x00\x14" and len(fd) == 1 and len(fd[0]) == 24,
          fd[0].hex())
    ext = isotp.segment(bytes(range(10)), ext=0xF1)
    r = isotp.Reassembler(ext=True)
    res = [r.feed(x) for x in ext]
    check("isotp: extended addressing", ext[0][0] == 0xF1 and res[-1] == ("done", bytes(range(10))), res)
    r = isotp.Reassembler()
    frames = isotp.segment(bytes(30))
    r.feed(frames[0])
    e = raises(lambda: r.feed(frames[2]), isotp.IsoTpError)
    check("isotp: wrong sequence number raises", e is not None and "sequence" in str(e), e)
    r = isotp.Reassembler(block_size=2)
    states = [r.feed(x)[0] for x in isotp.segment(bytes(40))]
    check("isotp: receiver block size asks for flow control every 2 frames",
          states == ["fc", "more", "fc", "more", "fc", "done"], states)
    check("isotp: STmin decoding", isotp.stmin_seconds(0x14) == 0.020 and isotp.stmin_seconds(0xF3) == 0.0003
          and isotp.stmin_seconds(0x90) == 0.127)
    check("isotp: flow control frame", isotp.parse_flow_control(isotp.flow_control(1, 8, 0x0A)) == (1, 8, 10))
    check("isotp: stray consecutive frame ignored", isotp.Reassembler().feed(b"\x21\x00")[0] == "ignore")


def test_rawcan():
    car = VirtualCar(time_scale=1.0)
    bus = VirtualCanBus(car)
    ch = isotp.IsoTpChannel(bus.endpoint(), 0x7E0, 0x7E8)
    ans = ch.request(b"\x22\xF1\x90", 1.0)
    check("rawcan: IsoTpChannel reads the VIN (multi-frame answer, our flow control)",
          ans == b"\x62\xF1\x90" + car.vin.encode(), ans)
    seen = [f for f in bus.frames_seen if f[0] == 0x7E0 and f[1][0] >> 4 == 3]
    check("rawcan: tester sent a flow control frame", len(seen) == 1, bus.frames_seen)
    link = demo_can_link(car, log=BusLog())
    u = UdsClient(link, 0x744)
    car.climate.dids[0x0700] = bytes(20)
    car.climate.writable[0x0700] = (0x01, 0)
    u.write_did(0x0700, bytes(range(1, 21)))
    check("rawcan: multi-frame request (20-byte write) with the unit's flow control",
          car.climate.dids[0x0700] == bytes(range(1, 21)))
    car2 = VirtualCar()
    bus2 = VirtualCanBus(car2, ecu_block_size=2, ecu_stmin=1)
    from radide.cardiag.link.rawcan import RawCanLink
    link2 = RawCanLink(bus2.endpoint(), "6", block_size=3, log=BusLog())
    link2.open()
    car2.climate.dids[0x0700] = bytes(40)
    car2.climate.writable[0x0700] = (0x01, 0)
    UdsClient(link2, 0x744).write_did(0x0700, bytes(range(40)))
    fcs = [f for f in bus2.frames_seen if f[0] == 0x74C and f[1][0] >> 4 == 3]
    check("rawcan: unit block size 2 -> several flow control frames while sending 43 bytes",
          car2.climate.dids[0x0700] == bytes(range(40)) and len(fcs) >= 3, len(fcs))
    rs = link.request(b"\x22\xF1\x90", None, None, 0.5)
    check("rawcan: functional UDS request: the emissions unit answers multi-frame (flow control to 7E0)",
          len(rs) == 1 and rs[0].source == 0x7E8 and rs[0].data.endswith(car.vin.encode()), rs)
    rs = link.request(b"\x01\x00", None, None, 0.3)
    check("rawcan: functional OBD request: only the engine answers", [r.source for r in rs] == [0x7E8], rs)
    car3 = VirtualCar("7")
    l3 = demo_can_link(car3, log=BusLog())
    vin = UdsClient(l3, protocols.phys_29(0x28)).read_text(0xF190)
    check("rawcan: 29-bit normal fixed addressing (18DA28F1 -> 18DAF128)", vin == car3.vin, vin)


# ===================================================================== ELM parsing
def test_elm_parse():
    p6, p7, p3, p5 = (protocols.get(c) for c in "6735")
    r, e = parse_response("7E8 06 41 00 BE 3F A8 13 00 \r\r>", p6, "0100")
    check("elm: CAN 11-bit single frame", r and r[0].source == 0x7E8 and r[0].data == bytes.fromhex("4100BE3FA813"), r)
    txt = ("0902\r7E8 10 14 49 02 01 58 52 44\r7E9 03 7F 09 31 00 00 00 00\r7E8 21 44 45 4D 30 43 41 52\r"
           "7E8 22 30 31 32 33 34 35 36\r\r>")
    r, e = parse_response(txt, p6, "0902")
    vin = next((x for x in r if x.source == 0x7E8), None)
    check("elm: multi-frame (headers on) interleaved with a second unit, echo removed",
          vin is not None and vin.data[3:] == b"XRDDEM0CAR0123456" and any(x.source == 0x7E9 and x.is_negative for x in r),
          r)
    r, e = parse_response("18 DA F1 10 06 41 00 BE 3F A8 13 AA\r\r>", p7)
    check("elm: CAN 29-bit with spaces", r and r[0].source == 0x18DAF110 and r[0].data[:2] == b"\x41\x00", r)
    r, e = parse_response("18DAF110064100BE3FA813AA\r\r>", p7)
    check("elm: CAN 29-bit without spaces", r and r[0].source == 0x18DAF110 and len(r[0].data) == 6, r)
    r, e = parse_response("7E8064100BE3FA813\r>", p6)
    check("elm: CAN 11-bit without spaces", r and r[0].data == bytes.fromhex("4100BE3FA813"), r)
    r, e = parse_response("014\r0: 49 02 01 58 52 44\r1: 44 45 4D 30 43 41 52\r2: 30 31 32 33 34 35 36\r\r>",
                          p6, headers=False)
    check("elm: multi-frame with headers off (014 / 0: / 1:)", r and r[0].data[3:] == b"XRDDEM0CAR0123456", r)
    r, e = parse_response("7E8 8 06 41 00 BE 3F A8 13 00\r>", p6)
    check("elm: ATD1 DLC digit skipped", r and r[0].data[:2] == b"\x41\x00", r)
    r, e = parse_response("NO DATA\r\r>", p6, "0902")
    check("elm: NO DATA -> no answers, no error", r == [] and e == [])
    r, e = parse_response("SEARCHING...\r7E8 06 41 00 BE 3F A8 13\r\r>", None, "0100")
    check("elm: SEARCHING... skipped, protocol guessed from the line", r and r[0].source == 0x7E8, r)
    r, e = parse_response("BUS INIT: ...OK\r48 6B 10 41 00 BE 3F A8 13 B9\r\r>", p3)
    check("elm: BUS INIT OK + ISO 9141-2 header / checksum stripped",
          r and r[0].source == 0x10 and r[0].data == bytes.fromhex("4100BE3FA813"), r)
    r, e = parse_response("BUS INIT: ...ERROR\r\r>", p3)
    check("elm: BUS INIT ERROR -> error with Arabic text", not r and e and e[0].code == "bus_init" and e[0].ar != e[0].en, e)
    r, e = parse_response("86 F1 10 41 00 BE 3F A8 13 2F\r\r>", p5)
    check("elm: KWP2000 format byte with length", r and r[0].data == bytes.fromhex("4100BE3FA813"), r)
    for text, code in (("SEARCHING...\rUNABLE TO CONNECT\r\r>", "unable_to_connect"), ("CAN ERROR\r>", "can_error"),
                       ("?\r>", "unknown_command"), ("BUFFER FULL\r>", "buffer_full"), ("ERR94\r>", "internal")):
        r, e = parse_response(text, p6)
        check(f"elm: '{text.split(chr(13))[-3] if 'SEARCH' in text else text.split(chr(13))[0]}' -> {code}",
              not r and e and e[0].code == code, e)
    r, e = parse_response("7E8 03 7F 31 78 AA AA AA AA\r\r>", p6)
    check("elm: response pending recognised", r and r[0].is_pending, r)
    r, e = parse_response("7E8 10 14 49 02 01 58 52 44\r\r>", p6)
    check("elm: incomplete multi-frame reported", not r and e and e[0].code == "isotp", e)


# ===================================================================== ElmLink vs Demo car
def test_elm_link():
    names = {}
    for code in ("6", "7", "8", "9", "3", "4", "5"):
        car = VirtualCar(code)
        try:
            link = elm_link(car)
            o = Obd(link)
            vin = o.vin()
            names[code] = (link.protocol.code, vin == car.vin, o.stored_dtcs())
        except LinkError as e:
            names[code] = ("error", False, e.en)
    ok = all(v[0] == k and v[1] for k, v in names.items())
    check("elm link: automatic protocol detection + VIN on CAN 11/29-bit 500/250k, ISO 9141, KWP 5-baud / fast",
          ok, names)
    check("elm link: K-line mode 03 (3 DTCs per message, zero padded)",
          names["3"][2] == {0x10: ["P0301", "P0420"]}, names["3"])
    car = VirtualCar("6")
    e = raises(lambda: elm_link(car, "8"), LinkError)
    check("elm link: wrong CAN speed -> CAN ERROR explained", e is not None and e.code == "can_error", e)
    car.set_ignition(False)
    e = raises(lambda: elm_link(car), LinkError)
    check("elm link: ignition off -> UNABLE TO CONNECT", e is not None and e.code == "unable_to_connect", e)
    car.set_ignition(True)
    car.start_engine()
    link = elm_link(car, stn="STN1110 v4.2.1")
    check("elm link: STN chip identified (STI / STDI)", link.stn.startswith("STN1110") and "STN1110" in link.device,
          (link.stn, link.device))
    check("elm link: battery voltage (ATRV)", 13.5 < (link.voltage() or 0) < 14.5, link.voltage())
    log = BusLog()
    link = ElmLink(LoopbackTransport(ElmInterpreter(car)), "0", log)
    link.open()
    txt = log.text()
    check("elm link: AT init sequence logged (ATZ, ATE0, ATH1, ATSP0, ATDPN)",
          all(c in txt for c in ("ATZ", "ATE0", "ATH1", "ATSP0", "ATDPN", "SEARCHING")), txt[-800:])
    rs = link.request(b"\x01\x0C", None)
    check("elm link: functional request after setting a physical header resets to 7DF",
          rs and rs[0].source == 0x7E8, rs)
    UdsClient(link, 0x760).read_did(0xF190)
    rs = link.request(b"\x01\x0C", None)
    check("elm link: header / receive filter switching", rs and rs[0].data[:2] == b"\x41\x0C" and "ATSH760" in log.text()
          and "ATCRA768" in log.text() and "ATAR" in log.text(), log.text()[-500:])


def test_tcp_and_serial_url():
    car = VirtualCar()
    srv = DemoCarServer(car, port=0, log=BusLog())
    port = srv.start()
    try:
        link = ElmLink(TcpTransport("127.0.0.1", port), "0", BusLog())
        link.open()
        check("tcp: Demo car server as a Wi-Fi adapter (VIN over TCP)", Obd(link).vin() == car.vin)
        link.close()
        link = open_link(LinkConfig(kind="wifi", host="127.0.0.1", tcp_port=port), log=BusLog())
        check("tcp: open_link(kind='wifi')", link.protocol.code == "6")
        link.close()
        try:
            st = SerialTransport(f"socket://127.0.0.1:{port}", 38400)
            l2 = ElmLink(st, "0", BusLog())
            l2.open()
            check("serial: pyserial socket:// URL through SerialTransport", Obd(l2).vin() == car.vin)
            l2.close()
        except LinkError as e:
            check("serial: pyserial socket:// URL through SerialTransport", False, e.en)
    finally:
        srv.stop()
    e = raises(lambda: TcpTransport("127.0.0.1", port, connect_timeout=1.0), LinkError)
    check("tcp: unreachable adapter -> readable error (Arabic too)", e is not None and e.code == "open_failed" and e.ar)


# ===================================================================== UDS
def test_uds():
    car = VirtualCar(time_scale=1.0)
    link = elm_link(car)
    eng = UdsClient(link, 0x7E0, did_lengths=car.engine.snapshot_dids)
    info = eng.diagnostic_session(0x03)
    check("uds: extended session with P2 / P2* timing", info.get("p2") == 0.05 and info.get("p2_star") == 5.0, info)
    eng.tester_present()
    eng.tester_present(suppress=True)
    check("uds: tester present (normal + suppressed answer)", True)
    dtcs = eng.read_dtcs()
    check("uds: 0x19 02 DTCs with status", [d.text for d in dtcs] == ["P0301-00", "P0171-00", "P0420-00"]
          and dtcs[0].mil and dtcs[0].active and dtcs[1].pending and not dtcs[1].confirmed, dtcs)
    check("uds: status text in Arabic", "طلب تشغيل لمبة التحذير" in status_text(dtcs[0].status, "ar"))
    check("uds: DTC count by mask (confirmed)", eng.dtc_count(0x08) == 2)
    snap = eng.snapshot(0x030100)
    rec = snap.records.get(1, {})
    check("uds: snapshot record decoded with DID lengths", int.from_bytes(rec.get(0x1001, b"\0\0"), "big") == 812
          and rec.get(0x1002) == bytes([128]), snap)
    check("uds: snapshot identification list", (0x030100, 1) in eng.snapshot_ids())
    ext = eng.extended_data(0x030100)
    check("uds: extended data (occurrence counter)", ext.get(1) == b"\x07", ext)
    check("uds: permanent DTCs (0x19 15)", [d.sae for d in eng.permanent_dtcs()] == ["P0301", "P0420"])
    check("uds: supported DTCs (0x19 0A)", len(eng.supported_dtcs()) == 3)
    abs_ = UdsClient(link, 0x760)
    abs_.clear_dtc("C0035")
    check("uds: clear one DTC (ABS C0035) -> gone", abs_.read_dtcs() == [])
    e = raises(lambda: abs_.clear_dtc("C1234"), NegativeResponse)
    check("uds: clearing a DTC the unit does not have -> requestOutOfRange", e is not None and e.nrc == 0x31, e)
    bag = UdsClient(link, 0x770)
    e = raises(lambda: bag.clear_dtc("B0001-1A"), NegativeResponse)
    check("uds: airbag unit only clears everything (0x31 for a single DTC), explanation in Arabic",
          e is not None and e.nrc == 0x31 and e.ar and e.ar != e.en, e)
    bag.clear_dtcs()
    check("uds: airbag fault still present after clear-all (not repaired)", [d.sae for d in bag.read_dtcs()] == ["B0001"])
    # routines
    e = raises(lambda: eng.start_routine(0x0301), NegativeResponse)
    check("uds: cooling bleed with engine running -> conditionsNotCorrect", e is not None and e.nrc == 0x22, e)
    car.stop_engine()
    eng.diagnostic_session(0x01)
    e = raises(lambda: eng.start_routine(0x0301), NegativeResponse)
    check("uds: routine in the default session -> serviceNotSupportedInActiveSession", e is not None and e.nrc == 0x7F, e)
    eng.diagnostic_session(0x03)
    car.time_scale = 10.0
    st = eng.start_routine(0x0301)
    check("uds: cooling system bleed started (status running)", st == b"\x01", st)
    r1 = eng.routine_results(0x0301)
    time.sleep(0.3)
    r2 = eng.routine_results(0x0301)
    check("uds: routine progress increases, pump runs", r2[1] > r1[1] and r2[2] >= 80, (r1.hex(), r2.hex()))
    deadline = time.monotonic() + 3
    while eng.routine_results(0x0301)[0] == 1 and time.monotonic() < deadline:
        time.sleep(0.1)
    r3 = eng.routine_results(0x0301)
    check("uds: cooling system bleed completed (status 2, 100 %)", r3[0] == 2 and r3[1] == 100, r3.hex())
    car.time_scale = 1.0
    e = raises(lambda: eng.stop_routine(0x0301), NegativeResponse)
    check("uds: stopping a finished routine -> requestSequenceError", e is not None and e.nrc == 0x24, e)
    # response pending through ATMA
    clu = UdsClient(link, 0x720)
    check("uds: service lamp on before the reset", car.lamps()["service"])
    clu.diagnostic_session(0x03)
    t0 = time.monotonic()
    out = clu.start_routine(0x0401)
    dt = time.monotonic() - t0
    check("uds: oil service reset answered after 'response pending' (78) via ATMA listen", out == b"\x02" and dt > 1.0,
          (out, dt))
    check("uds: service lamp off / distance to service reset", not car.lamps()["service"]
          and int.from_bytes(clu.read_did(0x2210), "big", signed=True) == 15000)
    check("uds: warning lamp bits DID (cluster 0x2220)", int.from_bytes(clu.read_did(0x2220), "big") & 0x01 == 1)
    # IO control
    e = raises(lambda: eng.actuate(0x4010, b"\x01"), NegativeResponse)
    check("uds: injector cut-off needs the engine running -> engineIsNotRunning", e is not None and e.nrc == 0x84, e)
    v = eng.actuate(0x4001, b"\x64")
    time.sleep(0.02)
    car.update()
    check("uds: radiator fan actuator test 100 %", v == b"\x64" and car.fan_duty == 100, (v, car.fan_duty))
    eng.release(0x4001)
    car.update()
    check("uds: return control to the unit", not car.engine.ios[0x4001].controlled)
    # security access - plug-in only
    cli = UdsClient(link, 0x744)
    cli.diagnostic_session(0x03)
    e = raises(lambda: cli.write_did(0x0600, b"\x01\x01\x24\x00"), NegativeResponse)
    check("uds: coding write while locked -> securityAccessDenied", e is not None and e.nrc == 0x33, e)
    e = raises(lambda: cli.security_access(1, None), UdsError)
    check("uds: security access without a plug-in sends nothing and explains", e is not None and e.code == "security", e)
    e = raises(lambda: cli.security_access(1, lambda seed, lvl, ecu: b"\0\0\0\1"), NegativeResponse)
    check("uds: wrong key -> invalidKey", e is not None and e.nrc == 0x35, e)
    from radide.cardiag.link.uds import load_seedkey_plugin
    plugin = load_seedkey_plugin(PLUGIN)
    cli.security_access(1, plugin)
    cli.write_did(0x0600, b"\x01\x01\x24\x00")
    check("uds: unlocked with the user plug-in, coding written", car.climate.dids[0x0600] == b"\x01\x01\x24\x00")
    e = raises(lambda: clu.write_did(0x2200, b"\x00\x00\x01"), NegativeResponse)
    check("uds: odometer DID is read-only (no write)", e is not None and e.nrc == 0x31, e)
    # S3 time-out and keep-alive
    car.time_scale = 40.0
    cli.start_keepalive(0.03)
    time.sleep(0.3)
    kept = car.climate.session == 0x03
    cli.stop_keepalive()
    time.sleep(0.3)
    car.update()
    car.climate.tick()
    check("uds: keep-alive holds the extended session; S3 time-out drops it", kept and car.climate.session == 0x01,
          (kept, car.climate.session))
    car.time_scale = 1.0
    e = raises(lambda: UdsClient(link, 0x7E5, timeout=0.2).read_did(0xF190), UdsError)
    check("uds: no unit at 7E5 -> timeout error", e is not None and e.code == "timeout", e)
    check("uds: DTC helpers", dtc_str(0xC121) == "U0121" and dtc_from_str("C0035-1F") == 0x40351F
          and dtc_from_str("P0301") == 0x0301)


def test_obd():
    car = VirtualCar()
    link = elm_link(car)
    o = Obd(link)
    sup = o.supported_pids()
    check("obd: supported PID chain 00/20/40/.../A0", 0x0C in sup[0x7E8] and 0xA6 in sup[0x7E8], sup)
    rpm, unit = o.query(0x0C)
    check("obd: engine speed live", 700 < rpm < 900 and unit == "rpm", rpm)
    v1 = o.query(0x0C)[0]
    time.sleep(0.15)
    v2 = o.query(0x0C)[0]
    check("obd: live data changes over time", v1 != v2, (v1, v2))
    ms = o.monitor_status()[0x7E8]
    check("obd: readiness (MIL on, 2 DTCs, EVAP incomplete)", ms.mil and ms.dtc_count == 2
          and [m.name for m in ms.incomplete] == ["EVAP system"], ms)
    check("obd: freeze frame DTC + rpm", o.freeze_frame_dtc() == {0x7E8: "P0301"}
          and decode_pid(0x0C, o.freeze_frame(0x0C)[0x7E8])[0] == 812)
    check("obd: modes 03 / 07 / 0A", o.stored_dtcs() == {0x7E8: ["P0301", "P0420"]} and
          o.pending_dtcs() == {0x7E8: ["P0301", "P0171"]} and o.permanent_dtcs() == {0x7E8: ["P0301", "P0420"]})
    e = raises(lambda: o.clear_dtcs(), NegativeResponse)
    check("obd: mode 04 refused with the engine running", e is not None and e.nrc == 0x22, e)
    car.stop_engine()
    check("obd: mode 04 clears", o.clear_dtcs())
    ms = o.monitor_status()[0x7E8]
    check("obd: after clearing: no stored DTCs, readiness not complete, permanent DTCs stay",
          o.stored_dtcs() == {0x7E8: []} and not ms.mil and len(ms.incomplete) == 7
          and o.permanent_dtcs() == {0x7E8: ["P0301", "P0420"]} and o.query(0x31)[0] == 0, ms)
    car.time_scale = 60.0
    car.start_engine()
    time.sleep(0.3)
    check("obd: misfire not repaired -> P0301 comes back as pending", o.pending_dtcs() == {0x7E8: ["P0301"]},
          o.pending_dtcs())
    car.time_scale = 1.0
    t = o.test_results(0x21)[0x7E8]
    check("obd: mode 06 catalyst monitor result (failing)", t and t[0]["value"] == 40 and not t[0]["passed"], t)
    check("obd: mode 08 EVAP test refused with engine running", o.control(0x01)[0].is_negative)
    check("obd: mode 09 CALID / CVN / ECU name", o.calibration_ids()[0x7E8] == ["RADSIM-ENG-0142"]
          and o.cvns()[0x7E8] == ["1A2B3C4D"] and o.ecu_names()[0x7E8].startswith("ECM"))
    check("obd: DTC decoding non-CAN / CAN", decode_dtcs(bytes.fromhex("430133000000"), False) == ["P0133"]
          and decode_dtcs(bytes.fromhex("430201330420"), True) == ["P0133", "P0420"])


def test_kwp():
    car = VirtualCar("5")
    link = elm_link(car)
    k = KwpClient(link, 0x10)
    ident = k.identification()
    check("kwp: 0x1A identification (VIN, part number)", ident.get(0x90) == car.vin and ident.get(0x87) == "RAD-SIM-1000",
          ident)
    dtcs = k.read_dtcs_by_status()
    check("kwp: 0x18 DTCs with state / lamp", [d.text for d in dtcs] == ["P0301", "P0171", "P0420"]
          and dtcs[0].state == 2 and dtcs[0].mil, dtcs)
    blk = k.read_local(0x01)
    check("kwp: 0x21 local identifier block", len(blk) == 4 and 600 < int.from_bytes(blk[:2], "big") < 1000, blk.hex())
    k.start_session(0x89)
    e = raises(lambda: k.start_routine_local(0x01), NegativeResponse)
    check("kwp: routine by local id refused with engine running (0x22)", e is not None and e.nrc == 0x22, e)
    car.stop_engine()
    check("kwp: 0x31 start routine by local id", k.start_routine_local(0x01) == b"\x01")
    k.clear_dtcs()
    check("kwp: 0x14 clear", [d.text for d in k.read_dtcs_by_status()] == [])


def test_discovery():
    car = VirtualCar("6")
    link = elm_link(car)
    ecus = discover(link)
    found = {e.tx: e for e in ecus}
    check("discovery: CAN 11-bit finds the five units with names / VIN",
          set(found) == {0x7E0, 0x720, 0x744, 0x760, 0x770} and found[0x7E0].obd and
          found[0x7E0].ident.get(0xF190) == car.vin and found[0x744].ident.get(0xF197) == "CLIMATE", ecus)
    car29 = VirtualCar("7")
    ecus = discover(elm_link(car29))
    check("discovery: CAN 29-bit", {(e.tx >> 8) & 0xFF for e in ecus} >= {0x10, 0x28, 0x58, 0x60}, ecus)
    carK = VirtualCar("3")
    ecus = discover(elm_link(carK), identify=False)
    check("discovery: K-line (engine 0x10)", [e.tx for e in ecus] == [0x10], ecus)


def test_service_shape():
    car = VirtualCar()
    link = elm_link(car)
    a = link.exchange(b"\x10\x03", 0x720, 0x728)
    b = link.exchange(b"\x31\x01\x04\x01", 0x720, 0x728, 1.0)
    c = b if not (b[:1] == b"\x7F" and b[2:3] == b"\x78") else link.receive(0x720, 0x728, 3.0)
    check("service shape: link.exchange / receive (response pending)", a[:2] == b"\x50\x03" and c[:4] == b"\x71\x01\x04\x01",
          (a, b, c))
    car2 = VirtualCar()
    car2.exchange(b"\x10\x03", 0x720)
    first = car2.exchange(b"\x31\x01\x04\x01", 0x720)
    later = car2.receive(0x720, timeout=3.0)
    check("service shape: car.exchange / receive", first == b"\x7F\x31\x78" and later[:2] == b"\x71\x01", (first, later))
    try:
        from radide.cardiag.service.transport import Ecu, ServiceClient
        sc = ServiceClient(link)
        ecu = Ecu("cluster", tx=0x720, rx=0x728)
        sc.session(ecu, "extended")
        resp = sc.request(ecu, b"\x31\x01\x04\x01", timeout=1.0)
        check("service shape: radide/cardiag/service ServiceClient over an ElmLink", resp[:2] == b"\x71\x01", resp)
    except ImportError as e:
        print("SKIP service ServiceClient:", e)


def test_misc():
    from radide.cardiag.link import j2534, ports, transport
    devs = j2534.devices()
    check("j2534: registry enumeration runs", isinstance(devs, list), devs)
    usable = [d for d in devs if d.usable]
    if usable:
        try:
            j2534.PassThru(usable[0].library)
            check(f"j2534: binding loads {usable[0].name}", True)
        except LinkError as e:
            check(f"j2534: binding loads {usable[0].name}", False, e.en)
    else:
        print(f"SKIP j2534 DLL load: {len(devs)} device(s) installed, none loadable by {8 * __import__('struct').calcsize('P')}-bit Python")
    check("j2534: PE bitness of a system DLL", j2534.dll_bits(os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                                                                          "System32", "kernel32.dll")) == 64)
    check("ble: availability check", isinstance(transport.ble_available(), bool) and len(transport.BLE_PROFILES) >= 3)
    lst = ports.list_ports()
    check("ports: COM port listing", isinstance(lst, list), lst)
    check("ports: adapter identification", ports.looks_like_adapter(b"ATI\r\rELM327 v2.1\r\r>") == "ELM327 v2.1"
          and ports.looks_like_adapter(b"STN2120 v5.6.19\r>") == "STN2120 v5.6.19" and not ports.looks_like_adapter(b"OK\r>"))
    link = demo_link(VirtualCar())
    n = len(BUS_LOG.snapshot())
    Obd(link).vin()
    check("bus log: traffic recorded in the IDE-wide log", len(BUS_LOG.snapshot()) > n)
    path = os.path.join(tempfile.gettempdir(), "radide_bus_test.log")
    BUS_LOG.save(path)
    with open(path, encoding="utf-8") as f:
        check("bus log: saved as text", "0902" in f.read())
    check("protocols: response / request ids", protocols.response_id(0x7E0) == 0x7E8 and
          protocols.response_id(0x18DA10F1) == 0x18DAF110 and protocols.request_id(0x18DAF128) == 0x18DA28F1
          and protocols.get("A6").code == "6")


def main() -> int:
    t0 = time.time()
    for fn in (test_isotp, test_rawcan, test_elm_parse, test_elm_link, test_tcp_and_serial_url, test_uds, test_obd,
               test_kwp, test_discovery, test_service_shape, test_misc):
        try:
            fn()
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            check(f"{fn.__name__} crashed", False, e)
    ok = sum(1 for _n, c in RESULTS if c)
    print(f"\n{ok}/{len(RESULTS)} passed in {time.time() - t0:.1f} s")
    return 0 if ok == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
