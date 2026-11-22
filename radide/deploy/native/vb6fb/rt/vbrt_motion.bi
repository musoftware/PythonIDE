' ============================================================================================
' vbrt_motion.bi - animations, visual states and layout variants of the RAD IDE VB6 runtime for
' FreeBASIC (included after vbrt_forms.bi by programs whose forms use them).  Part of RAD IDE (MIT).
'
' The same semantics as the IDE's Python runtime (radide/motion/runtime_py.py, features/timeline.py,
' features/states.py, variants/runtime_py.py) and the C runtime radforms_motion.inc, driven by the records
' of radide/motion/native_plan.py - the generated program passes them with VBFxRec(form, line):
'
'   XR respect                                  the form respects the reduced-motion setting
'   X  fx target count forever autorev delay restore   storyboard ("" target = the form)
'   XT on source interval after leave           its trigger (load click hover timer show hide after manual)
'   K  prop ms ease kind a b c d                keyframe; kind n number, c colour, b bool, s text,
'                                               r relative (start*a + b + d*start(c)), p parent colour,
'                                               v typewriter (start text up to fraction a)
'   Q  control state prop value                 visual state override ("" control = the form)
'   V  size minW maxW minH maxH orientation posture span fold     layout size
'   VL size control "x y w h rx ry rw rh"       place of the control on that size
'   VP size control prop value                  property on that size
'
' VB API: Form.BeginAnimation name, Form.StopAnimation name, Form.GoToState state[, control],
' control.GoToState state, Form.ApplySizeVariants, Form.CurrentSizes, Form.CurrentState; events
' <storyboard>_Completed, Form_SizeVariantChanged.  RADIDE_REDUCED_MOTION=1 (or the Windows "Show
' animations" setting off) ends every animation at once when the form respects reduced motion;
' RADIDE_POSTURE / RADIDE_SPAN / RADIDE_HINGE simulate a foldable.
' ============================================================================================

Const VBFX_FRAME = VB_FX_TIMER0               ' 15 ms frame timer of a form
Const VBFX_DELAY = VB_FX_TIMER0 + 1           ' + storyboard index: the delay before it starts
Const VBFX_EVERY = VB_FX_TIMER0 + 10001       ' + storyboard index: "On timer" interval
Const VBFX_PI = 3.14159265358979

Const VBFXK_NUM = 0
Const VBFXK_COLOR = 1
Const VBFXK_BOOL = 2
Const VBFXK_TEXT = 3
Const VBFXK_REL = 4
Const VBFXK_PARENT = 5
Const VBFXK_REVEAL = 6

Const VBFXP_NUM = 0
Const VBFXP_COLOR = 1
Const VBFXP_BOOL = 2
Const VBFXP_TEXT = 3

Const VBFXT_LOAD = 0
Const VBFXT_CLICK = 1
Const VBFXT_HOVER = 2
Const VBFXT_TIMER = 3
Const VBFXT_SHOW = 4
Const VBFXT_HIDE = 5
Const VBFXT_AFTER = 6
Const VBFXT_MANUAL = 7

Const VBFXF_OVER = 1
Const VBFXF_PRESSED = 2
Const VBFXF_FOCUSED = 4
Const VBFXF_DISABLED = 8

Type VBFxKey
    ms As Long
    ease As Long
    kind As Long
    ofs As Long                  ' 0, 1 = start Width, 2 = start Height
    a As Double
    b As Double
    d As Double
    s As String                  ' text key
    rv As Double                 ' resolved number / colour
    rs As String                 ' resolved text
End Type

Type VBFxTrack
    prop As String
    pt As Long
    k0 As Long                   ' first key (vbFxK index)
    nk As Long
    sNum As Double               ' value at Begin (number / colour / bool)
    sOwn As Long                 ' colour: the control had its own colour at Begin
    sText As String
    lastBool As Long             ' Visible: last value written (-2 none)
End Type

Type VBFxSb
    frm As Long
    fx As String
    tid As Long                  ' the animated control (the form itself for "")
    srcName As String
    srcId As Long
    after As String
    cnt As Long
    forever As Long
    autorev As Long
    delay As Long
    restoreIt As Long
    trig As Long
    interval As Long
    leave As Long                ' 0 reverse, 1 stop, 2 none
    tr0 As Long                  ' first track (vbFxT index)
    ntr As Long
    dur As Long
    playing As Long
    rev As Long
    hiding As Long
    saved As Long
    pending As Long
    every As Long
    t0 As Double
    posMs As Double
    pl0 As VBPlace
    hasPl0 As Long
End Type

Type VBFxQ
    cid As Long                  ' the form id for a form state
    state As String
    prop As String
    v As String
End Type

Type VBFxAp                      ' a visual state override in effect
    cid As Long
    prop As String
    saved As String
    v As String
End Type

Type VBFxSize
    id As String
    mnw As Double
    mxw As Double
    mnh As Double
    mxh As Double
    orient As String
    posture As String
    span As String
    fold As String
End Type

Type VBFxVL
    size As Long                 ' vbFxSz index
    cid As Long
    pl As VBPlace
End Type

Type VBFxVP
    size As Long
    cid As Long
    prop As String
    v As String
    base As String               ' the designed value (taken when the form loads)
End Type

Type VBFxDone
    frm As Long
    fx As String
    h As VBHandler
End Type

Type VBFxForm
    has As Long
    respect As Long
    reduced As Long
    started As Long
    state As String
    frameOn As Long
    cur As String
    hasCur As Long
    alphaSet As Long
    opacity As Double
    s0 As Long                   ' storyboards s0 .. s0 + ns - 1
    ns As Long
    q0 As Long
    nq As Long
    z0 As Long
    nz As Long
    l0 As Long
    nl As Long
    p0 As Long
    np As Long
End Type

Dim Shared vbFxF(Any) As VBFxForm
Dim Shared vbFxS(Any) As VBFxSb
Dim Shared vbFxT(Any) As VBFxTrack
Dim Shared vbFxK(Any) As VBFxKey
Dim Shared vbFxQs(Any) As VBFxQ
Dim Shared vbFxAps(Any) As VBFxAp
Dim Shared vbFxApN As Long
Dim Shared vbFxSz(Any) As VBFxSize
Dim Shared vbFxVLs(Any) As VBFxVL
Dim Shared vbFxVPs(Any) As VBFxVP
Dim Shared vbFxDones(Any) As VBFxDone
Dim Shared vbFxFl(Any) As Long                    ' per control: MouseOver / Pressed / Focused / Disabled
Dim Shared vbFxMan(Any) As String                 ' per control: state set by GoToState
Dim Shared vbFxBasePl(Any) As VBPlace             ' per control: designed place (layout variants)
Dim Shared vbFxHasBase(Any) As Long
Dim Shared vbFxCurSb As Long = -1                 ' parsing: the storyboard of the last X record
Dim Shared vbFxInstalled As Long

Declare Sub VBFxEvent(ByVal id As Long, ByVal ev As Long)
Declare Function VBFxSetHook(ByVal id As Long, ByVal p As Long, ByVal v As Long) As Long
Declare Sub VBFxFormHook(ByVal f As Long, ByVal what As Long, ByVal wp As WPARAM, ByVal lp As LPARAM)
Declare Sub VBFxBeginSb(ByVal i As Long)

' ------------------------------------------------------------------------------ small helpers
Private Function VBFxNow() As Double
    Return Timer() * 1000.0
End Function

Private Function VBFxHas(ByVal f As Long) As Long
    If f <= 0 OrElse f > UBound(vbFxF) Then Return 0
    Return vbFxF(f).has
End Function

Private Sub VBFxNeedForm(ByVal f As Long)
    If f > UBound(vbFxF) Then ReDim Preserve vbFxF(0 To f + 4)
End Sub

Private Sub VBFxNeedCtl(ByVal id As Long)
    If id > UBound(vbFxFl) Then
        Dim n As Long = IIf(vbCtlCount > id, vbCtlCount, id) + 8
        ReDim Preserve vbFxFl(0 To n)
        ReDim Preserve vbFxMan(0 To n)
        ReDim Preserve vbFxBasePl(0 To n)
        ReDim Preserve vbFxHasBase(0 To n)
    End If
End Sub

Private Function VBFxTrue(ByRef s As String) As Long
    Select Case LCase(Trim(s))
    Case "1", "true", "yes", "on", "-1": Return -1
    End Select
    Return 0
End Function

Private Function VBFxEnvTrue(ByRef nm As String, ByRef isSet As Long) As Long
    Dim v As String = LCase(Trim(Environ(nm)))
    isSet = (Len(v) > 0)
    If isSet = 0 Then Return 0
    Return (v = "1" OrElse v = "true" OrElse v = "yes" OrElse v = "on")
End Function

Private Function VBFxReducedSystem() As Long
    Dim isSet As Long
    Dim v As Long = VBFxEnvTrue("RADIDE_REDUCED_MOTION", isSet)
    If isSet Then Return v
    Dim onv As BOOL = 1
    If SystemParametersInfoW(&h1042, 0, @onv, 0) Then Return (onv = 0)       ' SPI_GETCLIENTAREAANIMATION
    Return 0
End Function

Private Function VBFxUnesc(ByRef s As String) As String
    If InStr(s, "\") = 0 Then Return s
    Dim r As String
    Dim i As Long = 1
    While i <= Len(s)
        Dim ch As String = Mid(s, i, 1)
        If ch = "\" AndAlso i < Len(s) Then
            Dim n As String = Mid(s, i + 1, 1)
            Select Case n
            Case "t": r &= Chr(9)
            Case "n": r &= Chr(10)
            Case "r": r &= Chr(13)
            Case Else: r &= n
            End Select
            i += 2
        Else
            r &= ch
            i += 1
        End If
    Wend
    Return r
End Function

Private Sub VBFxSplit(ByRef ln As String, fl() As String)
    For k As Long = 0 To 9
        fl(k) = ""
    Next
    Dim As Long k = 0, p = 1
    Do
        Dim q As Long = InStr(p, ln, Chr(9))
        If q = 0 Then
            fl(k) = VBFxUnesc(Mid(ln, p))
            Exit Do
        End If
        fl(k) = VBFxUnesc(Mid(ln, p, q - p))
        k += 1
        p = q + 1
        If k > 9 Then Exit Do
    Loop
End Sub

' FreeBASIC's RGB() is &hAARRGGBB; the runtime keeps colours as &hBBGGRR (COLORREF)
Private Function VBFxBGR(ByVal r As Long, ByVal g As Long, ByVal b As Long) As Long
    Return (b Shl 16) Or (g Shl 8) Or r
End Function

Private Function VBFxColorOf(ByRef s As String) As Long
    Dim h As String = Trim(s)
    If Left(h, 1) = "#" Then h = Mid(h, 2)
    If Len(h) = 8 Then h = Mid(h, 3)
    If Len(h) = 3 Then h = String(2, h[0]) & String(2, h[1]) & String(2, h[2])
    If Len(h) <> 6 Then Return 0
    Return VBFxBGR(ValInt("&h" & Mid(h, 1, 2)), ValInt("&h" & Mid(h, 3, 2)), ValInt("&h" & Mid(h, 5, 2)))
End Function

Private Function VBFxHex(ByVal c As Long) As String
    Return "#" & LCase(Hex(c And &hFF, 2) & Hex((c Shr 8) And &hFF, 2) & Hex((c Shr 16) And &hFF, 2))
End Function

Private Function VBFxNumStr(ByVal v As Double) As String
    If v = Int(v) AndAlso Abs(v) < 1e9 Then Return LTrim(Str(CLng(v)))
    Return LTrim(Str(v))
End Function

Private Function VBFxRound(ByVal v As Double) As Long
    Return CLng(Int(v + 0.5))
End Function

Private Function VBFxULen(ByRef s As String) As Long
    Dim n As Long = 0
    For i As Long = 0 To Len(s) - 1
        If (s[i] And &hC0) <> &h80 Then n += 1
    Next
    Return n
End Function

Private Function VBFxULeft(ByRef s As String, ByVal n As Long) As String
    If n <= 0 Then Return ""
    Dim c As Long = 0
    For i As Long = 0 To Len(s) - 1
        If (s[i] And &hC0) <> &h80 Then
            If c = n Then Return Left(s, i)
            c += 1
        End If
    Next
    Return s
End Function

Private Function VBFxEaseOf(ByRef s As String) As Long
    Select Case LCase(s)
    Case "in": Return 1
    Case "out": Return 2
    Case "inout": Return 3
    Case "sine": Return 4
    Case "back": Return 5
    Case "elastic": Return 6
    Case "bounce": Return 7
    End Select
    Return 0
End Function

Private Function VBFxEase(ByVal f As Double, ByVal e As Long) As Double
    Select Case e
    Case 1: Return f * f
    Case 2: Return 1 - (1 - f) * (1 - f)
    Case 3
        If f < 0.5 Then Return 2 * f * f
        Return 1 - 2 * (1 - f) * (1 - f)
    Case 4: Return -(Cos(VBFX_PI * f) - 1) / 2
    Case 5
        Dim g As Double = f - 1
        Return 1 + 2.70158 * g * g * g + 1.70158 * g * g
    Case 6
        If f <= 0 Then Return 0
        If f >= 1 Then Return 1
        Return 2 ^ (-10 * f) * Sin((f * 10 - 0.75) * (2 * VBFX_PI / 3)) + 1
    Case 7
        Dim As Double n = 7.5625, d = 2.75
        If f < 1 / d Then Return n * f * f
        If f < 2 / d Then
            f -= 1.5 / d
            Return n * f * f + 0.75
        End If
        If f < 2.5 / d Then
            f -= 2.25 / d
            Return n * f * f + 0.9375
        End If
        f -= 2.625 / d
        Return n * f * f + 0.984375
    End Select
    Return f
End Function

Private Function VBFxPType(ByRef p As String) As Long
    Select Case LCase(p)
    Case "backcolor", "forecolor": Return VBFXP_COLOR
    Case "visible", "fontbold", "fontitalic", "enabled", "checked": Return VBFXP_BOOL
    Case "text", "caption": Return VBFXP_TEXT
    End Select
    Return VBFXP_NUM
End Function

Private Function VBFxIntProp(ByRef p As String) As Long
    Select Case LCase(p)
    Case "left", "top", "width", "height", "fontsize", "value": Return -1
    End Select
    Return 0
End Function

Private Function VBFxGeo(ByRef p As String) As Long
    Select Case LCase(p)
    Case "left", "top", "width", "height": Return -1
    End Select
    Return 0
End Function

Private Function VBFxIsCtl(ByVal id As Long) As Long
    Return vbCtls(id).kind <> vbkForm
End Function

Private Function VBFxHasValue(ByVal id As Long) As Long
    Select Case vbCtls(id).kind
    Case vbkCheckBox, vbkOption, vbkProgress, vbkUpDown, vbkSlider: Return -1
    End Select
    Return 0
End Function

' the control named nm on form f (the form itself for "" or its own name; -1 = no such control)
Private Function VBFxCtl(ByVal f As Long, ByRef nm As String) As Long
    If Len(nm) = 0 Then Return f
    Dim l As String = LCase(nm)
    If l = LCase(vbCtls(f).name) Then Return f
    For i As Long = 1 To vbCtlCount
        If vbCtls(i).form = f AndAlso i <> f AndAlso vbCtls(i).kind <> vbkMenu AndAlso LCase(vbCtls(i).name) = l Then Return i
    Next
    Return -1
End Function

' ------------------------------------------------------------------------------ property access (design pixels)
Private Sub VBFxOpacity(ByVal f As Long, ByVal v As Double)
    If v < 0 Then v = 0
    If v > 1 Then v = 1
    vbFxF(f).alphaSet = -1
    vbFxF(f).opacity = v
    Dim h As HWND = vbCtls(f).hwnd
    If h = 0 Then Exit Sub
    Dim ex As Long = GetWindowLongW(h, GWL_EXSTYLE)
    If (ex And WS_EX_LAYERED) = 0 Then SetWindowLongW(h, GWL_EXSTYLE, ex Or WS_EX_LAYERED)
    Dim a As Long = VBFxRound(v * 255)
    If a > 255 Then a = 255
    SetLayeredWindowAttributes(h, 0, a, LWA_ALPHA)
End Sub

Private Function VBFxColorGet(ByVal id As Long, ByRef p As String) As Long
    If LCase(p) = "forecolor" Then
        If vbCtls(id).fore >= 0 Then Return vbCtls(id).fore
        Return GetSysColor(COLOR_BTNTEXT)
    End If
    Dim b As Long = VBEffBack(id)            ' its own colour, else the container's / form's
    If b > 0 Then Return vbCtls(b).back
    Dim f As Long = vbCtls(id).form
    If vbCtls(f).back >= 0 Then Return vbCtls(f).back
    Return GetSysColor(COLOR_BTNFACE)
End Function

Private Function VBFxParentColor(ByVal id As Long) As Long
    If VBFxIsCtl(id) = 0 Then Return VBFxColorGet(id, "BackColor")
    Dim p As Long = vbCtls(id).parent
    If p <= 0 Then p = vbCtls(id).form
    Return VBFxColorGet(p, "BackColor")
End Function

' col < 0: the default colour again
Private Sub VBFxColorSet(ByVal id As Long, ByVal fore As Long, ByVal col As Long)
    vbFxQuiet += 1
    If col >= 0 Then
        If (fore AndAlso vbCtls(id).fore <> col) OrElse (fore = 0 AndAlso vbCtls(id).back <> col) Then
            VBSetN(id, IIf(fore, vbpForeColor, vbpBackColor), col)
        End If
    ElseIf (fore AndAlso vbCtls(id).fore >= 0) OrElse (fore = 0 AndAlso vbCtls(id).back >= 0) Then
        VBSetN(id, IIf(fore, vbpForeColor, vbpBackColor), 0)
        If fore Then
            vbCtls(id).fore = -1
        Else
            vbCtls(id).back = -1
            VBApplyBrush(id)
        End If
        If vbCtls(id).hwnd Then
            InvalidateRect(vbCtls(id).hwnd, 0, -1)
            If vbCtls(id).kind <> vbkForm Then
                RedrawWindow(IIf(vbCtls(id).kind = vbkTab, vbCtls(id).inner, vbCtls(id).hwnd), 0, 0, RDW_INVALIDATE Or RDW_ERASE Or RDW_ALLCHILDREN)
            End If
        End If
    End If
    vbFxQuiet -= 1
End Sub

Private Function VBFxNumGet(ByVal id As Long, ByRef p As String) As Double
    Dim isForm As Long = (vbCtls(id).kind = vbkForm)
    Select Case LCase(p)
    Case "opacity"
        If isForm AndAlso vbFxF(id).alphaSet Then Return vbFxF(id).opacity
        Return 1
    Case "left"
        If isForm Then Return VBGetN(id, vbpLeft) / VBUnit(id)
        Return vbCtls(id).px
    Case "top"
        If isForm Then Return VBGetN(id, vbpTop) / VBUnit(id)
        Return vbCtls(id).py
    Case "width": Return vbCtls(id).pw
    Case "height": Return vbCtls(id).ph
    Case "fontsize": Return vbCtls(id).fontSize
    Case "value"
        If VBFxHasValue(id) Then Return VBGetN(id, vbpValue)
    End Select
    Return 0
End Function

Private Sub VBFxNumSet(ByVal id As Long, ByRef p As String, ByVal v As Double)
    Dim lp As String = LCase(p)
    vbFxQuiet += 1
    Select Case lp
    Case "opacity"
        If vbCtls(id).kind = vbkForm Then VBFxOpacity(id, v)     ' child windows have no transparency
    Case "left", "top", "width", "height"
        Dim iv As Long = VBFxRound(v)
        If vbCtls(id).kind = vbkForm Then
            Dim pr As Long = IIf(lp = "left", vbpLeft, IIf(lp = "top", vbpTop, IIf(lp = "width", vbpWidth, vbpHeight)))
            VBSetN(id, pr, iv * VBUnit(id))
        Else
            Select Case lp
            Case "left": vbCtls(id).px = iv
            Case "top": vbCtls(id).py = iv
            Case "width": vbCtls(id).pw = IIf(iv < 0, 0, iv)
            Case Else: vbCtls(id).ph = IIf(iv < 0, 0, iv)
            End Select
            If vbCtls(vbCtls(id).form).hwnd Then VBMoved(id)      ' keeps the anchors (Stop gives the place back)
        End If
    Case "fontsize"
        Dim fs As Long = VBFxRound(v)
        If fs < 1 Then fs = 1
        If vbCtls(id).fontSize <> fs Then VBSetN(id, vbpFontSize, fs)
    Case "value"
        If VBFxHasValue(id) Then VBSetN(id, vbpValue, VBFxRound(v))
    End Select
    vbFxQuiet -= 1
End Sub

Private Function VBFxBoolGet(ByVal id As Long, ByRef p As String) As Long
    Select Case LCase(p)
    Case "visible"
        If vbCtls(id).kind = vbkForm Then Return VBGetN(id, vbpVisible) <> 0
        Return vbCtls(id).visible <> 0
    Case "enabled": Return vbCtls(id).enabled <> 0
    Case "fontbold": Return vbCtls(id).bold <> 0
    Case "fontitalic": Return vbCtls(id).italic <> 0
    Case "checked"
        Select Case vbCtls(id).kind
        Case vbkCheckBox: Return VBGetN(id, vbpValue) = 1
        Case vbkOption: Return VBGetN(id, vbpValue) <> 0
        Case vbkMenu: Return vbCtls(id).checked <> 0
        End Select
    End Select
    Return 0
End Function

Private Sub VBFxBoolSet(ByVal id As Long, ByRef p As String, ByVal b As Long)
    vbFxQuiet += 1
    Select Case LCase(p)
    Case "visible"
        If vbCtls(id).kind <> vbkForm Then VBSetN(id, vbpVisible, IIf(b, -1, 0))
    Case "enabled": VBSetN(id, vbpEnabled, IIf(b, -1, 0))
    Case "fontbold"
        If (vbCtls(id).bold <> 0) <> (b <> 0) Then VBSetN(id, vbpFontBold, IIf(b, -1, 0))
    Case "fontitalic"
        If (vbCtls(id).italic <> 0) <> (b <> 0) Then VBSetN(id, vbpFontItalic, IIf(b, -1, 0))
    Case "checked"
        Select Case vbCtls(id).kind
        Case vbkCheckBox: VBSetN(id, vbpValue, IIf(b, 1, 0))
        Case vbkOption: VBSetN(id, vbpValue, IIf(b, -1, 0))
        Case vbkMenu: VBSetN(id, vbpChecked, IIf(b, -1, 0))
        End Select
    End Select
    vbFxQuiet -= 1
End Sub

Private Function VBFxTextGet(ByVal id As Long) As String
    Select Case vbCtls(id).kind
    Case vbkTimer, vbkMenu, vbkDlgOpen To vbkDlgFolder: Return vbCtls(id).text
    End Select
    Return VBGetS(id, vbpText)
End Function

Private Sub VBFxTextSet(ByVal id As Long, ByRef s As String)
    vbFxQuiet += 1
    Select Case vbCtls(id).kind
    Case vbkListBox, vbkTab, vbkTimer, vbkDlgOpen To vbkDlgFolder
        vbCtls(id).text = s
    Case Else
        VBSetS(id, vbpText, s)
    End Select
    vbFxQuiet -= 1
End Sub

' a property as text (visual states save it): numbers, True / False, #rrggbb ("" = default colour), text
Private Function VBFxGetV(ByVal id As Long, ByRef p As String) As String
    Select Case VBFxPType(p)
    Case VBFXP_COLOR
        Dim own As Long = IIf(LCase(p) = "forecolor", vbCtls(id).fore, vbCtls(id).back)
        If own < 0 Then Return ""
        Return VBFxHex(own)
    Case VBFXP_BOOL
        If VBFxBoolGet(id, p) Then Return "True"
        Return "False"
    Case VBFXP_TEXT
        Return VBFxTextGet(id)
    End Select
    Return VBFxNumStr(VBFxNumGet(id, p))
End Function

Private Sub VBFxSetV(ByVal id As Long, ByRef p As String, ByRef v As String)
    Select Case VBFxPType(p)
    Case VBFXP_COLOR
        VBFxColorSet(id, LCase(p) = "forecolor", IIf(Len(Trim(v)) = 0, -1, VBFxColorOf(v)))
    Case VBFXP_BOOL
        VBFxBoolSet(id, p, VBFxTrue(v))
    Case VBFXP_TEXT
        VBFxTextSet(id, v)
    Case Else
        VBFxNumSet(id, p, Val(v))
    End Select
End Sub

' ------------------------------------------------------------------------------ storyboards
Private Sub VBFxForget(ByVal i As Long)
    For t As Long = vbFxS(i).tr0 To vbFxS(i).tr0 + vbFxS(i).ntr - 1
        vbFxT(t).sText = ""
        For j As Long = vbFxT(t).k0 To vbFxT(t).k0 + vbFxT(t).nk - 1
            vbFxK(j).rs = ""
        Next
    Next
    vbFxS(i).saved = 0
End Sub

' the values at Begin; relative keys made absolute against them (_Storyboard._remember)
Private Sub VBFxRemember(ByVal i As Long)
    If vbFxS(i).saved Then Exit Sub
    vbFxS(i).saved = -1
    vbFxS(i).hasPl0 = 0
    Dim tid As Long = vbFxS(i).tid
    Dim sw As Double = VBFxNumGet(tid, "Width")
    Dim sh As Double = VBFxNumGet(tid, "Height")
    For t As Long = vbFxS(i).tr0 To vbFxS(i).tr0 + vbFxS(i).ntr - 1
        Dim prop As String = vbFxT(t).prop
        vbFxT(t).lastBool = -2
        If VBFxIsCtl(tid) AndAlso VBFxGeo(prop) AndAlso vbFxS(i).hasPl0 = 0 Then
            vbFxS(i).pl0 = vbCtls(tid).pl                       ' Stop gives Anchor / Dock back
            vbFxS(i).hasPl0 = -1
        End If
        Select Case vbFxT(t).pt
        Case VBFXP_COLOR
            vbFxT(t).sNum = VBFxColorGet(tid, prop)
            vbFxT(t).sOwn = (IIf(LCase(prop) = "forecolor", vbCtls(tid).fore, vbCtls(tid).back) >= 0)
        Case VBFXP_BOOL: vbFxT(t).sNum = VBFxBoolGet(tid, prop)
        Case VBFXP_TEXT: vbFxT(t).sText = VBFxTextGet(tid)
        Case Else: vbFxT(t).sNum = VBFxNumGet(tid, prop)
        End Select
        For j As Long = vbFxT(t).k0 To vbFxT(t).k0 + vbFxT(t).nk - 1
            vbFxK(j).rs = ""
            Select Case vbFxK(j).kind
            Case VBFXK_PARENT
                If vbFxT(t).pt = VBFXP_COLOR Then vbFxK(j).rv = VBFxParentColor(tid) Else vbFxK(j).rv = vbFxT(t).sNum
            Case VBFXK_REL
                If vbFxT(t).pt = VBFXP_NUM Then
                    Dim v As Double = vbFxT(t).sNum * vbFxK(j).a + vbFxK(j).b
                    If vbFxK(j).ofs = 1 Then v += vbFxK(j).d * sw
                    If vbFxK(j).ofs = 2 Then v += vbFxK(j).d * sh
                    If VBFxIntProp(prop) Then v = Int(v + 0.5)
                    If LCase(prop) = "opacity" Then
                        If v < 0 Then v = 0
                        If v > 1 Then v = 1
                    End If
                    vbFxK(j).rv = v
                ElseIf vbFxT(t).pt = VBFXP_TEXT Then
                    vbFxK(j).rs = vbFxT(t).sText
                Else
                    vbFxK(j).rv = vbFxT(t).sNum                  ' colours / bools keep their start value
                End If
            Case VBFXK_REVEAL
                Dim fr As Double = vbFxK(j).a
                If fr < 0 Then fr = 0
                If fr > 1 Then fr = 1
                vbFxK(j).rs = VBFxULeft(vbFxT(t).sText, CLng(Int(VBFxULen(vbFxT(t).sText) * fr + 0.5)))
            Case VBFXK_TEXT
                vbFxK(j).rs = vbFxK(j).s
            Case Else
                vbFxK(j).rv = vbFxK(j).a                         ' n / c / b
            End Select
        Next
    Next
End Sub

Private Function VBFxMixCol(ByVal a As Long, ByVal b As Long, ByVal fr As Double) As Long
    If fr >= 1 Then Return b
    Dim As Long r = VBFxRound((a And &hFF) + ((b And &hFF) - (a And &hFF)) * fr)
    Dim As Long g = VBFxRound(((a Shr 8) And &hFF) + (((b Shr 8) And &hFF) - ((a Shr 8) And &hFF)) * fr)
    Dim As Long bl = VBFxRound(((a Shr 16) And &hFF) + (((b Shr 16) And &hFF) - ((a Shr 16) And &hFF)) * fr)
    If r < 0 Then r = 0
    If r > 255 Then r = 255
    If g < 0 Then g = 0
    If g > 255 Then g = 255
    If bl < 0 Then bl = 0
    If bl > 255 Then bl = 255
    Return VBFxBGR(r, g, bl)
End Function

' text between two keys: typed / erased when one is a prefix of the other, else discrete
Private Function VBFxMixText(ByRef a As String, ByRef b As String, ByVal fr As Double) As String
    If fr <= 0 Then Return a
    Dim As Long la = VBFxULen(a), lb = VBFxULen(b)
    If (la <= lb AndAlso Left(b, Len(a)) = a) OrElse (lb < la AndAlso Left(a, Len(b)) = b) Then
        Dim ff As Double = fr
        If ff > 1 Then ff = 1
        Dim x As Double = la + (lb - la) * ff
        Dim n As Long = IIf(x < 0, 0, CLng(Int(x + 0.5)))
        If la > lb Then Return VBFxULeft(a, n)
        Return VBFxULeft(b, n)
    End If
    If fr >= 1 Then Return b
    Return a
End Function

Private Sub VBFxApply(ByVal i As Long, ByVal ms As Double)
    vbFxS(i).posMs = ms
    Dim tid As Long = vbFxS(i).tid
    For t As Long = vbFxS(i).tr0 To vbFxS(i).tr0 + vbFxS(i).ntr - 1
        Dim nk As Long = vbFxT(t).nk
        If nk = 0 Then Continue For
        Dim k0 As Long = vbFxT(t).k0
        Dim As Double v0, v1, fr = 1
        Dim As String s0, s1
        Dim lead As Long = (vbFxK(k0).ms > 0)        ' the start value is the implicit key at 0
        If ms <= IIf(lead, 0, vbFxK(k0).ms) Then
            If lead Then
                v0 = vbFxT(t).sNum: s0 = vbFxT(t).sText
            Else
                v0 = vbFxK(k0).rv: s0 = vbFxK(k0).rs
            End If
            v1 = v0: s1 = s0: fr = 1
        Else
            Dim j1 As Long = -1
            For j As Long = k0 To k0 + nk - 1
                If ms <= vbFxK(j).ms Then
                    j1 = j
                    Exit For
                End If
            Next
            If j1 < 0 Then
                j1 = k0 + nk - 1
                v0 = vbFxK(j1).rv: s0 = vbFxK(j1).rs
                v1 = v0: s1 = s0: fr = 1
            Else
                Dim tm0 As Long = 0
                If j1 > k0 Then
                    tm0 = vbFxK(j1 - 1).ms: v0 = vbFxK(j1 - 1).rv: s0 = vbFxK(j1 - 1).rs
                Else
                    v0 = vbFxT(t).sNum: s0 = vbFxT(t).sText
                End If
                v1 = vbFxK(j1).rv: s1 = vbFxK(j1).rs
                If vbFxK(j1).ms > tm0 Then fr = (ms - tm0) / (vbFxK(j1).ms - tm0) Else fr = 1
                fr = VBFxEase(fr, vbFxK(j1).ease)
            End If
        End If
        Dim prop As String = vbFxT(t).prop
        Select Case vbFxT(t).pt
        Case VBFXP_COLOR
            Dim col As Long
            If fr <= 0 Then col = CLng(v0) Else col = VBFxMixCol(CLng(v0), CLng(v1), fr)
            VBFxColorSet(tid, LCase(prop) = "forecolor", col)
        Case VBFXP_BOOL
            Dim b As Long = IIf(fr >= 1, v1 <> 0, v0 <> 0)
            If vbFxT(t).lastBool = b AndAlso LCase(prop) = "visible" Then Continue For   ' re-showing every frame re-places
            vbFxT(t).lastBool = b
            VBFxBoolSet(tid, prop, b)
        Case VBFXP_TEXT
            Dim w As String = VBFxMixText(s0, s1, fr)
            If VBFxTextGet(tid) <> w Then VBFxTextSet(tid, w)
        Case Else
            If fr <= 0 Then VBFxNumSet(tid, prop, v0) Else VBFxNumSet(tid, prop, v0 + (v1 - v0) * fr)
        End Select
    Next
End Sub

Private Sub VBFxFrame(ByVal f As Long)
    Dim anyP As Long = 0
    For i As Long = vbFxF(f).s0 To vbFxF(f).s0 + vbFxF(f).ns - 1
        If vbFxS(i).playing Then anyP = -1
    Next
    Dim h As HWND = vbCtls(f).hwnd
    If anyP AndAlso vbFxF(f).frameOn = 0 AndAlso h <> 0 Then
        SetTimer(h, VBFX_FRAME, 15, 0)
        vbFxF(f).frameOn = -1
    ElseIf anyP = 0 AndAlso vbFxF(f).frameOn Then
        If h Then KillTimer(h, VBFX_FRAME)
        vbFxF(f).frameOn = 0
    End If
End Sub

Private Sub VBFxStop(ByVal i As Long)
    Dim f As Long = vbFxS(i).frm
    Dim tid As Long = vbFxS(i).tid
    vbFxS(i).playing = 0
    vbFxS(i).rev = 0
    vbFxS(i).posMs = 0
    If vbFxS(i).pending Then
        If vbCtls(f).hwnd Then KillTimer(vbCtls(f).hwnd, VBFX_DELAY + i)
        vbFxS(i).pending = 0
    End If
    If vbFxS(i).saved Then
        Dim isCtl As Long = VBFxIsCtl(tid)
        For t As Long = vbFxS(i).tr0 To vbFxS(i).tr0 + vbFxS(i).ntr - 1
            Dim prop As String = vbFxT(t).prop
            If isCtl AndAlso VBFxGeo(prop) AndAlso vbFxS(i).hasPl0 Then Continue For
            Select Case vbFxT(t).pt
            Case VBFXP_COLOR: VBFxColorSet(tid, LCase(prop) = "forecolor", IIf(vbFxT(t).sOwn, CLng(vbFxT(t).sNum), -1))
            Case VBFXP_BOOL: VBFxBoolSet(tid, prop, vbFxT(t).sNum <> 0)
            Case VBFXP_TEXT: VBFxTextSet(tid, vbFxT(t).sText)
            Case Else: VBFxNumSet(tid, prop, vbFxT(t).sNum)
            End Select
        Next
        If isCtl AndAlso vbFxS(i).hasPl0 Then                ' Anchor / Dock take the control back
            vbCtls(tid).pl = vbFxS(i).pl0
            If vbCtls(f).hwnd Then
                VBRelayout(tid)
                If vbCtls(tid).inner Then VBLayoutChildren(tid, f)
            End If
        End If
        VBFxForget(i)
    End If
    VBFxFrame(f)
End Sub

Private Sub VBFxBeginNow(ByVal i As Long)
    VBFxRemember(i)
    vbFxS(i).playing = -1
    vbFxS(i).rev = 0
    vbFxS(i).t0 = VBFxNow()
    VBFxApply(i, 0)
    VBFxFrame(vbFxS(i).frm)
End Sub

Private Function VBFxSameNamePlaying(ByVal i As Long) As Long
    Dim f As Long = vbFxS(i).frm
    Dim l As String = LCase(vbFxS(i).fx)
    For j As Long = vbFxF(f).s0 To vbFxF(f).s0 + vbFxF(f).ns - 1
        If j <> i AndAlso vbFxS(j).playing AndAlso LCase(vbFxS(j).fx) = l Then Return -1
    Next
    Return 0
End Function

' the end of a storyboard: hide / give back / chains / <name>_Completed (_RadFx._done + Completed)
Private Sub VBFxCompleted(ByVal i As Long)
    Dim f As Long = vbFxS(i).frm
    vbFxS(i).playing = 0
    If vbFxS(i).hiding Then
        vbFxS(i).hiding = 0
        VBFxStop(i)
        VBFxBoolSet(vbFxS(i).tid, "Visible", 0)
    ElseIf vbFxS(i).restoreIt Then
        VBFxStop(i)
    End If
    Dim l As String = LCase(vbFxS(i).fx)
    For j As Long = vbFxF(f).s0 To vbFxF(f).s0 + vbFxF(f).ns - 1
        If vbFxS(j).trig = VBFXT_AFTER AndAlso LCase(vbFxS(j).after) = l Then VBFxBeginSb(j)
    Next
    If VBFxSameNamePlaying(i) = 0 AndAlso Left(vbFxS(i).fx, 4) <> "_fx_" AndAlso vbCtls(f).hwnd <> 0 Then
        PostMessageW(vbCtls(f).hwnd, VB_WM_FX, 1, i)
    End If
    VBFxFrame(f)
End Sub

Private Sub VBFxFinish(ByVal i As Long)
    VBFxRemember(i)
    VBFxApply(i, IIf(vbFxS(i).autorev, 0, vbFxS(i).dur))
    VBFxCompleted(i)
End Sub

Private Sub VBFxTick(ByVal i As Long)
    If vbFxS(i).playing = 0 Then Exit Sub
    Dim ms As Double = VBFxNow() - vbFxS(i).t0
    Dim dur As Double = vbFxS(i).dur
    If vbFxS(i).rev Then
        Dim back As Double = dur - ms
        If back <= 0 Then
            VBFxStop(i)
            Exit Sub
        End If
        VBFxApply(i, back)
        Exit Sub
    End If
    Dim span As Double = dur * IIf(vbFxS(i).autorev, 2, 1)
    Dim total As Double = span * vbFxS(i).cnt
    Dim done As Long = 0
    If span <= 0 Then
        ms = 0: done = -1
    ElseIf vbFxS(i).forever Then
        If ms >= span Then
            vbFxS(i).t0 += Int(ms / span) * span
            ms = ms - Int(ms / span) * span
        End If
    ElseIf ms >= total Then
        ms = span: done = -1
    Else
        ms = ms - Int(ms / span) * span
    End If
    If ms <= dur Then VBFxApply(i, ms) Else VBFxApply(i, span - ms)
    If done Then VBFxCompleted(i)
End Sub

' _RadFx.Begin: reduced motion jumps to the end; a delay shows the first frame, then waits
Private Sub VBFxBeginSb(ByVal i As Long)
    Dim f As Long = vbFxS(i).frm
    If vbFxF(f).reduced Then
        If vbFxS(i).playing = 0 Then VBFxForget(i)
        VBFxFinish(i)
        Exit Sub
    End If
    If vbFxS(i).playing = 0 Then VBFxForget(i)            ' start from the values the control has now
    If vbFxS(i).delay > 0 AndAlso vbCtls(f).hwnd <> 0 Then
        VBFxRemember(i)
        VBFxApply(i, 0)
        vbFxS(i).pending = -1
        SetTimer(vbCtls(f).hwnd, VBFX_DELAY + i, vbFxS(i).delay, 0)
    Else
        VBFxBeginNow(i)
    End If
End Sub

Private Sub VBFxReverse(ByVal i As Long)
    Dim f As Long = vbFxS(i).frm
    If vbFxS(i).pending Then
        If vbCtls(f).hwnd Then KillTimer(vbCtls(f).hwnd, VBFX_DELAY + i)
        vbFxS(i).pending = 0
    End If
    If vbFxF(f).reduced Then
        VBFxStop(i)
        Exit Sub
    End If
    If vbFxS(i).saved = 0 Then Exit Sub
    vbFxS(i).playing = -1
    vbFxS(i).rev = -1
    Dim p As Double = vbFxS(i).posMs
    If p > vbFxS(i).dur Then p = vbFxS(i).dur
    vbFxS(i).t0 = VBFxNow() - (vbFxS(i).dur - p)
    VBFxFrame(f)
End Sub

Private Function VBFxByName(ByVal f As Long, ByRef nm As String, ByVal stopIt As Long) As Long
    If VBFxHas(f) = 0 Then Return 0
    If vbCtls(f).loaded = 0 Then VBFormLoad(f)
    Dim As String l = LCase(nm), alt = "_fx_" & LCase(nm)
    Dim n As Long = 0
    For i As Long = vbFxF(f).s0 To vbFxF(f).s0 + vbFxF(f).ns - 1
        Dim s As String = LCase(vbFxS(i).fx)
        If s <> l AndAlso s <> alt Then Continue For
        n += 1
        If stopIt Then
            If vbFxS(i).every Then
                If vbCtls(f).hwnd Then KillTimer(vbCtls(f).hwnd, VBFX_EVERY + i)
                vbFxS(i).every = 0
            End If
            vbFxS(i).hiding = 0
            VBFxStop(i)
        Else
            VBFxBeginSb(i)
        End If
    Next
    Return n
End Function

' ------------------------------------------------------------------------------ visual states
Private Function VBFxHasStates(ByVal f As Long, ByVal cid As Long) As Long
    For q As Long = vbFxF(f).q0 To vbFxF(f).q0 + vbFxF(f).nq - 1
        If vbFxQs(q).cid = cid Then Return -1
    Next
    Return 0
End Function

Private Function VBFxWantAdd(ByVal f As Long, ByVal cid As Long, ByRef state As String, wp() As String, wv() As String, ByVal n As Long) As Long
    Dim ls As String = LCase(state)
    For q As Long = vbFxF(f).q0 To vbFxF(f).q0 + vbFxF(f).nq - 1
        If vbFxQs(q).cid <> cid OrElse LCase(vbFxQs(q).state) <> ls Then Continue For
        Dim j As Long
        For j = 0 To n - 1
            If LCase(wp(j)) = LCase(vbFxQs(q).prop) Then Exit For
        Next
        If j = n Then
            If n >= 32 Then Continue For
            n += 1
        End If
        wp(j) = vbFxQs(q).prop
        wv(j) = vbFxQs(q).v
    Next
    Return n
End Function

' _VisualStates._update: the wanted overrides of a control (cid = f: the form) are applied, the others given back
Private Sub VBFxVsm(ByVal f As Long, ByVal cid As Long)
    Dim As String wp(0 To 31), wv(0 To 31)
    Dim n As Long = 0
    If Len(vbFxF(f).state) Then n = VBFxWantAdd(f, cid, vbFxF(f).state, wp(), wv(), n)
    If cid <> f Then
        VBFxNeedCtl(cid)
        Dim fl As Long = vbFxFl(cid)
        If Len(vbFxMan(cid)) Then
            n = VBFxWantAdd(f, cid, vbFxMan(cid), wp(), wv(), n)
        ElseIf (fl And VBFXF_DISABLED) Then
            n = VBFxWantAdd(f, cid, "Disabled", wp(), wv(), n)
        Else
            If (fl And VBFXF_FOCUSED) Then n = VBFxWantAdd(f, cid, "Focused", wp(), wv(), n)
            If (fl And VBFXF_OVER) Then n = VBFxWantAdd(f, cid, "MouseOver", wp(), wv(), n)
            If (fl And VBFXF_PRESSED) Then n = VBFxWantAdd(f, cid, "Pressed", wp(), wv(), n)
        End If
    End If
    ' overrides no longer wanted: the saved value back
    Dim a As Long = 0
    While a < vbFxApN
        If vbFxAps(a).cid = cid Then
            Dim j As Long
            For j = 0 To n - 1
                If LCase(wp(j)) = LCase(vbFxAps(a).prop) Then Exit For
            Next
            If j = n Then
                Dim As String pr = vbFxAps(a).prop, sv = vbFxAps(a).saved
                vbFxApN -= 1
                If a < vbFxApN Then vbFxAps(a) = vbFxAps(vbFxApN)
                vbFxAps(vbFxApN).prop = "": vbFxAps(vbFxApN).saved = "": vbFxAps(vbFxApN).v = ""
                If cid = f AndAlso LCase(pr) = "opacity" Then
                    VBFxOpacity(f, Val(sv))
                ElseIf Not (cid <> f AndAlso LCase(pr) = "opacity") Then
                    VBFxSetV(cid, pr, sv)
                End If
                Continue While
            End If
        End If
        a += 1
    Wend
    For j As Long = 0 To n - 1
        Dim ai As Long = -1
        For k As Long = 0 To vbFxApN - 1
            If vbFxAps(k).cid = cid AndAlso LCase(vbFxAps(k).prop) = LCase(wp(j)) Then
                ai = k
                Exit For
            End If
        Next
        If ai >= 0 AndAlso vbFxAps(ai).v = wv(j) Then Continue For
        If ai < 0 Then
            If vbFxApN > UBound(vbFxAps) Then ReDim Preserve vbFxAps(0 To vbFxApN + 16)
            ai = vbFxApN
            vbFxApN += 1
            vbFxAps(ai).cid = cid
            vbFxAps(ai).prop = wp(j)
            vbFxAps(ai).saved = VBFxGetV(cid, wp(j))
        End If
        vbFxAps(ai).v = wv(j)
        If Not (cid <> f AndAlso LCase(wp(j)) = "opacity") Then VBFxSetV(cid, wp(j), wv(j))
    Next
End Sub

Private Sub VBFxFlag(ByVal f As Long, ByVal cid As Long, ByVal flag As Long, ByVal onv As Long)
    If cid = f OrElse VBFxHasStates(f, cid) = 0 Then Exit Sub
    VBFxNeedCtl(cid)
    If ((vbFxFl(cid) And flag) <> 0) = (onv <> 0) Then Exit Sub
    If onv Then vbFxFl(cid) Or= flag Else vbFxFl(cid) And= Not flag
    VBFxVsm(f, cid)
End Sub

Private Function VBFxStateKnown(ByVal f As Long, ByRef s As String) As Long
    Dim l As String = LCase(s)
    For q As Long = vbFxF(f).q0 To vbFxF(f).q0 + vbFxF(f).nq - 1
        If LCase(vbFxQs(q).state) = l Then Return -1
    Next
    Return 0
End Function

' GoToState(state[, control]): cid = f (or 0) for the form, else that control
Private Function VBFxGoToState(ByVal f As Long, ByVal cid As Long, ByRef state As String) As Long
    If VBFxHas(f) = 0 Then Return 0
    If vbCtls(f).loaded = 0 Then VBFormLoad(f)
    Dim s As String = state
    If Len(s) = 0 OrElse LCase(s) = "base" Then s = "Normal"
    If cid > 0 AndAlso cid <> f Then
        VBFxNeedCtl(cid)
        vbFxMan(cid) = IIf(LCase(s) = "normal", "", s)
        VBFxVsm(f, cid)
        Return -1
    End If
    If LCase(s) <> "normal" AndAlso VBFxStateKnown(f, s) = 0 Then Return 0
    vbFxF(f).state = IIf(LCase(s) = "normal", "", s)
    VBFxVsm(f, f)
    For k As Long = 1 To vbCtlCount
        If vbCtls(k).form = f AndAlso k <> f AndAlso VBFxHasStates(f, k) Then VBFxVsm(f, k)
    Next
    Return -1
End Function

Private Function VBFxGoToStateN(ByVal f As Long, ByRef ctl As String, ByRef state As String) As Long
    If Len(ctl) = 0 Then Return VBFxGoToState(f, f, state)
    Dim c As Long = VBFxCtl(f, ctl)
    If c < 0 Then Return 0
    Return VBFxGoToState(f, c, state)
End Function

' ------------------------------------------------------------------------------ layout variants
Private Function VBFxPostureNorm(ByRef s As String) As String
    Dim b As String
    For i As Long = 0 To Len(s) - 1
        Select Case s[i]
        Case Asc("-"), Asc("_"), Asc(" ")
        Case Else: b &= Chr(s[i])
        End Select
    Next
    b = LCase(b)
    Select Case b
    Case "halfopened", "halfopen", "half", "tabletop", "book": Return "half-opened"
    Case "folded", "closed", "fold", "cover": Return "folded"
    Case "flat", "open", "opened": Return "flat"
    End Select
    Return ""
End Function

Private Sub VBFxVEnv(ByRef posture As String, ByRef span As String, ByRef fold As String)
    posture = VBFxPostureNorm(Environ("RADIDE_POSTURE"))
    Dim b As String = LCase(Trim(Environ("RADIDE_SPAN")))
    span = "": fold = ""
    If Len(b) Then span = IIf(b = "dual" OrElse b = "2" OrElse b = "spanned", "dual", "single")
    Dim hg As String = Trim(Environ("RADIDE_HINGE"))
    Dim hx(0 To 3) As Long
    Dim n As Long = 0
    If Len(hg) Then
        Dim p As Long = 1
        While n < 4 AndAlso p <= Len(hg) + 1
            Dim q As Long = InStr(p, hg, ",")
            If q = 0 Then q = Len(hg) + 1
            hx(n) = ValInt(Mid(hg, p, q - p))
            n += 1
            p = q + 1
        Wend
    End If
    If n = 4 AndAlso posture <> "folded" Then fold = IIf(hx(2) <= hx(3), "vertical", "horizontal")
    If Len(span) = 0 Then
        Dim mn As Long = IIf(hx(2) < hx(3), hx(2), hx(3))
        span = IIf(posture = "half-opened" OrElse (n = 4 AndAlso posture <> "folded" AndAlso mn > 0), "dual", "single")
    End If
End Sub

Private Function VBFxMatch(ByVal z As Long, ByVal w As Double, ByVal h As Double, ByRef posture As String, ByRef span As String, ByRef fold As String) As Long
    With vbFxSz(z)
        If .mnw >= 0 AndAlso w < .mnw Then Return 0
        If .mxw >= 0 AndAlso w > .mxw Then Return 0
        If .mnh >= 0 AndAlso h < .mnh Then Return 0
        If .mxh >= 0 AndAlso h > .mxh Then Return 0
        If Len(.orient) AndAlso Left(.orient, 4) <> IIf(w > h, "land", "port") Then Return 0
        If Len(.posture) AndAlso .posture <> posture Then Return 0
        If Len(.span) AndAlso .span <> IIf(Len(span), span, "single") Then Return 0
        If Len(.fold) AndAlso .fold <> fold Then Return 0
    End With
    Return -1
End Function

' _RadVariants.update: which sizes apply; restore the designed values, apply the sizes in order
Private Function VBFxVariants(ByVal f As Long, ByVal notify As Long) As Long
    If VBFxHas(f) = 0 OrElse vbFxF(f).nz = 0 OrElse vbCtls(f).hwnd = 0 Then Return 0
    Dim rc As RECT
    GetClientRect(vbCtls(f).hwnd, @rc)
    Dim As Double cw = VBU(rc.right), ch = VBU(rc.bottom)
    If cw <= 1 OrElse ch <= 1 Then cw = vbCtls(f).pl.w: ch = vbCtls(f).pl.h
    Dim As String posture, span, fold
    VBFxVEnv(posture, span, fold)
    Dim nowS As String
    For z As Long = vbFxF(f).z0 To vbFxF(f).z0 + vbFxF(f).nz - 1
        nowS &= IIf(VBFxMatch(z, cw, ch, posture, span, fold), "1", "0")
    Next
    If vbFxF(f).hasCur AndAlso nowS = vbFxF(f).cur Then Return 0
    Dim first As Long = (vbFxF(f).hasCur = 0)
    vbFxF(f).cur = nowS
    vbFxF(f).hasCur = -1
    vbFxQuiet += 1
    For v As Long = vbFxF(f).l0 To vbFxF(f).l0 + vbFxF(f).nl - 1
        Dim c As Long = vbFxVLs(v).cid
        If vbFxHasBase(c) Then vbCtls(c).pl = vbFxBasePl(c)
    Next
    For v As Long = vbFxF(f).p0 To vbFxF(f).p0 + vbFxF(f).np - 1
        VBFxSetV(vbFxVPs(v).cid, vbFxVPs(v).prop, vbFxVPs(v).base)
    Next
    For z As Long = 0 To vbFxF(f).nz - 1
        If Mid(nowS, z + 1, 1) <> "1" Then Continue For
        Dim zi As Long = vbFxF(f).z0 + z
        For v As Long = vbFxF(f).l0 To vbFxF(f).l0 + vbFxF(f).nl - 1
            If vbFxVLs(v).size = zi Then vbCtls(vbFxVLs(v).cid).pl = vbFxVLs(v).pl
        Next
        For v As Long = vbFxF(f).p0 To vbFxF(f).p0 + vbFxF(f).np - 1
            If vbFxVPs(v).size = zi AndAlso LCase(vbFxVPs(v).prop) <> "visible" Then VBFxSetV(vbFxVPs(v).cid, vbFxVPs(v).prop, vbFxVPs(v).v)
        Next
        For v As Long = vbFxF(f).p0 To vbFxF(f).p0 + vbFxF(f).np - 1
            If vbFxVPs(v).size = zi AndAlso LCase(vbFxVPs(v).prop) = "visible" Then VBFxSetV(vbFxVPs(v).cid, vbFxVPs(v).prop, vbFxVPs(v).v)
        Next
    Next
    vbFxQuiet -= 1
    ' every control placed again from its (designed / variant) Anchor-Dock place, containers first
    For i As Long = 1 To vbCtlCount
        If vbCtls(i).form = f AndAlso i <> f AndAlso vbCtls(i).kind <> vbkMenu AndAlso vbCtls(i).hwnd <> 0 Then VBRelayout(i)
    Next
    If first = 0 AndAlso notify Then PostMessageW(vbCtls(f).hwnd, VB_WM_FX, 2, 0)
    Return -1
End Function

Private Function VBFxCurrentSizes(ByVal f As Long) As String
    If VBFxHas(f) = 0 Then Return ""
    If vbCtls(f).loaded = 0 Then VBFormLoad(f)
    Dim r As String
    For z As Long = 0 To vbFxF(f).nz - 1
        If Mid(vbFxF(f).cur, z + 1, 1) = "1" Then
            If Len(r) Then r &= ","
            r &= vbFxSz(vbFxF(f).z0 + z).id
        End If
    Next
    Return r
End Function

' ------------------------------------------------------------------------------ the VB API
Private Function VBFxBegin(ByVal f As Long, ByRef nm As String) As Long        ' Form.BeginAnimation
    Return VBFxByName(f, nm, 0) > 0
End Function

Private Function VBFxStopAnim(ByVal f As Long, ByRef nm As String) As Long     ' Form.StopAnimation
    Return VBFxByName(f, nm, -1) > 0
End Function

Private Function VBFxApplySizes(ByVal f As Long) As Long                       ' Form.ApplySizeVariants
    If VBFxHas(f) = 0 Then Return 0
    If vbCtls(f).loaded = 0 Then VBFormLoad(f)
    Return VBFxVariants(f, -1)
End Function

Private Function VBFxCurrentState(ByVal f As Long) As String                   ' Form.CurrentState
    If VBFxHas(f) = 0 OrElse Len(vbFxF(f).state) = 0 Then Return "Normal"
    Return vbFxF(f).state
End Function

Private Sub VBFxOnDone(ByVal f As Long, ByRef nm As String, ByVal h As VBHandler)  ' <storyboard>_Completed
    Dim n As Long = UBound(vbFxDones) + 1
    ReDim Preserve vbFxDones(0 To n)
    vbFxDones(n).frm = f
    vbFxDones(n).fx = LCase(nm)
    vbFxDones(n).h = h
End Sub

' ------------------------------------------------------------------------------ records (VBSetupForms)
Private Sub VBFxInstall()
    If vbFxInstalled Then Exit Sub
    vbFxInstalled = -1
    vbFxOnEvent = @VBFxEvent
    vbFxOnSet = @VBFxSetHook
    vbFxOnForm = @VBFxFormHook
End Sub

Private Function VBFxLim(ByRef s As String) As Double
    If Len(Trim(s)) = 0 Then Return -1
    Return Val(s)
End Function

Private Function VBFxTrig(ByRef s As String) As Long
    Select Case LCase(s)
    Case "load": Return VBFXT_LOAD
    Case "click": Return VBFXT_CLICK
    Case "hover": Return VBFXT_HOVER
    Case "timer": Return VBFXT_TIMER
    Case "show": Return VBFXT_SHOW
    Case "hide": Return VBFXT_HIDE
    Case "after": Return VBFXT_AFTER
    End Select
    Return VBFXT_MANUAL
End Function

' one record of form f (after the form's controls are described)
Private Sub VBFxRec(ByVal f As Long, ByRef ln As String)
    VBFxInstall()
    VBFxNeedForm(f)
    Dim fl(0 To 9) As String
    VBFxSplit(ln, fl())
    Dim k As String = fl(0)
    With vbFxF(f)
        If .has = 0 Then
            .has = -1
            .respect = -1
            .s0 = UBound(vbFxS) + 1
            .q0 = UBound(vbFxQs) + 1
            .z0 = UBound(vbFxSz) + 1
            .l0 = UBound(vbFxVLs) + 1
            .p0 = UBound(vbFxVPs) + 1
            vbFxCurSb = -1
        End If
    End With
    Select Case k
    Case "XR"
        vbFxF(f).respect = VBFxTrue(fl(1))
    Case "X"
        vbFxCurSb = -1
        Dim c As Long = VBFxCtl(f, fl(2))
        If c < 0 OrElse vbFxF(f).ns >= 9990 Then Exit Sub
        Dim i As Long = UBound(vbFxS) + 1
        ReDim Preserve vbFxS(0 To i)
        vbFxF(f).ns += 1
        vbFxCurSb = i
        With vbFxS(i)
            .frm = f
            .fx = fl(1)
            .tid = c
            .srcName = fl(2)
            .cnt = ValInt(fl(3))
            If .cnt < 1 Then .cnt = 1
            .forever = (ValInt(fl(4)) <> 0)
            .autorev = (ValInt(fl(5)) <> 0)
            .delay = ValInt(fl(6))
            .restoreIt = (ValInt(fl(7)) <> 0)
            .trig = VBFXT_MANUAL
            .tr0 = UBound(vbFxT) + 1
            .srcId = IIf(Len(fl(2)), c, 0)
        End With
    Case "XT"
        If vbFxCurSb < 0 Then Exit Sub
        With vbFxS(vbFxCurSb)
            .trig = VBFxTrig(fl(1))
            If Len(fl(2)) Then
                .srcName = fl(2)
                Dim sc As Long = VBFxCtl(f, fl(2))
                .srcId = IIf(sc < 0, 0, sc)
            End If
            .interval = ValInt(fl(3))
            .after = fl(4)
            .leave = IIf(LCase(fl(5)) = "stop", 1, IIf(LCase(fl(5)) = "none", 2, 0))
        End With
    Case "K"
        If vbFxCurSb < 0 Then Exit Sub
        Dim i As Long = vbFxCurSb
        Dim t As Long = -1
        If vbFxS(i).ntr > 0 Then t = vbFxS(i).tr0 + vbFxS(i).ntr - 1
        If t < 0 OrElse LCase(vbFxT(IIf(t < 0, 0, t)).prop) <> LCase(fl(1)) Then
            t = UBound(vbFxT) + 1
            ReDim Preserve vbFxT(0 To t)
            vbFxS(i).ntr += 1
            vbFxT(t).prop = fl(1)
            vbFxT(t).pt = VBFxPType(fl(1))
            vbFxT(t).k0 = UBound(vbFxK) + 1
            vbFxT(t).lastBool = -2
        End If
        Dim j As Long = UBound(vbFxK) + 1
        ReDim Preserve vbFxK(0 To j)
        vbFxT(t).nk += 1
        With vbFxK(j)
            .ms = ValInt(fl(2))
            If .ms > vbFxS(i).dur Then vbFxS(i).dur = .ms
            .ease = VBFxEaseOf(fl(3))
            .a = Val(fl(5))
            .b = Val(fl(6))
            .d = Val(fl(8))
            .ofs = IIf(LCase(fl(7)) = "width", 1, IIf(LCase(fl(7)) = "height", 2, 0))
            Select Case Left(fl(4), 1)
            Case "c": .kind = VBFXK_COLOR: .a = VBFxColorOf(fl(5))
            Case "b": .kind = VBFXK_BOOL: .a = IIf(VBFxTrue(fl(5)), 1, 0)
            Case "s": .kind = VBFXK_TEXT: .s = fl(5)
            Case "r": .kind = VBFXK_REL
            Case "p": .kind = VBFXK_PARENT
            Case "v": .kind = VBFXK_REVEAL
            Case Else: .kind = VBFXK_NUM
            End Select
        End With
    Case "Q"
        Dim c As Long = VBFxCtl(f, fl(1))
        If c < 0 Then Exit Sub
        Dim q As Long = UBound(vbFxQs) + 1
        ReDim Preserve vbFxQs(0 To q)
        vbFxF(f).nq += 1
        vbFxQs(q).cid = c
        vbFxQs(q).state = fl(2)
        vbFxQs(q).prop = fl(3)
        vbFxQs(q).v = fl(4)
    Case "V"
        Dim z As Long = UBound(vbFxSz) + 1
        ReDim Preserve vbFxSz(0 To z)
        vbFxF(f).nz += 1
        With vbFxSz(z)
            .id = fl(1)
            .mnw = VBFxLim(fl(2))
            .mxw = VBFxLim(fl(3))
            .mnh = VBFxLim(fl(4))
            .mxh = VBFxLim(fl(5))
            .orient = LCase(fl(6))
            .posture = VBFxPostureNorm(fl(7))
            .span = LCase(fl(8))
            .fold = LCase(fl(9))
        End With
    Case "VL", "VP"
        Dim c As Long = VBFxCtl(f, fl(2))
        If c < 0 Then Exit Sub
        Dim si As Long = -1
        For z As Long = vbFxF(f).z0 To vbFxF(f).z0 + vbFxF(f).nz - 1
            If LCase(vbFxSz(z).id) = LCase(fl(1)) Then si = z: Exit For
        Next
        If si < 0 Then Exit Sub
        If k = "VL" Then
            If c = f Then Exit Sub
            Dim p(0 To 7) As Single
            Dim As Long n = 0, pp = 1
            Dim s As String = Trim(fl(3)) & " "
            While n < 8 AndAlso pp <= Len(s)
                Dim q As Long = InStr(pp, s, " ")
                If q > pp Then
                    p(n) = Val(Mid(s, pp, q - pp))
                    n += 1
                End If
                pp = q + 1
            Wend
            If n <> 8 Then Exit Sub
            Dim v As Long = UBound(vbFxVLs) + 1
            ReDim Preserve vbFxVLs(0 To v)
            vbFxF(f).nl += 1
            vbFxVLs(v).size = si
            vbFxVLs(v).cid = c
            With vbFxVLs(v).pl
                .x = p(0): .y = p(1): .w = p(2): .h = p(3): .rx = p(4): .ry = p(5): .rw = p(6): .rh = p(7)
            End With
        Else
            Dim v As Long = UBound(vbFxVPs) + 1
            ReDim Preserve vbFxVPs(0 To v)
            vbFxF(f).np += 1
            vbFxVPs(v).size = si
            vbFxVPs(v).cid = c
            vbFxVPs(v).prop = fl(3)
            vbFxVPs(v).v = fl(4)
        End If
    End Select
End Sub

' ------------------------------------------------------------------------------ hooks (vbrt_forms.bi)
' the form was loaded (controls created, before Form_Load)
Private Sub VBFxInit(ByVal f As Long)
    If VBFxHas(f) = 0 Then Exit Sub
    VBFxNeedCtl(vbCtlCount)
    For i As Long = vbFxF(f).s0 To vbFxF(f).s0 + vbFxF(f).ns - 1
        vbFxS(i).playing = 0: vbFxS(i).rev = 0: vbFxS(i).hiding = 0: vbFxS(i).pending = 0: vbFxS(i).every = 0
        VBFxForget(i)
    Next
    With vbFxF(f)
        .started = 0: .frameOn = 0: .state = "": .cur = "": .hasCur = 0: .alphaSet = 0
    End With
    Dim a As Long = 0
    While a < vbFxApN                                    ' overrides of an earlier load are gone
        If vbCtls(vbFxAps(a).cid).form = f Then
            vbFxApN -= 1
            If a < vbFxApN Then vbFxAps(a) = vbFxAps(vbFxApN)
            Continue While
        End If
        a += 1
    Wend
    For i As Long = 1 To vbCtlCount
        If vbCtls(i).form = f Then vbFxFl(i) = 0: vbFxMan(i) = ""
    Next
    For v As Long = vbFxF(f).l0 To vbFxF(f).l0 + vbFxF(f).nl - 1
        Dim c As Long = vbFxVLs(v).cid
        vbFxBasePl(c) = vbCtls(c).pl
        vbFxHasBase(c) = -1
    Next
    For v As Long = vbFxF(f).p0 To vbFxF(f).p0 + vbFxF(f).np - 1
        vbFxVPs(v).base = VBFxGetV(vbFxVPs(v).cid, vbFxVPs(v).prop)
    Next
    vbFxF(f).reduced = vbFxF(f).respect AndAlso VBFxReducedSystem()
    For i As Long = 1 To vbCtlCount                      ' controls that start disabled are in their Disabled state
        If vbCtls(i).form = f AndAlso i <> f AndAlso vbCtls(i).enabled = 0 Then VBFxFlag(f, i, VBFXF_DISABLED, -1)
    Next
    VBFxVariants(f, 0)
End Sub

' the form is shown for the first time (after Form_Load): "On load" begins, "On timer" timers start
Private Sub VBFxStart(ByVal f As Long)
    If VBFxHas(f) = 0 OrElse vbFxF(f).started Then Exit Sub
    vbFxF(f).started = -1
    For i As Long = vbFxF(f).s0 To vbFxF(f).s0 + vbFxF(f).ns - 1
        If vbFxS(i).trig = VBFXT_LOAD Then
            VBFxBeginSb(i)
        ElseIf vbFxS(i).trig = VBFXT_TIMER AndAlso vbFxS(i).interval > 0 Then
            SetTimer(vbCtls(f).hwnd, VBFX_EVERY + i, vbFxS(i).interval, 0)
            vbFxS(i).every = -1
        End If
    Next
End Sub

Private Sub VBFxTimer(ByVal f As Long, ByVal id As WPARAM)
    If VBFxHas(f) = 0 Then
        KillTimer(vbCtls(f).hwnd, id)
        Exit Sub
    End If
    If id = VBFX_FRAME Then
        For i As Long = vbFxF(f).s0 To vbFxF(f).s0 + vbFxF(f).ns - 1
            If vbFxS(i).playing Then VBFxTick(i)
        Next
        VBFxFrame(f)
    ElseIf id >= VBFX_EVERY Then
        Dim i As Long = id - VBFX_EVERY
        If i >= vbFxF(f).s0 AndAlso i < vbFxF(f).s0 + vbFxF(f).ns Then VBFxBeginSb(i) Else KillTimer(vbCtls(f).hwnd, id)
    ElseIf id >= VBFX_DELAY Then
        Dim i As Long = id - VBFX_DELAY
        KillTimer(vbCtls(f).hwnd, id)
        If i >= vbFxF(f).s0 AndAlso i < vbFxF(f).s0 + vbFxF(f).ns Then
            If vbFxS(i).pending Then
                vbFxS(i).pending = 0
                VBFxBeginNow(i)
            End If
        End If
    End If
End Sub

Private Sub VBFxMessage(ByVal f As Long, ByVal what As WPARAM, ByVal arg As LPARAM)
    If what = 2 Then
        VBFire0(f, vbeSizeVariantChanged)
        Exit Sub
    End If
    If arg < 0 OrElse arg > UBound(vbFxS) Then Exit Sub
    Dim l As String = LCase(vbFxS(arg).fx)
    For d As Long = 0 To UBound(vbFxDones)
        If vbFxDones(d).frm = f AndAlso vbFxDones(d).fx = l AndAlso vbFxDones(d).h <> 0 Then
            Dim e As VBEventArgs
            e.index = -1
            vbFireDepth += 1
            vbFxDones(d).h(e)
            vbFireDepth -= 1
            If vbErrPending Then VBUnhandled()
        End If
    Next
End Sub

Private Sub VBFxFormHook(ByVal f As Long, ByVal what As Long, ByVal wp As WPARAM, ByVal lp As LPARAM)
    Select Case what
    Case 1: VBFxInit(f)
    Case 2: VBFxStart(f)
    Case 3: VBFxTimer(f, wp)
    Case 4: VBFxVariants(f, -1)
    Case 5
        If VBFxHas(f) Then
            For i As Long = vbFxF(f).s0 To vbFxF(f).s0 + vbFxF(f).ns - 1
                vbFxS(i).playing = 0: vbFxS(i).pending = 0: vbFxS(i).every = 0
            Next
            vbFxF(f).frameOn = 0
            vbFxF(f).started = 0
        End If
    Case 6: VBFxMessage(f, wp, lp)
    End Select
End Sub

' every event the runtime raises (before the handler): triggers and automatic states
Private Sub VBFxEvent(ByVal id As Long, ByVal ev As Long)
    Dim f As Long = vbCtls(id).form
    If VBFxHas(f) = 0 Then Exit Sub
    If ev = vbeClick OrElse ev = vbeMouseEnter OrElse ev = vbeMouseLeave Then
        For i As Long = vbFxF(f).s0 To vbFxF(f).s0 + vbFxF(f).ns - 1
            If vbFxS(i).srcId <> id Then Continue For
            If vbFxS(i).trig = VBFXT_CLICK AndAlso ev = vbeClick Then
                VBFxBeginSb(i)
            ElseIf vbFxS(i).trig = VBFXT_HOVER AndAlso ev = vbeMouseEnter Then
                VBFxBeginSb(i)
            ElseIf vbFxS(i).trig = VBFXT_HOVER AndAlso ev = vbeMouseLeave Then
                If vbFxS(i).leave = 0 Then
                    VBFxReverse(i)
                ElseIf vbFxS(i).leave = 1 Then
                    vbFxS(i).hiding = 0
                    VBFxStop(i)
                End If
            End If
        Next
    End If
    If id = f Then Exit Sub
    Select Case ev
    Case vbeMouseEnter: VBFxFlag(f, id, VBFXF_OVER, -1)
    Case vbeMouseLeave
        VBFxFlag(f, id, VBFXF_PRESSED, 0)
        VBFxFlag(f, id, VBFXF_OVER, 0)
    Case vbeMouseDown: VBFxFlag(f, id, VBFXF_PRESSED, -1)
    Case vbeMouseUp: VBFxFlag(f, id, VBFXF_PRESSED, 0)
    Case vbeGotFocus: VBFxFlag(f, id, VBFXF_FOCUSED, -1)
    Case vbeLostFocus: VBFxFlag(f, id, VBFXF_FOCUSED, 0)
    End Select
End Sub

' VB code sets .Visible (before) / .Enabled (after): "On show" / "On hide" play (-1 = handled here), Disabled state
Private Function VBFxSetHook(ByVal id As Long, ByVal p As Long, ByVal v As Long) As Long
    Dim f As Long = vbCtls(id).form
    If VBFxHas(f) = 0 OrElse id = f OrElse vbCtls(f).loaded = 0 Then Return 0
    If p = vbpEnabled Then
        VBFxFlag(f, id, VBFXF_DISABLED, v = 0)
        Return 0
    End If
    If p <> vbpVisible Then Return 0
    Dim onv As Long = (v <> 0)
    If onv = (vbCtls(id).visible <> 0) Then Return 0
    Dim n As Long = 0
    Dim want As Long = IIf(onv, VBFXT_SHOW, VBFXT_HIDE)
    For i As Long = vbFxF(f).s0 To vbFxF(f).s0 + vbFxF(f).ns - 1
        If vbFxS(i).tid = id AndAlso vbFxS(i).trig = want Then n += 1
    Next
    If n = 0 Then Return 0
    If onv Then VBFxBoolSet(id, "Visible", -1)
    For i As Long = vbFxF(f).s0 To vbFxF(f).s0 + vbFxF(f).ns - 1
        If vbFxS(i).tid <> id OrElse vbFxS(i).trig <> want Then Continue For
        If onv = 0 Then vbFxS(i).hiding = -1
        VBFxBeginSb(i)
    Next
    Return -1
End Function
