# Car diagnostics (radide/cardiag)

Scan-tool functions inside RAD IDE: understand what is wrong with a car (fault codes, warning lights, live data),
clear codes after a repair, and run standard workshop service routines. **Not in scope, by design:**
immobiliser / key / PIN functions, odometer changes, security-access algorithm cracking, disabling or masking
emissions monitors or emissions DTCs, readiness faking.

Several slices are built in parallel; each one owns a section below. Edit only your own section (insert-only
elsewhere).

## OBD-II scan tool (slice "obd": radide/cardiag/obd, radide/features/cardiag_scan.py)

### Transport interface the OBD layer needs (link slice: please provide / adapt)

`radide.cardiag.obd.client.ObdClient(transport)` talks to *any* object with

```python
transport.request(data: bytes, timeout: float = 2.0) -> list[tuple[str, bytes]]
#   data      = one OBD request, e.g. b"\x01\x0c" (mode 01 PID 0C), b"\x03", b"\x09\x02"
#   returns   = one (ecu, payload) per answering ECU, ecu = "7E8" / "7E9" (CAN) or "10"/"18" (K-line header),
#               payload = the complete reassembled response starting with the response SID
#               (b"\x41\x0c\x1a\xf8", negative: b"\x7f\x01\x12"); [] when no ECU answered.
transport.is_can -> bool        # optional (default True): multi-PID requests (up to 6) only on CAN
```

`radide.cardiag.obd.transport` has `DemoTransport` (the built-in OBD demo vehicle, no hardware) and
`LinkTransport`, which adapts the link slice's connection object (`radide.cardiag.link`) to the interface above.

### Demo vehicle (OBD services)

`radide.cardiag.obd.vehicle.DemoVehicle().handle(data: bytes) -> list[tuple[str, bytes]]` answers OBD modes
01-0A for an engine ECU (7E8) and a transmission ECU (7E9): a warming-up, driving engine (time based; tests call
`advance(seconds)`), stored / pending / permanent DTCs with freeze frames, readiness monitors that complete over
a drive cycle after a clear, mode 06 test results and mode 09 VIN / CALID / CVN / ECU names / IPT counters.
The link slice's ELM327 + UDS simulator can route OBD requests (SID 0x01-0x0A) to it instead of writing its
own OBD model.

### Workbench (Tools > Car Diagnostics...)

`radide/features/cardiag_scan.py` opens the OBD-II workbench as an IDE tab: Connect bar (adapter: Demo car,
Demo car through the ELM327 simulator, ELM327/STN serial / Wi-Fi / BLE, J2534, or the shared connection from
Tools > Car Connection; port; protocol), vehicle header (VIN, protocol, control units, MIL, confirmed codes,
battery voltage) and the tabs Faults (stored / pending / permanent with status, explanation from the fault
knowledge base, clear with a confirmation that lists what is cleared, warns that readiness monitors reset and that
permanent codes stay, safety warnings first), Live Data (PID picker from the supported-PID bitmaps, gauges,
numeric list with min / max, graph, sampling rate, CSV logging and playback), Freeze Frame (tied to the DTC that
stored it), Readiness (each monitor explained in Arabic + the drive cycle that completes it), Tests (mode 06 with
limits, failed tests highlighted), Info (mode 09 VIN / CALID / CVN / ECU names) and Log (request / response
traffic). With the shared connection the workbench follows Tools > Car Connection connect / disconnect and never
closes that link itself.

### Tests

- `samples/Tests/CarDiag/Obd/test_obd_core.py` - every mode 01 PID formula against hand-computed values,
  supported-PID bitmaps, multi-ECU answers, DTC decoding, readiness, mode 06 / 09, CSV logging / playback,
  end to end against the Demo vehicle and through the ELM327 simulator (202 checks).
- `samples/Tests/CarDiag/Obd/qa_scan_ide.py` - the real IDE with screenshots (`QA_LANG=ar QA_THEME=dark` for
  Arabic + dark).

