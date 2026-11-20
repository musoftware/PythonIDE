program CustomerApp;

uses
  Vcl.Forms,
  MainForm in 'MainForm.pas' {frmMain},
  AboutBox in 'AboutBox.pas' {frmAbout},
  CustomerData in 'CustomerData.pas';

{$R *.res}

begin
  Application.Initialize;
  Application.MainFormOnTaskbar := True;
  Application.Title := 'Customer Manager';
  Application.CreateForm(TfrmMain, frmMain);
  Application.CreateForm(TfrmAbout, frmAbout);
  Application.Run;
end.
