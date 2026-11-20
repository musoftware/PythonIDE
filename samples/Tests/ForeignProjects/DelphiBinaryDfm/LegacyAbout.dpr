program LegacyAbout;

uses
  Forms,
  AboutBox in 'AboutBox.pas' {frmAbout};

{$R *.res}

begin
  Application.Initialize;
  Application.CreateForm(TfrmAbout, frmAbout);
  Application.Run;
end.