## Service functions (slice "service": radide/cardiag/service, radide/features/cardiag_service.py)

**Tools > Car Service Functions...** opens a *Service Functions* tab; the Car Diagnostics workbench gets the same
panel as its *Service* tab (`cardiag_scan.TAB_HOOKS`). Connection: the built-in **Demo car** simulator or the
workbench's adapter connection (`workbench.link`, any `DiagLink` - it provides `exchange()` / `receive()`).

What it does:

- **Routines** (RoutineControl 0x31; KWP2000 0x31 / 0x33 / 0x32): a precondition checklist (manual items the
  user ticks + automatic checks read with 0x22, e.g. "coolant < 40 °C"), session (0x10) and security access, then
  `31 01 <RID> <params>`, polling `31 03 <RID>` with progress / status texts / user instructions at progress
  points, timeout (then `31 02` stop), Stop button (`31 02`), interpretation of the result bytes. Negative
  responses are explained in Arabic and English with what to do (`service/nrc.py`); "response pending" (0x78)
  is waited out.
- **Actuator tests** (0x2F; KWP 0x30): set a state, change it while running, keep-alive, time limit; control is
  **always** returned (`2F <DID> 00`) at the end, on Stop, on cancel and on errors.
- **Resets / adaptations / feature coding** (0x2E): fixed values or input fields (int ranges, enums); the old
  value is read first, the new value read back and compared.
- **Clear a specific fault**: explanation + possible causes first (fault knowledge base `radide.cardiag.kb` when
  present - `lookup/explain/get(code)` - else short built-in texts and "manufacturer-specific" for unknown
  codes), safety warnings for brakes / airbag / steering / overheating, emissions note (readiness monitors reset),
  required "repair done" confirmation, then `14 <DTC 3 bytes>`; when the unit cannot clear one DTC (NRC 0x31 /
  0x12 / 0x11 / 0x13) RAD IDE asks before clearing **all** faults of that unit; OBD-only: mode 04. The fault
  memory is read again: a fault that comes straight back is reported (cause still present).
