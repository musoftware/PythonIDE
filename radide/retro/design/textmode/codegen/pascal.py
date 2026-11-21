"""Pascal code generator: Free Pascal (go32v2 / i8086-msdos for DOS, win32 for a quick test) and
Turbo Pascal 7 (the user's own copy). Uses the Crt unit (TextAttr, GotoXY, Write, KeyPressed, ReadKey);
the mouse comes from FPC's Mouse unit or, in Turbo Pascal, INT 33h through Dos.Intr. The bottom-right cell
(which would scroll a Crt window) and the screen dump read / write the video memory directly.

Run-time API for the user code::

    TuiSetText(id, 'text');        s := TuiGetText(id);
    TuiSetValue(id, v);            v := TuiGetValue(id);        (check box 0/1, option 1, list index, progress)
    TuiSetVisible(id, 0/1);        TuiSetEnabled(id, 0/1);
    TuiAddItem(id, 'text');        TuiClearList(id);            s := TuiGetItem(id, k);
    TuiShowScreen(screen);         TuiMsgBox('Title', 'Text');   TuiQuit;
    TuiKey                         the key of a KeyPress event (set it to 0 to cancel the key)
"""
from __future__ import annotations

from .common import App, Regions, build_app, chunks, line_of

CM = ("{ ", " }")
HANDLER_DEFAULT = "begin\nend;"


def lit(b: bytes) -> str:
    """Pascal string expression: 'abc'#196'def' ('' for an empty string)."""
    if not b:
        return "''"
    out = []
    run = ""
    for x in b:
        if 32 <= x < 127 and x != 39 and x not in (123, 125):
            run += chr(x)
        else:
            if run:
                out.append(f"'{run}'")
                run = ""
            out.append(f"#{x}")
    if run:
        out.append(f"'{run}'")
    return "".join(out)


def assign(target: str, b: bytes, width: int = 90) -> list[str]:
    """``target := literal;`` (Turbo Pascal reads at most 127 characters per line)."""
    e = lit(b)
    if len(e) + len(target) < width:
        return [f"  {target} := {e};"]
    out = [f"  {target} := '';"]
    piece = b""
    for x in b:
        piece += bytes([x])
        if len(lit(piece)) > width - len(target) - 20:
            out.append(f"  {target} := {target} + {lit(piece)};")
            piece = b""
    if piece:
        out.append(f"  {target} := {target} + {lit(piece)};")
    return out


