"""Turbo Pascal-style templates (Free Pascal i8086-msdos, {$mode tp}). Original RAD IDE code."""

HELLO = """{ {name} - a Turbo Pascal-style program (RAD IDE)
  Build: Free Pascal i8086-msdos in TP mode -> a real 16-bit DOS .EXE. Run: Ctrl+F5 (DOSBox-X). }
{$mode tp}
program {ident};

uses Crt;

var
  Name: string;
  I: Integer;

begin
  ClrScr;
  TextColor(Yellow);
  TextBackground(Blue);
  WriteLn(' Hello from {name}! ');
  NormVideo;
  WriteLn;
  Write('What is your name? ');
  ReadLn(Name);
  if Name = '' then Name := 'friend';
  WriteLn('Welcome to DOS programming, ', Name, '!');
  for I := 1 to 5 do
    WriteLn(I:3, ' x ', I, ' = ', I * I);
  WriteLn('Done.');
end.
"""

MENU = """{ {name} - a text-mode menu with the Crt unit (arrow keys / 1-4 / Enter / Esc) }
{$mode tp}
program {ident};

uses Crt, Dos;

const
  Items: array[1..4] of string[20] = ('1  Say hello', '2  Show the time', '3  Count to ten', '4  Quit');

var
  Sel: Integer;
  Done: Boolean;
  K: Char;

procedure DrawBox(X1, Y1, X2, Y2: Integer);
var I: Integer;
begin
  TextColor(Yellow);
  GotoXY(X1, Y1); Write(#201);
  for I := X1 + 1 to X2 - 1 do Write(#205);
  Write(#187);
  for I := Y1 + 1 to Y2 - 1 do
  begin
    GotoXY(X1, I); Write(#186);
    GotoXY(X2, I); Write(#186);
  end;
  GotoXY(X1, Y2); Write(#200);
  for I := X1 + 1 to X2 - 1 do Write(#205);
  Write(#188);
end;

procedure ShowMenu;
var I: Integer;
begin
  for I := 1 to 4 do
  begin
    GotoXY(27, 6 + I);
    if I = Sel then begin TextColor(Black); TextBackground(Cyan); end
    else begin TextColor(White); TextBackground(Blue); end;
    Write(' ', Items[I], ' ': 24 - Length(Items[I]));
  end;
  TextColor(White);
  TextBackground(Blue);
end;

procedure RunItem;
var H, M, S, S100: Word;
    I: Integer;
begin
  GotoXY(10, 15); Write(' ': 60);
  GotoXY(10, 15);
  case Sel of
    1: Write('Hello! This menu was written in Pascal.');
    2: begin
         GetTime(H, M, S, S100);
         Write('The time is ', H, ':', M div 10, M mod 10, ':', S div 10, S mod 10);
       end;
    3: for I := 1 to 10 do Write(I, ' ');
    4: Done := True;
  end;
end;

begin
  TextBackground(Blue);
  ClrScr;
  TextColor(White);
  GotoXY(28, 2); Write('RAD IDE  -  DOS MENU');
  DrawBox(24, 5, 55, 12);
  Sel := 1;
  Done := False;
  repeat
    ShowMenu;
    K := ReadKey;
    case K of
      #0: begin
            K := ReadKey;
            if K = #72 then begin Dec(Sel); if Sel < 1 then Sel := 4; end;
            if K = #80 then begin Inc(Sel); if Sel > 4 then Sel := 1; end;
          end;
      '1'..'4': begin Sel := Ord(K) - Ord('0'); ShowMenu; RunItem; end;
      #13: RunItem;
      #27: Done := True;
    end;
  until Done;
  NormVideo;
  ClrScr;
  WriteLn('Goodbye!');
end.
"""

