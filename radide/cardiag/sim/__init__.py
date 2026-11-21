"""The Demo car simulator (docs/CARDIAG.md "Demo car"): a virtual vehicle with five UDS control units (car.py,
ecus.py, obd.py, kwp.py), an ELM327 interpreter in front of it (elm.py), a TCP server that makes it look like a
Wi-Fi OBD adapter (server.py, ``python -m radide.cardiag.sim``) and a virtual CAN bus with ISO-TP (canbus.py)."""
from .car import LAMPS, VIN, VirtualCar, demo_car, reset_demo_car

__all__ = ["VirtualCar", "demo_car", "reset_demo_car", "LAMPS", "VIN"]