RUNTIME = r"""
{ ===================================================================== RAD IDE text-mode runtime }
procedure TuiFire(i, ev: Integer); forward;
procedure TuiFireMenu(k: Integer); forward;
procedure TuiFireScreen(s, ev: Integer); forward;

{$IFNDEF FPC}
procedure TuiInt10(ax, cx, dx: Word);
var r: Registers;
begin
  r.AX := ax; r.BX := 0; r.CX := cx; r.DX := dx;
  Intr($10, r);
end;
{$ENDIF}

procedure TuiCursorOn(v: Integer);
begin
{$IFDEF FPC}
  if v <> 0 then CursorOn else CursorOff;
{$ELSE}
  if v <> 0 then TuiInt10($0100, $0607, 0) else TuiInt10($0100, $2000, 0);
{$ENDIF}
end;

procedure TuiMouseShow(v: Integer);
{$IFNDEF FPC}
var r: Registers;
{$ENDIF}
begin
  if TuiMouse = 0 then Exit;
  if v <> 0 then
  begin
    Dec(TuiHc);
    if TuiHc <> 0 then Exit;
{$IFDEF FPC}
    ShowMouse;
{$ELSE}
    r.AX := 1; Intr($33, r);
{$ENDIF}
  end
  else
  begin
    Inc(TuiHc);
    if TuiHc <> 1 then Exit;
{$IFDEF FPC}
    HideMouse;
{$ELSE}
    r.AX := 2; Intr($33, r);
{$ENDIF}
  end;
end;

procedure TuiPollMouse;
{$IFNDEF FPC}
var r: Registers;
{$ENDIF}
begin
  TuiMb := 0;
  if TuiMouse = 0 then Exit;
{$IFDEF FPC}
  TuiMb := GetMouseButtons and 7;
  TuiMx := GetMouseX;
  TuiMy := GetMouseY;
{$ELSE}
  r.AX := 3; Intr($33, r);
  TuiMb := r.BX and 7; TuiMx := r.CX shr 3; TuiMy := r.DX shr 3;
{$ENDIF}
end;

procedure TuiMouseInit;
{$IFNDEF FPC}
var r: Registers;
{$ENDIF}
begin
{$IFDEF FPC}
  InitMouse;
  if DetectMouse > 0 then begin TuiMouse := 1; ShowMouse; end;
{$ELSE}
  r.AX := 0; Intr($33, r);
  if r.AX = $FFFF then begin TuiMouse := 1; r.AX := 1; Intr($33, r); end;
{$ENDIF}
end;

function TuiNorm(c: Char): Integer;
begin
  if c = #0 then TuiNorm := 256 + Ord(ReadKey) else TuiNorm := Ord(c);
end;

function TuiReadKey: Integer;
begin
  TuiReadKey := 0;
  if KeyPressed then TuiReadKey := TuiNorm(ReadKey);
end;

function TuiGetEvent(var cl: Integer): Integer;
var k: Integer;
begin
  cl := 0;
  if TuiMouse = 0 then
  begin
    TuiGetEvent := TuiNorm(ReadKey);
    Exit;
  end;
  k := TuiReadKey;
  TuiPollMouse;
  if (TuiMb and 1) <> 0 then
  begin
    if TuiMp = 0 then begin TuiMp := 1; cl := 1; end;
  end
  else TuiMp := 0;
  if (k = 0) and (cl = 0) then Delay(10);
  TuiGetEvent := k;
end;

function TuiAltKey(k: Integer): Integer;
var s: Integer;
const R1: string[10] = 'QWERTYUIOP'; R2: string[9] = 'ASDFGHJKL'; R3: string[7] = 'ZXCVBNM';
      R4: string[10] = '1234567890';
begin
  s := k - 256;
  TuiAltKey := 0;
  if (s >= 16) and (s <= 25) then TuiAltKey := Ord(R1[s - 15]);
  if (s >= 30) and (s <= 38) then TuiAltKey := Ord(R2[s - 29]);
  if (s >= 44) and (s <= 50) then TuiAltKey := Ord(R3[s - 43]);
  if (s >= 120) and (s <= 129) then TuiAltKey := Ord(R4[s - 119]);
end;

function TuiUpper(k: Integer): Integer;
begin
  if (k >= 97) and (k <= 122) then TuiUpper := k - 32 else TuiUpper := k;
end;

procedure TuiCorner(c, a: Integer);
var o: Word;
{$IFDEF GO32V2}
  w: Word;
{$ENDIF}
begin
  o := ((ROWS - 1) * COLS + COLS - 1) * 2;
{$IFDEF GO32V2}
  w := c or (a shl 8);
  dosmemput($B800, o, w, 2);
{$ELSE}
{$IFDEF MSDOS}
  Mem[$B800:o] := c;
  Mem[$B800:o + 1] := a;
{$ENDIF}
{$ENDIF}
end;

procedure TuiOut(x, y: Integer; const s: string; a: Integer);
var n: Integer; t: string;
begin
  n := Length(s);
  if x + n > COLS then n := COLS - x;
  if (n <= 0) or (y < 0) or (y >= ROWS) then Exit;
  t := Copy(s, 1, n);
  if (y = ROWS - 1) and (x + n = COLS) then
  begin
    TuiCorner(Ord(t[n]), a);
    Dec(n);
    if n = 0 then Exit;
    t := Copy(t, 1, n);
  end;
  TextAttr := a;
  GotoXY(x + 1, y + 1);
  Write(t);
end;

procedure TuiPut(x, y: Integer; const s, m: string; w, a, h: Integer);
var t: string; st, en, c, d: Integer;
begin
  if w <= 0 then Exit;
  t := Copy(s, 1, w);
  while Length(t) < w do t := t + ' ';
  st := 1;
  while st <= w do
  begin
    if (st <= Length(m)) and (m[st] = '1') then c := h else c := a;
    en := st;
    while en < w do
    begin
      if (en + 1 <= Length(m)) and (m[en + 1] = '1') then d := h else d := a;
      if d <> c then Break;
      Inc(en);
    end;
    TuiOut(x + st - 1, y, Copy(t, st, en - st + 1), c);
    st := en + 1;
  end;
end;

function TuiRep(c: Char; n: Integer): string;
var s: string; i: Integer;
begin
  s := '';
  for i := 1 to n do s := s + c;
  TuiRep := s;
end;

procedure TuiBox(x, y, w, h, a, dbl: Integer);
var t, m, b: string; r: Integer;
begin
  if dbl <> 0 then
  begin
    t := #201 + TuiRep(#205, w - 2) + #187;
    m := #186 + TuiRep(' ', w - 2) + #186;
    b := #200 + TuiRep(#205, w - 2) + #188;
  end
  else
  begin
    t := #218 + TuiRep(#196, w - 2) + #191;
    m := #179 + TuiRep(' ', w - 2) + #179;
    b := #192 + TuiRep(#196, w - 2) + #217;
  end;
  TuiOut(x, y, t, a);
  for r := 1 to h - 2 do TuiOut(x, y + r, m, a);
  TuiOut(x, y + h - 1, b, a);
end;

procedure TuiBlit(const p: array of Byte);
var i, x, y, n: Integer;
begin
  i := 0; x := 0; y := 0;
  while p[i] <> 0 do
  begin
    n := p[i];
    TuiOut(x, y, TuiRep(Chr(p[i + 1]), n), p[i + 2]);
    Inc(x, n);
    if x >= COLS then begin x := 0; Inc(y); end;
    Inc(i, 3);
  end;
end;

procedure TuiFace(i: Integer);
var t, a, h, x, y, w, p, ix, iy, iw, ih, sel, tp, sa, r, k, b, mx, v, f: Integer; s, m: string;
begin
  if (ZI[i] = 0) or (ZT[i] = 9) then Exit;
  TuiMouseShow(0);
  t := ZT[i]; a := ZA[i]; h := ZB[i];
  if ZN[i] = 0 then begin a := (a and $F0) or 8; h := a; end
  else if (i = TuiFoc) and (t >= 2) and (t <= 5) then begin a := ZF[i]; h := ZG[i]; end;
  x := ZX[i]; y := ZY[i]; w := ZW[i];
  case t of
    1, 2:
      begin
        s := Copy(TX[i], 1, w); m := Copy(HM[i], 1, w); p := 0;
        if (t = 2) or (ZJ[i] = 1) then p := (w - Length(s)) div 2;
        if (t = 1) and (ZJ[i] = 2) then p := w - Length(s);
        TuiPut(x, y, TuiRep(' ', p) + s, TuiRep('0', p) + m, w, a, h);
      end;
    3:
      begin
        s := TX[i];
        if ZJ[i] <> 0 then s := TuiRep('*', Length(s));
        if (i = TuiFoc) and (Length(s) >= w) then s := Copy(s, Length(s) - w + 2, w - 1);
        TuiPut(x, y, s, '', w, a, a);
      end;
    4:
      begin
        if ZV[i] <> 0 then s := '[X] ' else s := '[ ] ';
        TuiPut(x, y, s + TX[i], '0000' + HM[i], w, a, h);
      end;
    5:
      begin
        if ZV[i] <> 0 then s := '(*) ' else s := '( ) ';
        TuiPut(x, y, s + TX[i], '0000' + HM[i], w, a, h);
      end;
    6:
      begin
        ix := x; iy := y; iw := w; ih := ZH[i];
        if ZJ[i] <> 0 then begin Inc(ix); Inc(iy); Dec(iw, 2); Dec(ih, 2); end;
        sel := ZV[i]; tp := ZP[i];
        if sel >= 0 then
        begin
          if sel < tp then tp := sel;
          if sel >= tp + ih then tp := sel - ih + 1;
        end;
        ZP[i] := tp;
        sa := ZL[i];
        if ZN[i] = 0 then sa := a;
        for r := 0 to ih - 1 do
        begin
          k := tp + r; s := '';
          if k < Z2[i] then s := IT[Z1[i] + k];
          b := a;
          if (k = sel) and (k < Z2[i]) then b := sa;
          TuiPut(ix, iy + r, s, '', iw, b, b);
        end;
      end;
    7:
      begin
        mx := ZM[i];
        if mx < 1 then mx := 1;
        v := ZV[i];
        if v < 0 then v := 0;
        if v > mx then v := mx;
        f := Integer(LongInt(v) * w div mx);
        TuiPut(x, y, TuiRep(#219, f) + TuiRep(#176, w - f), '', w, a, a);
      end;
    8: TuiPut(x, y, TX[i], HM[i], w, a, h);
  end;
  TuiMouseShow(1);
end;

procedure TuiCursor;
var i, p: Integer;
begin
  i := TuiFoc;
  if (i > 0) and (ZT[i] = 3) then
  begin
    p := Length(TX[i]);
    if p > ZW[i] - 1 then p := ZW[i] - 1;
    GotoXY(ZX[i] + p + 1, ZY[i] + 1);
    TuiCursorOn(1);
  end
  else TuiCursorOn(0);
end;

procedure TuiBlitScreen(s: Integer); forward;

procedure TuiRedraw;
var i: Integer;
begin
  TuiMouseShow(0);
  TuiBlitScreen(TuiCur);
  for i := 1 to NC do if ZS[i] = TuiCur then TuiFace(i);
  TuiCursor;
  TuiMouseShow(1);
end;

function TuiCanFocus(j: Integer): Boolean;
begin
  TuiCanFocus := (ZO[j] > 0) and (ZI[j] <> 0) and (ZN[j] <> 0);
end;

procedure TuiShowScreen(s: Integer);
var i, best: Integer;
begin
  TuiCur := s; TuiFoc := 0; best := 0;
  for i := 1 to NC do
    if (ZS[i] = s) and TuiCanFocus(i) then
      if (best = 0) or (ZO[i] < ZO[best]) then best := i;
  TuiFoc := best;
  TuiRedraw;
  if (SV[s] and 1) <> 0 then TuiFireScreen(s, 4);
end;

procedure TuiFocus(i: Integer);
var o: Integer;
begin
  o := TuiFoc;
  TuiFoc := i;
  if (o > 0) and (o <> i) then TuiFace(o);
  if i > 0 then TuiFace(i);
  TuiCursor;
end;

procedure TuiNext(d: Integer);
var c, best, wrap, j: Integer;
begin
  c := 0;
  if TuiFoc > 0 then c := ZO[TuiFoc];
  best := 0; wrap := 0;
  for j := 1 to NC do
    if (ZS[j] = TuiCur) and TuiCanFocus(j) then
    begin
      if d > 0 then
      begin
        if (ZO[j] > c) and ((best = 0) or (ZO[j] < ZO[best])) then best := j;
        if (wrap = 0) or (ZO[j] < ZO[wrap]) then wrap := j;
      end
      else
      begin
        if (ZO[j] < c) and ((best = 0) or (ZO[j] > ZO[best])) then best := j;
        if (wrap = 0) or (ZO[j] > ZO[wrap]) then wrap := j;
      end;
    end;
  if best = 0 then best := wrap;
  if best > 0 then TuiFocus(best);
end;

procedure TuiActivate(i: Integer);
var j: Integer;
begin
  case ZT[i] of
    2, 6: TuiFire(i, 1);
    4:
      begin
        ZV[i] := 1 - ZV[i];
        TuiFace(i);
        TuiFire(i, 1);
      end;
    5:
      begin
        for j := 1 to NC do
          if (ZT[j] = 5) and (ZS[j] = ZS[i]) and (ZR[j] = ZR[i]) and (j <> i) and (ZV[j] <> 0) then
          begin
            ZV[j] := 0; TuiFace(j);
          end;
        ZV[i] := 1;
        TuiFace(i);
        TuiFire(i, 1);
      end;
  end;
end;

procedure TuiListMove(i, d: Integer);
var n, v: Integer;
begin
  n := Z2[i];
  if n = 0 then Exit;
  v := ZV[i] + d;
  if v < 0 then v := 0;
  if v > n - 1 then v := n - 1;
  if v <> ZV[i] then
  begin
    ZV[i] := v;
    TuiFace(i);
    TuiFire(i, 2);
  end;
end;

function TuiStep(m, it, d: Integer): Integer;
var n, k, c: Integer;
begin
  TuiStep := -1;
  n := MIC[m];
  if n = 0 then Exit;
  k := it;
  for c := 1 to n do
  begin
    k := k + d;
    if k < 0 then k := n - 1;
    if k >= n then k := 0;
    if ISP[MI1[m] + k] = 0 then begin TuiStep := k; Exit; end;
  end;
end;

procedure TuiDrawMenu(m, it: Integer);
var b, x, y, w, k, j: Integer;
begin
  TuiMouseShow(0);
  b := SB[MSC[m]];
  TuiPut(MTX[m], ZY[b], MTS[m], MTM[m], Length(MTS[m]), ZL[b], ZG[b]);
  x := MDX[m]; y := MDY[m]; w := MDW[m];
  TuiBox(x, y, w, MDH[m], ZA[b], 0);
  for k := 0 to MIC[m] - 1 do
  begin
    j := MI1[m] + k;
    if ISP[j] <> 0 then
      TuiOut(x, y + 1 + k, #195 + TuiRep(#196, w - 2) + #180, ZA[b])
    else if k = it then
      TuiPut(x + 1, y + 1 + k, IL[j], IM[j], w - 2, ZL[b], ZG[b])
    else
      TuiPut(x + 1, y + 1 + k, IL[j], IM[j], w - 2, ZA[b], ZB[b]);
  end;
  TuiMouseShow(1);
end;

procedure TuiMenu(m: Integer);
var it, fire, done, k, cl, h, m2, k2, x, y, b, j: Integer;
begin
  it := TuiStep(m, -1, 1);
  fire := 0; done := 0;
  while done = 0 do
  begin
    TuiRedraw;
    TuiDrawMenu(m, it);
    repeat k := TuiGetEvent(cl) until (k <> 0) or (cl <> 0);
    if cl <> 0 then
    begin
      x := TuiMx; y := TuiMy; b := SB[TuiCur];
      done := 1;
      if y = ZY[b] then
      begin
        for m2 := SM[TuiCur] to SL[TuiCur] do
          if (x >= MTX[m2]) and (x < MTX[m2] + Length(MTS[m2])) then
          begin
            m := m2; it := TuiStep(m, -1, 1); done := 0;
          end;
      end
      else if (x > MDX[m]) and (x < MDX[m] + MDW[m] - 1) and (y > MDY[m]) and (y < MDY[m] + MDH[m] - 1) then
      begin
        j := MI1[m] + y - MDY[m] - 1;
        if ISP[j] = 0 then fire := j else done := 0;
      end;
    end
    else if (k = 27) or (k = 324) then done := 1
    else if k = 331 then
    begin
      Dec(m);
      if m < SM[TuiCur] then m := SL[TuiCur];
      it := TuiStep(m, -1, 1);
    end
    else if k = 333 then
    begin
      Inc(m);
      if m > SL[TuiCur] then m := SM[TuiCur];
      it := TuiStep(m, -1, 1);
    end
    else if k = 328 then it := TuiStep(m, it, -1)
    else if k = 336 then it := TuiStep(m, it, 1)
    else if k = 13 then
    begin
      if it >= 0 then begin fire := MI1[m] + it; done := 1; end;
    end
    else
    begin
      h := 0;
      if k > 256 then
      begin
        h := TuiAltKey(k);
        for m2 := SM[TuiCur] to SL[TuiCur] do
          if (h > 0) and (MKY[m2] = h) then begin m := m2; it := TuiStep(m, -1, 1); h := 0; end;
      end
      else if k < 256 then h := TuiUpper(k);
      if h > 0 then
        for k2 := 0 to MIC[m] - 1 do
          if (IKY[MI1[m] + k2] = h) and (ISP[MI1[m] + k2] = 0) then
          begin
            fire := MI1[m] + k2; done := 1; Break;
          end;
    end;
    if fire > 0 then done := 1;
  end;
  TuiRedraw;
  if fire > 0 then TuiFireMenu(fire);
end;

procedure TuiHandleKey(k: Integer);
var i, t, j, h, m: Integer;
begin
  TuiKey := k;
  i := TuiFoc;
  if (i > 0) and ((ZE[i] and 4) <> 0) then TuiFire(i, 3);
  if TuiKey = 0 then Exit;
  if (SV[TuiCur] and 4) <> 0 then TuiFireScreen(TuiCur, 3);
  k := TuiKey;
  if k = 0 then Exit;
  i := TuiFoc;
  t := 0;
  if i > 0 then t := ZT[i];
  if t = 3 then
  begin
    if k = 8 then
    begin
      if Length(TX[i]) > 0 then
      begin
        TX[i] := Copy(TX[i], 1, Length(TX[i]) - 1);
        TuiFace(i); TuiCursor;
        if (ZE[i] and 2) <> 0 then TuiFire(i, 2);
      end;
      Exit;
    end;
    if (k >= 32) and (k < 256) then
    begin
      if Length(TX[i]) < ZM[i] then
      begin
        TX[i] := TX[i] + Chr(k);
        TuiFace(i); TuiCursor;
        if (ZE[i] and 2) <> 0 then TuiFire(i, 2);
      end;
      Exit;
    end;
  end;
  case k of
    9: TuiNext(1);
    271: TuiNext(-1);
    336, 333: if t = 6 then TuiListMove(i, 1) else TuiNext(1);
    328, 331: if t = 6 then TuiListMove(i, -1) else TuiNext(-1);
    13: if t = 3 then TuiNext(1) else if i > 0 then TuiActivate(i);
    32: if (i > 0) and (t <> 6) then TuiActivate(i);
    27:
      if SK[TuiCur] > 0 then TuiActivate(SK[TuiCur])
      else if SE[TuiCur] <> 0 then TuiRun := 0;
    324: if SM[TuiCur] > 0 then TuiMenu(SM[TuiCur]);
  else
    begin
      h := 0;
      if k > 256 then h := TuiAltKey(k);
      if h > 0 then
        for m := 1 to NM do
          if (MSC[m] = TuiCur) and (MKY[m] = h) then begin TuiMenu(m); Exit; end;
      if (h = 0) and (k < 256) and (t <> 3) then h := TuiUpper(k);
      if h > 0 then
        for j := 1 to NC do
          if (ZS[j] = TuiCur) and (ZK[j] = h) and TuiCanFocus(j) then
          begin
            TuiFocus(j);
            if (ZT[j] = 2) or (ZT[j] = 4) or (ZT[j] = 5) then TuiActivate(j);
            Exit;
          end;
    end;
  end;
end;

procedure TuiClick(x, y: Integer);
var b, m, j, iy, ih, r: Integer;
begin
  b := SB[TuiCur];
  if (b > 0) and (y = ZY[b]) then
  begin
    for m := 1 to NM do
      if (MSC[m] = TuiCur) and (x >= MTX[m]) and (x < MTX[m] + Length(MTS[m])) then
      begin
        TuiMenu(m); Exit;
      end;
    Exit;
  end;
  for j := NC downto 1 do
    if (ZS[j] = TuiCur) and TuiCanFocus(j) and (x >= ZX[j]) and (x < ZX[j] + ZW[j]) and
       (y >= ZY[j]) and (y < ZY[j] + ZH[j]) then
    begin
      TuiFocus(j);
      if ZT[j] = 6 then
      begin
        iy := ZY[j]; ih := ZH[j];
        if ZJ[j] <> 0 then begin Inc(iy); Dec(ih, 2); end;
        r := y - iy;
        if (r >= 0) and (r < ih) and (ZP[j] + r < Z2[j]) then
        begin
          if ZV[j] <> ZP[j] + r then
          begin
            ZV[j] := ZP[j] + r; TuiFace(j);
            if (ZE[j] and 2) <> 0 then TuiFire(j, 2);
          end;
          TuiFire(j, 1);
        end;
      end
      else if ZT[j] <> 3 then TuiActivate(j);
      Exit;
    end;
end;

procedure TuiMsgBox(const t, s: string);
var w, h, x, y, k, cl: Integer; tt: string;
begin
  w := Length(s) + 4;
  if Length(t) + 6 > w then w := Length(t) + 6;
  if w < 12 then w := 12;
  if w > COLS then w := COLS;
  h := 6;
  x := (COLS - w) div 2; y := (ROWS - h) div 2;
  TuiMouseShow(0);
  TuiBox(x, y, w, h, $70, 1);
  if Length(t) > 0 then
  begin
    tt := ' ' + Copy(t, 1, w - 6) + ' ';
    TuiOut(x + (w - Length(tt)) div 2, y, tt, $70);
  end;
  TuiOut(x + 2, y + 2, Copy(s, 1, w - 4), $70);
  TuiOut(x + (w - 6) div 2, y + 4, '  OK  ', $2F);
  TuiCursorOn(0);
  TuiMouseShow(1);
  repeat k := TuiGetEvent(cl) until (cl <> 0) or (k = 13) or (k = 27) or (k = 32);
  TuiRedraw;
end;

procedure TuiSetText(i: Integer; const s: string);
begin
  TX[i] := s; HM[i] := '';
  if ZS[i] = TuiCur then begin TuiFace(i); TuiCursor; end;
end;

function TuiGetText(i: Integer): string;
begin
  TuiGetText := TX[i];
end;

procedure TuiSetValue(i, v: Integer);
var j: Integer;
begin
  if (ZT[i] = 5) and (v <> 0) then
  begin
    for j := 1 to NC do
      if (ZT[j] = 5) and (ZS[j] = ZS[i]) and (ZR[j] = ZR[i]) then ZV[j] := 0;
    ZV[i] := 1;
  end
  else ZV[i] := v;
  if ZS[i] = TuiCur then TuiRedraw;
end;

function TuiGetValue(i: Integer): Integer;
begin
  TuiGetValue := ZV[i];
end;

procedure TuiSetVisible(i, v: Integer);
begin
  ZI[i] := v;
  if (v = 0) and (TuiFoc = i) then begin TuiNext(1); if TuiFoc = i then TuiFoc := 0; end;
  if ZS[i] = TuiCur then TuiRedraw;
end;

procedure TuiSetEnabled(i, v: Integer);
begin
  ZN[i] := v;
  if (v = 0) and (TuiFoc = i) then begin TuiNext(1); if TuiFoc = i then TuiFoc := 0; end;
  if ZS[i] = TuiCur then TuiRedraw;
end;

procedure TuiAddItem(i: Integer; const s: string);
begin
  if Z2[i] >= Z3[i] then Exit;
  IT[Z1[i] + Z2[i]] := s;
  Inc(Z2[i]);
  if ZV[i] < 0 then ZV[i] := 0;
  if ZS[i] = TuiCur then TuiFace(i);
end;

procedure TuiClearList(i: Integer);
begin
  Z2[i] := 0; ZV[i] := -1; ZP[i] := 0;
  if ZS[i] = TuiCur then TuiFace(i);
end;

function TuiGetItem(i, k: Integer): string;
begin
  if (k >= 0) and (k < Z2[i]) then TuiGetItem := IT[Z1[i] + k] else TuiGetItem := '';
end;

procedure TuiQuit;
begin
  TuiRun := 0;
end;

procedure TuiDump;
var f: File; n: Integer;
{$IFNDEF GO32V2}
  i: Integer;
{$ENDIF}
begin
  TuiMouseShow(0);
  n := COLS * ROWS * 2;
{$IFDEF GO32V2}
  dosmemget($B800, 0, TuiDumpBuf, n);
{$ELSE}
{$IFDEF MSDOS}
  for i := 0 to n - 1 do TuiDumpBuf[i] := Mem[$B800:i];
{$ELSE}
  Exit;
{$ENDIF}
{$ENDIF}
  Assign(f, 'SCREEN.BIN');
  Rewrite(f, 1);
  BlockWrite(f, TuiDumpBuf, n);
  Close(f);
end;

procedure TuiInit;
var i: Integer; p: string;
begin
  for i := 1 to ParamCount do
  begin
    p := ParamStr(i);
    if (Length(p) >= 2) and (p[1] = '/') and (UpCase(p[2]) = 'D') then TuiDumpFlag := 1;
  end;
@MODE@
  TextAttr := 7;
  ClrScr;
  TuiCursorOn(0);
  TuiTables;
  TuiMouseInit;
  TuiRun := 1;
end;

procedure TuiMain;
var k, cl: Integer;
@SPLASHVARS@
begin
@SPLASH@
  TuiShowScreen(1);
  if TuiDumpFlag <> 0 then begin TuiDump; TuiRun := 0; end;
  while TuiRun <> 0 do
  begin
    k := TuiGetEvent(cl);
    if k <> 0 then TuiHandleKey(k);
    if cl <> 0 then TuiClick(TuiMx, TuiMy);
  end;
  TuiMouseShow(0);
{$IFDEF FPC}
  if TuiMouse <> 0 then DoneMouse;
{$ENDIF}
  TextAttr := 7;
  ClrScr;
  TuiCursorOn(1);
end;
"""

