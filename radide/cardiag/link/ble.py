"""Bluetooth LE OBD adapters (optional, needs ``pip install bleak``): ``scan()`` lists nearby adapters,
``BleTransport`` (transport.py) carries the ELM327 text protocol over the adapter's serial-like GATT service."""
from __future__ import annotations

from dataclasses import dataclass

from .transport import BLE_PROFILES, BleTransport, ble_available, ble_scan


@dataclass
class BleDevice:
    address: str
    name: str

    def __str__(self) -> str:
        return f"{self.name} ({self.address})" if self.name else self.address


def scan(timeout: float = 5.0) -> list[BleDevice]:
    return [BleDevice(a, n) for a, n in ble_scan(timeout)]


available = ble_available

__all__ = ["BleDevice", "scan", "available", "BleTransport", "BLE_PROFILES"]
