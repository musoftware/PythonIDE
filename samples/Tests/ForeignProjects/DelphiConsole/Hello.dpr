program Hello;

{$APPTYPE CONSOLE}

uses
  System.SysUtils,
  MathUtils in 'MathUtils.pas';

var
  I: Integer;
begin
  WriteLn('Hello from Delphi!');
  for I := 1 to 5 do
    WriteLn(Format('%d! = %d', [I, Factorial(I)]));
end.