SPLASH = r"""  TuiBlitScreen(0);
  if TuiDumpFlag = 0 then
  begin
    t := 0;
    if @SECONDS@ > 0 then
      while (t < @SECONDS@ * 20) and not KeyPressed do begin Delay(50); Inc(t); end
    else
      while not KeyPressed do Delay(20);
    if KeyPressed then k := TuiNorm(ReadKey);
  end;"""

MODES = {25: "  TextMode(CO80);", 43: "  TextMode(CO80 + Font8x8);", 50: "  TextMode(CO80 + Font8x8);"}


def _arr(name: str, values: list, typ: str = "Integer") -> list[str]:
    vals = [str(v) for v in values]
    out = [f"  {name}: array[0..{len(vals) - 1}] of {typ} = ("]
    for ch in chunks(vals, 18):
        out.append("    " + ", ".join(ch) + ",")
    out[-1] = out[-1].rstrip(",") + ");"
    return out


def generate(screens, old_text: str = "", app: App | None = None, program: str = "TuiApp") -> tuple[str, list[str]]:
    app = app or build_app(screens, basic=True)
    rg = Regions(old_text, CM)
    out: list[str] = []
    w = out.append
    w(f"{{ {app.screens[0].name} - DOS text-mode program generated by RAD IDE (Text-Mode Designer)")
    w("  Do not edit outside the USER CODE regions: the rest is rewritten when the screens change.")
    w("  Build: fpc -Tgo32v2 main.pas (DOS, 32-bit) | fpc -Tmsdos main.pas (16-bit) | fpc main.pas (Windows test)")
    w("         | tpc main.pas (Turbo Pascal 7) }")
    w(f"program {program};")
    w("")
    w("uses Crt")
    w("{$IFDEF FPC}, Mouse{$ENDIF}")
    w("{$IFDEF GO32V2}, Go32{$ENDIF}")
    w("{$IFNDEF FPC}, Dos{$ENDIF};")
    w("")
    nc, nm, ni = max(1, len(app.ctls)), max(1, len(app.menus)), max(1, len(app.items))
    w("const")
    w(f"  COLS = {app.cols};")
    w(f"  ROWS = {app.rows};")
    w(f"  NC = {len(app.ctls)};")
    w(f"  NM = {len(app.menus)};")
    for s in app.screens:
        w(f"  {s.name} = {s.index};")
    for c in app.ctls:
        w(f"  {c.name} = {c.index};")
    sp = app.splash()
    if sp:
        out.extend(_arr("TS0", [v for r in sp.splash_runs for v in r] + [0], "Byte"))
    for s in app.screens:
        out.extend(_arr(f"TS{s.index}", [v for r in s.runs for v in r] + [0], "Byte"))
    w("")
    w("type")
    w("  TStr = string[120];")
    w("  TItem = string[80];")
    w("")
    w("var")
    arrays = "ZT ZS ZX ZY ZW ZH ZA ZB ZF ZG ZL ZV ZM ZP ZO ZK ZR ZE ZI ZN ZJ Z1 Z2 Z3".split()
    for i in range(0, len(arrays), 8):
        w(f"  {', '.join(arrays[i:i + 8])}: array[0..{nc}] of Integer;")
    w(f"  TX, HM: array[0..{nc}] of TStr;")
    w(f"  IT: array[0..{app.n_items}] of TItem;")
    w(f"  MSC, MTX, MKY, MDX, MDY, MDW, MDH, MI1, MIC: array[0..{nm}] of Integer;")
    w(f"  MTS, MTM: array[0..{nm}] of TItem;")
    w(f"  IL, IM: array[0..{ni}] of TItem;")
    w(f"  ISP, IKY: array[0..{ni}] of Integer;")
    w(f"  SE, SK, SV, SB, SM, SL: array[0..{len(app.screens)}] of Integer;")
    w("  TuiCur, TuiFoc, TuiRun, TuiKey, TuiMouse, TuiHc, TuiMb, TuiMx, TuiMy, TuiMp, TuiDumpFlag: Integer;")
    w(f"  TuiDumpBuf: array[0..{app.cols * app.rows * 2 - 1}] of Byte;")
    w("")
    w(rg.region("declarations", "{ your const / type / var declarations }"))
    w("")
    w("procedure TuiTables;")
    w("begin")
    out.extend(_tables(app))
    w("end;")
    w("")
    rt = RUNTIME.replace("@MODE@", MODES.get(app.rows, MODES[25]))
    rt = rt.replace("@SPLASHVARS@", "var t: Integer;" if sp else "")
    rt = rt.replace("@SPLASH@", SPLASH.replace("@SECONDS@", str(sp.splash_seconds)) if sp else "")
    rt = rt.replace("procedure TuiMain;\nvar k, cl: Integer;\nvar t: Integer;", "procedure TuiMain;\nvar k, cl, t: Integer;")
    out.append(rt)
    w("procedure TuiBlitScreen(s: Integer);")
    w("begin")
    w("  case s of")
    if sp:
        w("    0: TuiBlit(TS0);")
    for s in app.screens:
        w(f"    {s.index}: TuiBlit(TS{s.index});")
    w("  end;")
    w("end;")
    w("")
    w("{ ===================================================================== event handlers }")
    w(rg.region("general", "{ your own procedures and functions }"))
    w("")
    for h in app.handlers:
        w(f"procedure {h.key};")
        w(rg.region(h.key, HANDLER_DEFAULT))
        w("")
    w(rg.orphans("{ ", " }", HANDLER_DEFAULT))
    w("")
    for name, params, expr, hs, code in (
            ("TuiFire", "i, ev: Integer", "i * 4 + ev", app.ctl_handlers(),
             lambda h: h.target * 4 + {"Click": 1, "Change": 2, "KeyPress": 3}[h.event]),
            ("TuiFireMenu", "k: Integer", "k", app.menu_handlers(), lambda h: h.target),
            ("TuiFireScreen", "s, ev: Integer", "s * 8 + ev", app.screen_handlers(),
             lambda h: h.target * 8 + (4 if h.event == "Load" else 3))):
        w(f"procedure {name}({params});")
        w("begin")
        if hs:
            w(f"  case {expr} of")
            for h in hs:
                w(f"    {code(h)}: {h.key};")
            w("  end;")
        w("end;")
        w("")
    w("begin")
    w("  TuiInit;")
    w(rg.region("startup", "  { code that runs before the first screen is shown }"))
    w("  TuiMain;")
    w("end.")
    return "\n".join(out).replace("\r", "") + "\n", list(app.warnings)