- **Vehicle profiles** by VIN (`service/profiles.py`, folder `%LOCALAPPDATA%\RADIDE\cardiag\vehicles\<VIN>\`,
  `RADIDE_CARDIAG_HOME` overrides): make / model / notes, history of scans, repairs, service actions and clears;
  `audit.jsonl` with **every** request / answer / error and every user confirmation (time, VIN, ECU, action,
  definition id); CSV export. Other slices can call `profiles.add_history(vin, kind, summary, summary_ar, ...)`.
- **Security access** only through a seed/key plug-in the user selects and confirms being licensed for
  (`service/security.py`): a `.py` module with `compute_key(seed, level, ecu) -> bytes`, or a DLL exporting
  `GenerateKeyEx`. No algorithms are included; nothing is guessed or brute-forced.

### Definition packs

JSON (`format: "radide-cardiag-service-pack"`, annotated template: `service/packs/template.json`, button
*Template...*), CSV (columns `kind,id,name,name_ar,category,ecu,tx,rx,protocol,session,security_level,identifier,
data,timeout_s,preconditions,preconditions_ar`; kind routine / io / adaptation / did; io data =
`Off=00;Full=64`; preconditions separated by `|`), and a **read-only ODX 2.x / PDX import** of the service subset
(31 01 routines, 2F state values, 2E fixed writes, 22 DIDs from CODED-CONST requests; CAN ids from
CP_CanPhysReqId / CP_CanRespUSDTId). Imported packs are validated and copied to `...\cardiag\packs\`.

RAD IDE ships definitions **only for the Demo car simulator** (`service/packs/demo_car.json`: cooling-system
bleed, throttle adaptation reset, brake-pad service mode, steering-angle calibration, fan / coolant-pump tests,
oil-service reset, battery registration, a demo coding byte behind security level 1). Its identifiers belong to
the simulator only; the demo pack refuses to run on a real connection. Real vehicles need packs the user imports
from service information they are entitled to use - no manufacturer RIDs / DIDs are shipped as facts.

**Policy filter** (`definitions.policy_reason`, English + Arabic keywords): packs / CSV rows defining immobiliser,
key / PIN, odometer / mileage, emissions-system "off" / delete / bypass (DPF, EGR, AdBlue / SCR, lambda, cat),
readiness faking, permanent fault / monitor masking or seed/key cracking are rejected; ODX services matching it
are skipped with a warning. DPF *service regeneration*, oil-service km resets and EGR valve *tests* are allowed.
Definitions can only produce 0x10 / 0x27 (plug-in) / 0x22 / 0x2E / 0x2F / 0x31 / 0x14 / 0x19 requests - no raw
requests, no flashing services.

### Demo car simulator (`service/demo_ecu.py`)

`DemoCar(clock)` with Engine (7E0/7E8), ABS / ESP (760/768) and Airbag (737/73F) units: sessions with S3
timeout, tester present, 0x22 / 0x2E / 0x31 / 0x2F / 0x19 02 / 0x14 / 0x27 / OBD 03 / 04, physical state
(ignition, engine running, coolant temperature, speed, battery voltage) that drives the NRCs (0x22, 0x83, 0x84,
0x88, 0x93 ...), a 20 s bleed routine with response-pending, a fan whose override ends when control is returned
or the session drops, P0217 that comes back while the engine is hot, an airbag unit that only supports
clear-all. `DemoTransport` gives it the transport shape; `SimClock` makes tests instant. `service.demo_session()`
returns `(car, client, pack)`.

Tests: `samples/Tests/CarDiag/Service/test_service_core.py` (core, 72 checks) and `qa_service_ide.py` (the IDE
with qh.py, English + Arabic, 41 checks).

## Link layer (slice "link": radide/cardiag/link, radide/cardiag/sim, radide/features/cardiag_link.py)

Everything that talks to the car. Other slices use `radide.cardiag.link.current_link()` (set by
Tools > Car Connection > Connect to Car..., or by the scan tool's own connect) or open their own with
`open_link(LinkConfig(...))` / `demo_link()`.

### Adapters (`LinkConfig.kind`)

| kind | adapter | module |
|---|---|---|
| `demo` | the Demo car (no hardware; ELM327 interpreter in process) | `manager.py`, `sim/` |
| `serial` | ELM327 / STN11xx / OBDLink over a COM port: USB cables and paired classic-Bluetooth (SPP) adapters. Port scan with adapter identification (`ATI` / `STI`), automatic baud rate (38400, 115200, 9600, 230400, 57600, 500000, 19200) | `ports.py`, `transport.py`, `elm.py` (pyserial) |
| `wifi` | ELM327 Wi-Fi, TCP (default 192.168.0.10:35000) | `transport.py`, `elm.py` |
| `ble` | ELM327 Bluetooth LE (FFF0 / FFE0 / 18F0 GATT profiles) when `bleak` is installed | `transport.py`, `ble.py` |
| `j2534` | J2534 PassThru: installed drivers from the registry (`HKLM\SOFTWARE\PassThruSupport.04.04`, both views), PE bitness check (a 32-bit DLL cannot load into 64-bit Python and is shown as "not loadable"), ctypes binding of PassThruOpen / Connect / ReadMsgs / WriteMsgs / StartMsgFilter / Ioctl (ISO15765 with flow-control filters, ISO9141 / ISO14230 with 5-baud / fast init, READ_VBATT) | `j2534.py` |
| `can` | raw CAN through python-can (PCAN, Kvaser, Vector, slcan, ...) with RAD IDE's own ISO-TP | `rawcan.py`, `isotp.py` |

ELM init: `ATZ` (`ATI` fallback), `ATE0`, `ATL0`, `ATS1`, `ATH1`, `ATCAF1`, `ATAT1`, `ATSP0` / `ATSPx`, `ATDPN`; addressing
with `ATSH` / `ATCP` / `ATCRA`; protocol auto-detect
tries CAN 11/29-bit 500/250k, KWP fast / 5-baud, ISO 9141-2 and J1850 (via the ELM), with `SEARCHING...`,
`BUS INIT: ...ERROR`, `NO DATA`, `CAN ERROR`, `BUFFER FULL`, `?` and `STOPPED` handled; multi-frame CAN answers
(`0: / 1:` lines, with or without headers) are reassembled; response-pending (0x78) waits are extended.
All raw traffic goes to `BUS_LOG` (log.py) and is shown live in Tools > Car Connection > Bus Monitor (filter,
pause, errors only, save, raw command line).

### Protocol stack

* `isotp.py` - ISO 15765-2 segmentation, flow control (block size, STmin), padding, 11/29-bit ids.
* `obd.py` - OBD-II modes 01-0A: supported PIDs, live PIDs, freeze frame, stored / pending / permanent DTCs,
  clear (mode 04), mode 06 results, mode 08, VIN / CALID / CVN / ECU name; readiness monitors.
* `uds.py` - ISO 14229: 0x10 sessions, 0x3E tester present (+ keep-alive thread), 0x11 reset, 0x14 clear all /
  group / one DTC, 0x19 (count, by status mask, supported, permanent, snapshot ids / records, extended data),
  0x22 / 0x2E, 0x31 start / stop / results, 0x2F (short-term adjustment, return control), 0x27 **only** with a
  user-supplied seed/key plug-in (`compute_key(seed, level, ecu)` or a .dll through service/security.py); no
  algorithms are built in.
* `kwp.py` - KWP2000 basics: 0x10, 0x3E, 0x1A, 0x18, 0x14, 0x21 / 0x22, 0x31.
* `nrc.py` - negative response code names, with the English / Arabic explanations shared with
  radide/cardiag/service/nrc.py (`nrc.explain(code)`).
* `discovery.py` - find control units: functional request (0x7DF / 0x18DB33F1), then 0x7E0-0x7E7 and common
  body/chassis addresses (full scan: 0x700-0x7E7, 29-bit 0x18DAxxF1, K-line 0x01-0xFE), with names and
  identification DIDs (F190, F187, F18A, F18C, F191, F195, F197).

### Demo car (radide/cardiag/sim)

`VirtualCar` (one shared instance: `demo_car()`): engine (7E0/7E8, also K-line 0x10), ABS / ESP (760/768),
airbag (770/778, clear-all only), instrument cluster (720/728) and climate (744/74C); live data that changes
over time (idle / driving profile, warm-up, overheating with a stuck thermostat), stored / pending / permanent
DTCs with freeze frames and snapshots, faults that come back while their cause is present, readiness monitors
that complete while driving, warning lamps, VIN, routines with preconditions and progress (cooling-system bleed
0x0301, throttle / fuel-trim adaptation reset, injector test, battery registration, brake-pad service position,
steering angle calibration, oil service reset), IO controls (fan, coolant pump, injector cut-off), NRCs such as
0x22 conditions not correct when the engine runs. `sim/elm.py` is an ELM327 command interpreter in front of it
(all protocols 3-9, headers on/off, STN identity), `sim/canbus.py` a virtual CAN bus with ISO-TP for raw-CAN
tests, `sim/server.py` makes it a Wi-Fi adapter for other apps:

    python -m radide.cardiag.sim --port 35000 [--protocol 6] [--stn] [--drive] [--engine-off]

In the IDE: Tools > Car Connection > Demo Car (Simulator) (ignition / engine / driving / overheating, warning
lamps, TCP server on/off).

### Tests

`samples/Tests/CarDiag/Link/test_link_core.py` (ISO-TP, raw CAN, ELM response parsing incl. multi-frame, 29-bit,
NO DATA, SEARCHING..., BUS INIT: ERROR; ELM link and UDS / OBD / KWP clients against the Demo car on every
protocol; TCP and pyserial `socket://`; discovery; J2534 load when a 64-bit driver is installed, skipped
otherwise) and `qa_link_ide.py` (the IDE with qh.py: menu, Demo car dock and TCP server, Connect dialog test over
TCP and connect, status bar, Bus Monitor, Find Control Units, English + Arabic).


