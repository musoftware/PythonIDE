VERSION 5.00
Begin VB.Form Form1
   Caption         =   "Customers (SQLite) - VB6"
   ClientHeight    =   4950
   ClientWidth     =   6900
   ScaleMode       =   3  'Pixel
   StartUpPosition =   2  'CenterScreen
   Begin VB.PictureBox CustomersBindingNavigator
      Left            =   180
      Top             =   180
      Width           =   4980
      Height          =   405
      TabIndex        =   0
      Begin VB.CommandButton CustomersBindingNavigatorMoveFirstItem
         Caption         =   "|<"
         Left            =   30
         Top             =   30
         Width           =   390
         Height          =   345
         TabIndex        =   0
      End
      Begin VB.CommandButton CustomersBindingNavigatorMovePreviousItem
         Caption         =   "<"
         Left            =   450
         Top             =   30
         Width           =   390
         Height          =   345
         TabIndex        =   0
      End
      Begin VB.Label CustomersBindingNavigatorPositionItem
         Caption         =   "0 of 0"
         Left            =   870
         Top             =   75
         Width           =   1050
         Height          =   255
         TabIndex        =   0
      End
      Begin VB.CommandButton CustomersBindingNavigatorMoveNextItem
         Caption         =   ">"
         Left            =   1950
         Top             =   30
         Width           =   390
         Height          =   345
         TabIndex        =   0
      End
      Begin VB.CommandButton CustomersBindingNavigatorMoveLastItem
         Caption         =   ">|"
         Left            =   2370
         Top             =   30
         Width           =   390
         Height          =   345
         TabIndex        =   0
      End
      Begin VB.CommandButton CustomersBindingNavigatorAddNewItem
         Caption         =   "Add"
         Left            =   2790
         Top             =   30
         Width           =   660
         Height          =   345
         TabIndex        =   0
      End
      Begin VB.CommandButton CustomersBindingNavigatorDeleteItem
         Caption         =   "Delete"
         Left            =   3480
         Top             =   30
         Width           =   750
         Height          =   345
         TabIndex        =   0
      End
      Begin VB.CommandButton CustomersBindingNavigatorSaveItem
         Caption         =   "Save"
         Left            =   4260
         Top             =   30
         Width           =   660
         Height          =   345
         TabIndex        =   0
      End
   End
   Begin VB.Label IdLabel
      Caption         =   "Id:"
      Left            =   180
      Top             =   720
      Width           =   990
      Height          =   255
      TabIndex        =   0
   End
   Begin VB.TextBox IdTextBox
      Text            =   ""
      Left            =   1260
      Top             =   675
      Width           =   2700
      Height          =   300
      TabIndex        =   0
   End
   Begin VB.Label NameLabel
      Caption         =   "Name:"
      Left            =   180
      Top             =   1110
      Width           =   990
      Height          =   255
      TabIndex        =   0
   End
   Begin VB.TextBox NameTextBox
      Text            =   ""
      Left            =   1260
      Top             =   1065
      Width           =   2700
      Height          =   300
      TabIndex        =   0
   End
   Begin VB.Label EmailLabel
      Caption         =   "Email:"
      Left            =   180
      Top             =   1500
      Width           =   990
      Height          =   255
      TabIndex        =   0
   End
   Begin VB.TextBox EmailTextBox
      Text            =   ""
      Left            =   1260
      Top             =   1455
      Width           =   2700
      Height          =   300
      TabIndex        =   0
   End
   Begin VB.Label CityLabel
      Caption         =   "City:"
      Left            =   180
      Top             =   1890
      Width           =   990
      Height          =   255
      TabIndex        =   0
   End
   Begin VB.TextBox CityTextBox
      Text            =   ""
      Left            =   1260
      Top             =   1845
      Width           =   2700
      Height          =   300
      TabIndex        =   0
   End
   Begin VB.Label ActiveLabel
      Caption         =   "Active:"
      Left            =   180
      Top             =   2280
      Width           =   990
      Height          =   255
      TabIndex        =   0
   End
   Begin VB.CheckBox ActiveCheckBox
      Caption         =   ""
      Left            =   1260
      Top             =   2235
      Width           =   2400
      Height          =   300
      TabIndex        =   0
   End
   Begin VB.Label BalanceLabel
      Caption         =   "Balance:"
      Left            =   180
      Top             =   2670
      Width           =   990
      Height          =   255
      TabIndex        =   0
   End
   Begin VB.TextBox BalanceTextBox
      Text            =   ""
      Left            =   1260
      Top             =   2625
      Width           =   2700
      Height          =   300
      TabIndex        =   0
   End
   Begin VB.CommandButton cmdCairo
      Caption         =   "Cairo customers"
      Left            =   4500
      Top             =   750
      Width           =   1950
      Height          =   375
      TabIndex        =   0
   End
   Begin VB.CommandButton cmdAll
      Caption         =   "All customers"
      Left            =   4500
      Top             =   1200
      Width           =   1950
      Height          =   375
      TabIndex        =   0
   End
   Begin VB.CommandButton cmdRich
      Caption         =   "Who has most?"
      Left            =   4500
      Top             =   1650
      Width           =   1950
      Height          =   375
      TabIndex        =   0
   End
   Begin VB.Label lblStatus
      Caption         =   ""
      Left            =   180
      Top             =   4350
      Width           =   6300
      Height          =   255
      TabIndex        =   0
   End
End
Attribute VB_Name = "Form1"
' (generated by RAD IDE - the code lives in Form1.bas)
