object frmMain: TfrmMain
  Left = 0
  Top = 0
  Caption = 'Customer Manager - Caf'#233
  ClientHeight = 441
  ClientWidth = 624
  Color = clBtnFace
  Font.Charset = DEFAULT_CHARSET
  Font.Color = clWindowText
  Font.Height = -12
  Font.Name = 'Segoe UI'
  Font.Style = []
  Menu = MainMenu1
  Position = poScreenCenter
  OnCreate = FormCreate
  TextHeight = 15
  object pnlTop: TPanel
    Left = 0
    Top = 0
    Width = 624
    Height = 49
    Align = alTop
    BevelOuter = bvNone
    Color = $00F0E6DC
    ParentBackground = False
    TabOrder = 0
    object lblName: TLabel
      Left = 12
      Top = 16
      Width = 35
      Height = 15
      Caption = '&Name:'
      FocusControl = edtName
    end
    object edtName: TEdit
      Left = 64
      Top = 12
      Width = 241
      Height = 23
      TabOrder = 0
      TextHint = 'Customer name'
    end
    object btnAdd: TButton
      Left = 320
      Top = 11
      Width = 89
      Height = 25
      Action = actAdd
      Caption = '&Add'
      Default = True
      TabOrder = 1
      OnClick = btnAddClick
    end
  end
  object lstCustomers: TListBox
    Left = 12
    Top = 60
    Width = 293
    Height = 333
    ItemHeight = 15
    Items.Strings = (
      'Contoso Ltd.'
      'Fabrikam, Inc.'
      'Northwind Traders')
    TabOrder = 1
  end
  object grpDetails: TGroupBox
    Left = 320
    Top = 60
    Width = 289
    Height = 333
    Caption = ' Details '
    TabOrder = 2
    object chkVip: TCheckBox
      Left = 16
      Top = 24
      Width = 97
      Height = 17
      Caption = 'VIP customer'
      Checked = True
      State = cbChecked
      TabOrder = 0
    end
    object rbPrivate: TRadioButton
      Left = 16
      Top = 52
      Width = 113
      Height = 17
      Caption = 'Private'
      Checked = True
      TabOrder = 1
      TabStop = True
    end
    object rbCompany: TRadioButton
      Left = 144
      Top = 52
      Width = 113
      Height = 17
      Caption = 'Company'
      TabOrder = 2
    end
    object cboCountry: TComboBox
      Left = 16
      Top = 84
      Width = 257
      Height = 23
      Style = csDropDownList
      TabOrder = 3
      Items.Strings = (
        'Germany'
        'France'
        #1605#1589#1585)
    end
    object memNotes: TMemo
      Left = 16
      Top = 120
      Width = 257
      Height = 197
      Lines.Strings = (
        'Notes about the customer'
        'second line with ''quotes''')
      ScrollBars = ssVertical
      TabOrder = 4
    end
  end
  object StatusBar1: TStatusBar
    Left = 0
    Top = 422
    Width = 624
    Height = 19
    Panels = <>
    SimplePanel = True
    SimpleText = 'Ready'
  end
  object MainMenu1: TMainMenu
    Left = 448
    Top = 8
    object mnuFile: TMenuItem
      Caption = '&File'
      object mnuExit: TMenuItem
        Caption = 'E&xit'
        ShortCut = 32883
        OnClick = mnuExitClick
      end
    end
    object mnuHelp: TMenuItem
      Caption = '&Help'
      object mnuAbout: TMenuItem
        Caption = '&About...'
        OnClick = mnuAboutClick
      end
    end
  end
  object tmrClock: TTimer
    OnTimer = tmrClockTimer
    Left = 512
    Top = 8
  end
  object ActionList1: TActionList
    Left = 568
    Top = 8
    object actAdd: TAction
      Caption = '&Add'
      ShortCut = 16449
      OnExecute = btnAddClick
    end
  end
end
