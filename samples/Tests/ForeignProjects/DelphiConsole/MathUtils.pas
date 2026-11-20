unit MathUtils;

interface

function Factorial(N: Integer): Int64;

implementation

function Factorial(N: Integer): Int64;
begin
  if N <= 1 then
    Result := 1
  else
    Result := N * Factorial(N - 1);
end;

end.