## Fault knowledge base (slice "kb": radide/cardiag/kb, radide/features/cardiag_help.py)

**Tools > Car Fault Guide...** opens a *Car Fault Guide* tab; the Car Diagnostics workbench gets the same guide as
its *Guide* tab (`cardiag_scan.TAB_HOOKS`). Four tabs:

- **Fault Codes** - lookup and search by code, code prefix (`P030`), words or symptom in English and Arabic,
  including Egyptian colloquial words (`سخونية`, `بترج`, `مش بتدور`); filters by system and severity. A code page
  shows the SAE title (English + Arabic), a plain explanation, common causes ranked, step-by-step checks with simple
  tools, severity (green / amber / red), "safe to drive?", the readiness monitor / system, related codes, a safety
  warning for brakes / airbag / steering / overheating codes, and links: *Watch in Live Data* (the code's PIDs),
  *Scan the car*, *Explain with AI*. UDS DTCs with a failure-type byte (`C0035-1F`) also explain the failure type
  (ISO 15031-6 / ISO 14229 FTB categories, `kb/ftb.py`).
- **Warning Lights** - "What light is on?": RAD IDE's own SVG icons (`kb/lights.py`, 20 lights: check engine,
  oil pressure, coolant temperature, engine cold, battery / charging, ABS, brake, airbag, TPMS, ESP / traction,
  glow plugs, DPF, power steering, service, transmission, low fuel, key / immobiliser *light explanation only*,
  AdBlue, water in fuel), colour meaning, what it means, what to do now, the control unit that holds the codes
  when a generic OBD-II scan cannot see them, hints for combinations (battery + temperature = belt), likely codes
  (codes the car really reported first) and *Scan the car* / *Watch in Live Data*.