def _tables(app: App) -> list[str]:
    t: list[str] = []
    for c in app.ctls:
        i = c.index
        vals = {"ZT": c.code, "ZS": c.screen, "ZX": c.x, "ZY": c.y, "ZW": c.w, "ZH": c.h, "ZA": c.a, "ZB": c.ha,
                "ZF": c.fa, "ZG": c.fha, "ZL": c.sa, "ZV": c.value, "ZM": c.max, "ZO": c.tab, "ZK": c.hotkey,
                "ZR": c.group, "ZE": c.events, "ZI": c.visible, "ZN": c.enabled, "ZJ": c.flag, "Z1": c.first_item,
                "Z2": len(c.items), "Z3": c.capacity}
        parts = [f"{k}[{i}] := {v};" for k, v in vals.items() if v]
        for ch in chunks(parts, 6):
            t.append("  " + " ".join(ch))
        if c.text:
            t.extend(assign(f"TX[{i}]", c.text))
        if "1" in c.mask:
            t.append(f"  HM[{i}] := '{c.mask}';")
        for k, it in enumerate(c.items):
            t.extend(assign(f"IT[{c.first_item + k}]", it))
    for m in app.menus:
        i = m.index
        x, y, ww, hh = m.box
        t.append(f"  MSC[{i}] := {m.screen}; MTX[{i}] := {m.title_x}; MKY[{i}] := {m.hotkey}; MDX[{i}] := {x};")
        t.append(f"  MDY[{i}] := {y}; MDW[{i}] := {ww}; MDH[{i}] := {hh}; MI1[{i}] := {m.first_item}; "
                 f"MIC[{i}] := {m.count};")
        t.extend(assign(f"MTS[{i}]", m.title))
        t.append(f"  MTM[{i}] := '{m.mask}';")
    for it in app.items:
        i = it.index
        if it.sep:
            t.append(f"  ISP[{i}] := 1;")
            continue
        t.extend(assign(f"IL[{i}]", it.line))
        t.append(f"  IM[{i}] := '{it.mask}'; IKY[{i}] := {it.hotkey};")
    for s in app.screens:
        i = s.index
        t.append(f"  SE[{i}] := {s.esc_quits}; SK[{i}] := {s.cancel}; SV[{i}] := {s.events}; SB[{i}] := {s.bar}; "
                 f"SM[{i}] := {s.menu_first}; SL[{i}] := {s.menu_last};")
    return t


def handler_line(text: str, key: str) -> int:
    return line_of(text, rf"^procedure\s+{key}\s*;")


def handler_name(key: str) -> str:
    return key
