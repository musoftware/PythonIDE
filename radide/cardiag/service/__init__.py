"""Service functions for car diagnostics (docs/CARDIAG.md "Service functions").

* definitions.py - definition packs (JSON / CSV / ODX-PDX subset), validation and the policy filter
* transport.py   - ServiceClient: request / response checking, NRCs in Arabic, sessions, security via plug-in
* runner.py      - preconditions checklist + RoutineControl runner (start / poll with progress / stop / timeout)
* iocontrol.py   - actuator tests (0x2F) that always return control to the ECU
* adaptation.py  - service resets / adaptations / feature coding (0x2E) with read-back
* dtc.py         - "clear a specific fault" flow (explanation and safety warnings first, 0x14 single DTC or
                   clear-all fallback, OBD-II mode 04)
* security.py    - seed/key plug-ins chosen by the user (no algorithms included)
* profiles.py    - vehicle profiles (VIN) with history and the audit log of every service action
* demo_ecu.py    - the Demo car simulator used by the tests and the "Demo car" mode
"""
from __future__ import annotations

from .definitions import PackError, demo_pack, import_pack, load_pack_file, normalize, policy_reason
from .transport import Ecu, NegativeResponse, NoResponse, ServiceClient, ServiceError

__all__ = ["PackError", "demo_pack", "import_pack", "load_pack_file", "normalize", "policy_reason", "Ecu",
           "NegativeResponse", "NoResponse", "ServiceClient", "ServiceError", "demo_session"]


def demo_session(*, clock=None, sleep=None, bleed_seconds: float = 20.0, audit=None):
    """(DemoCar, ServiceClient, demo pack) - ready to run the Demo car's service functions."""
    import time

    from .demo_ecu import DemoCar, DemoTransport
    car = DemoCar(clock=clock or time.monotonic, bleed_seconds=bleed_seconds)
    client = ServiceClient(DemoTransport(car), audit=audit, sleep=sleep or time.sleep, clock=clock or time.monotonic)
    return car, client, demo_pack()
