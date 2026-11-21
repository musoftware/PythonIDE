{ SORTDEMO.PAS - old Turbo Pascal style: Crt, Dos, records, a bubble sort (original RAD IDE sample) }
program SortDemo;

uses Crt, Dos;

type
  TScore = record
    Name: string[10];
    Points: Integer;
  end;

const
  Count = 5;
  Names: array[1..Count] of string[10] = ('ALI', 'MONA', 'OMAR', 'SARA', 'ZAID');
  Points: array[1..Count] of Integer = (40, 95, 70, 15, 60);

var
  Scores: array[1..Count] of TScore;
  I, J: Integer;
  Tmp: TScore;
  H, M, S, S100: Word;

begin
  ClrScr;
  TextColor(LightGreen);
  WriteLn('HIGH SCORES');
  NormVideo;
  for I := 1 to Count do
  begin
    Scores[I].Name := Names[I];
    Scores[I].Points := Points[I];
  end;
  for I := 1 to Count - 1 do
    for J := 1 to Count - I do
      if Scores[J].Points < Scores[J + 1].Points then
      begin
        Tmp := Scores[J];
        Scores[J] := Scores[J + 1];
        Scores[J + 1] := Tmp;
      end;
  for I := 1 to Count do
    WriteLn(I:2, '. ', Scores[I].Name:10, Scores[I].Points:5);
  GetTime(H, M, S, S100);
  WriteLn('Sorted.');
end.