- **Symptoms** - a question wizard (`kb/symptoms.py`, 12 symptoms: overheating, rough idle, cranks but no start,
  no crank, lack of power, stalling, fuel consumption, smoke, battery light / flat battery, gearbox, cold heater,
  high idle). Each answer re-weights the causes; the result lists likely causes with what to check, the live data
  to watch with normal values (one click selects those PIDs in the workbench's Live Data, after connecting if
  needed) and codes that often come with it.
- **Explain with AI** - the fault codes (with ECU and status), freeze frames, live values, VIN, selected lights and
  symptom go to the IDE's AI provider (`radide.ai`, the user's "chat" default) with a careful prompt
  (`kb/ai.py`: knowledge-base facts as grounding, say how sure, safety first, no part swapping without a check,
  manufacturer-specific codes not guessed, clear only after repair, no immobiliser / odometer / emissions-defeat
  advice); the answer is shown in Arabic by default. *Explain (Knowledge Base)* gives the offline explanation
  without any AI; when no provider is available the offline text is shown.

### Data and API

```python
from radide.cardiag import kb
kb.lookup("P0217")      # title / title_ar, explain(_ar), causes(_ar), checks(_ar), severity, drive, safety,
                        # system, monitor, related, tags, pids, specific, source ...; None if not a DTC
kb.search("سخونية")     # [(code, score)]
kb.import_pack(path)    # user CSV / JSON pack (manufacturer-specific codes), stored in <cardiag home>\dtc-packs
kb.stats(); kb.validate()
```

