unit MainForm;

interface

uses
  Winapi.Windows, Winapi.Messages, System.SysUtils, System.Variants, System.Classes, Vcl.Graphics,
  Vcl.Controls, Vcl.Forms, Vcl.Dialogs, Vcl.StdCtrls, Vcl.ExtCtrls, Vcl.Menus, Vcl.ComCtrls,
  System.Actions, Vcl.ActnList, CustomerData;

type
  TfrmMain = class(TForm)
    pnlTop: TPanel;
    lblName: TLabel;
    edtName: TEdit;
    btnAdd: TButton;
    lstCustomers: TListBox;
    chkVip: TCheckBox;
    grpDetails: TGroupBox;
    memNotes: TMemo;
    rbPrivate: TRadioButton;
    rbCompany: TRadioButton;
    cboCountry: TComboBox;
    MainMenu1: TMainMenu;
    mnuFile: TMenuItem;
    mnuExit: TMenuItem;
    mnuHelp: TMenuItem;
    mnuAbout: TMenuItem;
    tmrClock: TTimer;
    StatusBar1: TStatusBar;
    ActionList1: TActionList;
    actAdd: TAction;
    procedure btnAddClick(Sender: TObject);
    procedure FormCreate(Sender: TObject);
    procedure mnuExitClick(Sender: TObject);
    procedure mnuAboutClick(Sender: TObject);
    procedure tmrClockTimer(Sender: TObject);
  private
    { Private declarations }
    FCount: Integer;
  public
    { Public declarations }
  end;

var
  frmMain: TfrmMain;

implementation

{$R *.dfm}

uses AboutBox;

procedure TfrmMain.FormCreate(Sender: TObject);
begin
  FCount := 0;
  cboCountry.ItemIndex := 0;
end;

procedure TfrmMain.btnAddClick(Sender: TObject);
begin
  if Trim(edtName.Text) = '' then
    Exit;
  lstCustomers.Items.Add(FormatCustomer(edtName.Text, chkVip.Checked));
  Inc(FCount);
  StatusBar1.SimpleText := Format('%d customers', [FCount]);
end;

procedure TfrmMain.mnuExitClick(Sender: TObject);
begin
  Close;
end;

procedure TfrmMain.mnuAboutClick(Sender: TObject);
begin
  frmAbout.ShowModal;
end;

procedure TfrmMain.tmrClockTimer(Sender: TObject);
begin
  Caption := 'Customer Manager - ' + TimeToStr(Now);
end;

end.
