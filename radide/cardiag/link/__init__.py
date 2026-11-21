"""Connections to the car and the diagnostic protocol stack (docs/CARDIAG.md "Link layer").

* adapters: ELM327 / STN11xx / OBDLink over COM ports (USB, Bluetooth SPP), Wi-Fi and Bluetooth LE (elm.py,
  transport.py, ports.py), J2534 PassThru (j2534.py), raw CAN with our ISO-TP (rawcan.py, isotp.py) and the
  Demo car (radide/cardiag/sim);
* protocols: OBD-II modes 01-0A (obd.py), UDS / ISO 14229 (uds.py), KWP2000 (kwp.py), negative response codes
  (nrc.py), control unit discovery (discovery.py);
* ``open_link(LinkConfig)`` / ``demo_link()`` (manager.py), the raw traffic log ``BUS_LOG`` (log.py) and the Qt
  Connect dialog / Bus Monitor (qt.py).

Security access only through a seed/key plug-in the user supplies; no immobiliser, odometer or emissions-defeat
functions anywhere in the stack.
"""
from .base import DiagLink, LinkError, NoResponse, NotConnected, Response
from .log import BUS_LOG
from .manager import LinkConfig, current_link, demo_can_link, demo_link, open_link, set_current_link

__all__ = ["DiagLink", "LinkError", "NoResponse", "NotConnected", "Response", "BUS_LOG", "LinkConfig", "open_link",
           "demo_link", "demo_can_link", "current_link", "set_current_link"]
