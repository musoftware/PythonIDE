"""Run the Demo car as a Wi-Fi ELM327 adapter: ``python -m radide.cardiag.sim [--port 35000] [--host 0.0.0.0]
[--protocol 6] [--stn] [--drive] [--engine-off]``. Press Ctrl+C to stop."""
from __future__ import annotations

import argparse
import time

from .car import VirtualCar
from .server import DEFAULT_PORT, DemoCarServer


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m radide.cardiag.sim", description="RAD IDE Demo car (ELM327 over TCP)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--protocol", default="6", help="ELM protocol number of the car's bus (3-9)")
    ap.add_argument("--stn", action="store_true", help="identify as an STN1110 chip")
    ap.add_argument("--drive", action="store_true", help="start driving (speed / rpm profile)")
    ap.add_argument("--engine-off", action="store_true", help="ignition on, engine off")
    a = ap.parse_args(argv)
    car = VirtualCar(a.protocol, engine_running=not a.engine_off)
    if a.drive:
        car.set_driving(True)
    srv = DemoCarServer(car, a.host, a.port, stn="STN1110 v4.2.1" if a.stn else None)
    port = srv.start()
    print(f"Demo car listening on {a.host}:{port} (protocol {a.protocol}). Ctrl+C stops.", flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    srv.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
