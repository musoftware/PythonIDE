unit mainunit;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, Forms, Controls, Graphics, Dialogs, StdCtrls, ExtCtrls,
  convert;

type

  { TfrmConverter }

  TfrmConverter = class(TForm)
    btnConvert: TButton;
    edtCelsius: TEdit;
    lblCelsius: TLabel;
    lblResult: TLabel;
    rgDirection: TRadioGroup;
    procedure btnConvertClick(Sender: TObject);
    procedure FormCreate(Sender: TObject);
  private

  public

  end;

var
  frmConverter: TfrmConverter;

implementation

{$R *.lfm}

{ TfrmConverter }

procedure TfrmConverter.FormCreate(Sender: TObject);
begin
  lblResult.Caption := '';
  if ParamStr(1) = '--selftest' then
  begin
    edtCelsius.Text := '100';
    btnConvertClick(nil);
    with TStringList.Create do try Add('SELFTEST ' + lblResult.Caption); SaveToFile(ChangeFileExt(ParamStr(0), '.selftest.txt')); finally Free; end;
    Application.Terminate;
  end;
end;

procedure TfrmConverter.btnConvertClick(Sender: TObject);
var
  V: Double;
begin
  V := StrToFloatDef(edtCelsius.Text, 0);
  if rgDirection.ItemIndex = 0 then
    lblResult.Caption := FormatFloat('0.0', CelsiusToFahrenheit(V)) + ' °F'
  else
    lblResult.Caption := FormatFloat('0.0', FahrenheitToCelsius(V)) + ' °C';
end;

end.

