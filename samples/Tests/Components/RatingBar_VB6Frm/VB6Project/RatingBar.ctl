VERSION 5.00
Begin VB.UserControl RatingBar 
   ClientHeight    =   420
   ClientLeft      =   0
   ClientTop       =   0
   ClientWidth     =   2100
   ScaleHeight     =   420
   ScaleWidth      =   2100
End
Attribute VB_Name = "RatingBar"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = True
Attribute VB_PredeclaredId = False
Attribute VB_Exposed = False
Option Explicit
' Stand-in of the RAD IDE component package RatingBar 1.0.0 (written by RAD IDE):
' its properties are kept in the .frm; RAD IDE runs the form with the package's own runtime.

Event ValueChanged()

Private m_Value As Long
Const m_def_Value = 3
Private m_MaxStars As Long
Const m_def_MaxStars = 5
Private m_ReadOnly As Boolean
Const m_def_ReadOnly = False
Private m_StarColor As OLE_COLOR
Const m_def_StarColor = &H0000B4FF&
Private m_EmptyColor As OLE_COLOR
Const m_def_EmptyColor = &H00D5CDC8&

Public Property Get Value() As Long
    Value = m_Value
End Property

Public Property Let Value(ByVal New_Value As Long)
    m_Value = New_Value
    PropertyChanged "Value"
    UserControl.Refresh
End Property

Public Property Get MaxStars() As Long
    MaxStars = m_MaxStars
End Property

Public Property Let MaxStars(ByVal New_MaxStars As Long)
    m_MaxStars = New_MaxStars
    PropertyChanged "MaxStars"
    UserControl.Refresh
End Property

Public Property Get ReadOnly() As Boolean
    ReadOnly = m_ReadOnly
End Property

Public Property Let ReadOnly(ByVal New_ReadOnly As Boolean)
    m_ReadOnly = New_ReadOnly
    PropertyChanged "ReadOnly"
    UserControl.Refresh
End Property

Public Property Get StarColor() As OLE_COLOR
    StarColor = m_StarColor
End Property

Public Property Let StarColor(ByVal New_StarColor As OLE_COLOR)
    m_StarColor = New_StarColor
    PropertyChanged "StarColor"
    UserControl.Refresh
End Property

Public Property Get EmptyColor() As OLE_COLOR
    EmptyColor = m_EmptyColor
End Property

Public Property Let EmptyColor(ByVal New_EmptyColor As OLE_COLOR)
    m_EmptyColor = New_EmptyColor
    PropertyChanged "EmptyColor"
    UserControl.Refresh
End Property

Public Sub Reset()
    ' Sets Value to 0.
End Sub

Public Sub SetValue(ByVal value As Variant)
    ' Sets Value (clamped to 0..MaxStars).
End Sub

Private Sub UserControl_InitProperties()
    m_Value = m_def_Value
    m_MaxStars = m_def_MaxStars
    m_ReadOnly = m_def_ReadOnly
    m_StarColor = m_def_StarColor
    m_EmptyColor = m_def_EmptyColor
End Sub

Private Sub UserControl_ReadProperties(PropBag As PropertyBag)
    m_Value = PropBag.ReadProperty("Value", m_def_Value)
    m_MaxStars = PropBag.ReadProperty("MaxStars", m_def_MaxStars)
    m_ReadOnly = PropBag.ReadProperty("ReadOnly", m_def_ReadOnly)
    m_StarColor = PropBag.ReadProperty("StarColor", m_def_StarColor)
    m_EmptyColor = PropBag.ReadProperty("EmptyColor", m_def_EmptyColor)
End Sub

Private Sub UserControl_WriteProperties(PropBag As PropertyBag)
    Call PropBag.WriteProperty("Value", m_Value, m_def_Value)
    Call PropBag.WriteProperty("MaxStars", m_MaxStars, m_def_MaxStars)
    Call PropBag.WriteProperty("ReadOnly", m_ReadOnly, m_def_ReadOnly)
    Call PropBag.WriteProperty("StarColor", m_StarColor, m_def_StarColor)
    Call PropBag.WriteProperty("EmptyColor", m_EmptyColor, m_def_EmptyColor)
End Sub

Private Sub UserControl_Paint()
    UserControl.Cls
    UserControl.Line (0, 0)-(UserControl.ScaleWidth - 15, UserControl.ScaleHeight - 15), , B
    UserControl.CurrentX = 60: UserControl.CurrentY = 30: UserControl.Print Ambient.DisplayName & " (RatingBar)"
End Sub
