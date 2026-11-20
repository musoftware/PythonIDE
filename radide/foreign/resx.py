""".resx (ResX resource files of Visual Studio / WinForms) - read and write WITHOUT losing anything.

The file is kept as text: entries are located with their character spans and only the entries that
change are rewritten (a file saved without changes is byte-identical).  Supported values:

* strings (``<data name="label1.Text" xml:space="preserve"><value>Hello</value></data>``)
* byte arrays (``mimetype="application/x-microsoft.net.object.bytearray.base64"``) - images
  (``System.Drawing.Bitmap``), icons (``System.Drawing.Icon``) and other files stored as raw bytes
* everything else (BinaryFormatter blobs, ``ResXFileRef``, metadata, ...) is kept verbatim and can be
  read as raw text (``entry(name).value``).

Usage::

    rx = ResxFile.load(path)            # or ResxFile.new(path) for a form that has none yet
    rx.get_string("label1.Text")
    rx.get_bytes("pictureBox1.Image")  # PNG/JPEG/... bytes of a Bitmap
    rx.set_bytes("pictureBox1.Image", data, BITMAP)
    rx.set_string("label1.Text", "Hi")
    rx.remove("button1.Image")
    rx.save()                           # writes only when something changed
"""
from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

BYTEARRAY_MIME = "application/x-microsoft.net.object.bytearray.base64"
BINARY_MIME = "application/x-microsoft.net.object.binary.base64"
BITMAP = "System.Drawing.Bitmap, System.Drawing"
ICON = "System.Drawing.Icon, System.Drawing"
STRING = ""          # plain string entry (no type attribute)

_ENTRY_RE = re.compile(r"(?s)([ \t]*)<(data|metadata)\b([^>]*?)(/>|>(.*?)</\2>)([ \t]*\r?\n)?")
_ATTR_RE = re.compile(r"""([\w:.-]+)\s*=\s*("([^"]*)"|'([^']*)')""")
_VALUE_RE = re.compile(r"(?s)<value\s*>(.*?)</value\s*>|<value\s*/>")
_COMMENT_RE = re.compile(r"(?s)<!--.*?-->")


def _unxml(s: str) -> str:
    s = re.sub(r"&#x([0-9a-fA-F]+);", lambda m: chr(int(m.group(1), 16)), s)
    s = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), s)
    return s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'") \
        .replace("&amp;", "&")


@dataclass
class ResxEntry:
    name: str
    tag: str                       # "data" | "metadata"
    attrs: dict                    # attribute name -> value (unescaped)
    value: str | None              # unescaped text of <value> (None = no <value>)
    comment: str | None = None
    start: int = -1                # span in the original text (-1 = new entry)
    end: int = -1

    @property
    def type(self) -> str:
        return self.attrs.get("type", "")

    @property
    def mimetype(self) -> str:
        return self.attrs.get("mimetype", "")

    @property
    def is_string(self) -> bool:
        return not self.type and not self.mimetype or self.type.startswith("System.String")

    @property
    def is_bytes(self) -> bool:
        return self.mimetype == BYTEARRAY_MIME


