unit CustomerData;

interface

function FormatCustomer(const AName: string; AVip: Boolean): string;

implementation

uses System.SysUtils;

function FormatCustomer(const AName: string; AVip: Boolean): string;
begin
  Result := Trim(AName);
  if AVip then
    Result := Result + ' (VIP)';
end;

end.