Shards `kb/data/{p0,p2,p3,u,b,c}.json` + `meta.json` are generated by `python -m radide.cardiag.kb.builder` from
`kb/builder/` (codes.py: the generic J2012 titles - facts; components.py / faults.py / special.py / extra.py: RAD
IDE's own explanations, causes and checks in English and Arabic). `--check` fails when the shards are stale.
Coverage: 1243 generic codes (P0 832, P2 262, P34 98, U0 33, C0 12, B0 6). Manufacturer-specific ranges (P1xxx,
P30-P33, B1/B2, C1/C2, U1/U2) are never shipped as facts: without a user pack, lookup() says
"manufacturer-specific - meaning varies". Pack CSV columns: `code,make,title,title_ar,explain,explain_ar,causes,
causes_ar,checks,checks_ar,severity,drive,system,related,tags` (lists separated by `|`; *Save Template...*).

Other slices: `kb.lookup / explain / get(code)` (scan and service slices), `win.cardiag_guide.show_code(code)`,
`show_lights(ids)`, `show_symptom(id)`.

Tests: `samples/Tests/CarDiag/Kb/test_kb_core.py` (schema, coverage, packs, search EN / AR, lights picker,
wizard, AI prompt with a mock provider; 84 checks) and `qa_help_ide.py` (the IDE with qh.py, English + Arabic,
37 checks).

## End-to-end QA and integration (all four slices together)

`samples/Tests/CarDiag/QA/qa_cardiag_e2e.py` drives the real IDE as a car owner / mechanic would, with one car for
everything: Tools > Car Diagnostics... with the adapter **Demo car through the ELM327 simulator** (the shared
`radide/cardiag/sim` VirtualCar). English, then `QA_LANG=ar QA_THEME=dark`; screenshots
`%TEMP%\radide-qa\shots\e2e_<tag>_*.png` (widget.grab()).

Added during QA (small, in the existing files):

- **Scan All Control Units** (Faults tab, `CarDiagWorkbench.scan_all_units()`): OBD-II modes 03/07/0A plus control
  unit discovery (`link.discovery.discover`) and UDS `19 02 FF` on every unit found, so ABS / airbag / cluster /
  climate faults appear next to the engine codes (code with failure-type byte, e.g. `C0035-1F`, unit name from
  the discovery guess). Needs a CAN link (adapter or the ELM327 Demo car); kept across Read Codes
  (`unit_entries`). Mode 04 (Clear Codes...) only lists / clears the OBD entries. Safety marking uses the
  5-character SAE code, so `C0035-1F` and `B0001-1A` are flagged.
- **Save Report...** (Faults tab, `save_report(path)` / `report_html()`): HTML diagnosis report in the UI language
  (`dir="rtl"` in Arabic): vehicle header, every fault with explanation, causes, checks and safety note,
  freeze frames of every unit, readiness summary + table, the live values read so far.
- **Read the Car's Lights** (Guide > Warning Lights, `CarFaultGuide.read_car_lights()`): MIL from OBD-II 01 01 on
  every car; on the Demo car simulator the instrument cluster's lamp word (DID `2220`, manufacturer-specific on
  real cars, so not read there); ABS / airbag lamps inferred from confirmed UDS faults of those units after Scan
  All Control Units. The lit lights are selected in the picker with a "Read from the car: ..." note.
- The **Service** tab of the workbench follows the workbench connection (`connected` signal: link -> "Car
  Diagnostics connection" with the workbench pack; disconnect -> its own Demo car), and after clearing a specific
  fault on that link it refreshes the workbench's Faults tab (Scan All again when it was used).
- Policy filter: "... faking" readiness and "mask / hide / suppress / disable <DTC>" are now rejected too.
- Simulator: mode 02 answers up to three (PID, frame) pairs per request (the OBD client asks three at a time on
  CAN; before, only the first was answered so most freeze-frame values were missing over ELM327).
- Routine result text: "Completed." instead of "Completed: completed" when the status label is the same word.

Arabic course: `radide/tutorials/car-diagnostics/` (9 lessons: car computers / OBD-II / UDS / adapters, connecting
and the Demo car, warning lights, fault codes, live data and freeze frames, readiness and the drive cycle, service
functions (cooling bleed, fan test, packs, policy, security plug-in), clearing faults correctly, full diagnosis
project with a report). `python radide/tutorials/car-diagnostics/tools/check_lessons.py` runs every block
(`carpy run` blocks use `radide.cardiag.*` against the simulator); CHM: `python tools/build_chm.py car-diagnostics
--verify` -> docs/chm/RADIDE_CAR_DIAGNOSTICS_ar.chm.