@dataclass
class ResxFile:
    path: Path
    text: str
    entries: list[ResxEntry] = field(default_factory=list)
    newline: str = "\r\n"
    _edits: dict = field(default_factory=dict)       # name -> ResxEntry | None (None = removed)
    _order: list = field(default_factory=list)       # new names in insertion order

    # ------------------------------------------------------------------ io
    @staticmethod
    def load(path) -> "ResxFile":
        path = Path(path)
        raw = path.read_bytes()
        text = raw.decode("utf-8-sig")
        rx = ResxFile(path, text)
        rx._bom = raw.startswith(b"\xef\xbb\xbf")
        rx.newline = "\r\n" if "\r\n" in text else "\n"
        rx._parse()
        return rx

    @staticmethod
    def new(path) -> "ResxFile":
        """A new, empty .resx with the standard Visual Studio header."""
        rx = ResxFile(Path(path), EMPTY_RESX.replace("\n", "\r\n"))
        rx._bom = True
        rx._parse()
        rx._new_file = True
        return rx

    def _parse(self) -> None:
        comments = [(m.start(), m.end()) for m in _COMMENT_RE.finditer(self.text)]

        def in_comment(pos):
            return any(a <= pos < b for a, b in comments)
        self.entries = []
        for m in _ENTRY_RE.finditer(self.text):
            if in_comment(m.start(2)):
                continue
            attrs = {a.group(1): _unxml(a.group(3) if a.group(3) is not None else a.group(4) or "")
                     for a in _ATTR_RE.finditer(m.group(3))}
            name = attrs.get("name")
            if name is None:
                continue
            body = m.group(5) or ""
            vm = _VALUE_RE.search(body)
            value = _unxml(vm.group(1) or "") if vm else None
            cm = re.search(r"(?s)<comment\s*>(.*?)</comment\s*>", body)
            self.entries.append(ResxEntry(name, m.group(2), attrs, value,
                                          _unxml(cm.group(1)) if cm else None, m.start(), m.end()))

    @property
    def modified(self) -> bool:
        return bool(self._edits) or getattr(self, "_new_file", False) and bool(self._order)

    def render(self) -> str:
        if not self._edits:
            return self.text
        out = self.text
        spans = []
        for e in self.entries:
            if e.name in self._edits:
                ne = self._edits[e.name]
                spans.append((e.start, e.end, "" if ne is None else self._entry_text(ne)))
        for a, b, rep in sorted(spans, reverse=True):
            out = out[:a] + rep + out[b:]
        new = [self._edits[n] for n in self._order if self._edits.get(n) is not None and
               not any(e.name == n for e in self.entries)]
        if new:
            add = "".join(self._entry_text(e) for e in new)
            pos = out.rfind("</root>")
            if pos < 0:
                out += add
            else:
                line_start = out.rfind("\n", 0, pos) + 1
                if out[line_start:pos].strip() == "":
                    pos = line_start
                out = out[:pos] + add + out[pos:]
        return out

    def save(self, path=None) -> bool:
        """Write the file when it changed (or is new); True when written."""
        if not self.modified:
            return False
        text = self.render()
        target = Path(path) if path else self.path
        data = text.encode("utf-8")
        if getattr(self, "_bom", False):
            data = b"\xef\xbb\xbf" + data
        target.write_bytes(data)
        # the saved text becomes the new baseline
        self.text, self._edits, self._order = text, {}, []
        self._new_file = False
        self._parse()
        return True

    # ------------------------------------------------------------------ queries
    def entry(self, name: str) -> ResxEntry | None:
        if name in self._edits:
            return self._edits[name]
        for e in self.entries:
            if e.name == name:
                return e
        return None

    def names(self) -> list[str]:
        out = [e.name for e in self.entries if self._edits.get(e.name, e) is not None]
        return out + [n for n in self._order if n not in out and self._edits.get(n) is not None]

    def get_string(self, name: str) -> str | None:
        e = self.entry(name)
        return e.value if e is not None and e.is_string else None

    def get_bytes(self, name: str) -> bytes | None:
        e = self.entry(name)
        if e is None or not e.is_bytes or e.value is None:
            return None
        try:
            return base64.b64decode("".join(e.value.split()))
        except ValueError:
            return None

    # ------------------------------------------------------------------ edits
    def _put(self, e: ResxEntry) -> None:
        old = self.entry(e.name)
        if old is not None and old.start >= 0 and self._same(old, e):
            self._edits.pop(e.name, None)          # back to the original
            return
        self._edits[e.name] = e
        if e.name not in self._order:
            self._order.append(e.name)

    @staticmethod
    def _same(a: ResxEntry, b: ResxEntry) -> bool:
        if a.attrs.get("type", "") != b.attrs.get("type", "") or a.mimetype != b.mimetype:
            return False
        if a.is_bytes:
            return "".join((a.value or "").split()) == "".join((b.value or "").split())
        return a.value == b.value and (b.comment is None or a.comment == b.comment)

    def set_string(self, name: str, value: str, comment: str | None = None) -> None:
        old = self.entry(name)
        attrs = {"name": name, "xml:space": "preserve"}
        if old is not None and old.is_string:
            attrs = dict(old.attrs)
            if comment is None:
                comment = old.comment
        self._put(ResxEntry(name, "data", attrs, value, comment))

    def set_bytes(self, name: str, data: bytes, type_name: str = BITMAP) -> None:
        old = self.entry(name)
        if old is not None and old.is_bytes and self.get_bytes(name) == data:
            return
        attrs = {"name": name, "type": type_name, "mimetype": BYTEARRAY_MIME}
        self._put(ResxEntry(name, "data", attrs, base64.b64encode(data).decode("ascii")))

    def set_metadata(self, name: str, value: str, type_name: str) -> None:
        self._put(ResxEntry(name, "metadata", {"name": name, "type": type_name}, value))

    def remove(self, name: str) -> None:
        if any(e.name == name for e in self.entries):
            self._edits[name] = None
        else:
            self._edits.pop(name, None)
            if name in self._order:
                self._order.remove(name)

    # ------------------------------------------------------------------ formatting
    def _entry_text(self, e: ResxEntry) -> str:
        nl = self.newline
        attrs = " ".join(f"{k}={quoteattr(v)}" for k, v in e.attrs.items())
        if e.value is None:
            return f"  <{e.tag} {attrs} />{nl}"
        if e.mimetype in (BYTEARRAY_MIME, BINARY_MIME):
            b64 = "".join(e.value.split())
            lines = [b64[i:i + 80] for i in range(0, len(b64), 80)] or [""]
            value = nl + "".join(f"        {ln}{nl}" for ln in lines)
        else:
            value = escape(e.value)
        out = f"  <{e.tag} {attrs}>{nl}    <value>{value}</value>{nl}"
        if e.comment is not None:
            out += f"    <comment>{escape(e.comment)}</comment>{nl}"
        return out + f"  </{e.tag}>{nl}"


