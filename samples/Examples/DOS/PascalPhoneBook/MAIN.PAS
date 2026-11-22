{ (c) 2026 Musoftware - https://musoftwares.com - MIT License

  PascalPhoneBook - a Turbo Pascal style phone book for DOS.
  * records (name, phone, city) kept in a typed file PHONES.DAT ("file of TContact") - they survive between runs;
  * menu: A add, L list, F find (case-insensitive part of a name), D delete, S sort by name, Q quit;
  * Crt unit for colours / ClrScr / ReadKey, ReadLn for the input lines, IOResult checks ($I-) for the file.
  RAD IDE builds it with Free Pascal for 16-bit DOS (ppcross8086 -Tmsdos, Turbo Pascal mode) and runs it in
  DOSBox-X (Ctrl+F5). If you own Turbo Pascal 7, Project > DOS Settings > Compiler = Turbo Pascal builds it too. }
{$mode tp}
program PhoneBook;

uses Crt;

const
  DataFile = 'PHONES.DAT';
  MaxContacts = 100;

type
  TContact = record
    Name: string[24];
    Phone: string[16];
    City: string[16];
  end;

var
  Book: array[1..MaxContacts] of TContact;
  Count: Integer;
  Key: Char;
  Done: Boolean;

function UpperStr(const S: string): string;
var I: Integer; R: string;
begin
  R := S;
  for I := 1 to Length(R) do R[I] := UpCase(R[I]);
  UpperStr := R;
end;

procedure LoadBook;
var F: file of TContact;
begin
  Count := 0;
  Assign(F, DataFile);
  {$I-} Reset(F); {$I+}
  if IOResult <> 0 then Exit;              { no file yet: an empty book }
  while (not Eof(F)) and (Count < MaxContacts) do
  begin
    Inc(Count);
    Read(F, Book[Count]);
  end;
  Close(F);
end;

procedure SaveBook;
var F: file of TContact; I: Integer;
begin
  Assign(F, DataFile);
  {$I-} Rewrite(F); {$I+}
  if IOResult <> 0 then
  begin
    WriteLn('Cannot write ', DataFile);
    Exit;
  end;
  for I := 1 to Count do Write(F, Book[I]);
  Close(F);
end;

procedure Title(const S: string);
begin
  TextColor(Yellow);
  WriteLn;
  WriteLn('--- ', S, ' ---');
  TextColor(LightGray);
end;

procedure ShowContact(I: Integer);
begin
  WriteLn(I:3, '. ', Book[I].Name, '':(25 - Length(Book[I].Name)), Book[I].Phone,
          '':(17 - Length(Book[I].Phone)), Book[I].City);
end;

procedure AddContact;
var C: TContact;
begin
  Title('Add a contact');
  if Count >= MaxContacts then
  begin
    WriteLn('The book is full.');
    Exit;
  end;
  Write('Name : '); ReadLn(C.Name);
  if C.Name = '' then
  begin
    WriteLn('Nothing added.');
    Exit;
  end;
  Write('Phone: '); ReadLn(C.Phone);
  Write('City : '); ReadLn(C.City);
  Inc(Count);
  Book[Count] := C;
  SaveBook;
  TextColor(LightGreen);
  WriteLn('Saved: ', C.Name, ' (', Count, ' contacts)');
  TextColor(LightGray);
end;

procedure ListContacts;
var I: Integer;
begin
  Title('All contacts');
  if Count = 0 then WriteLn('The book is empty.');
  for I := 1 to Count do ShowContact(I);
end;

procedure FindContact;
var Part: string; I, Hits: Integer;
begin
  Title('Find');
  Write('Part of a name: '); ReadLn(Part);
  Part := UpperStr(Part);
  Hits := 0;
  for I := 1 to Count do
    if Pos(Part, UpperStr(Book[I].Name)) > 0 then
    begin
      ShowContact(I);
      Inc(Hits);
    end;
  WriteLn(Hits, ' found.');
end;

procedure DeleteContact;
var N, Code, I: Integer; S: string;
begin
  ListContacts;
  Write('Number to delete (Enter = none): '); ReadLn(S);
  Val(S, N, Code);
  if (Code <> 0) or (N < 1) or (N > Count) then
  begin
    WriteLn('Nothing deleted.');
    Exit;
  end;
  WriteLn('Deleted: ', Book[N].Name);
  for I := N to Count - 1 do Book[I] := Book[I + 1];
  Dec(Count);
  SaveBook;
end;

procedure SortContacts;
var I, J: Integer; T: TContact;
begin
  for I := 2 to Count do                   { insertion sort by name, ignoring case }
  begin
    T := Book[I];
    J := I - 1;
    while (J >= 1) and (UpperStr(Book[J].Name) > UpperStr(T.Name)) do
    begin
      Book[J + 1] := Book[J];
      Dec(J);
    end;
    Book[J + 1] := T;
  end;
  SaveBook;
  Title('Sorted by name');
  ListContacts;
end;

begin
  LoadBook;
  TextBackground(Black);
  ClrScr;
  TextColor(LightCyan);
  WriteLn('PHONE BOOK  (Turbo Pascal style, RAD IDE)  - ', Count, ' contacts in ', DataFile);
  Done := False;
  repeat
    TextColor(White);
    WriteLn;
    Write('[A]dd  [L]ist  [F]ind  [D]elete  [S]ort  [Q]uit > ');
    Key := UpCase(ReadKey);
    WriteLn(Key);
    TextColor(LightGray);
    case Key of
      'A': AddContact;
      'L': ListContacts;
      'F': FindContact;
      'D': DeleteContact;
      'S': SortContacts;
      'Q', #27: Done := True;
    end;
  until Done;
  WriteLn('Goodbye!');
end.