MODE13 = """{ {name} - mode 13h graphics (320 x 200, 256 colours) by writing to the video memory at A000:0000.
  Any key quits. }
{$mode tp}
program {ident};

uses Crt, Dos;

procedure SetMode(Mode: Byte);
var R: Registers;
begin
  R.AX := Mode;          { AH = 0: set video mode, AL = mode }
  Intr($10, R);
end;

procedure PutPixel(X, Y: Integer; Color: Byte);
begin
  if (X >= 0) and (X < 320) and (Y >= 0) and (Y < 200) then
    Mem[$A000:Y * 320 + X] := Color;
end;

procedure Box(X1, Y1, X2, Y2: Integer; Color: Byte);
var X, Y: Integer;
begin
  for Y := Y1 to Y2 do
    for X := X1 to X2 do
      PutPixel(X, Y, Color);
end;

var
  X, Y, I: Integer;
begin
  SetMode($13);
  for X := 0 to 255 do                      { colour bars }
    for Y := 150 to 199 do
      PutPixel(X + 32, Y, X);
  for I := 0 to 99 do                       { a diagonal pattern }
    for X := 0 to 99 do
      PutPixel(110 + X, 20 + I, 32 + ((X xor I) and 15));
  Box(20, 20, 80, 60, 4);
  Box(240, 20, 300, 60, 2);
  RandSeed := 1;
  for I := 1 to 300 do PutPixel(Random(320), Random(140), 16 + Random(16));
  repeat until KeyPressed;
  ReadKey;
  SetMode($03);
  WriteLn('Back in text mode.');
end.
"""

SPEAKER = """{ {name} - PC speaker music with Sound / Delay / NoSound (Crt unit) }
{$mode tp}
program {ident};

uses Crt;

const
  Notes: array[1..11] of Word = (523, 587, 659, 698, 784, 784, 880, 880, 880, 880, 784);
  Lens:  array[1..11] of Word = (150, 150, 150, 150, 300, 300, 150, 150, 150, 150, 450);

var
  I: Integer;
begin
  WriteLn('Playing a little tune on the PC speaker...');
  for I := 1 to 11 do
  begin
    Sound(Notes[I]);
    Delay(Lens[I]);
    NoSound;
    Delay(20);
  end;
  WriteLn('Finished.');
end.
"""

MOUSE = """{ {name} - the mouse driver (INT 33h) in text mode. Right button or any key quits. }
{$mode tp}
program {ident};

uses Crt, Dos;

var
  R: Registers;
  X, Y, B, OldX, OldY: Integer;

begin
  ClrScr;
  R.AX := 0; Intr($33, R);                  { reset: AX = FFFFh when a driver is present }
  if R.AX <> $FFFF then
  begin
    WriteLn('No mouse driver found.');
    Exit;
  end;
  WriteLn('Mouse found (', R.BX, ' buttons). Left button: draw a star, right button: quit.');
  R.AX := 1; Intr($33, R);                  { show the cursor }
  OldX := -1; OldY := -1;
  repeat
    R.AX := 3; Intr($33, R);                { position in pixels, BX = buttons }
    X := R.CX div 8 + 1; Y := R.DX div 8 + 1; B := R.BX;
    if (X <> OldX) or (Y <> OldY) then
    begin
      R.AX := 2; Intr($33, R);              { hide while writing }
      GotoXY(1, 25); Write('Column ', X:2, '  Row ', Y:2, '   ');
      R.AX := 1; Intr($33, R);
      OldX := X; OldY := Y;
    end;
    if (B and 1) <> 0 then
    begin
      R.AX := 2; Intr($33, R);
      GotoXY(X, Y); TextColor(Yellow); Write('*');
      R.AX := 1; Intr($33, R);
    end;
  until ((B and 2) <> 0) or KeyPressed;
  R.AX := 2; Intr($33, R);
  NormVideo;
  ClrScr;
  WriteLn('Mouse demo finished.');
end.
"""

TEMPLATES = [
    ("dostp_hello", "Hello (Turbo Pascal style)", "WriteLn / ReadLn with the Crt unit. Free Pascal compiles it "
     "into a real 16-bit DOS .EXE.", {"MAIN.PAS": HELLO}),
    ("dostp_menu", "Text-Mode Menu", "A boxed menu with GotoXY, TextColor, ReadKey and the Dos unit's GetTime.",
     {"MAIN.PAS": MENU}),
    ("dostp_mode13", "Mode 13h Graphics", "Intr($10) and Mem[$A000:...] - pixels straight into the VGA memory.",
     {"MAIN.PAS": MODE13}),
    ("dostp_speaker", "PC Speaker Music", "Sound, Delay and NoSound from the Crt unit.", {"MAIN.PAS": SPEAKER}),
    ("dostp_mouse", "Mouse (INT 33h)", "Reset, show, read the mouse with Intr($33) from the Dos unit.",
     {"MAIN.PAS": MOUSE}),
]