def image_type_for(data: bytes) -> str:
    """resx type of an image file's bytes (an .ico is an Icon, everything else a Bitmap)."""
    return ICON if data[:4] == b"\x00\x00\x01\x00" else BITMAP


def image_ext(data: bytes) -> str:
    if data.startswith(b"\x89PNG"):
        return ".png"
    if data[:3] == b"GIF":
        return ".gif"
    if data[:2] == b"\xff\xd8":
        return ".jpg"
    if data[:2] == b"BM":
        return ".bmp"
    if data[:4] == b"\x00\x00\x01\x00":
        return ".ico"
    return ".bin"


EMPTY_RESX = """<?xml version="1.0" encoding="utf-8"?>
<root>
  <!--
    Microsoft ResX Schema

    Version 2.0

    The primary goals of this format is to allow a simple XML format
    that is mostly human readable. The generation and parsing of the
    various data types are done through the TypeConverter classes
    associated with the data types.
    -->
  <xsd:schema id="root" xmlns="" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:msdata="urn:schemas-microsoft-com:xml-msdata">
    <xsd:import namespace="http://www.w3.org/XML/1998/namespace" />
    <xsd:element name="root" msdata:IsDataSet="true">
      <xsd:complexType>
        <xsd:choice maxOccurs="unbounded">
          <xsd:element name="metadata">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element name="value" type="xsd:string" minOccurs="0" />
              </xsd:sequence>
              <xsd:attribute name="name" use="required" type="xsd:string" />
              <xsd:attribute name="type" type="xsd:string" />
              <xsd:attribute name="mimetype" type="xsd:string" />
              <xsd:attribute ref="xml:space" />
            </xsd:complexType>
          </xsd:element>
          <xsd:element name="assembly">
            <xsd:complexType>
              <xsd:attribute name="alias" type="xsd:string" />
              <xsd:attribute name="name" type="xsd:string" />
            </xsd:complexType>
          </xsd:element>
          <xsd:element name="data">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element name="value" type="xsd:string" minOccurs="0" msdata:Ordinal="1" />
                <xsd:element name="comment" type="xsd:string" minOccurs="0" msdata:Ordinal="2" />
              </xsd:sequence>
              <xsd:attribute name="name" type="xsd:string" use="required" msdata:Ordinal="1" />
              <xsd:attribute name="type" type="xsd:string" msdata:Ordinal="3" />
              <xsd:attribute name="mimetype" type="xsd:string" msdata:Ordinal="4" />
              <xsd:attribute ref="xml:space" />
            </xsd:complexType>
          </xsd:element>
          <xsd:element name="resheader">
            <xsd:complexType>
              <xsd:sequence>
                <xsd:element name="value" type="xsd:string" minOccurs="0" msdata:Ordinal="1" />
              </xsd:sequence>
              <xsd:attribute name="name" type="xsd:string" use="required" />
            </xsd:complexType>
          </xsd:element>
        </xsd:choice>
      </xsd:complexType>
    </xsd:element>
  </xsd:schema>
  <resheader name="resmimetype">
    <value>text/microsoft-resx</value>
  </resheader>
  <resheader name="version">
    <value>2.0</value>
  </resheader>
  <resheader name="reader">
    <value>System.Resources.ResXResourceReader, System.Windows.Forms, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089</value>
  </resheader>
  <resheader name="writer">
    <value>System.Resources.ResXResourceWriter, System.Windows.Forms, Version=4.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089</value>
  </resheader>
</root>"""
