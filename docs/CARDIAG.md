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
